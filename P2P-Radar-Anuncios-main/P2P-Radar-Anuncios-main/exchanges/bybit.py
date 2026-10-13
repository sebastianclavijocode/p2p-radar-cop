"""Read-only Bybit P2P: public ads, or official signed API with credentials."""
import hashlib
import hmac
import json
import os
import time
import math
import requests
from core.cache import TTLCache
from core.models import P2PAd

_ENDPOINT = "https://api.bybit.com/v5/p2p/item/online"
_PUBLIC_ENDPOINT = "https://api2.bybit.com/fiat/otc/item/online"
BYBIT_PAGOS = {"126":"Bancolombia","209":"Nequi","236":"Daviplata","142":"Davivienda",
               "703":"Bre-B","276":"Banco de Bogotá","740":"BBVA","14":"Transferencia bancaria"}
_cache = TTLCache(ttl_seconds=30)
EXCHANGE_NOTE = "Bybit P2P consulta anuncios públicos sin utilizar claves. La disponibilidad depende del servidor y de Bybit."


def credentials():
    key, secret = os.environ.get('BYBIT_API_KEY', ''), os.environ.get('BYBIT_API_SECRET', '')
    if not (key and secret):
        import streamlit as st
        try:
            key = st.secrets.get('BYBIT_API_KEY', '')
            secret = st.secrets.get('BYBIT_API_SECRET', '')
        except (FileNotFoundError, KeyError):
            return '', ''
    return str(key), str(secret)


def is_supported():
    return True


def _parse_ads(items, fiat, asset, exchange='Bybit'):
    ads = []
    for item in items:
        try:
            if item.get('tokenId') != asset or item.get('currencyId') != fiat:
                continue
            side = str(item['side'])
            if side not in ('0', '1'):
                continue
            price, quantity = float(item['price']), float(item['lastQuantity'])
            minimum, maximum = float(item['minAmount']), float(item['maxAmount'])
            if not all(math.isfinite(v) for v in (price,quantity,minimum,maximum)) or price <= 0 or quantity <= 0 or minimum < 0 or maximum < minimum:
                continue
            maximum = min(maximum,price*quantity)
            if maximum < minimum: continue
            pays = item.get('payments', [])
            ads.append(P2PAd(str(item['id']), 'BUY' if side == '1' else 'SELL', asset, fiat,
                price, minimum, maximum, quantity, [str(x) for x in pays],
                str(item.get('nickName', '')), exchange, raw_data=item))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return ads


def fetch_ads(asset, fiat, trade_type, pay_types=None, rows=10, max_retries=1, merchant_check=True, amount=""):
    """The radar uses public ads even when credentials remain saved in Streamlit."""
    return fetch_public_ads(asset, fiat, trade_type, pay_types, rows, merchant_check, amount)


