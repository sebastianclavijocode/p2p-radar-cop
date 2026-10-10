import requests
from exchanges import live_routes as live


def test_failed_sources_do_not_become_empty_or_synthetic_success(monkeypatch):
    def unavailable(*args, **kwargs):
        raise requests.ConnectionError('unavailable')
    monkeypatch.setattr(live, '_request', unavailable)
    edges, statuses, received = live.collect({'Bitso':0,'Binance':0,'Bybit':0,'Binance P2P':0}, ('Nequi',))
    assert edges == []
    assert len(statuses) == 6
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
