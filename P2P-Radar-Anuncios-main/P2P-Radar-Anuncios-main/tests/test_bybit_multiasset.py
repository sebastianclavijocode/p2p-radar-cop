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


def test_payment_groups_never_mix_banks_and_apply_depth_per_method(monkeypatch):
    from core.models import P2PAd
    def quote(name, side, price, pays):
        return P2PAd(name,side,'USDT','COP',price,1000,10000000,10000,pays,name,'Bybit')
    books={'BUY':[quote('bank', 'BUY',3100,['126']),quote('shared','BUY',3200,['209','703']),quote('nequi2','BUY',3210,['209'])],
           'SELL':[quote('nequi','SELL',3300,['209']),quote('bank2','SELL',3000,['126']),quote('unknown','SELL',2990,['999'])]}
    calls=[]
    def fetch(asset,fiat,side,pays,rows,merchant_check):
        calls.append((side,pays,rows,merchant_check))
        return books[side]
    monkeypatch.setattr(bybit,'fetch_ads',fetch)
    catalog,groups=bybit.fetch_payment_groups(rows=1)
    assert calls==[('BUY',[],300,True),('SELL',[],300,True)]
    assert groups['bybit_cop_209']['BUY'][0].ad_id=='shared'
    assert groups['bybit_cop_209']['SELL'][0].ad_id=='nequi'
    assert groups['bybit_cop_126']['BUY'][0].ad_id=='bank'
    assert groups['bybit_cop_126']['SELL'][0].ad_id=='bank2'
    assert groups['bybit_cop_703']['BUY'][0].ad_id=='shared'
    assert groups['bybit_cop_703']['SELL']==[]
    assert next(m for m in catalog if m['id']=='bybit_cop_999')['human_name']=='Bybit · pago ID 999'
    assert groups['bybit_cop_236']=={'BUY':[],'SELL':[]}


@pytest.mark.parametrize('exchange', ['Binance','Bybit'])
def test_radar_only_uses_primary_methods_with_exchange_specific_ids(monkeypatch,exchange):
    import app
    from core.custom_methods import primary_catalog
    from types import SimpleNamespace
    methods=primary_catalog(exchange)
    calls=[]
    def fetch(**kw):
        calls.append(kw)
        return [kw['pay_types'][0]+'-'+kw['trade_type']]
    monkeypatch.setattr(app.EXCHANGES[exchange],'fetch_ads',fetch)
    analyzed=[]
    def analyze(**kw):
        analyzed.append(kw)
        return SimpleNamespace(status='OK',net_profit_pct=1)
    monkeypatch.setattr(app,'analyze_opportunity',analyze)
    excluded=next(m['id'] for m in methods if m['human_name']=='Daviplata')
    args=dict(exchange_name=exchange,asset='USDT',mappings={},is_verified=True,
              publication_mode='match_top',epsilon_fiat=0,epsilon_pct=0,fee_slippage_pct=0,
              exclude_ads=False,ad_threshold_pct=0,capital_cfg={},buffer_pct=0,
              min_net_profit_pct=0,allow_outside_target=True,top_n=10,selected_fiats=['COP','USD'],
              excluded_methods=[excluded],extra_methods=[{'id':'unknown','human_name':'Unknown','fiat':'COP'}])
    results=app.run_queries(**args)
    assert len(results)==len(methods)-1
    assert len(calls)==2*len(results)
    for row in analyzed:
        pid=row['method_mapped']
        assert row['buy_ads']==[pid+'-BUY'] and row['sell_ads']==[pid+'-SELL']
        assert row['method_id']!=excluded
        assert row['method_human'] in {'Bancolombia','Nequi','Llaves Bre-B','Zinli','Facebank'}
    zinli=next(row for row in analyzed if row['method_human']=='Zinli')
    assert zinli['fiat']=='USD'
    assert zinli['method_mapped']==('189' if exchange=='Bybit' else 'Zinli')
    calls.clear()
    args['selected_fiats']=['EUR']
    assert app.run_queries(**args)==[] and calls==[]


def test_primary_catalog_contains_only_four_cop_methods_and_usd_wallets():
    from core.custom_methods import primary_catalog
    for exchange in ('Binance','Bybit'):
        methods=primary_catalog(exchange)
        assert {m['human_name'] for m in methods if m['fiat']=='COP'}=={'Bancolombia','Nequi','Daviplata','Llaves Bre-B'}
        assert all(m['_exchange']==exchange for m in methods)
        assert len({m['id'] for m in methods})==len(methods)
        assert all(m['fiat'] in ('COP','USD') for m in methods)
