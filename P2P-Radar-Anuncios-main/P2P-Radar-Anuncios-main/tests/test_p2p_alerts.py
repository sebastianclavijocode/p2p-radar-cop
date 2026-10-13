from dataclasses import replace
from decimal import Decimal
from core.models import P2PAd
from core.p2p_alerts import best_taker_pair, quote_pair


def ad(price, minimum=1, maximum=10000000, available=10000, name='seller'):
    return P2PAd(name,'BUY','USDT','COP',price,minimum,maximum,available,['Nequi'],name,'Binance')


def test_taker_has_no_maker_percentage_threshold():
    q=best_taker_pair([ad(4000)],[ad(4001)],2000000,fixed_crypto_fee=0)
    assert q and 0 < q['net_pct'] < 0.25 and q['commission_pct']==0
    assert best_taker_pair([ad(4000)],[ad(4000)],2000000,fixed_crypto_fee=0) is None
    assert best_taker_pair([ad(4000)],[ad(4000.01)],2000000) is None


def test_maker_cop_total_commission_net():
    from types import SimpleNamespace
    from core.p2p_alerts import cop_net
    r=SimpleNamespace(fiat='COP',net_profit_pct=0.5,fee_exchange_pct=0.25)
    assert cop_net(r)==0.25
    r.net_profit_pct=0.501
    assert cop_net(r)>0.25


def test_first_ad_unavailable_uses_next_executable_pair():
    bad=ad(3900,minimum=5000000)
    valid=ad(4000,name='executable')
    q=best_taker_pair([bad,valid],[ad(4040)],2000000)
    assert q and q['buy'] is valid
    assert q['net_pct'] < q['gross_pct']


def test_sell_limits_use_actual_sale_not_initial_cop():
    assert best_taker_pair([ad(4000)],[ad(4040,maximum=2000000)],2000000) is None
    q=best_taker_pair([ad(4000)],[ad(4040,minimum=2010000)],2000000)
    assert q and q['sell_amount']>2000000


def test_both_balances_and_minimums_must_cover_exact_capital():
    assert quote_pair(ad(4000,available=499),ad(4040),2000000) is None
    assert quote_pair(ad(4000),ad(4040,available=499),2000000) is None
    assert quote_pair(ad(4000,minimum=2000001),ad(4040),2000000) is None
    assert quote_pair(ad(4000),ad(4040),0) is None
    assert quote_pair(ad(float('nan')),ad(4040),2000000) is None
    assert quote_pair(replace(ad(4000),is_ad=True),ad(4040),2000000) is None


def test_bot_old_configuration_cannot_lower_cop_requirements(monkeypatch):
    import importlib,alert_bot
    monkeypatch.setenv('UMBRAL_PCT','0.15');monkeypatch.setenv('MAKER_FEE_COP','0.25')
    bot=importlib.reload(alert_bot)
    assert bot.UMBRAL_PCT==0.25 and bot.MAKER_FEE_COP==0.50
    q=best_taker_pair([ad(4000)],[ad(4040)],2000000)
    message=bot.build_taker_message({'human_name':'Nequi'},q)
    assert 'Beneficio estimado' in message and 'Costo fijo' in message and 'Capital validado' in message


def test_higher_old_secret_does_not_suppress_requested_quarter_percent(monkeypatch):
    import importlib,alert_bot
    monkeypatch.setenv('UMBRAL_PCT','0.50')
    assert importlib.reload(alert_bot).UMBRAL_PCT==0.25
