"""
Bybit P2P — public endpoint, no API key required.
POST https://api2.bybit.com/fiat/otc/item/online

Payment IDs are numeric strings (e.g. "8" = Mercado Pago).
tradeType: "1" = we BUY, "0" = we SELL
"""
import logging
import time
from typing import List, Optional

import requests

from core.cache import TTLCache
from core.models import P2PAd

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api2.bybit.com/fiat/otc/item/online"
_HEADERS  = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json",
}

_cache = TTLCache(ttl_seconds=45)

EXCHANGE_NOTE = (
    "Bybit P2P — API pública sin key. Usa IDs numéricos para métodos de pago. "
    "Confirmado: ID 8 = Mercado Pago. El resto no está confirmado; "
    "editá el Mapeo si encontrás los IDs correctos."
)


def _is_promoted(item: dict) -> bool:
    return bool(
        item.get("isAd")
        or item.get("isPromoted")
        or item.get("adType")
    )


def _parse_ads(items: list, fiat: str, asset: str, exchange: str) -> List[P2PAd]:
    ads: List[P2PAd] = []
    for item in items:
        try:
            price = float(item.get("price", 0) or 0)
            if price <= 0:
                continue
            side  = item.get("side", "")
            ttype = "BUY" if side == "1" else "SELL"
            pays  = item.get("payments", []) or []
            ad = P2PAd(
                ad_id            = str(item.get("id", "")),
                trade_type       = ttype,
                asset            = item.get("tokenId", asset),
                fiat             = item.get("currencyId", fiat),
                price            = price,
                min_amount       = float(item.get("minAmount", 0) or 0),
                max_amount       = float(item.get("maxAmount", 0) or 0),
                available_amount = float(item.get("quantity", 0) or item.get("lastQuantity", 0) or 0),
                payment_methods  = [str(p.get("paymentType", "")) for p in pays],
                advertiser_name  = str(item.get("nickName") or item.get("userId") or "Unknown"),
                exchange         = exchange,
                is_ad            = _is_promoted(item),
                raw_data         = item,
            )
            ads.append(ad)
        except (ValueError, TypeError, KeyError) as exc:
            logger.debug(f"Bybit: skipping malformed ad – {exc}")
    return ads


def fetch_ads(
    asset: str,
    fiat: str,
    trade_type: str,
    pay_types: Optional[List[str]] = None,
    rows: int = 10,
    max_retries: int = 3,
    merchant_check: bool = True,  # ignorado en Bybit, solo para compatibilidad de firma
) -> List[P2PAd]:
    pay_types = pay_types or []
    side      = "1" if trade_type == "BUY" else "0"
    cache_key = f"bybit|{asset}|{fiat}|{trade_type}|{'_'.join(sorted(pay_types))}"

    cached = _cache.get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit: {cache_key}")
        return cached

    payload = {
        "tokenId": asset, "currencyId": fiat,
        "payment": pay_types, "side": side,
        "size": str(rows), "page": "1", "amount": "",
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(_ENDPOINT, json=payload, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            data  = resp.json()
            items = (
                data.get("result", {}).get("items", [])
                or data.get("data", {}).get("list", [])
                or []
            )
            ads = _parse_ads(items, fiat=fiat, asset=asset, exchange="Bybit")
            _cache.set(cache_key, ads)
            logger.info(f"Bybit {trade_type} {asset}/{fiat} payments={pay_types}: {len(ads)} ads")
            return ads
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            logger.warning(f"Bybit HTTP {status} (attempt {attempt+1}): {exc}")
        except requests.RequestException as exc:
            logger.warning(f"Bybit request error (attempt {attempt+1}): {exc}")

        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)

    logger.error(f"Bybit: all {max_retries} attempts failed for {cache_key}")
    return []


def is_supported() -> bool:
    return True
