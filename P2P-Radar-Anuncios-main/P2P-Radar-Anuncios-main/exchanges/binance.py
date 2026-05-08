"""
Binance P2P — public endpoint, no API key required.
POST https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search

Estrategia de verificación ◆ (badge diamante):
  Criterio único y estricto: advertiser.vipLevel != null.
  userType y proMerchant NO son confiables para ◆.

Estrategia de búsqueda robusta (cuando merchant_check=True + pay_types específico):
  1. merchantCheck=True + publisherType="merchant" + payTypes exacto, hasta 5 páginas.
  2. Filtrar client-side: método de pago + vipLevel != null.
  3. Cortar cuando se acumulan ≥3 ads ◆ válidos.
  4. Si no alcanza, fallback sin payTypes server-side (filtro local doble).
  5. Deduplicar por advNo. Logs claros en cada paso.
"""
import logging
import time
from typing import List, Optional, Set

import requests

from core.cache import TTLCache
from core.models import P2PAd

logger = logging.getLogger(__name__)

_ENDPOINT = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "application/json",
}

_cache = TTLCache(ttl_seconds=90)

EXCHANGE_NOTE = "Binance P2P — API pública sin key. Filtrado client-side garantizado."


# ── parseo ────────────────────────────────────────────────────────────────────

def _is_promoted(adv: dict) -> bool:
    return bool(
        adv.get("isAd")
        or adv.get("advTag") == "ad"
        or adv.get("isPromoted")
        or "ad" in str(adv.get("advTag", "")).lower()
    )


def _parse_ads(raw_items: list, exchange: str) -> List[P2PAd]:
    ads: List[P2PAd] = []
    for item in raw_items:
        adv        = item.get("adv", {})
        advertiser = item.get("advertiser", {})
        try:
            price = float(adv.get("price", 0) or 0)
            if price <= 0:
                continue
            ad = P2PAd(
                ad_id            = adv.get("advNo", ""),
                trade_type       = adv.get("tradeType", ""),
                asset            = adv.get("asset", ""),
                fiat             = adv.get("fiatUnit", ""),
                price            = price,
                min_amount       = float(adv.get("minSingleTransAmount", 0) or 0),
                max_amount       = float(adv.get("dynamicMaxSingleTransAmount", 0) or 0),
                available_amount = float(adv.get("tradableQuantity", 0) or 0),
                payment_methods  = [m.get("identifier", "") for m in adv.get("tradeMethods", [])],
                advertiser_name  = advertiser.get("nickName", "Unknown"),
                exchange         = exchange,
                is_ad            = _is_promoted(adv),
                raw_data         = item,
            )
            ads.append(ad)
        except (ValueError, TypeError, KeyError) as exc:
            logger.debug(f"Binance: skipping malformed ad – {exc}")
    return ads


# ── verificación ◆ ────────────────────────────────────────────────────────────

def _is_verified_merchant(ad: P2PAd) -> bool:
    """
    True si el anunciante tiene el badge ◆ (diamante) de Binance P2P.

    Criterio único confiable: advertiser.vipLevel != null (valor 1 o 2).
    userType="merchant" NO es confiable — también lo tienen no-◆.
    proMerchant NO se usa — no distingue correctamente en todos los mercados.
    """
    return ad.raw_data.get("advertiser", {}).get("vipLevel") is not None


# ── filtros y helpers ─────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return s.lower().replace(" ", "").replace("-", "").replace("_", "").replace(".", "")


def _filter_by_method(ads: List[P2PAd], expected_ids: List[str]) -> List[P2PAd]:
    """Filtro client-side por método de pago (substring case-insensitive)."""
    if not expected_ids:
        return ads
    exp_norms = [_norm(e) for e in expected_ids]
    result = []
    for ad in ads:
        for pm in ad.payment_methods:
            pm_n = _norm(pm)
            if any(e in pm_n or pm_n in e for e in exp_norms):
                result.append(ad)
                break
    return result


