"""Public Colombian comparison quotes and per-network withdrawal fees.

These are indicative aggregate quotes, never order books or execution edges.
"""
import time
import math
import requests

BASE = 'https://criptoya.com/api'
NAMES = {'binancep2p':'Binance P2P', 'bitsoalpha':'Bitso Alpha', 'bitso':'Bitso',
         'okexp2p':'OKX P2P', 'bybitp2p':'Bybit P2P', 'mexcp2p':'MEXC P2P',
         'lemoncash':'Lemon Cash', 'bitgetp2p':'Bitget P2P', 'bingxp2p':'BingX P2P',
         'vitawallet':'Vita Wallet', 'saldo':'Saldo', 'cryptomktpro':'CryptoMarket Pro',
         'cryptomkt':'CryptoMarket', 'buda':'Buda', 'eldoradop2p':'El Dorado P2P',
         'kucoinp2p':'KuCoin P2P', 'ripio':'Ripio', 'belo':'Belo', 'letsbit':"Let’s Bit",
         'buenbit':'Buenbit', 'dolarapp':'DolarApp'}
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
