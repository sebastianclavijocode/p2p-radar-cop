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
    result=bybit.fetch_signed_ads('BTC','COP','BUY',['8'])
    assert len(result)==1 and result[0].asset=='BTC' and result[0].trade_type=='BUY'
    assert result[0].payment_methods==['8']


def test_missing_credentials_uses_public_ads(monkeypatch):
    monkeypatch.setattr(bybit,'credentials',lambda:('',''))
    monkeypatch.setattr(bybit,'fetch_public_ads',lambda *a:['public'])
    assert bybit.fetch_signed_ads('USDT','COP','BUY')==['public']


def test_bybit_block_not_empty_market(monkeypatch):
    bybit._cache.clear()
    monkeypatch.setattr(bybit,'credentials',lambda:('key','secret'))
    class Response: status_code=403
    monkeypatch.setattr(bybit.requests,'post',lambda *a,**kw:Response())
    with pytest.raises(RuntimeError,match='HTTP 403'): bybit.fetch_signed_ads('USDT','COP','SELL')


def test_bybit_code_error_does_not_leak_response(monkeypatch):
    bybit._cache.clear()
    monkeypatch.setattr(bybit,'credentials',lambda:('key','secret'))
    class Response:
        status_code=200
        def raise_for_status(self): pass
        def json(self): return {'retCode':10005,'retMsg':'do not display secret'}
    monkeypatch.setattr(bybit.requests,'post',lambda *a,**kw:Response())
    with pytest.raises(RuntimeError,match='sin permisos P2P') as error: bybit.fetch_signed_ads('ETH','COP','SELL')
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


def test_public_direction_filters_and_inventory_limit(monkeypatch):
    bybit._cache.clear()
    def post(url,json,headers,timeout):
        assert url==bybit._PUBLIC_ENDPOINT
        assert json['side']=='1' and json['payment']==['209']
        assert json['amount']=='2000000' and json['authMaker'] is True
        good=ad(asset='USDT',payments=['209']); good.update(price='3200',lastQuantity='700',minAmount='100000',maxAmount='3000000')
        other=dict(good,id='2',payments=['126'])
        class Response:
            status_code=200
            def raise_for_status(self):pass
            def json(self):return {'ret_code':0,'result':{'items':[good,other]}}
        return Response()
    monkeypatch.setattr(bybit.requests,'post',post)
    ads=bybit.fetch_public_ads('USDT','COP','BUY',['209'],20,True,2000000)
    assert len(ads)==1 and ads[0].trade_type=='BUY'
    assert ads[0].max_amount==2240000


def test_public_rejected_query_is_not_empty_market(monkeypatch):
    bybit._cache.clear()
    class Response:
        status_code=200
        def raise_for_status(self):pass
        def json(self):return {'ret_code':100,'ret_msg':'not shown'}
    monkeypatch.setattr(bybit.requests,'post',lambda *a,**k:Response())
    with pytest.raises(RuntimeError,match='rechazada'):bybit.fetch_public_ads()


def test_radar_always_uses_public_without_reading_credentials(monkeypatch):
    def forbidden():raise AssertionError('The public radar must not read secrets')
    monkeypatch.setattr(bybit,'credentials',forbidden)
    calls=[]
    monkeypatch.setattr(bybit,'fetch_public_ads',lambda *args:calls.append(args) or ['public'])
    assert bybit.fetch_ads('USDT','COP','BUY',[],20,merchant_check=True)==['public']
    assert calls[0][3]==[] and calls[0][2]=='BUY'
