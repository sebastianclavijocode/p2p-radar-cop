"""
alert_bot.py — Bot de alertas P2P para GitHub Actions
Consulta Binance P2P cada vez que se ejecuta y manda alerta a Telegram
si hay oportunidad >= umbral configurado.

Variables de entorno requeridas (GitHub Secrets):
  TG_USERNAME   → tu username de Telegram sin @ (ej: Sebastian_Clavijo)
  UMBRAL_PCT    → ganancia mínima para alertar (ej: 0.15)
  MAKER_FEE_COP → comisión maker COP en % (ej: 0.25)

Opcionales:
  SOLO_COP      → "true" para solo alertar COP (default: true)
  ASSET         → cripto a monitorear (default: USDT)
  TOP_N         → anuncios a analizar (default: 20)
"""
import os
import sys
import json
import time
import urllib.request
import urllib.parse
import logging

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("alert_bot")

# ── Configuración desde variables de entorno ──────────────────────────────────
TG_USERNAME   = os.environ.get("TG_USERNAME", "")
UMBRAL_PCT    = float(os.environ.get("UMBRAL_PCT", "0.15"))
MAKER_FEE_COP = float(os.environ.get("MAKER_FEE_COP", "0.25"))
SOLO_COP      = os.environ.get("SOLO_COP", "true").lower() == "true"
ASSET         = os.environ.get("ASSET", "USDT")
TOP_N         = int(os.environ.get("TOP_N", "20"))

METODOS_COP = [
    {"id": "bancolombia", "nombre": "Bancolombia", "payment_id": "BancolombiaSA", "fiat": "COP"},
    {"id": "nequi",       "nombre": "Nequi",        "payment_id": "Nequi",         "fiat": "COP"},
    {"id": "daviplata",   "nombre": "Daviplata",     "payment_id": "Daviplata",     "fiat": "COP"},
    {"id": "breb",        "nombre": "Llaves Bre-B",  "payment_id": "BreBKeys",      "fiat": "COP"},
]

_ENDPOINT = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
_HEADERS  = {
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json",
    "Accept":       "application/json",
}