def _find_real_ids(all_ads: List[P2PAd], expected_ids: List[str]) -> List[str]:
    """Auto-discovery: busca los IDs reales que usa la API para un método."""
    all_methods: set = set()
    for ad in all_ads:
        for pm in ad.payment_methods:
            if pm:
                all_methods.add(pm)
    exp_norms = [_norm(e) for e in expected_ids]
    matched = []
    for actual in sorted(all_methods):
        act_n = _norm(actual)
        if any(e in act_n or act_n in e for e in exp_norms):
            if actual not in matched:
                matched.append(actual)
                logger.info(f"Binance auto-discovery: {expected_ids} → '{actual}'")
    return matched


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _raw_fetch(payload: dict, max_retries: int = 3) -> List[P2PAd]:
    """Llamada HTTP directa sin cache."""
    for attempt in range(max_retries):
        try:
            resp = requests.post(_ENDPOINT, json=payload, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") and data.get("code") != "000000":
                logger.warning(f"Binance API error {data.get('code')}: {data.get('message', '')}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
            return _parse_ads(data.get("data", []) or [], exchange="Binance")
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            logger.warning(f"Binance HTTP {status} (attempt {attempt+1}): {exc}")
        except requests.RequestException as exc:
            logger.warning(f"Binance request error (attempt {attempt+1}): {exc}")
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)
    return []


# ── búsqueda robusta de ◆ ─────────────────────────────────────────────────────

def _fetch_verified_ads_robust(
    asset: str,
    fiat: str,
    trade_type: str,
    pay_types: List[str],
    max_pages: int = 5,
    rows: int = 20,
    target_verified: int = 3,
    max_retries: int = 3,
) -> List[P2PAd]:
    """
    Búsqueda robusta y paginada de anunciantes ◆ (vipLevel != null).

    Paso 1 — merchantCheck=True + publisherType="merchant" + payTypes exacto.
              Pagina hasta max_pages o hasta acumular target_verified ◆.
              Filtro local: método de pago + vipLevel != null.

    Paso 2 — Fallback sin payTypes server-side (si Paso 1 no alcanzó).
              Filtra localmente por método de pago + vipLevel != null.

    Deduplicación por advNo en toda la búsqueda.
    """
    verified: List[P2PAd] = []
    seen_ids: Set[str] = set()

    base_payload = {
        "asset": asset,
        "fiat": fiat,
        "tradeType": trade_type,
        "merchantCheck": True,
        "publisherType": "merchant",
        "rows": min(rows, 20),  # Binance API cap: rows <= 20
    }

    # ── Paso 1: paginar con payTypes exacto ───────────────────────────────────
    for page in range(1, max_pages + 1):
        payload = {**base_payload, "payTypes": pay_types, "page": page}
        page_ads = _raw_fetch(payload, max_retries=max_retries)

        if not page_ads:
            logger.debug(
                f"Binance [{trade_type}] {asset}/{fiat} page={page}: "
                f"sin resultados, corto paginación."
            )
            break

        filtered = _filter_by_method(page_ads, pay_types)
        new_v = 0
        for ad in filtered:
            if ad.ad_id not in seen_ids and _is_verified_merchant(ad):
                verified.append(ad)
                seen_ids.add(ad.ad_id)
                new_v += 1

        logger.info(
            f"Binance [{trade_type}] {asset}/{fiat} {pay_types} "
            f"page={page}: {len(page_ads)} total, {len(filtered)} con método, "
            f"+{new_v} ◆ nuevos → acumulados: {len(verified)}"
        )

        if len(verified) >= target_verified:
            break

    if len(verified) >= target_verified:
        return verified

    # ── Paso 2: fallback sin payTypes server-side ─────────────────────────────
    if pay_types:
        logger.warning(
            f"Binance [{trade_type}] {asset}/{fiat}: {len(verified)} ◆ con payTypes exacto. "
            f"Fallback sin payTypes (filtro local)..."
        )
        for page in range(1, 4):
            payload = {**base_payload, "payTypes": None, "page": page}
            page_ads = _raw_fetch(payload, max_retries=2)

            if not page_ads:
                break

            filtered = _filter_by_method(page_ads, pay_types)
            new_v = 0
            for ad in filtered:
                if ad.ad_id not in seen_ids and _is_verified_merchant(ad):
                    verified.append(ad)
                    seen_ids.add(ad.ad_id)
                    new_v += 1

            logger.info(
                f"Binance [{trade_type}] {asset}/{fiat} fallback page={page}: "
                f"{len(page_ads)} total, {len(filtered)} con método, "
                f"+{new_v} ◆ nuevos → acumulados: {len(verified)}"
            )

            if len(verified) >= target_verified:
                break

    if not verified:
        logger.warning(
            f"Binance [{trade_type}] {asset}/{fiat} {pay_types}: "
            f"0 ◆ encontrados tras {max_pages} páginas + fallback. "
            f"El método retornará NO_ADS."
        )
    else:
        logger.info(
            f"Binance [{trade_type}] {asset}/{fiat}: {len(verified)} ◆ encontrados en total."
        )

    return verified


# ── fetch_ads (entrada pública) ───────────────────────────────────────────────

def fetch_ads(
    asset: str,
    fiat: str,
    trade_type: str,
    pay_types: Optional[List[str]] = None,
    rows: int = 10,
    max_retries: int = 3,
    merchant_check: bool = True,
) -> List[P2PAd]:
    """
    Punto de entrada principal para obtener ads de Binance P2P.

    Si merchant_check=True y pay_types no vacío:
        → _fetch_verified_ads_robust: paginado, publisherType="merchant",
          filtro ◆ estricto (vipLevel != null). Aplica a TODOS los métodos
          incluyendo Prex — la robustez extra no cambia su comportamiento,
          solo garantiza que otros métodos sean igualmente consistentes.

    Si merchant_check=False o pay_types vacío (escaneo/descubrimiento):
        → fetch simple de una página, sin filtro ◆.
    """
    pay_types = pay_types or []
    cache_key = (
        f"binance|{asset}|{fiat}|{trade_type}"
        f"|{'_'.join(sorted(pay_types))}|mc{merchant_check}"
    )

    cached = _cache.get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit: {cache_key}")
        return cached

    if merchant_check and pay_types:
        # ── Búsqueda robusta con verificación ◆ ──────────────────────────────
        ads = _fetch_verified_ads_robust(
            asset=asset,
            fiat=fiat,
            trade_type=trade_type,
            pay_types=pay_types,
            max_pages=5,
            rows=20,
            target_verified=3,
            max_retries=max_retries,
        )
    else:
        # ── Fetch simple: escaneo automático o descubrimiento ─────────────────
        # payTypes=[] en la API significa "sin métodos" → 0 resultados.
        # Usar None para "todos los métodos".
        pay_types_payload = pay_types if pay_types else None
        payload = {
            "asset": asset, "fiat": fiat,
            "merchantCheck": merchant_check,
            "page": 1,
            "publisherType": None,
            "rows": min(max(rows, 10), 20),
            "tradeType": trade_type,
            "payTypes": pay_types_payload,
        }
        ads = _raw_fetch(payload, max_retries)

        if pay_types:
            filtered = _filter_by_method(ads, pay_types)
            if not filtered:
                # auto-discovery: buscar ID real en el mercado completo
                logger.warning(
                    f"Binance: 0 ads para {pay_types} en {asset}/{fiat} {trade_type}. "
                    f"Iniciando auto-discovery..."
                )
                disc_payload = {**payload, "payTypes": None, "merchantCheck": False, "rows": 20}
                all_ads = _raw_fetch(disc_payload, max_retries=2)
                real_ids = _find_real_ids(all_ads, pay_types)
                if real_ids:
                    ads = _raw_fetch({**payload, "payTypes": real_ids}, max_retries)
                    ads = _filter_by_method(ads, real_ids) or ads
                else:
                    ads = []
            else:
                ads = filtered

    _cache.set(cache_key, ads)
    logger.info(f"Binance {trade_type} {asset}/{fiat} {pay_types}: {len(ads)} ads final")
    return ads


def is_supported() -> bool:
    return True
