"""
Escaneo automático — detecta spreads en TODOS los métodos de pago disponibles
sin necesidad de configurar un catálogo.

Lógica:
  1. Fetcha top N anuncios BUY y SELL sin filtro de método de pago.
  2. Agrupa por método de pago.
  3. Para cada método con ads en ambos lados llama a analyze_opportunity()
     — exactamente el mismo pipeline que el Feed principal.
  4. Retorna resultados ordenados por net_profit_pct desc.
"""
from typing import Dict, List

from .models import P2PAd, SpreadResult
from .spread import analyze_opportunity


def scan_all_methods(
    buy_ads_raw: List[P2PAd],    # trade_type=BUY: advertisers que VENDEN (yo compro)
    sell_ads_raw: List[P2PAd],   # trade_type=SELL: advertisers que COMPRAN (yo vendo)
    fiat: str,
    asset: str,
    exchange: str,
    fee_exchange_pct: float,
    capital_target_min: float,
    capital_target_max: float,
    capital_simulado: float,
    min_spread_pct: float = 0.0,
    exclude_ads: bool = True,
    ad_threshold_pct: float = 1.5,
) -> List[SpreadResult]:
    """
    Escanea todos los métodos de pago disponibles usando el mismo pipeline
    que analyze_opportunity(). Retorna resultados ordenados por net_profit_pct desc.

    Solo se incluyen resultados con status OK o FILTERED_NET (tienen datos de precio).
    """
    # Agrupar ads por método de pago
    buy_by_method: Dict[str, List[P2PAd]] = {}
    sell_by_method: Dict[str, List[P2PAd]] = {}

    for ad in buy_ads_raw:
        for pm in ad.payment_methods:
            if pm:
                buy_by_method.setdefault(pm, []).append(ad)

    for ad in sell_ads_raw:
        for pm in ad.payment_methods:
            if pm:
                sell_by_method.setdefault(pm, []).append(ad)

    # Métodos con ads en ambos lados
    common = set(buy_by_method.keys()) & set(sell_by_method.keys())

    results: List[SpreadResult] = []
    for pm in common:
        result = analyze_opportunity(
            buy_ads=buy_by_method[pm],
            sell_ads=sell_by_method[pm],
            exchange=exchange,
            method_id=pm,
            method_human=pm,
            method_mapped=pm,
            fiat=fiat,
            asset=asset,
            fee_exchange_pct=fee_exchange_pct,
            fee_slippage_pct=0.0,
            fee_method_pct=0.0,
            fee_method_fixed=0.0,
            publication_mode="match_top",
            epsilon_fiat=0.0,
            epsilon_pct=0.0,
            exclude_ads=exclude_ads,
            ad_threshold_pct=ad_threshold_pct,
            capital_target_min=capital_target_min,
            capital_target_max=capital_target_max,
            capital_simulado=capital_simulado,
            buffer_pct=1.0,
            min_net_profit_pct=min_spread_pct,
            allow_outside_target=True,
        )
        # Solo incluir resultados que tienen datos de precio (OK o bajo umbral)
        if result.status in ("OK", "FILTERED_NET"):
            results.append(result)

    return sorted(
        results,
        key=lambda r: r.net_profit_pct if r.net_profit_pct is not None else -9999,
        reverse=True,
    )