# ── Funciones Binance ─────────────────────────────────────────────────────────
def fetch_ads(fiat: str, trade_type: str, pay_types: list, rows: int = 20) -> list:
    payload = {
        "asset":         ASSET,
        "fiat":          fiat,
        "merchantCheck": False,
        "page":          1,
        "payTypes":      pay_types,
        "publisherType": None,
        "rows":          rows,
        "tradeType":     trade_type,
    }
    try:
        resp = requests.post(_ENDPOINT, json=payload, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        ads  = []
        for item in data.get("data", []):
            adv  = item.get("adv", {})
            advr = item.get("advertiser", {})
            # Saltar anuncios promocionados
            if adv.get("isAd") or adv.get("advTag") == "ad":
                continue
            price = float(adv.get("price", 0) or 0)
            if price <= 0:
                continue
            ads.append({
                "price":  price,
                "name":   advr.get("nickName", "?"),
                "min":    float(adv.get("minSingleTransAmount", 0) or 0),
                "max":    float(adv.get("dynamicMaxSingleTransAmount", 0) or 0),
                "metodos": [m.get("identifier","") for m in adv.get("tradeMethods", [])],
            })
        return ads
    except Exception as e:
        logger.error(f"Error fetch_ads {fiat} {trade_type} {pay_types}: {e}")
        return []

def calcular_spread(buy_ads: list, sell_ads: list, fee_pct: float):
    """
    buy_ads  = anuncios de COMPRA en Binance (tab Comprar) → precio más bajo = mejor para nosotros
    sell_ads = anuncios de VENTA en Binance (tab Vender)   → precio más alto = mejor para nosotros
    
    Lógica:
      - Compramos USDT al precio más bajo (buy_ads[0])
      - Vendemos USDT al precio más alto (sell_ads[0])
      - spread_bruto = (precio_venta - precio_compra) / precio_compra * 100
      - neto = spread_bruto - fee_pct
    """
    if not buy_ads or not sell_ads:
        return None

    # Mejor precio de compra = el más bajo (BUY ordenado ASC por Binance)
    precio_compra = buy_ads[0]["price"]
    # Mejor precio de venta = el más alto (SELL ordenado DESC por Binance)
    precio_venta  = sell_ads[0]["price"]

    spread_bruto = (precio_venta - precio_compra) / precio_compra * 100
    neto         = spread_bruto - fee_pct

    return {
        "precio_compra":  precio_compra,
        "precio_venta":   precio_venta,
        "spread_bruto":   spread_bruto,
        "neto":           neto,
        "maker_compra":   buy_ads[0]["name"],
        "maker_venta":    sell_ads[0]["name"],
        "min_compra":     buy_ads[0]["min"],
        "max_compra":     buy_ads[0]["max"],
        "min_venta":      sell_ads[0]["min"],
        "max_venta":      sell_ads[0]["max"],
        "metodos_compra": ", ".join(buy_ads[0]["metodos"][:4]),
        "metodos_venta":  ", ".join(sell_ads[0]["metodos"][:4]),
    }

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
            logger.warning(f"⚠️ CallMeBot respondió: {body[:100]}")
        return ok
    except Exception as e:
        logger.error(f"Error Telegram: {e}")
        return False

def build_message(metodo: dict, resultado: dict) -> str:
    sep = "─" * 28
    return (
        f"🤖 ALERTA P2P RADAR\n"
        f"{sep}\n"
        f"💰 Ganancia neta: {resultado['neto']:.2f}%\n"
        f"💱 {metodo['nombre']} ({metodo['fiat']})\n"
        f"{sep}\n"
        f"📗 COMPRAR (tab Comprar)\n"
        f"👤 {resultado['maker_compra']}\n"
        f"💵 Precio: {resultado['precio_compra']:,.2f} {metodo['fiat']} / {ASSET}\n"
        f"🔴 Límite: {resultado['min_compra']:,.0f} – {resultado['max_compra']:,.0f} {metodo['fiat']}\n"
        f"💳 Métodos: {resultado['metodos_compra']}\n"
        f"{sep}\n"
        f"📕 VENDER (tab Vender)\n"
        f"👤 {resultado['maker_venta']}\n"
        f"💵 Precio: {resultado['precio_venta']:,.2f} {metodo['fiat']} / {ASSET}\n"
        f"🔴 Límite: {resultado['min_venta']:,.0f} – {resultado['max_venta']:,.0f} {metodo['fiat']}\n"
        f"💳 Métodos: {resultado['metodos_venta']}"
    )

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not TG_USERNAME:
        logger.error("❌ TG_USERNAME no configurado. Agregalo en GitHub Secrets.")
        sys.exit(1)

    logger.info(f"🔍 Consultando Binance P2P | Umbral: {UMBRAL_PCT}% | Fee COP: {MAKER_FEE_COP}%")

    alertas_enviadas = 0

    for metodo in METODOS_COP:
        fiat       = metodo["fiat"]
        pay_types  = [metodo["payment_id"]]
        fee        = MAKER_FEE_COP

        logger.info(f"  → {metodo['nombre']} ({fiat})")

        buy_ads  = fetch_ads(fiat=fiat, trade_type="BUY",  pay_types=pay_types, rows=TOP_N)
        time.sleep(1)  # evitar rate limit
        sell_ads = fetch_ads(fiat=fiat, trade_type="SELL", pay_types=pay_types, rows=TOP_N)
        time.sleep(1)

        resultado = calcular_spread(buy_ads, sell_ads, fee)

        if resultado is None:
            logger.info(f"    Sin anuncios suficientes")
            continue

        logger.info(f"    Spread bruto: {resultado['spread_bruto']:.4f}% | Neto: {resultado['neto']:.4f}%")

        if resultado["neto"] >= UMBRAL_PCT:
            logger.info(f"    ✅ Oportunidad detectada! Enviando alerta...")
            msg = build_message(metodo, resultado)
            if send_telegram(TG_USERNAME, msg):
                alertas_enviadas += 1
            time.sleep(2)  # pausa entre mensajes
        else:
            logger.info(f"    ⏳ Por debajo del umbral ({UMBRAL_PCT}%)")

    logger.info(f"✅ Finalizado. {alertas_enviadas} alerta(s) enviada(s).")

if __name__ == "__main__":
    main()
