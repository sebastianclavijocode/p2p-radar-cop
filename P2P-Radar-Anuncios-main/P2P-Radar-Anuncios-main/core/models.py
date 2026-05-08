from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
from datetime import datetime


@dataclass
class P2PAd:
    ad_id: str
    trade_type: str           # "BUY" or "SELL" (our perspective)
    asset: str
    fiat: str
    price: float
    min_amount: float
    max_amount: float
    available_amount: float
    payment_methods: List[str]
    advertiser_name: str
    exchange: str
    is_ad: bool = False       # True if detected as promoted/sponsored
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpreadResult:
    exchange: str
    method_id: str
    method_human: str
    method_mapped: str
    fiat: str
    asset: str
    buy_price_effective: Optional[float]     # precio que publico para comprar
    sell_price_effective: Optional[float]    # precio que publico para vender
    spread_gross_pct: Optional[float]
    net_profit_pct: Optional[float]
    capital_min_fiat: Optional[float]        # max(min_buy, min_sell)
    capital_max_fiat: Optional[float]        # min(max_buy, max_sell)
    capital_recommended_fiat: Optional[float]
    capital_recommended_usdt: Optional[float]
    ref_buy_ad: Optional["P2PAd"]
    ref_sell_ad: Optional["P2PAd"]
    buy_ads_count: int
    sell_ads_count: int
    buy_ads_skipped: int
    sell_ads_skipped: int
    status: str   # OK | INCOMPATIBLE_LIMITS | NOT_AVAILABLE | MAPPING_REQUIRED | ERROR | NO_ADS | FILTERED_NET
    error_msg: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    ref_buy_ad_label: str = ""
    ref_sell_ad_label: str = ""
    ads_filtered_buy: bool = False
    ads_filtered_sell: bool = False
    capital_from_market: bool = True   # True = viene de la liquidez del mercado; False = fallback simulado
    fee_exchange_pct: float = 0.0      # comisión maker del exchange aplicada al net profit


METHODS_CATALOG = [
    {"id": "mercado_pago_ars", "human_name": "Mercado Pago",  "fiat": "ARS"},
    {"id": "facebank_usd",     "human_name": "Facebank",      "fiat": "USD"},
    {"id": "dukascopy_eur",    "human_name": "Dukascopy",     "fiat": "EUR"},
    {"id": "zinli_usd",        "human_name": "Zinli",         "fiat": "USD"},
    {"id": "prex_uy_uyu",      "human_name": "Prex Uruguay",  "fiat": "UYU"},
    {"id": "prex_uy_usd",      "human_name": "Prex Uruguay",  "fiat": "USD"},
]