def fetch_signed_ads(asset, fiat, trade_type, pay_types=None, rows=10, max_retries=1, merchant_check=True, amount=""):
    if trade_type not in ("BUY","SELL"):
        raise ValueError("Lado P2P inválido")
    key, secret = credentials()
    if not key or not secret:
        return fetch_public_ads(asset,fiat,trade_type,pay_types,rows,merchant_check,amount)
    if trade_type not in ('BUY', 'SELL'):
        raise ValueError('Lado P2P inválido')
    side = '1' if trade_type == 'BUY' else '0'
    # Cache only public advertisements, partitioned by credential fingerprint.
    fingerprint = hashlib.sha256((key + secret).encode()).hexdigest()
    cache_key = (fingerprint, asset, fiat, side)
    items = _cache.get(cache_key)
    if items is None:
        body = json.dumps({'tokenId':asset, 'currencyId':fiat, 'side':side, 'page':'1', 'size':'300'}, separators=(',', ':'))
        timestamp, window = str(int(time.time()*1000)), '5000'
        signature = hmac.new(secret.encode(), (timestamp+key+window+body).encode(), hashlib.sha256).hexdigest()
        headers = {'X-BAPI-API-KEY':key, 'X-BAPI-TIMESTAMP':timestamp,
                   'X-BAPI-RECV-WINDOW':window, 'X-BAPI-SIGN':signature, 'Content-Type':'application/json'}
        try:
            response = requests.post(_ENDPOINT, data=body, headers=headers, timeout=(4,12))
            if response.status_code == 403:
                raise RuntimeError('Bybit HTTP 403: acceso rechazado desde este servidor. Una clave no elimina restricciones de alojamiento.')
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            raise RuntimeError('Bybit: error de red o HTTP; consulta no disponible.') from None
        except ValueError:
            raise RuntimeError('Bybit: respuesta no válida.') from None
        if not isinstance(data, dict) or str(data.get('retCode')) != '0':
            code = data.get('retCode') if isinstance(data, dict) else None
            reason = {10003:'clave o entorno incorrecto',10004:'firma no válida',10005:'sin permisos P2P',10002:'hora de servidor fuera de ventana',10010:'IP no autorizada'}.get(code,'consulta rechazada; revisa permisos de anunciante')
            raise RuntimeError('Bybit: ' + reason)
        items = data.get('result', {}).get('items')
        if not isinstance(items, list):
            raise RuntimeError('Bybit: lista de anuncios inválida.')
        _cache.set(cache_key, items)
    ads = _parse_ads(items, fiat, asset)
    allowed = set(map(str, pay_types or []))
    ads = [a for a in ads if a.trade_type == trade_type and
           (not allowed or allowed.intersection(a.payment_methods)) and
           (not merchant_check or set(a.raw_data.get('authTag', [])).intersection({'VA','BA'}))]
    ads.sort(key=lambda a:a.price, reverse=trade_type=='SELL')
    return ads[:rows]


def fetch_public_ads(asset='USDT',fiat='COP',trade_type='BUY',pay_types=None,rows=20,merchant_check=True,amount=''):
    if trade_type not in ('BUY','SELL'): raise ValueError('Lado P2P inválido')
    rows=int(rows)
    if not 1<=rows<=300: raise ValueError('Cantidad de anuncios inválida')
    if amount!='' and (not math.isfinite(float(amount)) or float(amount)<=0):
        raise ValueError('Monto inválido')
    side='1' if trade_type=='BUY' else '0'
    payments=sorted(set(map(str,pay_types or [])))
    cache_key=('public',asset,fiat,side,tuple(payments),bool(merchant_check),str(amount),rows)
    items=_cache.get(cache_key)
    if items is None:
        try:
            response=requests.post(_PUBLIC_ENDPOINT,headers={'Content-Type':'application/json','User-Agent':'Mozilla/5.0'},
                json={'tokenId':asset,'currencyId':fiat,'side':side,'payment':payments,'amount':str(amount),
                      'authMaker':bool(merchant_check),'canTrade':False,'page':'1','size':str(rows)},timeout=(4,12))
            if response.status_code==403:
                raise RuntimeError('Bybit público HTTP 403: el servidor no puede consultar anuncios.')
            response.raise_for_status()
            data=response.json()
        except requests.RequestException as exc:
            code=getattr(getattr(exc,'response',None),'status_code',None)
            raise RuntimeError(f'Bybit público: HTTP {code}' if code else 'Bybit público: consulta de red no disponible') from None
        except ValueError:
            raise RuntimeError('Bybit público: respuesta no válida') from None
        if not isinstance(data,dict) or str(data.get('ret_code'))!='0':
            raise RuntimeError('Bybit público: consulta rechazada')
        items=data.get('result',{}).get('items')
        if not isinstance(items,list): raise RuntimeError('Bybit público: lista de anuncios inválida')
        _cache.set(cache_key,items)
    allowed=set(payments)
    ads=[a for a in _parse_ads(items,fiat,asset) if a.trade_type==trade_type and
         (not allowed or allowed.intersection(a.payment_methods)) and
         (not merchant_check or set(a.raw_data.get('authTag',[])).intersection({'VA','BA'})) and
         (amount=='' or a.min_amount<=float(amount)<=a.max_amount)]
    ads.sort(key=lambda a:a.price,reverse=trade_type=='SELL')
    return ads[:rows]
