import hashlib
import hmac
import json
import pytest
import requests
from exchanges import bybit
from exchanges import live_routes as live


def ad(side='1', asset='BTC', payments=None, tag='VA'):
    return dict(id='1', side=side, tokenId=asset, currencyId='COP', price='100000',
                lastQuantity='0.5', minAmount='1000', maxAmount='50000', payments=payments or ['8'], authTag=[tag])


def test_signed_read_only_request_and_local_filters(monkeypatch):
    bybit._cache.clear()
    monkeypatch.setattr(bybit, 'credentials', lambda:('test-key','test-secret'))
    monkeypatch.setattr(bybit.time, 'time', lambda: 1000)
    def post(url, data, headers, timeout):
        assert url == 'https://api.bybit.com/v5/p2p/item/online'
        assert json.loads(data)['side'] == '1'
        assert headers['X-BAPI-SIGN'] == hmac.new(b'test-secret', ('1000000test-key5000'+data).encode(), hashlib.sha256).hexdigest()
        class Response:
            status_code=200
            def raise_for_status(self): pass
            def json(self): return {'retCode':0,'result':{'items':[ad(),ad(payments=['9']),ad(tag='GA'),ad(asset='USDT'),ad(side='0')]}}
        return Response()
    monkeypatch.setattr(bybit.requests, 'post', post)
    result=bybit.fetch_ads('BTC','COP','BUY',['8'])
    assert len(result)==1 and result[0].asset=='BTC' and result[0].trade_type=='BUY'
    assert result[0].payment_methods==['8']


def test_missing_credentials_does_not_call_api(monkeypatch):
    monkeypatch.setattr(bybit,'credentials',lambda:('',''))
    with pytest.raises(RuntimeError,match='BYBIT_API_KEY'): bybit.fetch_ads('USDT','COP','BUY')


def test_bybit_block_not_empty_market(monkeypatch):
    bybit._cache.clear()
    monkeypatch.setattr(bybit,'credentials',lambda:('key','secret'))
    class Response: status_code=403
    monkeypatch.setattr(bybit.requests,'post',lambda *a,**kw:Response())
    with pytest.raises(RuntimeError,match='HTTP 403'): bybit.fetch_ads('USDT','COP','SELL')


def test_bybit_code_error_does_not_leak_response(monkeypatch):
    bybit._cache.clear()
    monkeypatch.setattr(bybit,'credentials',lambda:('key','secret'))
    class Response:
        status_code=200
        def raise_for_status(self): pass
        def json(self): return {'retCode':10005,'retMsg':'do not display secret'}
    monkeypatch.setattr(bybit.requests,'post',lambda *a,**kw:Response())
    with pytest.raises(RuntimeError,match='sin permisos P2P') as error: bybit.fetch_ads('ETH','COP','SELL')
    assert 'secret' not in str(error.value)


def test_spot_symbol_and_asset_identity(monkeypatch):
    def request(method,url,**kwargs):
        assert kwargs['params']['symbol']=='ETHUSDT'
        return {'asks':[['2000','1']], 'bids':[['1999','1']]}
    monkeypatch.setattr(live,'_request',request)
    edges=live.fetch_spot('Binance',0,'ETH')
    assert edges[0].target==('Binance','ETH')
    assert edges[1].source==('Binance','ETH')
    assert 'ETHUSDT' in edges[0].reference
