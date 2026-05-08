"""Tabla secundaria y gráfico de spreads."""
from typing import List, Optional

import altair as alt
import pandas as pd
import streamlit as st

from core.models import SpreadResult


_TABLE_CSS = """
<style>
.p2p-table { width:100%; border-collapse:collapse; font-size:12px;
             font-family:'Inter',-apple-system,sans-serif; }
.p2p-table th { background:rgba(255,255,255,0.04); color:rgba(255,255,255,0.4);
                font-size:10px; font-weight:700; text-transform:uppercase;
                letter-spacing:0.8px; padding:8px 12px; text-align:left;
                border-bottom:1px solid rgba(255,255,255,0.07); white-space:nowrap; }
.p2p-table td { padding:7px 12px; color:rgba(255,255,255,0.75); font-size:12px;
                border-bottom:1px solid rgba(255,255,255,0.04); white-space:nowrap; }
.p2p-table tr:last-child td { border-bottom:none; }
.p2p-table tr:hover td { background:rgba(255,255,255,0.02); }
</style>
"""

def _html_table(rows: list) -> str:
    if not rows:
        return ""
    headers = list(rows[0].keys())
    ths = "".join(f"<th>{h}</th>" for h in headers)
    trs = ""
    for row in rows:
        tds = "".join(f"<td>{row[h]}</td>" for h in headers)
        trs += f"<tr>{tds}</tr>"
    return f'{_TABLE_CSS}<div style="overflow-x:auto"><table class="p2p-table"><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table></div>'

STATUS_BADGE = {
    "OK":                  "🟢 OK",
    "FILTERED_NET":        "🟡 Net bajo umbral",
    "NO_ADS":              "🟠 Sin anuncios limpios",
    "INCOMPATIBLE_LIMITS": "🔴 Límites incompatibles",
    "NOT_AVAILABLE":       "⚫ No disponible",
    "MAPPING_REQUIRED":    "🔵 Sin mapeo configurado",
    "ERROR":               "🔴 Error de consulta",
}

STATUS_HINT = {
    "FILTERED_NET":        "Bajá el umbral de ganancia mínima para verlo.",
    "NO_ADS":              "Verificá el ID de pago en la pestaña Diagnóstico.",
    "INCOMPATIBLE_LIMITS": "Los límites de compra y venta no se solapan.",
    "NOT_AVAILABLE":       "Exchange o método no soportado.",
    "MAPPING_REQUIRED":    "Configurá el ID de este método en Diagnóstico → Agregar.",
    "ERROR":               "Error al consultar el exchange. Reintentá.",
}


def _pct(v: Optional[float], d: int = 4) -> str:
    return "—" if v is None else f"{v:.{d}f}%"

def _fmt(v: Optional[float], suffix: str = "", d: int = 2) -> str:
    if v is None: return "—"
    return f"{v:,.{d}f}{(' ' + suffix) if suffix else ''}"


def render_ok_table(results: List[SpreadResult]) -> None:
    ok = [r for r in results if r.status == "OK"]
    if not ok:
        return
    rows = []
    for r in ok:
        ads_info = ""
        if r.ads_filtered_buy or r.ads_filtered_sell:
            p = []
            if r.ads_filtered_buy:  p.append(f"BUY-{r.buy_ads_skipped}")
            if r.ads_filtered_sell: p.append(f"SELL-{r.sell_ads_skipped}")
            ads_info = "⚡ " + ", ".join(p)
        cap_source = "📊 Mercado" if r.capital_from_market else "⚠️ Simulado"
        rows.append({
            "Método":                  r.method_human,
            "Moneda":                  r.fiat,
            "Mi precio VENTA":         _fmt(r.buy_price_effective,  r.fiat),
            "Mi precio COMPRA":        _fmt(r.sell_price_effective, r.fiat),
            "Spread bruto":            _pct(r.spread_gross_pct),
            "Ganancia neta":           _pct(r.net_profit_pct),
            "Capital recomendado":     _fmt(r.capital_recommended_fiat, r.fiat, 0),
            "Capital en USDT":         _fmt(r.capital_recommended_usdt, "USDT"),
            "Fuente del capital":      cap_source,
            "Anunciante ref. VENTA":   r.ref_buy_ad_label,
            "Anunciante ref. COMPRA":  r.ref_sell_ad_label,
            "Anuncios filtrados":      ads_info,
        })
    st.markdown(_html_table(rows), unsafe_allow_html=True)


def render_discarded_table(results: List[SpreadResult]) -> None:
    disc = [r for r in results if r.status != "OK"]
    if not disc:
        st.info("Sin descartes. Todos los métodos tienen oportunidades válidas.")
        return
    rows = []
    for r in disc:
        detail = r.error_msg or ""
        hint   = STATUS_HINT.get(r.status, "")
        rows.append({
            "Método":                r.method_human,
            "Moneda":                r.fiat,
            "Estado":                STATUS_BADGE.get(r.status, r.status),
            "Anuncios COMPRA":       r.buy_ads_count,
            "Anuncios VENTA":        r.sell_ads_count,
            "Ganancia neta actual":  _pct(r.net_profit_pct),
            "Spread bruto":          _pct(r.spread_gross_pct),
            "Por qué fue descartado": detail,
            "Qué hacer":             hint,
        })
    st.markdown(_html_table(rows), unsafe_allow_html=True)


def render_chart(results: List[SpreadResult]) -> None:
    ok = sorted(
        [r for r in results if r.status == "OK" and r.net_profit_pct is not None],
        key=lambda r: r.net_profit_pct,
        reverse=True,
    )
    if not ok:
        return
    df = pd.DataFrame({
        "Método": [f"{r.method_human} ({r.fiat})" for r in ok],
        "Ganancia neta (%)": [round(r.net_profit_pct, 4) for r in ok],
        "Color": [
            "#00d68f" if r.net_profit_pct >= 2.0
            else "#69f0ae" if r.net_profit_pct >= 0.5
            else "#ffd740" if r.net_profit_pct >= 0.0
            else "#ef5350"
            for r in ok
        ],
    })
    order = df["Método"].tolist()
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(
                "Método:N",
                sort=order,
                axis=alt.Axis(
                    labelAngle=-35,
                    labelColor="#666",
                    titleColor="#555",
                    labelFontSize=11,
                    domainColor="rgba(255,255,255,0.06)",
                    tickColor="rgba(255,255,255,0.06)",
                ),
            ),
            y=alt.Y(
                "Ganancia neta (%):Q",
                title="Ganancia neta (%)",
                axis=alt.Axis(
                    labelColor="#666",
                    titleColor="#555",
                    gridColor="rgba(255,255,255,0.04)",
                    labelFontSize=11,
                    domainColor="rgba(255,255,255,0.06)",
                    tickColor="rgba(255,255,255,0.06)",
                ),
            ),
            color=alt.Color("Color:N", scale=None, legend=None),
            tooltip=[
                alt.Tooltip("Método:N", title="Método"),
                alt.Tooltip("Ganancia neta (%):Q", title="Ganancia neta", format=".4f"),
            ],
        )
        .properties(height=230, padding={"left": 8, "right": 8, "top": 12, "bottom": 8})
        .configure_view(strokeWidth=0)
        .configure(background="transparent")
    )
    st.altair_chart(chart, use_container_width=True)
