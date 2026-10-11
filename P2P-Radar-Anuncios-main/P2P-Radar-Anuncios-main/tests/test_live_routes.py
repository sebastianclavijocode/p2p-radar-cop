import requests
from exchanges import live_routes as live


def test_failed_sources_do_not_become_empty_or_synthetic_success(monkeypatch):
    def unavailable(*args, **kwargs):
        raise requests.ConnectionError('unavailable')
    monkeypatch.setattr(live, '_request', unavailable)
    edges, statuses, received = live.collect({'Bitso':0,'Binance':0,'Bybit':0,'Binance P2P':0}, ('Nequi',))
    assert edges == []
    assert len(statuses) == 8
    assert all(s['Estado'] == 'No disponible' for s in statuses)
    assert received > 0


def test_p2p_api_error_and_empty_market_are_distinct(monkeypatch):
    monkeypatch.setattr(live, '_request', lambda *a, **kw: {'code':'blocked', 'data':[]})
    import pytest
    with pytest.raises(ValueError): live.fetch_p2p('BUY',0,('Nequi',))
    monkeypatch.setattr(live, '_request', lambda *a, **kw: {'code':'000000', 'data':[]})
    assert live.fetch_p2p('BUY',0,('Nequi',)) == []


def test_malformed_p2p_rows_do_not_crash():
    assert live.parse_binance_ads([None,{}, {'adv':None}, {'adv':{'asset':'BTC'}}], 'BUY',0,('Nequi',),1000) == []


def test_okx_four_field_levels_and_timestamp(monkeypatch):
    def request(method, url, **kw):
        assert url == 'https://www.okx.com/api/v5/market/books'
        assert kw['params']['instId'] == 'ETH-USDT'
        return {'code':'0','data':[{'asks':[['2000','3','0','4']], 'bids':[['1999','2','0','3']], 'ts':'1000000'}]}
    monkeypatch.setattr(live,'_request',request)
    buy,sell = live.fetch_spot('OKX',0.1,'ETH')
    assert buy.target == ('OKX','ETH') and sell.target == ('OKX','USDT')
    assert buy.observed == 1000 and buy.levels[0][1] == 3


def test_mexc_market_identity(monkeypatch):
    def request(method,url,**kw):
        assert url == 'https://api.mexc.com/api/v3/depth'
        assert kw['params']['symbol'] == 'SOLUSDT'
        return {'asks':[['100','3']], 'bids':[['99','2']]}
    monkeypatch.setattr(live,'_request',request)
    buy,sell=live.fetch_spot('MEXC',0.1,'SOL')
    assert buy.target == ('MEXC','SOL') and sell.source == ('MEXC','SOL')
