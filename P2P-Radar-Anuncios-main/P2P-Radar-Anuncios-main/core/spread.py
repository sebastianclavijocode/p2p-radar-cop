"""
Spread/arbitrage analysis with "yo publico" (I publish) model.

Logic:
  - Fetch top-of-book clean prices (non-promoted ads) for BUY and SELL sides.
  - Simulate publishing my own ad at match_top or beat_top prices.
  - Check limit intersection (min/max fiat overlap between both sides).
  - Calculate capital recommendation + buffer.
  - Compute net_profit_pct including all fees.
  - Return SpreadResult with full detail.
"""
import logging
from typing import List, Optional, Tuple

from .models import P2PAd, SpreadResult
from .orderbook import get_top_of_book, get_top_n_clean, weighted_ref_price

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _ad_label(ad: Optional[P2PAd]) -> str:
    if ad is None:
        return "—"
    return f"{ad.advertiser_name[:16]} | {ad.price:,.2f}"


def _make_empty(
    exchange, method_id, method_human, method_mapped, fiat, asset,
    buy_ads, sell_ads, skipped_buy, skipped_sell, filtered_buy, filtered_sell,
    ref_buy, ref_sell, status, error_msg,
    buy_eff=None, sell_eff=None, min_fiat=None, max_fiat=None,
    cap_fiat=None, cap_usdt=None,
) -> SpreadResult:
    return SpreadResult(
        exchange=exchange, method_id=method_id, method_human=method_human,
        method_mapped=method_mapped, fiat=fiat, asset=asset,
        buy_price_effective=buy_eff, sell_price_effective=sell_eff,
        spread_gross_pct=None, net_profit_pct=None,
        capital_min_fiat=min_fiat, capital_max_fiat=max_fiat,
        capital_recommended_fiat=cap_fiat, capital_recommended_usdt=cap_usdt,
        ref_buy_ad=ref_buy, ref_sell_ad=ref_sell,
        buy_ads_count=len(buy_ads), sell_ads_count=len(sell_ads),
        buy_ads_skipped=skipped_buy, sell_ads_skipped=skipped_sell,
        status=status, error_msg=error_msg,
        ref_buy_ad_label=_ad_label(ref_buy),
        ref_sell_ad_label=_ad_label(ref_sell),
        ads_filtered_buy=filtered_buy, ads_filtered_sell=filtered_sell,
    )


# ── limit intersection ────────────────────────────────────────────────────────

def _limit_intersection(
    buy_ad: P2PAd, sell_ad: P2PAd
) -> Tuple[float, float, bool]:
    """
    Returns (min_fiat, max_fiat, compatible).
    buy_ad  = advertiser selling USDT (we buy from them)
    sell_ad = advertiser buying  USDT (we sell to them)
    Both have min_amount/max_amount in fiat.
    """
    lo = max(buy_ad.min_amount, sell_ad.min_amount)
    hi = min(buy_ad.max_amount, sell_ad.max_amount)
    return lo, hi, (lo <= hi and hi > 0)


# ── effective price (yo publico) ──────────────────────────────────────────────

def _effective_price(
    ref_price: float,
    side: str,        # "BUY" | "SELL"  — our side
    mode: str,        # "match_top" | "beat_top"
    epsilon_fiat: float,
    epsilon_pct: float,
) -> float:
    """
    Calculate my publication price.

    BUY  side (I post a buy ad, competing with other buyers):
        - beat_top: offer slightly MORE fiat per USDT → I queue first
        - price_eff = ref + epsilon

    SELL side (I post a sell ad, competing with other sellers):
        - beat_top: ask slightly LESS fiat per USDT → I queue first
        - price_eff = ref - epsilon
    """
    if mode == "match_top":
        return ref_price

    eps = epsilon_fiat if epsilon_fiat > 0 else ref_price * (epsilon_pct / 100.0)
    if side == "BUY":
        return ref_price + eps
    else:
        return max(ref_price - eps, 0.0001)


# ── capital recommendation ────────────────────────────────────────────────────

def _weighted_max_fiat(ads: List[P2PAd], weights: tuple = (0.50, 0.30, 0.20)) -> float:
    """
    Weighted average of max_amount (fiat limit) from top-N ads.
    Same 50/30/20 weighting used for price references.
    Gives a realistic estimate of how much fiat the market can absorb on this side.
    """
    if not ads:
        return 0.0
    used  = ads[: len(weights)]
    ws    = list(weights[: len(used)])
    total = sum(ws)
    ws    = [w / total for w in ws]
    return sum(ad.max_amount * w for ad, w in zip(used, ws))


