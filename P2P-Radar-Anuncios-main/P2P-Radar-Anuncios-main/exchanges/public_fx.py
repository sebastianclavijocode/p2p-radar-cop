"""Public wallet FX references; USD balances are never treated as USDT."""
import math
import time
from concurrent.futures import ThreadPoolExecutor
import requests

GLOBAL66 = 'https://api.global66.com/quote/public'
ASTROPAY = 'https://partners-api.astropay.com/v1/public/exchanges'


def positive(value):
    result=float(value)
    if not math.isfinite(result) or result<=0:
        raise ValueError('Importe o tasa inválidos')
    return result


def global_quote(amount, origin=291, destination=287):
    amount=positive(amount)
    response=requests.get(GLOBAL66,params={'originRoute':origin,'destinationRoute':destination,
        'amount':amount,'way':'origin','product':'EXCHANGE'},timeout=(4,12))
    response.raise_for_status()
    q=response.json()['quoteData']
    expected=('COP','USD') if (origin,destination)==(291,287) else ('USD','COP')
    if (q['originCurrency'],q['destinationCurrency'])!=expected:
        raise ValueError('Monedas inesperadas')
    sent,received=positive(q['originAmount']),positive(q['destinationAmount'])
    if abs(sent-amount)>max(.01,amount*1e-6):
        raise ValueError('La cotización corresponde a otro importe')
    if sent<float(q.get('minOriginAmount',0)) or sent>float(q.get('maxOriginAmount',math.inf)):
        raise ValueError('Importe fuera del rango publicado')
    cost=float(q['totalCost'])
    if not math.isfinite(cost) or cost<0: raise ValueError('Costo inválido')
    return {'sent':sent,'received':received,'cost':cost,'currency':expected[0],
            'rate':received/sent,'observed':time.time()}


def astro_quote(origin='cop',destination='usd'):
    response=requests.post(ASTROPAY,json={'from':origin,'to':destination},timeout=(4,12))
    response.raise_for_status()
    q=response.json()
    if (q['from'].upper(),q['to'].upper())!=(origin.upper(),destination.upper()):
        raise ValueError('Monedas inesperadas')
    return {'rate':positive(q['exchange']),'official':positive(q['official_exchange']),
            'observed':time.time()}


def fetch_references(capital):
    capital=positive(capital)
    # Reverse quote uses a displayed USD amount; never assumes USD = USDT.
    usd_amount=1000.0
    calls=[('Global66',lambda:global_quote(capital),lambda:global_quote(usd_amount,287,291)),
           ('AstroPay',lambda:astro_quote(),lambda:astro_quote('usd','cop'))]
    def fetch(item):
        name,buy,sell=item
        try:
            a,b=buy(),sell()
            return {'Aplicación':name,'Compra USD (COP)':1/a['rate'],
                    'Venta USD (COP)':b['rate'],'COP consultados':capital,
                    'USD compra estimados':capital*a['rate'],
                    'USD consultados venta':usd_amount,
                    'COP venta estimados':usd_amount*b['rate'],
                    'Costo compra':a.get('cost'),'Costo venta USD':b.get('cost'),
                    'timestamp':min(a['observed'],b['observed'])},''
        except (requests.RequestException,ValueError,KeyError,TypeError):
            return None,f'{name}: sin cotización pública disponible en esta consulta'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(fetch,calls))
    return [r for r,e in results if r],[e for r,e in results if e]
