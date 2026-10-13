"""Conservative COP alerts based on advertised executable amounts, not maker prices."""
from decimal import Decimal, InvalidOperation
COP_COMMISSION_PCT = Decimal('0.50')
COP_MIN_NET_PCT = Decimal('0.25')

def value(ad,key,default=None):
    return ad.get(key,default) if isinstance(ad,dict) else getattr(ad,key,default)

def number(v):
    n=Decimal(str(v))
    if not n.is_finite():raise ValueError('Non-finite amount')
    return n

def cop_net(result):
    net=number(result.net_profit_pct or 0)
    return float(net-max(Decimal(0),COP_COMMISSION_PCT-number(result.fee_exchange_pct or 0))) if result.fiat=='COP' else float(net)

def quote_pair(buy,sell,capital,commission_pct=0.0,fixed_crypto_fee=0.14):
    """Validate the BUY amount and the different SELL amount after the buy fee.
    The existing fixed fee is split equally between buy and sell.
    API advertisement limits do not establish account/KYC eligibility.
    """
    try:
        capital=number(capital);fee=number(commission_pct);fixed=number(fixed_crypto_fee)
        if capital<=0 or fixed<0 or fee<0:return None
        for ad in (buy,sell):
            if value(ad,'is_ad',False):return None
        if value(buy,'asset')!=value(sell,'asset') or value(buy,'fiat')!='COP' or value(sell,'fiat')!='COP':return None
        bp=number(value(buy,'price'));sp=number(value(sell,'price'))
        if bp<=0 or sp<=0:return None
        quantity=capital/bp;sell_quantity=quantity-fixed/2
        if sell_quantity<=0 or quantity<=fixed:return None
        sell_amount=sell_quantity*sp
        for ad,amount,qty in ((buy,capital,quantity),(sell,sell_amount,sell_quantity)):
            lo=number(value(ad,'min_amount'));hi=number(value(ad,'max_amount'));available=number(value(ad,'available_amount'))
            if lo<0 or hi<lo or available<=0 or not lo<=amount<=hi or qty>available:return None
        gross=(quantity*sp-capital)/capital*100
        profit=(quantity-fixed)*sp-capital-capital*fee/100
        net=profit/capital*100
        return dict(buy=buy,sell=sell,capital=float(capital),quantity=float(quantity),sell_quantity=float(sell_quantity),
                    sell_amount=float(sell_amount),gross_pct=float(gross),net_pct=float(net),profit=float(profit),
                    commission_pct=float(fee),fixed_crypto_fee=float(fixed),_net=net)
    except (InvalidOperation,ValueError,TypeError,ZeroDivisionError):return None

def best_taker_pair(buy_ads,sell_ads,capital,threshold=None,commission_pct=0.0,fixed_crypto_fee=0.14):
    threshold=Decimal(0) if threshold is None else number(threshold)
    feasible=[]
    for buy in buy_ads:
        for sell in sell_ads:
            q=quote_pair(buy,sell,capital,commission_pct,fixed_crypto_fee)
            if q and q['_net']>threshold:feasible.append(q)
    return max(feasible,key=lambda q:q['_net']) if feasible else None
