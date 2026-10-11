"""Read-only live adapters, isolated from the legacy maker scanner.

No order endpoints, secrets, synthetic quotes, or cached fallback on failure.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from decimal import Decimal
import time
import requests
from core.routes import Edge, number


def _request(method, url, **kwargs):
    response = requests.request(method, url, timeout=(4, 12), **kwargs)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError('Respuesta inesperada')
    return data


def _levels(rows, reverse=False):
    result = tuple(sorted(((number(p), number(q)) for p, q in rows),
                          key=lambda x: x[0], reverse=reverse))
    if not result or any(p <= 0 or q <= 0 for p, q in result):
        raise ValueError('Libro vacío o inválido')
    return result


def market(venue, base, quote, asks, bids, timestamp, reference, fee):
    return [Edge((venue, quote), (venue, base), 'buy', _levels(asks),
                 fee_pct=number(fee), observed=timestamp, label=f'Comprar {base} · spot', reference=reference),
            Edge((venue, base), (venue, quote), 'sell', _levels(bids, True),
                 fee_pct=number(fee), observed=timestamp, label=f'Vender {base} · spot', reference=reference)]


def fetch_bitso(base, quote, fee):
    book = f'{base}_{quote}'.lower()
    url = 'https://api.bitso.com/v3/order_book/'
    data = _request('GET', url, params={'book': book})
    if data.get('success') is not True:
        raise ValueError('Bitso rechazó la consulta')
    data = data['payload']
    timestamp = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')).timestamp()
    return market('Bitso', base, quote,
                  [(r['price'], r['amount']) for r in data['asks']],
                  [(r['price'], r['amount']) for r in data['bids']],
                  timestamp, url + '?book=' + book, fee)


def fetch_spot(venue, fee, base="BTC"):
    symbol = base + "USDT"
    if venue == 'MEXC':
        url = 'https://api.mexc.com/api/v3/depth'
        data = _request('GET', url, params={'symbol': symbol, 'limit': 100})
        return market(venue, base, 'USDT', data['asks'], data['bids'],
                      time.time(), url + '?symbol=' + symbol, fee)
    if venue == 'OKX':
        url = 'https://www.okx.com/api/v5/market/books'
        data = _request('GET', url, params={'instId': base + '-USDT', 'sz': 50})
        if str(data.get('code')) != '0' or not data.get('data'):
            raise ValueError('OKX rechazó la consulta')
        book = data['data'][0]
        return market(venue, base, 'USDT', [r[:2] for r in book['asks']],
                      [r[:2] for r in book['bids']], float(book['ts']) / 1000,
                      url + '?instId=' + base + '-USDT', fee)
    if venue == 'Binance':
        url = 'https://data-api.binance.vision/api/v3/depth'
        data = _request('GET', url, params={'symbol': symbol, 'limit': 100})
        # Binance depth has no source timestamp: timestamp denotes receipt.
        return market(venue, base, 'USDT', data['asks'], data['bids'],
                      time.time(), url + '?symbol=' + symbol + '&limit=100', fee)
    url = 'https://api.bybit.com/v5/market/orderbook'
    data = _request('GET', url, params={'category': 'spot', 'symbol': symbol, 'limit': 50})
    if data.get('retCode') != 0:
        raise ValueError('Bybit rechazó la consulta')
    data = data['result']
    return market('Bybit', base, 'USDT', data['a'], data['b'],
                  float(data['ts']) / 1000, url + '?category=spot&symbol=' + symbol, fee)


def parse_binance_ads(items, side, fee, allowed_methods, timestamp):
    """BUY request means user buys from SELL advertisers; never invert sides."""
    edges = []
    for item in items:
        try:
            ad = item['adv']
            if ad.get('asset') != 'USDT' or ad.get('fiatUnit') != 'COP':
                continue
            methods = [m['identifier'] for m in ad.get('tradeMethods', [])]
            if not allowed_methods or not set(methods).intersection(allowed_methods):
                continue
            price, quantity = number(ad['price']), number(ad['tradableQuantity'])
            lo, hi = number(ad['minSingleTransAmount']), number(ad['dynamicMaxSingleTransAmount'])
            if price <= 0 or quantity <= 0 or lo < 0 or hi < lo:
                continue
            buying = side == 'BUY'
            source, target = (('Binance', 'COP'), ('Binance', 'USDT')) if buying else (('Binance', 'USDT'), ('Binance', 'COP'))
            edges.append(Edge(source, target, 'buy' if buying else 'sell',
                ((price, quantity),), fee_pct=number(fee),
                minimum=lo if buying else lo / price,
                maximum=min(hi, price * quantity) if buying else min(hi / price, quantity),
                observed=timestamp, label=('Comprar' if buying else 'Vender') + ' USDT · P2P · ' + ', '.join(sorted(set(methods).intersection(allowed_methods))),
                reference='Anuncio ' + str(ad.get('advNo', ''))))
        except (KeyError, ValueError, TypeError, AttributeError, ArithmeticError):
            continue
    return edges


def fetch_p2p(side, fee, allowed_methods):
    url = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
    data = _request('POST', url, json={'asset': 'USDT', 'fiat': 'COP',
        'tradeType': side, 'page': 1, 'rows': 20, 'payTypes': list(allowed_methods)})
    if str(data.get('code')) != '000000' or not isinstance(data.get('data'), list):
        raise ValueError('Binance P2P rechazó la consulta')
    return parse_binance_ads(data['data'], side, fee, allowed_methods, time.time())


def collect(fees, methods, include_p2p=True, assets=('BTC',)):
    jobs = [('Bitso USDT/COP', lambda: fetch_bitso('USDT', 'COP', fees['Bitso']))]
    for base in dict.fromkeys(assets):
        if base not in ('BTC', 'ETH', 'SOL', 'USDC'):
            raise ValueError('Cripto no soportada')
        jobs.append((f'Bitso {base}/USDT', lambda base=base: fetch_bitso(base, 'USDT', fees['Bitso'])))
        for venue in ('Binance', 'Bybit', 'OKX', 'MEXC'):
            jobs.append((f'{venue} {base}/USDT', lambda venue=venue, base=base: fetch_spot(venue, fees.get(venue, 0.10), base)))
    if include_p2p and methods:
        for side in ('BUY', 'SELL'):
            jobs.append((f'Binance P2P {side}', lambda side=side: fetch_p2p(side, fees['Binance P2P'], methods)))
    edges, statuses = [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fn): name for name, fn in jobs}
        for future in as_completed(futures):
            name = futures[future]
            try:
                batch = future.result()
                edges.extend(batch)
                statuses.append({'Fuente': name, 'Estado': 'OK' if batch else 'Sin anuncios compatibles',
                                 'Cotizaciones': len(batch), 'Detalle': ''})
            except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError, ArithmeticError) as exc:
                # No raw response, private data or HTML from upstream in UI.
                status = getattr(getattr(exc, 'response', None), 'status_code', None)
                statuses.append({'Fuente': name, 'Estado': 'No disponible', 'Cotizaciones': 0,
                                 'Detalle': f'HTTP {status}' if status else type(exc).__name__})
    return edges, sorted(statuses, key=lambda s: s['Fuente']), time.time()
