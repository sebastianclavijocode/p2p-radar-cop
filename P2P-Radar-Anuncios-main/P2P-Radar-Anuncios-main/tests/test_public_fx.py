import pytest
from exchanges import public_fx

class Response:
    def __init__(self,data): self.data=data
    def raise_for_status(self): pass
    def json(self): return self.data


def test_global_uses_final_amount_including_cost(monkeypatch):
    q={'originCurrency':'COP','destinationCurrency':'USD','originAmount':5000000,
       'destinationAmount':1543.56,'totalCost':80000,'minOriginAmount':60000,'maxOriginAmount':1e9}
    monkeypatch.setattr(public_fx.requests,'get',lambda *a,**k:Response({'quoteData':q}))
    result=public_fx.global_quote(5000000)
    assert result['rate']==1543.56/5000000
    assert result['cost']==80000
    with pytest.raises(ValueError): public_fx.global_quote(1000)


def test_astro_direction_and_client_spread(monkeypatch):
    monkeypatch.setattr(public_fx.requests,'post',lambda *a,**k:Response({'from':'USD','to':'COP','exchange':3149.7,'official_exchange':3214}))
    assert public_fx.astro_quote('usd','cop')['rate']==3149.7
    with pytest.raises(ValueError): public_fx.astro_quote('cop','usd')


def test_failed_sources_never_create_prices(monkeypatch):
    monkeypatch.setattr(public_fx,'global_quote',lambda *a:(_ for _ in ()).throw(ValueError()))
    monkeypatch.setattr(public_fx,'astro_quote',lambda *a:(_ for _ in ()).throw(ValueError()))
    rows,errors=public_fx.fetch_references(2000000)
    assert rows==[] and len(errors)==2
