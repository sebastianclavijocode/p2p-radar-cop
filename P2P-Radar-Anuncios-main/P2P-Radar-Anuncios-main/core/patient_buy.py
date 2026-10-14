"""Read-only planning for fixed-price maker buy advertisements."""
import math
from datetime import datetime, timezone, timedelta


def positive(value):
    try:
        value = float(value)
        return value if math.isfinite(value) and value > 0 else None
    except (ValueError, TypeError):
        return None


def history_window(history, method_id, exchange, asset, now, hours=24):
    # The existing bot history is Binance USDT/COP only, keyed by payment method.
    if exchange != 'Binance' or asset != 'USDT':
        return []
    data = history.get(method_id, {})
    if data.get('fiat') != 'COP':
        return []
    points = {}
    for record in data.get('registros', []):
        try:
            stamp = datetime.fromisoformat(record['ts'].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                continue
            stamp = stamp.astimezone(timezone.utc)
            buy = positive(record.get('taker_sell'))  # Other buyers' bids, where I publish a buy ad.
            sell = positive(record.get('taker_buy'))  # Other sellers' asks, possible future resale reference.
            if buy and sell and now-timedelta(hours=hours) <= stamp <= now:
                points[stamp] = {'time':stamp, 'buy':buy, 'sell':sell}
        except (ValueError, TypeError, KeyError):
            continue
    return [points[stamp] for stamp in sorted(points)]


def quantile(values, fraction):
    values = sorted(values)
    position = (len(values)-1)*fraction
    left = int(position)
    right = min(left+1, len(values)-1)
    return values[left]+(values[right]-values[left])*(position-left)


def plan_levels(current_buy, discount_pct, points, now):
    if not positive(current_buy) or not math.isfinite(discount_pct) or not 0 < discount_pct <= 10:
        raise ValueError('Precio o descuento inválido')
    usable = len(points) >= 12 and now-points[-1]['time'] <= timedelta(minutes=30)
    prices = [p['buy'] for p in points] if usable else []
    levels = []
    for name, factor, fraction in [('Cerca del mercado',0.5,0.35),('Intermedia',1,0.20),('Más baja',1.75,0.10)]:
        target = current_buy*(1-discount_pct*factor/100)
        # Round down so the displayed fixed price always stays below the current bid.
        target = math.floor(target*100)/100
        levels.append({'name':name, 'price':target, 'discount':(1-target/current_buy)*100,
                       'historical_reference':quantile(prices,fraction) if prices else None,
                       'observed_pct':100*sum(p<=target for p in prices)/len(prices) if prices else None})
    return levels, usable


def scenario(capital, buy_price, sell_price, buy_fee_pct, sell_fee_pct, extra_cop=0):
    if not all(positive(v) for v in (capital,buy_price,sell_price)):
        raise ValueError('Capital y precios deben ser positivos')
    if not all(math.isfinite(v) and v>=0 for v in (buy_fee_pct,sell_fee_pct,extra_cop)) or sell_fee_pct>=100:
        raise ValueError('Costos inválidos')
    quantity = capital/(buy_price*(1+buy_fee_pct/100))
    proceeds = quantity*sell_price*(1-sell_fee_pct/100)-extra_cop
    return {'quantity':quantity, 'profit':proceeds-capital, 'net_pct':(proceeds/capital-1)*100,
            'breakeven':(capital+extra_cop)/(quantity*(1-sell_fee_pct/100))}


def review(published, target):
    if not positive(published):
        return 'Precio de referencia para tu anuncio', target
    difference = (target/published-1)*100
    if abs(difference) <= 0.10:
        return 'Mantener: tu anuncio está cerca del objetivo', target
    if difference < 0:
        return 'Revisar a la baja: tu anuncio supera el objetivo', target
    return 'Podrías subir hasta el objetivo si priorizas recibir compras; mantenerlo compra más barato', target
