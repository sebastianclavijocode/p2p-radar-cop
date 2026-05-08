"""
Top-of-book logic: ad detection (sponsored/promoted) + clean price extraction.
"""
import logging
import statistics
from typing import List, Optional, Sequence, Tuple

from .models import P2PAd

logger = logging.getLogger(__name__)


def detect_promoted_ads(
    ads: List[P2PAd],
    threshold_pct: float,
    trade_type: str,
) -> List[P2PAd]:
    """
    Mark probable promoted/sponsored ads using heuristics.

    For BUY (we want lowest price):  promoted ads have price HIGHER than market median.
    For SELL (we want highest price): promoted ads have price LOWER than market median.

    Also checks the raw_data for any exchange-provided flag (advTag, isAd, isPromoted).
    Returns a new list with .is_ad updated.
    """
    if not ads:
        return ads

    result = [P2PAd(**{k: getattr(a, k) for k in a.__dataclass_fields__}) for a in ads]

    # 1. Exchange-provided flags
    for ad in result:
        raw = ad.raw_data
        adv = raw.get("adv", raw)
        if (
            adv.get("isAd")
            or adv.get("isPromoted")
            or adv.get("advTag") == "ad"
            or adv.get("sponsored")
            or raw.get("isAd")
            or raw.get("isPromoted")
        ):
            ad.is_ad = True

    # 2. Heuristic: price outlier vs median of clean ads.
    # Requires at least 5 clean ads to have a robust median.
    # With fewer ads the sample is too small and legitimate ads can be
    # incorrectly flagged, causing valid alerts (Facebank, Zinli, etc.) to disappear.
    prices = [a.price for a in result if a.price > 0 and not a.is_ad]
    if len(prices) < 5:
        return result

    try:
        med = statistics.median(prices)
    except Exception:
        return result

    threshold = threshold_pct / 100.0
    for ad in result:
        if ad.is_ad:
            continue
        if ad.price > med * (1 + threshold):
            ad.is_ad = True
            logger.debug(
                f"Probable ad (outlier alto): {ad.ad_id} price={ad.price:.4f} > median={med:.4f}"
            )
        elif ad.price < med * (1 - threshold):
            ad.is_ad = True
            logger.debug(
                f"Probable ad (outlier bajo): {ad.ad_id} price={ad.price:.4f} < median={med:.4f}"
            )

    return result


def get_top_of_book(
    ads: List[P2PAd],
    trade_type: str,
    exclude_ads: bool = True,
    ad_threshold_pct: float = 1.5,
) -> Tuple[Optional[P2PAd], int, bool]:
    """
    Get the best clean (non-promoted) top-of-book ad.

    trade_type="BUY"  → we buy USDT (advertiser sells) → want LOWEST price
    trade_type="SELL" → we sell USDT (advertiser buys)  → want HIGHEST price

    Returns: (best_ad, n_skipped, had_ads_filtered)
    """
    if not ads:
        return None, 0, False

    # Sort by best price first
    if trade_type == "BUY":
        sorted_ads = sorted([a for a in ads if a.price > 0], key=lambda a: a.price)
    else:
        sorted_ads = sorted([a for a in ads if a.price > 0], key=lambda a: a.price, reverse=True)

    if not sorted_ads:
        return None, 0, False

    if exclude_ads:
        sorted_ads = detect_promoted_ads(sorted_ads, ad_threshold_pct, trade_type)

    clean = [a for a in sorted_ads if not a.is_ad] if exclude_ads else sorted_ads
    skipped = len(sorted_ads) - len(clean)
    had_filtered = skipped > 0

    if not clean:
        logger.warning(f"All {len(sorted_ads)} ads filtered as promoted for {trade_type}. Using first available.")
        return sorted_ads[0], skipped, had_filtered

    return clean[0], skipped, had_filtered


def get_top_n_clean(
    ads: List[P2PAd],
    trade_type: str,
    n: int = 3,
    exclude_ads: bool = True,
    ad_threshold_pct: float = 1.5,
) -> List[P2PAd]:
    """
    Return up to N best clean (non-promoted) ads.

    trade_type="BUY"  → sorted asc  (cheapest first — Comprar tab)
    trade_type="SELL" → sorted desc (highest first — Vender tab)
    """
    if not ads:
        return []

    if trade_type == "BUY":
        sorted_ads = sorted([a for a in ads if a.price > 0], key=lambda a: a.price)
    else:
        sorted_ads = sorted([a for a in ads if a.price > 0], key=lambda a: a.price, reverse=True)

    if not sorted_ads:
        return []

    if exclude_ads:
        sorted_ads = detect_promoted_ads(sorted_ads, ad_threshold_pct, trade_type)

    clean = [a for a in sorted_ads if not a.is_ad] if exclude_ads else sorted_ads

    if not clean:
        # fallback: use first available even if it looked like an ad
        clean = sorted_ads

    return clean[:n]


def weighted_ref_price(
    clean_ads: List[P2PAd],
    weights: Sequence[float] = (0.50, 0.30, 0.20),
) -> Optional[float]:
    """
    Compute a weighted reference price from the top N clean ads.

    Default weights: 50% to #1, 30% to #2, 20% to #3.
    If fewer ads are available the weights are renormalized automatically.

    Returns None if clean_ads is empty.
    """
    if not clean_ads:
        return None

    used   = clean_ads[: len(weights)]
    ws     = list(weights[: len(used)])
    total  = sum(ws)
    ws     = [w / total for w in ws]          # renormalize so they always sum to 1

    price  = sum(ad.price * w for ad, w in zip(used, ws))
    return price
