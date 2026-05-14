"""
alert_bot.py — Bot de alertas P2P para GitHub Actions
- Alerta maker-maker (spread normal)
- Alerta taker-taker (compra/venta directa sin anuncio)
- Guarda historial de precios en price_history.json
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
import logging
import requests

from pathlib import Path
from datetime import datetime, timezone

PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from core.spread import analyze_opportunity
from exchanges import binance

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("alert_bot")

# ── Config ────────────────────────────────────────────────────────────────────
TG_USERNAME   = os.environ.get("TG_USERNAME", "")
UMBRAL_PCT    = float(os.environ.get("UMBRAL_PCT", "0.15"))
MAKER_FEE_COP = float(os.environ.get("MAKER_FEE_COP", "0.25"))
GH_PAT        = os.environ.get("GH_PAT", "")

GH_REPO       = "sebastianclavijocode/p2p-radar-cop"
HISTORY_PATH  = "P2P-Radar-Anuncios-main/P2P-Radar-Anuncios-main/price_history.json"

ASSET         = os.environ.get("ASSET", "USDT")
TOP_N         = int(os.environ.get("TOP_N", "20"))
MAX_HISTORY   = 1008  # 7 días cada 10 min

# Fee taker estimado: $0.07 compra + $0.07 venta en USDT
TAKER_FEE     = 0.14

METODOS_COP = [
    {
        "id": "bancolombia_cop_custom",
        "human_name": "Bancolombia",
        "payment_id": "BancolombiaSA",
        "fiat": "COP",
    },
    {
        "id": "nequi_cop_custom",
        "human_name": "Nequi",
        "payment_id": "Nequi",
        "fiat": "COP",
    },
    {
        "id": "daviplata_cop_custom",
        "human_name": "Daviplata",
        "payment_id": "Daviplata",
        "fiat": "COP",
    },
    {
        "id": "breb_cop_custom",
        "human_name": "Llaves Bre-B",
        "payment_id": "BreBKeys",
        "fiat": "COP",
    },
]

CAPITAL_COP = {
    "target_min": 800_000,
    "target_max": 8_000_000,
    "simulado": 2_000_000,
}


# ── Helpers para soportar dict o P2PAd ────────────────────────────────────────
def ad_value(ad, key, default=None):
    """
    Permite leer anuncios tanto si vienen como dict:
        ad["price"]
    como si vienen como objeto P2PAd:
        ad.price
    """
    if ad is None:
        return default

    if isinstance(ad, dict):
        return ad.get(key, default)

    return getattr(ad, key, default)


def ad_price(ad) -> float:
    """
    Obtiene el precio del anuncio de forma segura.
    Corrige el error:
        TypeError: 'P2PAd' object is not subscriptable
    """
    price = ad_value(ad, "price")

    if price is None:
        raise ValueError(f"Anuncio sin price válido: {ad}")

    return float(price)


# ── GitHub API ────────────────────────────────────────────────────────────────
def gh_get_file(path: str):
    """Obtiene contenido y SHA de un archivo en el repo."""
    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {GH_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception as e:
        logger.error(f"Error gh_get_file: {e}")
        return None


def gh_save_file(path: str, content: str, sha: str = None, message: str = "bot: update history"):
    """Guarda un archivo en el repo via GitHub API."""
    import base64

    url = f"https://api.github.com/repos/{GH_REPO}/contents/{path}"
    headers = {
        "Authorization": f"token {GH_PAT}",
        "Accept": "application/vnd.github.v3+json",
    }

    data = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
        "branch": "main",
    }

    if sha:
        data["sha"] = sha

    try:
        r = requests.put(url, headers=headers, json=data, timeout=15)

        if r.status_code in (200, 201):
            logger.info(f"💾 {path} guardado en GitHub")
            return True

        logger.error(f"Error guardando {path}: {r.status_code} {r.text[:300]}")
        return False

    except Exception as e:
        logger.error(f"Error gh_save_file: {e}")
        return False


def load_history_from_github() -> tuple:
    """Carga el historial desde GitHub. Retorna (history_dict, sha)."""
    file_info = gh_get_file(HISTORY_PATH)

    if file_info:
        import base64

        try:
            content = base64.b64decode(file_info["content"]).decode("utf-8")
            return json.loads(content), file_info["sha"]
        except Exception as e:
            logger.warning(f"Error parseando historial: {e}")

    return {}, None


def save_history_to_github(history: dict, sha: str = None):
    content = json.dumps(history, indent=2, ensure_ascii=False)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    gh_save_file(HISTORY_PATH, content, sha, message=f"bot: precio {now_str}")


def update_history(
    history: dict,
    metodo: dict,
    buy_price: float,
    sell_price: float,
    taker_buy: float,
    taker_sell: float,
) -> dict:
    key = metodo["id"]

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "buy_price": round(float(buy_price), 2),
        "sell_price": round(float(sell_price), 2),
        "taker_buy": round(float(taker_buy), 2),
        "taker_sell": round(float(taker_sell), 2),
        "spread_pct": round((float(sell_price) - float(buy_price)) / float(buy_price) * 100, 4)
        if float(buy_price) > 0
        else 0,
    }

    if key not in history:
        history[key] = {
            "nombre": metodo["human_name"],
            "fiat": metodo["fiat"],
            "registros": [],
        }

    history[key]["registros"].append(entry)
    history[key]["registros"] = history[key]["registros"][-MAX_HISTORY:]

    return history


# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(username: str, text: str) -> bool:
    params = urllib.parse.urlencode({
        "user": f"@{username}",
        "text": text,
    })

    url = f"https://api.callmebot.com/text.php?{params}"

    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=15)
        body = resp.read().decode("utf-8", errors="ignore")

        ok = "error" not in body.lower()

        if ok:
            logger.info(f"✅ Telegram enviado a @{username}")
        else:
            logger.warning(f"⚠️ CallMeBot: {body[:300]}")

        return ok

    except Exception as e:
        logger.error(f"Error Telegram: {e}")
        return False


def build_maker_message(result, pct) -> str:
    buy = result.ref_buy_ad
    sell = result.ref_sell_ad

    def pays(ad):
        methods = ad_value(ad, "payment_methods", [])
        if not ad or not methods:
            return "—"
        return ", ".join([m for m in methods if m][:4])

    def fmt(v):
        return f"{float(v):,.2f}" if v else "—"

    buy_name = ad_value(buy, "advertiser_name", "—")
    buy_min = ad_value(buy, "min_amount")
    buy_max = ad_value(buy, "max_amount")

    sell_name = ad_value(sell, "advertiser_name", "—")
    sell_min = ad_value(sell, "min_amount")
    sell_max = ad_value(sell, "max_amount")

    sep = "─" * 28

    return (
        f"🤖 ALERTA P2P RADAR\n{sep}\n"
        f"💰 Ganancia neta: {pct:.2f}%\n"
        f"💱 {result.method_human} ({result.fiat})\n{sep}\n"
        f"📗 COMPRAR (tab Comprar)\n"
        f"👤 {buy_name if buy else '—'}\n"
        f"💵 {fmt(result.buy_price_effective)} {result.fiat} / {result.asset}\n"
        f"🔴 {f'{float(buy_min):,.0f}' if buy_min else '—'} – "
        f"{f'{float(buy_max):,.0f}' if buy_max else '—'} {result.fiat}\n"
        f"💳 {pays(buy)}\n{sep}\n"
        f"📕 VENDER (tab Vender)\n"
        f"👤 {sell_name if sell else '—'}\n"
        f"💵 {fmt(result.sell_price_effective)} {result.fiat} / {result.asset}\n"
        f"🔴 {f'{float(sell_min):,.0f}' if sell_min else '—'} – "
        f"{f'{float(sell_max):,.0f}' if sell_max else '—'} {result.fiat}\n"
        f"💳 {pays(sell)}"
    )


def build_taker_message(metodo, taker_buy, taker_sell, ganancia_cop, cantidad_usdt) -> str:
    sep = "─" * 28

    return (
        f"🟠 ALERTA TAKER-TAKER\n{sep}\n"
        f"💱 {metodo['human_name']} ({metodo['fiat']})\n"
        f"⚡ Compra y venta directa SIN anuncio\n{sep}\n"
        f"📗 COMPRÁ directamente a: {taker_buy:,.2f} {metodo['fiat']}\n"
        f"📕 VENDÉ directamente a:  {taker_sell:,.2f} {metodo['fiat']}\n"
        f"📦 Cantidad aprox: {cantidad_usdt:.1f} USDT\n"
        f"💰 Ganancia estimada: {ganancia_cop:,.0f} {metodo['fiat']}\n"
        f"💳 Comisión fija: $0.14 USDT\n{sep}\n"
        f"⚠️ Actuar rápido — precio puede cambiar"
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not TG_USERNAME:
        logger.error("❌ TG_USERNAME no configurado.")
        sys.exit(1)

    logger.info(
        f"🔍 Consultando Binance P2P | Umbral: {UMBRAL_PCT}% | "
        f"Fee COP: {MAKER_FEE_COP}% | Asset: {ASSET} | TOP_N: {TOP_N}"
    )

    alertas_enviadas = 0
    history, history_sha = load_history_from_github() if GH_PAT else ({}, None)

    for metodo in METODOS_COP:
        fiat = metodo["fiat"]
        pay_ids = [metodo["payment_id"]]
        nombre = metodo["human_name"]

        logger.info(f"  → {nombre} ({fiat})")

        try:
            buy_ads = binance.fetch_ads(
                asset=ASSET,
                fiat=fiat,
                trade_type="BUY",
                pay_types=pay_ids,
                rows=TOP_N,
                merchant_check=False,
            )

            time.sleep(1)

            sell_ads = binance.fetch_ads(
                asset=ASSET,
                fiat=fiat,
                trade_type="SELL",
                pay_types=pay_ids,
                rows=TOP_N,
                merchant_check=False,
            )

            time.sleep(1)

        except Exception as e:
            logger.error(f"    Error fetch: {e}")
            continue

        if not buy_ads or not sell_ads:
            logger.info("    Sin anuncios suficientes")
            continue

        try:
            # CORRECCIÓN PRINCIPAL:
            # Antes estaba:
            #   buy_ads[0]["price"]
            #   sell_ads[0]["price"]
            #
            # Eso falla cuando los anuncios vienen como objetos P2PAd.
            taker_buy = ad_price(buy_ads[0])
            taker_sell = ad_price(sell_ads[0])

        except Exception as e:
            logger.error(f"    Error leyendo precios taker: {e}")
            continue

        # ── Estrategia Maker-Maker ────────────────────────────────────────────
        try:
            result = analyze_opportunity(
                buy_ads=buy_ads,
                sell_ads=sell_ads,
                exchange="Binance",
                method_id=metodo["id"],
                method_human=nombre,
                method_mapped=metodo["payment_id"],
                fiat=fiat,
                asset=ASSET,
                fee_exchange_pct=MAKER_FEE_COP,
                fee_slippage_pct=0.0,
                fee_method_pct=0.0,
                fee_method_fixed=0.0,
                publication_mode="match_top",
                epsilon_fiat=0.0,
                epsilon_pct=0.0,
                exclude_ads=True,
                ad_threshold_pct=999.0,
                capital_target_min=CAPITAL_COP["target_min"],
                capital_target_max=CAPITAL_COP["target_max"],
                capital_simulado=CAPITAL_COP["simulado"],
                buffer_pct=1.0,
                min_net_profit_pct=0.0,
                allow_outside_target=True,
            )

        except Exception as e:
            logger.error(f"    Error analyze_opportunity: {e}")
            continue

        pct = result.net_profit_pct or 0

        logger.info(
            f"    Maker | Spread: {result.spread_gross_pct:.4f}% | "
            f"Neto: {pct:.4f}% | Status: {result.status}"
        )

        if result.status == "OK" and pct >= UMBRAL_PCT:
            logger.info("    ✅ Oportunidad maker! Enviando...")

            if send_telegram(TG_USERNAME, build_maker_message(result, pct)):
                alertas_enviadas += 1

            time.sleep(2)

        # ── Estrategia Taker-Taker ────────────────────────────────────────────
        # taker_buy  = precio al que compramos
        # taker_sell = precio al que vendemos
        if taker_sell > taker_buy:
            cantidad_usdt = CAPITAL_COP["simulado"] / taker_buy
            ganancia_bruta = (taker_sell - taker_buy) * cantidad_usdt
            ganancia_cop = ganancia_bruta - (TAKER_FEE * taker_sell)
            ganancia_pct = (taker_sell - taker_buy) / taker_buy * 100

            logger.info(
                f"    Taker | Compra: {taker_buy:,.2f} | "
                f"Venta: {taker_sell:,.2f} | "
                f"Ganancia: {ganancia_cop:,.0f} COP ({ganancia_pct:.3f}%)"
            )

            if ganancia_pct >= UMBRAL_PCT:
                logger.info("    🟠 Oportunidad taker! Enviando...")

                msg = build_taker_message(
                    metodo,
                    taker_buy,
                    taker_sell,
                    ganancia_cop,
                    cantidad_usdt,
                )

                if send_telegram(TG_USERNAME, msg):
                    alertas_enviadas += 1

                time.sleep(2)
        else:
            spread_taker = (taker_sell - taker_buy) / taker_buy * 100 if taker_buy > 0 else 0
            logger.info(
                f"    Taker | Sin oportunidad | "
                f"Compra: {taker_buy:,.2f} | Venta: {taker_sell:,.2f} | "
                f"Spread: {spread_taker:.4f}%"
            )

        # ── Guardar historial ─────────────────────────────────────────────────
        buy_price = result.buy_price_effective or taker_buy
        sell_price = result.sell_price_effective or taker_sell

        history = update_history(
            history,
            metodo,
            buy_price,
            sell_price,
            taker_buy,
            taker_sell,
        )

    if GH_PAT and history:
        save_history_to_github(history, history_sha)

    logger.info(f"✅ Finalizado. {alertas_enviadas} alerta(s) enviada(s).")


if __name__ == "__main__":
    main()
