import pytest
from exchanges import criptoya
from ui.rulos import default_transfers


def test_total_prices_direction_and_stale_exclusion():
    sample={'okexp2p':{'ask':999,'bid':999,'totalAsk':3200,'totalBid':3210,'time':990},
            'lemoncash':{'totalAsk':3170,'totalBid':3100,'time':990},
            'buda':{'totalAsk':3100,'totalBid':3000,'time':700}}
    rows=criptoya.parse_quotes(sample,'USDT',1000,now=1000)
    assert [r['Plataforma'] for r in rows]==['Lemon Cash','OKX P2P']
    assert rows[1]['Compra COP']==3200 and rows[1]['Venta COP']==3210
    assert rows[1]['Spread %']>0
    assert rows[1]['Volumen']==1000


def test_invalid_and_unavailable_quotes_are_excluded():
    sample={'binancep2p':{'totalAsk':0,'totalBid':1,'time':990},
            'bybitp2p':{'totalAsk':float('inf'),'totalBid':1,'time':990},
            'okexp2p':None, 'mexcp2p':{'totalAsk':1,'totalBid':1,'time':1010}}
    assert criptoya.parse_quotes(sample,'USDT',1000,now=1000)==[]


def test_profiles_choose_shared_network_and_actual_fee_including_zero():
    data={'binancep2p':{'USDT':{'TRON':{'withdraw':1.5,'time':1000},'BSC':{'withdraw':0,'time':0}}},
          'okexp2p':{'USDT':{'TRON':{'withdraw':2.3,'time':1000}}}}
    df=default_transfers(data)
    row=df[(df.Origen=='Binance')&(df.Destino=='OKX')&(df.Activo=='USDT')].iloc[0]
    assert row.Red=='TRON' and row['Comisión en activo']==1.5
    assert row['Mínimo de retiro']==0 and not row.Confirmada
    assert 'CriptoYa' in row.Referencia and 'mínimo inicial 0' in row.Referencia
    data['okexp2p']['USDT']['BSC']={'withdraw':0,'time':0}
    row=default_transfers(data).query("Origen=='Binance' and Destino=='OKX' and Activo=='USDT'").iloc[0]
    assert row.Red=='BSC' and row['Comisión en activo']==0


def test_failed_api_does_not_generate_prices(monkeypatch):
    monkeypatch.setattr(criptoya,'request',lambda path: (_ for _ in ()).throw(ValueError('unavailable')))
    with pytest.raises(ValueError): criptoya.fetch_quotes()