# ── main analysis function ────────────────────────────────────────────────────

def analyze_opportunity(
    buy_ads: List[P2PAd],
    sell_ads: List[P2PAd],
    exchange: str,
    method_id: str,
    method_human: str,
    method_mapped: str,
    fiat: str,
    asset: str,
    # fees
    fee_exchange_pct: float,
    fee_slippage_pct: float,
    fee_method_pct: float,
    fee_method_fixed: float,
    # publication mode
    publication_mode: str,
    epsilon_fiat: float,
    epsilon_pct: float,
    # ad filtering
    exclude_ads: bool,
    ad_threshold_pct: float,
    # capital
    capital_target_min: float,
    capital_target_max: float,
    capital_simulado: float,
    buffer_pct: float,
    # filters
    min_net_profit_pct: float,
    allow_outside_target: bool,
) -> SpreadResult:

    # ── 1. Top-3 clean ads per side ────────────────────────────────────────────
    #
    # COMPRAR tab (trade_type=BUY):
    #   Advertisers are SELLING USDT here.
    #   We will publish OUR OWN SELL ad here to compete with them.
    #   Sorted ASC → cheapest seller first = top-of-book for our sell reference.
    #
    # VENDER tab (trade_type=SELL):
    #   Advertisers are BUYING USDT here.
    #   We will publish OUR OWN BUY/RECOMPRA ad here to compete with them.
    #   Sorted DESC → highest buyer first = top-of-book for our buy reference.
    #
    top3_comprar = get_top_n_clean(
        buy_ads, "BUY", n=3, exclude_ads=exclude_ads, ad_threshold_pct=ad_threshold_pct
    )
    top3_vender = get_top_n_clean(
        sell_ads, "SELL", n=3, exclude_ads=exclude_ads, ad_threshold_pct=ad_threshold_pct
    )

    # top-1 ads kept for display / limit intersection
    ref_buy_ad  = top3_comprar[0] if top3_comprar else None   # Comprar tab reference
    ref_sell_ad = top3_vender[0]  if top3_vender  else None   # Vender tab reference

    # skipped/filtered counts (reuse get_top_of_book for those stats only)
    _, skip_buy,  filt_buy  = get_top_of_book(
        buy_ads,  "BUY",  exclude_ads=exclude_ads, ad_threshold_pct=ad_threshold_pct
    )
    _, skip_sell, filt_sell = get_top_of_book(
        sell_ads, "SELL", exclude_ads=exclude_ads, ad_threshold_pct=ad_threshold_pct
    )

    if ref_buy_ad is None or ref_sell_ad is None:
        missing = []
        if ref_buy_ad  is None: missing.append(f"Comprar ({len(buy_ads)} ads, {skip_buy} filtrados)")
        if ref_sell_ad is None: missing.append(f"Vender ({len(sell_ads)} ads, {skip_sell} filtrados)")
        return _make_empty(
            exchange, method_id, method_human, method_mapped, fiat, asset,
            buy_ads, sell_ads, skip_buy, skip_sell, filt_buy, filt_sell,
            ref_buy_ad, ref_sell_ad,
            status="NO_ADS",
            error_msg=f"Sin anuncios limpios en: {', '.join(missing)}",
        )

    # ── 2. Weighted reference prices (top-3 ponderado 50/30/20) ───────────────
    #
    # precio_venta_inicial  = ponderado de los 3 mejores en Comprar tab
    # precio_recompra_final = ponderado de los 3 mejores en Vender tab
    #
    # Ponderación: 50% al primero, 30% al segundo, 20% al tercero
    # Si hay menos de 3 se renormaliza automáticamente.
    #
    precio_venta_inicial  = weighted_ref_price(top3_comprar)   # Comprar tab → nuestro precio de VENTA
    precio_recompra_final = weighted_ref_price(top3_vender)    # Vender tab  → nuestro precio de RECOMPRA

    # ── 3. Effective prices (yo publico, con epsilon si beat_top) ─────────────
    #
    # Comprar tab: somos VENDEDORES compitiendo con otros vendedores
    #   → beat_top: precio ligeramente MÁS BAJO para quedar primeros
    # Vender tab: somos COMPRADORES compitiendo con otros compradores
    #   → beat_top: precio ligeramente MÁS ALTO para quedar primeros
    #
    # buy_eff  = precio efectivo de nuestra VENTA (solapa Comprar)
    # sell_eff = precio efectivo de nuestra RECOMPRA (solapa Vender)
    #
    # spread POSITIVO cuando Comprar > Vender → ganamos la diferencia
    #
    buy_eff = _effective_price(
        precio_venta_inicial, "SELL", publication_mode, epsilon_fiat, epsilon_pct
    )
    sell_eff = _effective_price(
        precio_recompra_final, "BUY", publication_mode, epsilon_fiat, epsilon_pct
    )

    # 3. Limit intersection — informativa únicamente.
    # En el modelo "yo publico" los límites de los anuncios de referencia no restringen
    # la operación: vos publicás tus propios anuncios con los límites que quieras.
    lo, hi, compatible = _limit_intersection(ref_buy_ad, ref_sell_ad)

    # 4. Capital recommendation — ponderado 50/30/20 sobre los límites máximos del top-3
    #
    # cap_market_comprar = promedio ponderado de max_amount del top-3 en Comprar tab
    # cap_market_vender  = promedio ponderado de max_amount del top-3 en Vender tab
    # El cuello de botella es el mínimo de ambos lados.
    # Luego se acota por el target_max del usuario.
    #
    cap_market_comprar = _weighted_max_fiat(top3_comprar)
    cap_market_vender  = _weighted_max_fiat(top3_vender)
    cap_market = min(cap_market_comprar, cap_market_vender) if (cap_market_comprar > 0 and cap_market_vender > 0) else capital_simulado

    # Respetar límites del usuario
    cap_fiat = min(cap_market, capital_target_max)
    capital_from_market = True
    if cap_fiat < capital_target_min:
        cap_fiat = capital_simulado   # fallback al simulado si el mercado tiene muy poca liquidez
        capital_from_market = False
    cap_usdt = (cap_fiat / sell_eff) if sell_eff > 0 else None

    # 6. Net profit
    # buy_eff = precio de mi VENTA (Comprar tab), sell_eff = precio de mi COMPRA (Vender tab)
    # ganancia = vendo alto - compro bajo
    spread_gross = (buy_eff - sell_eff) / sell_eff * 100
    fee_total_pct = fee_exchange_pct + fee_slippage_pct + fee_method_pct
    fee_fija_pct = 0.0
    if fee_method_fixed > 0 and cap_fiat and cap_fiat > 0:
        fee_fija_pct = (fee_method_fixed / cap_fiat) * 100
    net_profit = spread_gross - fee_total_pct - fee_fija_pct

    # 7. Net profit filter
    if net_profit < min_net_profit_pct:
        return SpreadResult(
            exchange=exchange, method_id=method_id, method_human=method_human,
            method_mapped=method_mapped, fiat=fiat, asset=asset,
            buy_price_effective=buy_eff, sell_price_effective=sell_eff,
            spread_gross_pct=spread_gross, net_profit_pct=net_profit,
            capital_min_fiat=lo, capital_max_fiat=hi,
            capital_recommended_fiat=cap_fiat, capital_recommended_usdt=cap_usdt,
            ref_buy_ad=ref_buy_ad, ref_sell_ad=ref_sell_ad,
            buy_ads_count=len(buy_ads), sell_ads_count=len(sell_ads),
            buy_ads_skipped=skip_buy, sell_ads_skipped=skip_sell,
            status="FILTERED_NET",
            error_msg=f"Net {net_profit:.4f}% < umbral {min_net_profit_pct}% | Spread bruto: {spread_gross:.4f}%",
            ref_buy_ad_label=_ad_label(ref_buy_ad),
            ref_sell_ad_label=_ad_label(ref_sell_ad),
            ads_filtered_buy=filt_buy, ads_filtered_sell=filt_sell,
            capital_from_market=capital_from_market,
            fee_exchange_pct=fee_exchange_pct,
        )

    return SpreadResult(
        exchange=exchange, method_id=method_id, method_human=method_human,
        method_mapped=method_mapped, fiat=fiat, asset=asset,
        buy_price_effective=buy_eff, sell_price_effective=sell_eff,
        spread_gross_pct=spread_gross, net_profit_pct=net_profit,
        capital_min_fiat=lo, capital_max_fiat=hi,
        capital_recommended_fiat=cap_fiat, capital_recommended_usdt=cap_usdt,
        ref_buy_ad=ref_buy_ad, ref_sell_ad=ref_sell_ad,
        buy_ads_count=len(buy_ads), sell_ads_count=len(sell_ads),
        buy_ads_skipped=skip_buy, sell_ads_skipped=skip_sell,
        status="OK",
        ref_buy_ad_label=_ad_label(ref_buy_ad),
        ref_sell_ad_label=_ad_label(ref_sell_ad),
        ads_filtered_buy=filt_buy, ads_filtered_sell=filt_sell,
        capital_from_market=capital_from_market,
        fee_exchange_pct=fee_exchange_pct,
    )
