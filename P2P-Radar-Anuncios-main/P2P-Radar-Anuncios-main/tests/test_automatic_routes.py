from core.routes import find_routes
from exchanges.criptoya import automatic_edges


def samples():
    rows=[{'id':'lemoncash','Plataforma':'Lemon Cash','Activo':'USDT','Volumen':1000,'Compra COP':4000,'Venta COP':3990,'timestamp':1000},
          {'id':'okexp2p','Plataforma':'OKX P2P','Activo':'USDT','Volumen':1000,'Compra COP':4401,'Venta COP':4400,'timestamp':1000}]
    fees={'lemoncash':{'USDT':{'ETHEREUM':{'withdraw':1,'time':1000}}},
          'okexp2p':{'USDT':{'ETHEREUM':{'withdraw':1,'time':1000}}}}
    return rows,fees


def test_automatic_estimate_applies_known_withdrawal_fee_without_manual_confirmation():
    rows,fees=samples()
    quotes,transfers=automatic_edges(rows,fees,now=1000)
    assert all(e.indicative for e in quotes+transfers)
    assert all(not e.verified for e in transfers)
    assert find_routes(quotes+transfers,2000000,now=1000)==[]
    routes=find_routes(quotes+transfers,2000000,now=1000,allow_indicative=True)
    assert routes and routes[0].final==2195600
    assert routes[0].profit==195600


def test_missing_old_or_undated_fees_do_not_become_free_transfers():
    rows,fees=samples()
    _,transfers=automatic_edges(rows,{},now=1000)
    assert transfers==[]
    fees['lemoncash']['USDT']['ETHEREUM']['time']=0
    _,transfers=automatic_edges(rows,fees,now=1000)
    assert all(e.source[0]!='Lemon Cash' for e in transfers)
    fees['lemoncash']['USDT']['ETHEREUM']['time']=1000
    fees['lemoncash']['USDT']['ETHEREUM']['withdraw']=0
    _,transfers=automatic_edges(rows,fees,now=1000)
    assert any(e.source[0]=='Lemon Cash' and e.fixed==0 for e in transfers)


def test_queried_volume_limits_and_expired_prices():
    rows,fees=samples()
    quotes,transfers=automatic_edges(rows,fees,now=1000)
    assert find_routes(quotes+transfers,10000000,now=1000,allow_indicative=True)==[]
    quotes,_=automatic_edges(rows,fees,now=1200)
    assert quotes==[]
