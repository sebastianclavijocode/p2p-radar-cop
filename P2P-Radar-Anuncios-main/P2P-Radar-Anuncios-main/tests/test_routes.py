from decimal import Decimal as D
import pytest
from core.routes import Edge, find_routes, number
from exchanges.live_routes import parse_binance_ads

NOW = 1000


def trade(venue, source, target, price, kind='buy', quantity=10000000, **kwargs):
    return Edge((venue, source), (venue, target), kind, ((D(str(price)), D(str(quantity))),), observed=NOW, **kwargs)


def transfer(a, b, asset, fee=0, **kwargs):
    return Edge((a, asset), (b, asset), 'transfer', fixed=D(str(fee)), **kwargs)


def test_orderbook_depth_and_fee():
    edge = Edge(('A','COP'),('A','USDT'),'buy', ((D(4000),D(100)),(D(5000),D(100))), fee_pct=D(1), observed=NOW)
    assert edge.apply(900000, NOW) == D(198)
    with pytest.raises(ValueError, match='Liquidez'):
        edge.apply(900001, NOW)


def test_two_exchanges_costs_and_direction():
    edges = [trade('A','COP','USDT',4000), transfer('A','B','USDT',1),
             trade('B','USDT','COP',4400,'sell', fee_pct=D(1))]
    routes = find_routes(edges, 1000000, cash_cost=10000, now=NOW)
    assert len(routes) == 1
    assert routes[0].profit == D('74644')
    assert routes[0].balances[1] == D(250)
    assert routes[0].venues == ['A', 'B']


def test_three_exchanges_seven_steps():
    edges = [trade('A','COP','USDT',4000), transfer('A','B','USDT'),
             trade('B','USDT','BTC',100), transfer('B','C','BTC'),
             trade('C','BTC','USDT',110,'sell'), transfer('C','A','USDT'),
             trade('A','USDT','COP',4000,'sell')]
    result = find_routes(edges,1000000,now=NOW)
    assert len(result) == 1
    assert result[0].profit == 100000
    assert len(result[0].steps) == 7
    assert find_routes(edges,1000000,max_venues=2,now=NOW) == []


@pytest.mark.parametrize('observed', [0, 909, 1010])
def test_stale_missing_future_quotes(observed):
    edge = trade('A','COP','USDT',4000)
    from dataclasses import replace
    with pytest.raises(ValueError, match='vencida'):
        replace(edge,observed=observed).apply(1000000,NOW)


def test_transfer_must_be_confirmed_and_same_asset():
    with pytest.raises(ValueError): transfer('A','B','USDT',verified=False).apply(10,NOW)
    with pytest.raises(ValueError): transfer('A','B','USDT',11).apply(10,NOW)
    with pytest.raises(ValueError): Edge(('A','BTC'),('B','USDT'),'transfer').apply(10,NOW)


def test_p2p_limits_apply_to_sale_proceeds_not_starting_capital():
    item={'adv':{'asset':'USDT','fiatUnit':'COP','price':'4400','tradableQuantity':'300',
         'minSingleTransAmount':'100000','dynamicMaxSingleTransAmount':'1050000',
         'tradeMethods':[{'identifier':'Nequi'}], 'advNo':'test'}}
    sell=parse_binance_ads([item],'SELL',0,('Nequi',),NOW)[0]
    with pytest.raises(ValueError,match='límites'):
        sell.apply(250,NOW)
    assert sell.apply(200,NOW) == 880000
    buy=parse_binance_ads([item],'BUY',0,('Nequi',),NOW)[0]
    assert buy.source == ('Binance','COP')
    assert buy.apply(440000,NOW) == 100
    assert parse_binance_ads([item],'BUY',0,('Other',),NOW) == []


def test_non_finite_rejected():
    for value in ['NaN', 'Infinity', '-Infinity']:
        with pytest.raises(ValueError): number(value)


def test_no_artificial_three_venue_transfer_chain():
    edges=[trade('A','COP','USDT',4000),transfer('A','B','USDT'),transfer('B','C','USDT'),
           trade('C','USDT','COP',4500,'sell')]
    assert find_routes(edges,1000000,now=NOW) == []


def test_slippage_and_negative_routes_are_not_hidden():
    edges=[trade('A','COP','USDT',4000),transfer('A','B','USDT'),trade('B','USDT','COP',4000,'sell')]
    result=find_routes(edges,1000000,now=NOW,slippage_pct=1)
    assert result[0].final == 980100
    assert result[0].profit == -19900


def test_exclusions_apply_to_intermediate_exchange_and_before_limit():
    edges=[trade('A','COP','USDT',4000),transfer('A','OKX','USDT'),trade('OKX','USDT','COP',4500,'sell'),
           transfer('A','B','USDT'),trade('B','USDT','COP',4400,'sell')]
    result=find_routes(edges,1000000,now=NOW,limit=1,excluded_venues=['OKX'])
    assert len(result)==1 and result[0].venues==['A','B']
    assert find_routes(edges,1000000,now=NOW,excluded_venues=['A'])==[]


def test_triangular_cop_uses_crypto_exit_and_costs():
    from core.routes import strategy
    edges=[trade('A','COP','USDT',4000),trade('A','USDT','BTC',100),
           transfer('A','B','BTC',.1),trade('B','BTC','COP',440000,'sell')]
    result=find_routes(edges,1000000,now=NOW,strategies=['Triangular COP'])
    assert len(result)==1 and strategy(result[0])=='Triangular COP'
    assert result[0].final==1056000
    assert find_routes(edges,1000000,now=NOW,strategies=['Compra y venta directa'])==[]
    assert find_routes(edges,1000000,now=NOW,strategies=[])==[]
