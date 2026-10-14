from datetime import datetime, timezone, timedelta
import pytest
from core.patient_buy import history_window, plan_levels, scenario, review
from core.preferences import clean_preferences

NOW=datetime(2026,10,14,16,tzinfo=timezone.utc)


def test_history_uses_competing_buyers_not_instant_buy_price_and_correct_identity():
    record={'ts':(NOW-timedelta(minutes=10)).isoformat(),'taker_buy':3200,'taker_sell':3150}
    history={'nequi_cop_custom':{'fiat':'COP','registros':[record,dict(record,ts=(NOW+timedelta(minutes=10)).isoformat()),
                                                               dict(record,ts='2026-10-01T00:00:00Z'),dict(record,ts='bad')]}}
    points=history_window(history,'nequi_cop_custom','Binance','USDT',NOW)
    assert len(points)==1 and points[0]['buy']==3150 and points[0]['sell']==3200
    assert history_window(history,'nequi_cop_custom','Bybit','USDT',NOW)==[]
    assert history_window(history,'nequi_cop_custom','Binance','BTC',NOW)==[]
    assert history_window(history,'other_method','Binance','USDT',NOW)==[]


def test_levels_remain_below_live_bid_even_when_history_is_higher():
    points=[{'time':NOW-timedelta(minutes=i),'buy':3300+i,'sell':3350+i} for i in range(12,0,-1)]
    levels,usable=plan_levels(3150,0.35,points,NOW)
    assert usable and all(p['price']<3150 for p in levels)
    assert levels[0]['price']>=levels[1]['price']>=levels[2]['price']
    assert all(p['observed_pct']==0 for p in levels)


def test_stale_or_sparse_history_does_not_influence_prices_or_show_frequency():
    points=[{'time':NOW-timedelta(hours=1,minutes=i),'buy':1000,'sell':1100} for i in range(12,0,-1)]
    levels,usable=plan_levels(3200,0.5,points,NOW)
    assert not usable and levels[1]['price']==3184
    assert all(p['observed_pct'] is None for p in levels)
    points[0]['time']=NOW
    levels,usable=plan_levels(3200,0.5,points[:1],NOW)
    assert not usable and levels[1]['price']==3184


def test_costs_are_included_in_quantity_break_even_and_adverse_scenario():
    result=scenario(2000000,3153.3,3170,0.25,0.25,500)
    assert result['quantity']==pytest.approx(2000000/(3153.3*1.0025))
    breakeven=scenario(2000000,3153.3,result['breakeven'],0.25,0.25,500)
    assert breakeven['profit']==pytest.approx(0,abs=1e-8)
    assert scenario(2000000,3153.3,3140,0.25,0.25,500)['profit']<0
    assert scenario(2000000,3153.3,3170,0.25,0.25,500)['profit']<scenario(2000000,3153.3,3170,0,0)['profit']


def test_invalid_or_nonfinite_inputs_are_not_price_recommendations():
    with pytest.raises(ValueError):plan_levels(float('nan'),0.35,[],NOW)
    with pytest.raises(ValueError):plan_levels(3200,0,[],NOW)
    with pytest.raises(ValueError):scenario(0,3153,3180,0.25,0.25)
    with pytest.raises(ValueError):scenario(2000000,3153,3180,0.25,100)


def test_review_retains_low_price_option_and_preferences_are_saved_without_secrets():
    assert 'Mantener' in review(3153.3,3154)[0]
    assert 'baja' in review(3200,3153.3)[0]
    assert 'mantenerlo compra más barato' in review(3100,3153.3)[0]
    saved=clean_preferences({'patient_discount':0.35,'patient_published_Binance_nequi_cop_custom':3153.3,'BYBIT_API_SECRET':'secret'})
    assert saved=={'patient_discount':0.35,'patient_published_Binance_nequi_cop_custom':3153.3}


def test_patient_tab_renders_next_to_hold_and_calculates_with_public_quotes(monkeypatch):
    from streamlit.testing.v1 import AppTest
    from core.models import P2PAd
    from exchanges import bybit
    import requests
    def ads(**kw):
        return [P2PAd('test',kw['trade_type'],kw['asset'],kw['fiat'],3200 if kw['trade_type']=='BUY' else 3180,
                      1000,10000000,10000,kw['pay_types'],'Test','Bybit',raw_data={'authTag':['VA']})]
    monkeypatch.setattr(bybit,'fetch_ads',ads)
    class History:
        status_code=200
        def json(self):return {'content':'e30='}  # Empty public history; no network or credentials.
    monkeypatch.setattr(requests,'get',lambda *a,**k:History())
    at=AppTest.from_file('../app.py',default_timeout=15)
    at.session_state['_preferences_loaded']=True
    at.session_state['radar-view']='Radar original · Yo publico'
    at.session_state['cfg-p2p-5b13eac7ed3a']='Bybit'
    at.session_state['cfg-p2p-fiats']=['COP','USD']
    at.run()
    assert not at.exception
    labels=[tab.label for tab in at.tabs]
    assert labels.index('🎯 Compra paciente')==labels.index('🔵 Hold')+1
    assert any(m.label=='Venta mínima para cubrir costos' for m in at.metric)
    assert any('sin claves' in info.value for info in at.info)
