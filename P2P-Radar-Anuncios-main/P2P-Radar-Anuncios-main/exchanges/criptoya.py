"""Public Colombian comparison quotes and per-network withdrawal fees.

These are indicative aggregate quotes, never order books or execution edges.
"""
import time
import math
import requests
from itertools import permutations
from core.routes import Edge, number

BASE = 'https://criptoya.com/api'
NAMES = {'binancep2p':'Binance P2P', 'bitsoalpha':'Bitso Alpha', 'bitso':'Bitso',
         'okexp2p':'OKX P2P', 'bybitp2p':'Bybit P2P', 'mexcp2p':'MEXC P2P',
         'lemoncash':'Lemon Cash', 'bitgetp2p':'Bitget P2P', 'bingxp2p':'BingX P2P',
         'vitawallet':'Vita Wallet', 'saldo':'Saldo', 'cryptomktpro':'CryptoMarket Pro',
         'cryptomkt':'CryptoMarket', 'buda':'Buda', 'eldoradop2p':'El Dorado P2P',
         'kucoinp2p':'KuCoin P2P', 'ripio':'Ripio', 'belo':'Belo', 'letsbit':"Let’s Bit",
         'buenbit':'Buenbit', 'dolarapp':'ARQ (antes DolarApp)', 'astropay':'AstroPay'}
VENUE_KEYS = {'Binance':'binancep2p', 'Bybit':'bybitp2p', 'OKX':'okexp2p',
              'MEXC':'mexcp2p', 'Bitso':'bitsoalpha'}


def request(path):
    response = requests.get(BASE + '/' + path, timeout=(4,12))
    response.raise_for_status()
    data = response.json()
    if not isinstance(data,dict):
        raise ValueError('Respuesta CriptoYa inválida')
    return data


def parse_quotes(data, asset, volume, now=None):
    now = time.time() if now is None else now
    rows = []
    for key, item in data.items():
        if key not in NAMES or not isinstance(item,dict): continue
        try:
            ask,bid,stamp = map(float,(item['totalAsk'],item['totalBid'],item['time']))
            if not all(math.isfinite(v) for v in (ask,bid,stamp)) or ask<=0 or bid<=0:
                continue
            # Provider refreshes each minute; include a visible 3-minute age ceiling.
            if not -5 <= now-stamp <= 180: continue
            rows.append({'id':key, 'Plataforma':NAMES[key], 'Activo':asset,
                         'Compra COP':ask, 'Venta COP':bid,
                         'Spread %':(bid/ask-1)*100, 'timestamp':stamp,
                         'Volumen':float(volume), 'Fuente':'CriptoYa'})
        except (KeyError,ValueError,TypeError):
            continue
    return sorted(rows,key=lambda r:r['Compra COP'])


def fetch_quotes(asset='USDT', volume=1000):
    if asset not in ('USDT','USDC','BTC','ETH','SOL') or not math.isfinite(float(volume)) or float(volume)<=0:
        raise ValueError('Moneda o volumen inválidos')
    return parse_quotes(request(f'{asset}/COP/{float(volume):g}'),asset,volume)


def fetch_fees():
    return request('fees')


def automatic_edges(rows, fee_data, now=None):
    """Simulation inputs, bounded by queried volume, with known published fees.

    Aggregated quotes omit account/order minimums, bank methods and executable
    depth. Public withdrawal networks do not certify deposit availability.
    All inputs are explicitly indicative and require find_routes opt-in.
    """
    now = time.time() if now is None else now
    reverse={v:k for k,v in VENUE_KEYS.items()}
    quotes=[]
    providers={}
    for row in rows:
        # ARQ's USDc balance is not assumed to be withdrawable on-chain USDC.
        if row['id']=='dolarapp': continue
        venue=reverse.get(row['id'],row['Plataforma'])
        coin=row['Activo']
        providers[venue]=row['id']
        if not -5<=now-row['timestamp']<=180: continue
        volume,ask,bid=map(number,(row['Volumen'],row['Compra COP'],row['Venta COP']))
        if min(volume,ask,bid)<=0: continue
        # totalAsk/totalBid already come from provider totals; do not add spot fees.
        quotes.extend([
            Edge((venue,'COP'),(venue,coin),'buy',((ask,volume),),maximum=ask*volume,
                 observed=row['timestamp'],label=f'Comprar {coin} · CriptoYa · precio indicativo',reference=BASE,indicative=True),
            Edge((venue,coin),(venue,'COP'),'sell',((bid,volume),),maximum=volume,
                 observed=row['timestamp'],label=f'Vender {coin} · CriptoYa · precio indicativo',reference=BASE,indicative=True)])
    # The five spot venues can participate even if only entry/exit has a COP quote.
    providers.update(VENUE_KEYS)
    coins=set(r['Activo'] for r in rows)|{'BTC','ETH','SOL','USDC','USDT'}
    transfers=[]
    for a,b in permutations(providers,2):
        for coin in coins:
            origin=fee_data.get(providers[a],{}).get(coin,{})
            target=fee_data.get(providers[b],{}).get(coin,{})
            if not isinstance(origin,dict) or not isinstance(target,dict): continue
            options=[]
            for chain in set(origin).intersection(target):
                try:
                    fee=number(origin[chain]['withdraw'])
                    stamp=float(origin[chain].get('time',0))
                    # Undated/older fees require manual review and are excluded automatically.
                    if fee>=0 and stamp>0 and -5<=now-stamp<=86400: options.append((fee,chain))
                except (KeyError,TypeError,ValueError,ArithmeticError): continue
            if not options: continue
            fee,chain=min(options)
            transfers.append(Edge((a,coin),(b,coin),'transfer',fixed=fee,verified=False,indicative=True,
                label=f'Transferir {coin} por {chain} · comisión publicada {fee:g} {coin}',
                reference=BASE+'/fees · red de retiro publicada, depósito y mínimos sin verificar'))
    return quotes,transfers
