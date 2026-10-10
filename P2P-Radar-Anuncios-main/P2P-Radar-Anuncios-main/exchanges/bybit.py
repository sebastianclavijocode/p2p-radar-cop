"""Bybit official P2P ads API. Read-only, HMAC credentials from server secrets."""
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
_cache = TTLCache(ttl_seconds=30)
EXCHANGE_NOTE = "Bybit P2P requiere una cuenta anunciante y BYBIT_API_KEY / BYBIT_API_SECRET en Secrets."


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
    return all(credentials())


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
            pays = item.get('payments', [])
            ads.append(P2PAd(str(item['id']), 'BUY' if side == '1' else 'SELL', asset, fiat,
                price, minimum, maximum, quantity, [str(x) for x in pays],
                str(item.get('nickName', '')), exchange, raw_data=item))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return ads


def fetch_ads(asset, fiat, trade_type, pay_types=None, rows=10, max_retries=1, merchant_check=True):
    key, secret = credentials()
    if not key or not secret:
        raise RuntimeError(EXCHANGE_NOTE)
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
