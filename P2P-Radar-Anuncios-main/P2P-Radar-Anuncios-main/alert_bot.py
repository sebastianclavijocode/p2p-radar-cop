"""
alert_bot.py — Bot de alertas P2P para GitHub Actions
Usa exactamente la misma lógica de cálculo que la app Streamlit.

Secret requerido en GitHub:
  TG_USERNAME   → username de Telegram sin @ (ej: Sebastian_Clavijo)
  UMBRAL_PCT    → ganancia mínima para alertar (ej: 0.15)
  MAKER_FEE_COP → comisión maker COP en % (ej: 0.25)
"""
import os
import sys
import time
import urllib.request
import urllib.parse
import logging
from pathlib import Path

# Agregar el directorio del proyecto al path para importar módulos
PROJECT_DIR = Path(__file__).parent
sys.path.insert(0, str(PROJECT_DIR))

from core.mapping  import load_mappings
from core.spread   import analyze_opportunity
from exchanges     import binance

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("alert_bot")

# ── Config desde secrets ──────────────────────────────────────────────────────
TG_USERNAME   = os.environ.get("TG_USERNAME", "")
UMBRAL_PCT    = float(os.environ.get("UMBRAL_PCT",    "0.15"))
MAKER_FEE_COP = float(os.environ.get("MAKER_FEE_COP", "0.25"))
ASSET         = "USDT"
TOP_N         = 20

METODOS_COP = [
    {"id": "bancolombia_cop_custom", "human_name": "Bancolombia",  "payment_id": "BancolombiaSA", "fiat": "COP"},
    {"id": "nequi_cop_custom",       "human_name": "Nequi",         "payment_id": "Nequi",         "fiat": "COP"},
    {"id": "daviplata_cop_custom",   "human_name": "Daviplata",      "payment_id": "Daviplata",     "fiat": "COP"},
    {"id": "breb_cop_custom",        "human_name": "Llaves Bre-B",   "payment_id": "BreBKeys",      "fiat": "COP"},
]

CAPITAL_COP = {"target_min": 800_000, "target_max": 8_000_000, "simulado": 2_000_000}

# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(username: str, text: str) -> bool:
    params = urllib.parse.urlencode({"user": f"@{username}", "text": text})
    url    = f"https://api.callmebot.com/text.php?{params}"
    try:
        req  = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=15)
        body = resp.read().decode("utf-8", errors="ignore")
        ok   = "error" not in body.lower()
        if ok:
            logger.info(f"✅ Telegram enviado a @{username}")
        else:
            logger.warning(f"⚠️ CallMeBot: {body[:100]}")
        return ok
    except Exception as e:
        logger.error(f"Error Telegram: {e}")
        return False

def build_message(result) -> str:
    buy  = result.ref_buy_ad
    sell = result.ref_sell_ad
    def pays(ad):
        if not ad or not ad.payment_methods: return "—"
        return ", ".join([m for m in ad.payment_methods if m][:4])
    sep = "─" * 28
    pct = result.net_profit_pct or 0
    fiat = result.fiat
    def fmt(v):
        if v is None: return "—"
        return f"{v:,.2f}"
    return (
        f"🤖 ALERTA P2P RADAR\n"
        f"{sep}\n"
        f"💰 Ganancia neta: {pct:.2f}%\n"
        f"💱 {result.method_human} ({fiat})\n"
        f"{sep}\n"
        f"📗 COMPRAR (tab Comprar)\n"
        f"👤 {buy.advertiser_name if buy else '—'}\n"
        f"💵 Precio: {fmt(result.buy_price_effective)} {fiat} / {result.asset}\n"
        f"🔴 Límite: {f'{buy.min_amount:,.0f}' if buy else '—'} – {f'{buy.max_amount:,.0f}' if buy else '—'} {fiat}\n"
        f"💳 Métodos: {pays(buy)}\n"
        f"{sep}\n"
        f"📕 VENDER (tab Vender)\n"
        f"👤 {sell.advertiser_name if sell else '—'}\n"
        f"💵 Precio: {fmt(result.sell_price_effective)} {fiat} / {result.asset}\n"
        f"🔴 Límite: {f'{sell.min_amount:,.0f}' if sell else '—'} – {f'{sell.max_amount:,.0f}' if sell else '—'} {fiat}\n"
        f"💳 Métodos: {pays(sell)}"
    )

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not TG_USERNAME:
        logger.error("❌ TG_USERNAME no configurado.")
        sys.exit(1)

    logger.info(f"🔍 Consultando Binance P2P | Umbral: {UMBRAL_PCT}% | Fee COP: {MAKER_FEE_COP}%")

    alertas_enviadas = 0

    for metodo in METODOS_COP:
        fiat       = metodo["fiat"]
        pay_ids    = [metodo["payment_id"]]
        nombre     = metodo["human_name"]

        logger.info(f"  → {nombre} ({fiat})")

        try:
            buy_ads  = binance.fetch_ads(asset=ASSET, fiat=fiat, trade_type="BUY",  pay_types=pay_ids, rows=TOP_N, merchant_check=False)
            time.sleep(1)
            sell_ads = binance.fetch_ads(asset=ASSET, fiat=fiat, trade_type="SELL", pay_types=pay_ids, rows=TOP_N, merchant_check=False)
            time.sleep(1)
        except Exception as e:
            logger.error(f"    Error fetch: {e}")
            continue

        if not buy_ads or not sell_ads:
            logger.info(f"    Sin anuncios suficientes")
            continue

        # Usar exactamente el mismo analyze_opportunity que la app
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

        pct = result.net_profit_pct or 0
        logger.info(f"    Spread bruto: {result.spread_gross_pct:.4f}% | Neto: {pct:.4f}% | Status: {result.status}")

        if result.status == "OK" and pct >= UMBRAL_PCT:
            logger.info(f"    ✅ Oportunidad! Enviando alerta...")
            if send_telegram(TG_USERNAME, build_message(result)):
                alertas_enviadas += 1
            time.sleep(2)
        else:
            logger.info(f"    ⏳ Por debajo del umbral ({UMBRAL_PCT}%)")

    logger.info(f"✅ Finalizado. {alertas_enviadas} alerta(s) enviada(s).")

if __name__ == "__main__":
    main()
