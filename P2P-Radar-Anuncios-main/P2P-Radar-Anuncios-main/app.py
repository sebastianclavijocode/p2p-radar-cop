"""
P2P Spread Radar — Bot de Alertas
===================================
Ejecutar: streamlit run app.py
"""
import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, ".")

from core.custom_methods import add_custom_method, load_custom_methods, save_custom_methods
from core.mapping import DEFAULT_MAPPINGS, load_mappings, save_mappings
from core.models import METHODS_CATALOG, SpreadResult
from core.scanner import scan_all_methods
from core.spread import analyze_opportunity
from ui.cards import build_alerts_html, build_dashboard_html, build_feed_html, build_hero_html, build_kpi_html, build_telegram_html
from ui.styles import GLASS_CSS
from ui.table import render_chart, render_discarded_table, render_ok_table

import exchanges.binance as binance_ex
import exchanges.bybit   as bybit_ex
import exchanges.bingx   as bingx_ex

# ── logging ───────────────────────────────────────────────────────────────────
log_records: List[str] = []

class _UIHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        log_records.append(self.format(record))
        if len(log_records) > 200:
            log_records.pop(0)

_root = logging.getLogger()
_root.setLevel(logging.DEBUG)
if not any(isinstance(h, _UIHandler) for h in _root.handlers):
    _h = _UIHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S"))
    _root.addHandler(_h)

logger = logging.getLogger("app")

EXCHANGES = {"Binance": binance_ex, "Bybit": bybit_ex, "BingX": bingx_ex}

# Comisiones maker de Binance P2P por fiat (verificado / no verificado)
BINANCE_MAKER_FEES: Dict[str, Dict[str, float]] = {
    "USD": {"verified": 0.28, "non_verified": 0.35},
    "ARS": {"verified": 0.16, "non_verified": 0.20},
    "EUR": {"verified": 0.0,  "non_verified": 0.0},
    "UYU": {"verified": 0.16, "non_verified": 0.20},
}

DEFAULT_CAPITAL: Dict[str, Dict] = {
    "ARS": {"target_min": 180_000, "target_max": 1_800_000, "simulado": 500_000},
    "USD": {"target_min": 200,     "target_max": 2_000,     "simulado": 500},
    "EUR": {"target_min": 200,     "target_max": 2_000,     "simulado": 500},
    "UYU": {"target_min": 8_000,   "target_max": 80_000,    "simulado": 20_000},
}

# ── helpers ───────────────────────────────────────────────────────────────────
def _pct(v, d=4): return "—" if v is None else f"{v:.{d}f}%"
def _fmt(v, s="", d=2): return "—" if v is None else f"{v:,.{d}f}{(' '+s) if s else ''}"

def _section(icon: str, title: str) -> None:
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:10px;margin:24px 0 10px;'>"
        f"<span style='font-size:15px;'>{icon}</span>"
        f"<span style='font-size:13px;font-weight:600;color:rgba(255,255,255,.85);"
        f"letter-spacing:0.1px;'>{title}</span>"
        f"<div style='flex:1;height:1px;background:rgba(255,255,255,0.06);margin-left:6px;'></div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── query engine ──────────────────────────────────────────────────────────────
def run_queries(
    exchange_name, asset, mappings,
    is_verified: bool,
    publication_mode, epsilon_fiat, epsilon_pct,
    fee_slippage_pct: float,
    exclude_ads, ad_threshold_pct,
    capital_cfg, buffer_pct,
    min_net_profit_pct, allow_outside_target, top_n,
    extra_methods: List[dict] = [],
    merchant_check: bool = True,
) -> List[SpreadResult]:
    exchange_mod = EXCHANGES[exchange_name]
    ex_key = exchange_name.lower()
    results: List[SpreadResult] = []
    catalog = METHODS_CATALOG + extra_methods

    for method in catalog:
        mid, mname, fiat = method["id"], method["human_name"], method["fiat"]
        # Custom methods carry their payment_id directly — validate exchange and auto-build mapping config
        if "_payment_id" in method:
            method_exchange = method.get("_exchange", "Binance")
            if method_exchange.lower() != ex_key:
                results.append(_stub(
                    "NOT_AVAILABLE",
                    f"Método configurado para {method_exchange}, no para {exchange_name}. "
                    f"Cambiá el exchange o agregá el método desde {method_exchange}."
                ))
                continue
            if mid not in mappings.get(ex_key, {}):
                method_cfg = {"payment_ids": [method["_payment_id"]], "available": True}
            else:
                method_cfg = mappings.get(ex_key, {}).get(mid, {})
        else:
            method_cfg = mappings.get(ex_key, {}).get(mid, {})

        def _stub(status, msg, _mid=mid, _mname=mname, _fiat=fiat):
            return SpreadResult(
                exchange=exchange_name, method_id=_mid, method_human=_mname,
                method_mapped="—", fiat=_fiat, asset=asset,
                buy_price_effective=None, sell_price_effective=None,
                spread_gross_pct=None, net_profit_pct=None,
                capital_min_fiat=None, capital_max_fiat=None,
                capital_recommended_fiat=None, capital_recommended_usdt=None,
                ref_buy_ad=None, ref_sell_ad=None,
                buy_ads_count=0, sell_ads_count=0,
                buy_ads_skipped=0, sell_ads_skipped=0,
                status=status, error_msg=msg,
                ref_buy_ad_label="—", ref_sell_ad_label="—",
            )

        if not method_cfg:
            results.append(_stub("MAPPING_REQUIRED", "Sin configuración de mapeo.")); continue
        if not method_cfg.get("available", False):
            continue  # método deshabilitado: no aparece en lista ni descartados
        if not exchange_mod.is_supported():
            results.append(_stub("NOT_AVAILABLE", exchange_mod.EXCHANGE_NOTE[:120])); continue

        pay_ids       = method_cfg.get("payment_ids", [])
        method_mapped = ", ".join(pay_ids) if pay_ids else "—"

        try:
            buy_ads  = exchange_mod.fetch_ads(asset=asset, fiat=fiat, trade_type="BUY",  pay_types=pay_ids, rows=top_n, merchant_check=merchant_check)
            sell_ads = exchange_mod.fetch_ads(asset=asset, fiat=fiat, trade_type="SELL", pay_types=pay_ids, rows=top_n, merchant_check=merchant_check)
        except Exception as exc:
            logger.error(f"{exchange_name} [{mid}]: {exc}\n{traceback.format_exc()}")
            results.append(_stub("ERROR", str(exc)[:120])); continue

        cap_cfg = capital_cfg.get(fiat, DEFAULT_CAPITAL.get(fiat, {"target_min": 200, "target_max": 2000, "simulado": 500}))
        if exchange_name == "Binance":
            fee_fiat_cfg = BINANCE_MAKER_FEES.get(fiat, {"verified": 0.0, "non_verified": 0.0})
            fee_exchange_pct = fee_fiat_cfg["verified"] if is_verified else fee_fiat_cfg["non_verified"]
        else:
            fee_exchange_pct = 0.0

        result = analyze_opportunity(
            buy_ads=buy_ads, sell_ads=sell_ads,
            exchange=exchange_name, method_id=mid, method_human=mname,
            method_mapped=method_mapped, fiat=fiat, asset=asset,
            fee_exchange_pct=fee_exchange_pct, fee_slippage_pct=fee_slippage_pct,
            fee_method_pct=0.0,
            fee_method_fixed=0.0,
            publication_mode=publication_mode,
            epsilon_fiat=epsilon_fiat, epsilon_pct=epsilon_pct,
            exclude_ads=exclude_ads, ad_threshold_pct=ad_threshold_pct,
            capital_target_min=cap_cfg["target_min"],
            capital_target_max=cap_cfg["target_max"],
            capital_simulado=cap_cfg["simulado"],
            buffer_pct=buffer_pct,
            min_net_profit_pct=min_net_profit_pct,
            allow_outside_target=allow_outside_target,
        )
        results.append(result)

    ok     = sorted([r for r in results if r.status == "OK"],
                    key=lambda r: r.net_profit_pct or -9999, reverse=True)
    others = [r for r in results if r.status != "OK"]
    return ok + others


# ── sidebar panels ────────────────────────────────────────────────────────────
def _mapping_panel(exchange_name: str, mappings: Dict, custom_methods: List[dict] = []) -> None:
    ex_key = exchange_name.lower()
    ex_cfg = mappings.get(ex_key, {})
    with st.expander("Métodos de pago configurados", expanded=False):
        st.caption(
            "Estos son los metodos de pago que el radar monitorea. "
            "Para agregar nuevos, usá la pestaña Diagnóstico → Descubrir métodos."
        )
        catalog_rows = [{
            "Metodo": m["human_name"], "Fiat": m["fiat"],
            "Activo": "Si",
            "ID en Binance": ", ".join(ex_cfg.get(m["id"], {}).get("payment_ids", [])) or "--",
        } for m in METHODS_CATALOG if ex_cfg.get(m["id"], {}).get("available", False)]
        custom_rows = [{
            "Metodo": m["human_name"], "Fiat": m["fiat"],
            "Activo": "Si",
            "ID en Binance": m["_payment_id"],
        } for m in custom_methods]
        from ui.table import _html_table
        st.markdown(_html_table(catalog_rows + custom_rows), unsafe_allow_html=True)



def _capital_panel() -> Dict:
    """Capital simplificado: el usuario ingresa cuanto quiere invertir por moneda."""
    caps = st.session_state.get("capital_cfg", json.loads(json.dumps(DEFAULT_CAPITAL)))
    with st.expander("Capital a invertir por moneda", expanded=False):
        st.caption(
            "Cuanto capital tenes disponible para operar en cada moneda. "
            "Se usa para calcular cuantos USDT podrias comprar/vender en cada operacion."
        )
        for fiat, defs in DEFAULT_CAPITAL.items():
            cur = caps.get(fiat, defs)
            simulado = st.number_input(
                f"Capital en {fiat}",
                min_value=0.0,
                value=float(cur["simulado"]),
                step=100.0,
                key=f"csim_{fiat}",
                help=f"Cuanto {fiat} tenes para operar. El radar calcula la ganancia sobre este monto.",
            )
            caps[fiat] = {
                "target_min": simulado,
                "target_max": simulado,
                "simulado":   simulado,
            }
    st.session_state["capital_cfg"] = caps
    return caps


# ── KPI row ───────────────────────────────────────────────────────────────────
def _render_kpis(ok_count, best_net, best_cap, best_cap_fiat, best_cap_usdt, best_ars_cap, last_upd) -> None:
    if best_cap_usdt is not None:
        cap_str = f"~{best_cap_usdt:,.0f} USDT"
    elif best_cap is not None:
        cap_str = f"{best_cap:,.0f} {best_cap_fiat}"
    else:
        cap_str = "—"
    upd_s = last_upd.strftime("%H:%M:%S") if last_upd else "—"
    html = build_hero_html(ok_count, best_net, cap_str, upd_s)
    components.html(html, height=168, scrolling=False)


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    st.set_page_config(
        page_title="P2P Spread Radar · Bot de Alertas",
        page_icon="🤖", layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(GLASS_CSS, unsafe_allow_html=True)

    for k, v in [
        ("results",         []),
        ("last_update",     None),
        ("last_exchange",   None),
        ("mappings",        load_mappings()),
        ("capital_cfg",     json.loads(json.dumps(DEFAULT_CAPITAL))),
        ("custom_methods",  load_custom_methods()),
    ]:
        if k not in st.session_state:
            st.session_state[k] = v

    # ── SIDEBAR ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            "<link rel='stylesheet' href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css'>"
            "<style>"
            ".p2p-brand { margin-bottom: 2px; }"
            ".p2p-brand-name { font-size:20px; font-weight:900; color:#fff; letter-spacing:-0.5px; }"
            ".p2p-brand-dot  { color:#00d68f; }"
            ".p2p-sub { font-size:11.5px; color:rgba(255,255,255,0.38); margin-top:5px; display:flex; align-items:center; gap:6px; }"
            ".p2p-mode { background:rgba(0,214,143,0.09); border:1px solid rgba(0,214,143,0.22); color:#00d68f;"
            "  font-size:9.5px; font-weight:700; text-transform:uppercase; letter-spacing:1.2px;"
            "  padding:2px 8px; border-radius:20px; }"
            ".p2p-help { display:inline-flex; align-items:center; justify-content:center;"
            "  width:15px; height:15px; border-radius:50%;"
            "  background:transparent; border:1px solid rgba(255,193,7,0.4);"
            "  color:#FFC107; font-size:9px; font-weight:700; cursor:default;"
            "  position:relative; font-style:normal; }"
            ".p2p-help:hover .p2p-tooltip { display:block; }"
            ".p2p-tooltip { display:none; position:absolute; left:20px; top:-10px; width:220px;"
            "  background:#1a2035; border:1px solid rgba(255,255,255,0.1); border-radius:10px;"
            "  padding:10px 12px; font-size:11px; color:rgba(255,255,255,0.7); line-height:1.6;"
            "  z-index:999; box-shadow:0 8px 24px rgba(0,0,0,0.5); pointer-events:none; }"
            ".p2p-dev { font-size:10.5px; color:rgba(255,255,255,0.3); margin-top:10px; }"
            ".p2p-dev span { color:#00d68f; font-weight:700; }"
            ".p2p-divider { height:1px; background:rgba(255,255,255,0.05); margin:14px 0; }"
            "</style>"
            "<div class='p2p-brand'>"
            "  <div class='p2p-brand-name'>P2P Radar<span class='p2p-brand-dot'>.</span></div>"
            "  <div class='p2p-sub'>"
            "    Binance P2P"
            "    <span class='p2p-mode'>Yo Publico</span>"
            "    <i class='p2p-help' style='font-family:inherit'>"
            "      ?"
            "      <span class='p2p-tooltip'>"
            "        <b style='color:#fff'>Modo Yo Publico</b><br>"
            "        Publicás tus propios anuncios en Binance P2P compitiendo con el top del libro."
            "        Vendés USDT en tab Comprar al precio más alto y recomprás en tab Vender al más bajo."
            "        La ganancia es la diferencia menos comisiones."
            "      </span>"
            "    </i>"
            "  </div>"
            "</div>"
            "<div class='p2p-divider'></div>"
            "<div class='p2p-dev'>Desarrollado por <span>Ezequiel Sack</span></div>"
            "<div style='display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;'>"
            "<a href='https://t.me/EzequielSackTelegram' target='_blank' title='Telegram' style='display:flex;align-items:center;justify-content:center;"
            "width:32px;height:32px;border-radius:8px;background:rgba(41,182,246,0.12);"
            "border:1px solid rgba(41,182,246,0.25);color:#29B6F6;font-size:15px;text-decoration:none;'>"
            "<i class='fab fa-telegram'></i></a>"
            "<a href='https://www.instagram.com/ezequielsack/' target='_blank' title='Instagram' style='display:flex;align-items:center;justify-content:center;"
            "width:32px;height:32px;border-radius:8px;background:rgba(225,48,108,0.1);"
            "border:1px solid rgba(225,48,108,0.22);color:#E1306C;font-size:15px;text-decoration:none;'>"
            "<i class='fab fa-instagram'></i></a>"
            "<a href='https://www.threads.com/@ezequielsack?hl=es-la' target='_blank' title='Threads' style='display:flex;align-items:center;justify-content:center;"
            "width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,0.06);"
            "border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.75);font-size:15px;text-decoration:none;'>"
            "<i class='fab fa-threads'></i></a>"
            "<a href='https://open.spotify.com/show/4OqJ0tFSyxbQl2tRHLoby3?si=fe132beadedc4710' target='_blank' title='Spotify' style='display:flex;align-items:center;justify-content:center;"
            "width:32px;height:32px;border-radius:8px;background:rgba(29,185,84,0.1);"
            "border:1px solid rgba(29,185,84,0.22);color:#1DB954;font-size:15px;text-decoration:none;'>"
            "<i class='fab fa-spotify'></i></a>"
            "<a href='https://www.linkedin.com/in/ezequiel-sack-28154a17b/' target='_blank' title='LinkedIn' style='display:flex;align-items:center;justify-content:center;"
            "width:32px;height:32px;border-radius:8px;background:rgba(10,102,194,0.12);"
            "border:1px solid rgba(10,102,194,0.28);color:#0A66C2;font-size:15px;text-decoration:none;'>"
            "<i class='fab fa-linkedin'></i></a>"
            "<a href='https://twitter.com/EzequielSack' target='_blank' title='X / Twitter' style='display:flex;align-items:center;justify-content:center;"
            "width:32px;height:32px;border-radius:8px;background:rgba(255,255,255,0.06);"
            "border:1px solid rgba(255,255,255,0.15);color:rgba(255,255,255,0.8);font-size:15px;text-decoration:none;'>"
            "<i class='fab fa-x-twitter'></i></a>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        with st.expander("Exchange", expanded=True):
            exchange_name = st.selectbox("Exchange",
                ["Binance", "Bybit"],
                help="El exchange donde se buscan los anuncios P2P. BingX no tiene API pública y no está soportado.",
                label_visibility="collapsed")
        with st.expander("Cripto", expanded=True):
            asset = st.selectbox("Cripto",
                ["USDT"],
                help="La criptomoneda que se compra y vende. USDT es la más común en P2P.",
                label_visibility="collapsed")

        st.divider()
        prev_merchant = st.session_state.get("_prev_merchant_check", True)
        with st.expander("Filtros de oportunidad", expanded=True):
            min_net = st.number_input("Ganancia minima (%)", -50.0, 50.0, 0.0, 0.05, "%.2f",
                help="Solo muestra oportunidades con esta ganancia neta o más. "
                     "0% = muestra todo. 1% = solo oportunidades con al menos 1% de ganancia después de fees.")
            allow_out = st.toggle("Ignorar límite de capital",
                value=True,
                help="Si está activado, muestra oportunidades aunque el capital recomendado quede fuera del rango objetivo.")

        with st.expander("Consulta al mercado", expanded=True):
            top_n = st.slider("Anuncios a analizar", 3, 20, 10,
                help="Cuántos anuncios del mercado se analizan por lado (compra y venta). "
                     "Más anuncios = más preciso pero más lento.")
        buf_pct = 1.0

        with st.expander("Filtro de anuncios", expanded=True):
            merchant_check = st.toggle("Solo comerciantes verificados",
                value=True,
                help="Activado: muestra solo anuncios de comerciantes verificados (Pro Merchants de Binance) "
                     "y aplica comisión maker reducida. "
                     "Desactivado: incluye todos y aplica comisión estándar.")
            excl_ads = st.toggle("Excluir anuncios pagos",
                value=True,
                help="Algunos anuncios son publicidad pagada con precios fuera del mercado real. "
                     "Activar para ignorarlos y usar solo el precio real del mercado.")
        if merchant_check != prev_merchant:
            st.warning("⚠️ Presioná **Actualizar** para aplicar el cambio.")
        st.session_state["_prev_merchant_check"] = merchant_check
        ad_thresh = 999.0

        with st.expander("Estrategia de publicación", expanded=True):
            beat_top = st.toggle(
                "Beat top (superar al primero)",
                value=False,
                help="Activado: publicás ligeramente mejor que el top del libro para quedar primero en la cola. "
                     "Desactivado: publicás al mismo precio que el top (match_top).",
            )
            pub_mode = "beat_top" if beat_top else "match_top"
            eps_fiat = 0.0
            eps_pct  = st.number_input(
                "Epsilon (%)",
                min_value=0.0, max_value=1.0, value=0.05, step=0.01, format="%.2f",
                help="Cuánto mejorar el precio del top para ganar prioridad. Solo se usa en modo beat_top.",
                disabled=not beat_top,
            ) if beat_top else 0.0
            fee_slippage_pct = st.number_input(
                "Slippage (%)",
                min_value=0.0, max_value=2.0, value=0.0, step=0.05, format="%.2f",
                help="Coste estimado de deslizamiento por ejecución parcial o demoras. "
                     "0% = sin slippage. Se descuenta del net profit.",
            )

        # is_verified se deriva de merchant_check:
        # si filtrás solo verificados → vos también sos verificado → comisión reducida
        # si incluís no verificados → comisión de no verificado
        is_verified = merchant_check

        st.divider()
        if exchange_name == "Binance":
            rows_html = "".join(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:9px 14px;border-bottom:1px solid rgba(255,255,255,0.05);">'
                f'<span style="font-size:12px;font-weight:700;color:rgba(255,255,255,0.65);'
                f'text-transform:uppercase;letter-spacing:0.8px;">{fk}</span>'
                f'<span style="font-size:13px;font-weight:800;color:#00d68f;">'
                f'{(fv["verified"] if is_verified else fv["non_verified"]):.2f}%</span></div>'
                for fk, fv in BINANCE_MAKER_FEES.items()
            )
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.025);border:1px solid rgba(0,214,143,0.22);'
                f'border-left:3px solid #00d68f;border-radius:10px;overflow:hidden;margin-top:4px;">'
                f'<div style="padding:10px 14px 8px;border-bottom:1px solid rgba(255,255,255,0.06);">'
                f'<div style="font-size:12px;text-transform:uppercase;letter-spacing:1px;'
                f'color:rgba(255,255,255,0.75);font-weight:700;">Comisión maker por divisa</div>'
                f'<div style="font-size:10px;color:rgba(255,255,255,0.25);margin-top:3px;line-height:1.4;">'
                f'Se descuenta del net profit según la divisa.</div>'
                f'</div>'
                f'{rows_html}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Sin comisión (0%)")

        st.divider()
        caps = _capital_panel()
        _mapping_panel(exchange_name, st.session_state["mappings"], st.session_state.get("custom_methods", []))
        st.divider()

        refresh = st.button("Actualizar ahora", use_container_width=True, type="primary")


    # ── QUERY ─────────────────────────────────────────────────────────────────
    if refresh or (
        st.session_state["last_exchange"] != exchange_name
        and not st.session_state["results"]
    ):
        with st.spinner(f"Consultando {exchange_name} P2P…"):
            res = run_queries(
                exchange_name=exchange_name, asset=asset,
                mappings=st.session_state["mappings"],
                is_verified=is_verified,
                publication_mode=pub_mode,
                epsilon_fiat=eps_fiat, epsilon_pct=eps_pct,
                fee_slippage_pct=fee_slippage_pct,
                exclude_ads=excl_ads, ad_threshold_pct=ad_thresh,
                capital_cfg=caps, buffer_pct=buf_pct,
                min_net_profit_pct=min_net, allow_outside_target=allow_out,
                top_n=top_n,
                extra_methods=st.session_state.get("custom_methods", []),
                merchant_check=merchant_check,
            )
        st.session_state["results"]       = res
        st.session_state["last_update"]   = datetime.now()
        st.session_state["last_exchange"] = exchange_name

    results: List[SpreadResult] = st.session_state["results"]

    if not results:
        st.info("Presioná **Actualizar** en el sidebar para comenzar.")
        return

    ok_results = [r for r in results if r.status == "OK"]
    disc_count = len(results) - len(ok_results)

    # ── 1. KPI / HERO (topbar + métricas) ────────────────────────────────────
    kpi_html = build_kpi_html(
        results=results,
        exchange_name=exchange_name,
        asset=asset,
        last_upd=st.session_state["last_update"],
    )
    components.html(kpi_html, height=290, scrolling=False)

    # ── 2. GRÁFICO DE BARRAS ──────────────────────────────────────────────────
    st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
    if ok_results:
        render_chart(results)

    # ── 3. ALERTAS ────────────────────────────────────────────────────────────
    alerts_html = build_alerts_html(results)
    alerts_height = 80 + max(len(ok_results) * 280, 200)
    components.html(alerts_html, height=alerts_height, scrolling=True)

    # ── VISTAS SECUNDARIAS (tabs debajo del dashboard) ────────────────────────
    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    tab_scan, tab_tg, tab_table, tab_disc, tab_diag = st.tabs([
        "🔁 Escaneo",
        "📱 Telegram",
        "📊 Tabla",
        f"🗑️ Descartadas ({disc_count})",
        "🔬 Diagnóstico",
    ])

    # ── TAB: ESCANEO AUTOMÁTICO ───────────────────────────────────────────────
    with tab_scan:
        _section("🔁", "Escaneo automático — todos los métodos")
        st.caption(
            "Escanea Binance P2P sin filtro de método de pago. "
            "Detecta spreads en CUALQUIER método disponible. "
            "No necesita configuración de catálogo."
        )

        sc1, sc2, sc3 = st.columns(3)
        scan_fiats   = sc1.multiselect("Monedas", ["USD", "EUR", "ARS", "UYU"], default=["USD", "EUR"], key="scan_fiats")
        scan_min_net = sc2.number_input("Umbral net (%)", -50.0, 50.0, 0.0, 0.05, "%.2f", key="scan_min")
        scan_rows    = sc3.slider("Ads por lado", 10, 50, 20, key="scan_rows")

        if st.button("🔁 Escanear ahora", use_container_width=True, type="primary", key="scan_btn"):
            all_scan: List[SpreadResult] = []
            with st.spinner("Escaneando todos los métodos…"):
                for fiat_s in scan_fiats:
                    try:
                        b_ads = binance_ex.fetch_ads(asset=asset, fiat=fiat_s, trade_type="BUY",  pay_types=[], rows=scan_rows, merchant_check=merchant_check)
                        s_ads = binance_ex.fetch_ads(asset=asset, fiat=fiat_s, trade_type="SELL", pay_types=[], rows=scan_rows, merchant_check=merchant_check)
                        scan_fee_cfg = BINANCE_MAKER_FEES.get(fiat_s, {"verified": 0.0, "non_verified": 0.0})
                        scan_fee = scan_fee_cfg["verified"] if is_verified else scan_fee_cfg["non_verified"]
                        cap_cfg_s = caps.get(fiat_s, DEFAULT_CAPITAL.get(fiat_s, {"target_min": 200, "target_max": 2000, "simulado": 500}))
                        partial = scan_all_methods(
                            buy_ads_raw=b_ads, sell_ads_raw=s_ads,
                            fiat=fiat_s, asset=asset,
                            exchange=exchange_name,
                            fee_exchange_pct=scan_fee,
                            capital_target_min=cap_cfg_s["target_min"],
                            capital_target_max=cap_cfg_s["target_max"],
                            capital_simulado=cap_cfg_s["simulado"],
                            min_spread_pct=scan_min_net,
                            exclude_ads=excl_ads,
                            ad_threshold_pct=ad_thresh,
                        )
                        all_scan.extend(partial)
                    except Exception as exc:
                        st.error(f"Error escaneando {fiat_s}: {exc}")

            st.session_state["scan_results"] = all_scan

        scan_results: List[SpreadResult] = st.session_state.get("scan_results", [])

        if scan_results:
            ok_scan = [r for r in scan_results if r.status == "OK"]
            st.success(f"✅ {len(ok_scan)} métodos con spread positivo encontrados ({len(scan_results)} totales con datos)")
            rows_s = []
            for r in scan_results:
                cap_src = "📊 Mercado" if r.capital_from_market else "⚠️ Simulado"
                rows_s.append({
                    "Método de pago":           r.method_human,
                    "Fiat":                     r.fiat,
                    "Estado":                   "🟢 OK" if r.status == "OK" else "🟡 Bajo umbral",
                    # buy_price_effective = precio que publico en tab COMPRAR (mi anuncio de VENTA, el mayor)
                    # sell_price_effective = precio que publico en tab VENDER (mi recompra, el menor)
                    "Mi VENTA (tab Comprar)":   _fmt(r.buy_price_effective,  r.fiat, 4),
                    "Mi COMPRA (tab Vender)":   _fmt(r.sell_price_effective, r.fiat, 4),
                    "Spread bruto":             _pct(r.spread_gross_pct),
                    "Ganancia neta":            _pct(r.net_profit_pct),
                    "Cap. rec.":                _fmt(r.capital_recommended_fiat, r.fiat, 0),
                    "Cap. fuente":              cap_src,
                    "Ref VENTA":                r.ref_buy_ad_label,
                    "Ref COMPRA":               r.ref_sell_ad_label,
                })
            from ui.table import _html_table
            st.markdown(_html_table(rows_s), unsafe_allow_html=True)
            st.caption(
                "Modo Yo Publico: "
                "**Mi VENTA** = precio que publicás en la tab Comprar de Binance (tu anuncio de venta, el mayor). "
                "**Mi COMPRA** = precio que publicás en la tab Vender (tu recompra, el menor). "
                "Spread = VENTA − COMPRA. "
                "📊 Cap. fuente Mercado = capital basado en liquidez real. "
                "⚠️ Simulado = mercado con poca liquidez, se usó tu capital configurado."
            )
        elif "scan_results" in st.session_state:
            st.info("Sin métodos con datos de precio en este momento.")

    # ── TAB: TELEGRAM ─────────────────────────────────────────────────────────
    with tab_tg:
        _section("📱", "Vista previa — formato Telegram")
        st.caption("Así se ve el mensaje en tu bot de Telegram.")
        tg_html = build_telegram_html(results)
        components.html(tg_html, height=max(len(ok_results) * 480 + 80, 300), scrolling=True)

        if ok_results:
            st.divider()
            with st.expander("📋 Texto plano para copiar", expanded=False):
                for r in ok_results:
                    buy  = r.ref_buy_ad
                    sell = r.ref_sell_ad
                    pct  = r.net_profit_pct or 0

                    def pays(ad):
                        if not ad or not ad.payment_methods: return "—"
                        return ", ".join([m for m in ad.payment_methods if m][:5])

                    txt = (
                        f"🤖 Bot de Alertas P2P\n"
                        f"Diferencia: {pct:.2f}% 💰\n\n"
                        f"COMPRA P2P\n"
                        f"🍒 Cripto: {r.asset}\n"
                        f"🏷️ Vendedor: {buy.advertiser_name if buy else '—'}\n"
                        f"💵 Precio: {_fmt(r.buy_price_effective, r.fiat)} (1 {r.asset})\n"
                        f"✅ Disponible: {f'{buy.available_amount:.8f}' if buy else '—'} {r.asset}\n"
                        f"🔴 Límite: {f'{buy.min_amount:,.2f}' if buy else '—'} – {f'{buy.max_amount:,.2f}' if buy else '—'} {r.fiat}\n"
                        f"🟰 Métodos: {pays(buy)}\n\n"
                        f"VENTA P2P\n"
                        f"🍒 Cripto: {r.asset}\n"
                        f"🏷️ Vendedor: {sell.advertiser_name if sell else '—'}\n"
                        f"💵 Precio: {_fmt(r.sell_price_effective, r.fiat)} (1 {r.asset})\n"
                        f"✅ Disponible: {f'{sell.available_amount:.8f}' if sell else '—'} {r.asset}\n"
                        f"🔴 Límite: {f'{sell.min_amount:,.2f}' if sell else '—'} – {f'{sell.max_amount:,.2f}' if sell else '—'} {r.fiat}\n"
                        f"🟰 Métodos: {pays(sell)}"
                    )
                    st.code(txt, language="")
                    st.divider()

    # ── TAB: TABLA ────────────────────────────────────────────────────────────
    with tab_table:
        _section("📊", "Tabla — oportunidades válidas")
        render_ok_table(results)

    # ── TAB: DESCARTADAS ──────────────────────────────────────────────────────
    with tab_disc:
        st.caption(
            "Métodos sin oportunidad. "
            "'Net bajo' → bajá el umbral. "
            "'Sin anuncios' → verificá el Mapeo de métodos."
        )
        render_discarded_table(results)

    # ── TAB: DIAGNÓSTICO ──────────────────────────────────────────────────────
    with tab_diag:
        _section("🔬", "Diagnóstico — todos los métodos")
        st.caption(
            "Esta tabla muestra datos brutos de TODOS los métodos sin importar el umbral. "
            "'NO_ADS' con 0 anuncios = ID de pago incorrecto. "
            "Usá el botón de abajo para descubrir los IDs reales de Binance."
        )

        diag_rows = []
        for r in results:
            diag_rows.append({
                "Método":                r.method_human,
                "Moneda":                r.fiat,
                "Estado":                r.status,
                "Anuncios COMPRA":       r.buy_ads_count,
                "Anuncios VENTA":        r.sell_ads_count,
                "Mi precio VENTA":       f"{r.buy_price_effective:,.4f}" if r.buy_price_effective else "—",
                "Mi precio COMPRA":      f"{r.sell_price_effective:,.4f}" if r.sell_price_effective else "—",
                "Spread bruto":          f"{r.spread_gross_pct:.4f}%" if r.spread_gross_pct is not None else "—",
                "Ganancia neta":         f"{r.net_profit_pct:.4f}%" if r.net_profit_pct is not None else "—",
                "IDs de pago":           r.method_mapped,
                "Detalle":               (r.error_msg or "")[:80],
            })
        if diag_rows:
            from ui.table import _html_table
            st.markdown(_html_table(diag_rows), unsafe_allow_html=True)

        st.divider()
        _section("🔎", "Buscar método de pago por nombre")
        st.caption(
            "Ingresá el nombre exacto (o parcial) del método de pago tal como aparece en Binance. "
            "Se consultan ambas tabs (Comprar y Vender) y si hay anuncios podés agregarlo al radar."
        )
        pm_col1, pm_col2, pm_col3 = st.columns([3, 1, 1])
        pm_search_name = pm_col1.text_input(
            "Nombre del método de pago",
            placeholder="Ej: WallyTech, Zinli, Facebank...",
            key="pm_search_name",
        )
        pm_search_fiat = pm_col2.selectbox("Moneda", ["USD", "ARS", "EUR", "UYU"], key="pm_search_fiat")
        pm_search_rows = pm_col3.slider("Ads a traer", 10, 50, 20, key="pm_search_rows")

        if st.button("🔎 Buscar método", type="primary", key="pm_search_btn"):
            if not pm_search_name.strip():
                st.warning("Ingresá un nombre de método de pago.")
            else:
                with st.spinner(f"Buscando '{pm_search_name}' en {pm_search_fiat}…"):
                    try:
                        pm_buy  = binance_ex.fetch_ads(asset=asset, fiat=pm_search_fiat, trade_type="BUY",
                                                       pay_types=[pm_search_name.strip()], rows=pm_search_rows,
                                                       merchant_check=False)
                        pm_sell = binance_ex.fetch_ads(asset=asset, fiat=pm_search_fiat, trade_type="SELL",
                                                       pay_types=[pm_search_name.strip()], rows=pm_search_rows,
                                                       merchant_check=False)
                        # Recolectar todos los IDs reales encontrados
                        real_ids: set = set()
                        for ad in pm_buy + pm_sell:
                            for m in ad.payment_methods:
                                if m and pm_search_name.strip().lower() in m.lower():
                                    real_ids.add(m)
                        st.session_state["pm_search_result"] = {
                            "name": pm_search_name.strip(),
                            "fiat": pm_search_fiat,
                            "buy_count": len(pm_buy),
                            "sell_count": len(pm_sell),
                            "real_ids": sorted(real_ids),
                            "sample_buy":  [{"Anunciante": a.advertiser_name, "Precio": f"{a.price:,.4f} {pm_search_fiat}",
                                             "Disponible": f"{a.available_amount:,.2f} {asset}",
                                             "Métodos": ", ".join(a.payment_methods[:3])} for a in pm_buy[:5]],
                            "sample_sell": [{"Anunciante": a.advertiser_name, "Precio": f"{a.price:,.4f} {pm_search_fiat}",
                                             "Disponible": f"{a.available_amount:,.2f} {asset}",
                                             "Métodos": ", ".join(a.payment_methods[:3])} for a in pm_sell[:5]],
                        }
                    except Exception as exc:
                        st.error(f"Error buscando: {exc}")

        if "pm_search_result" in st.session_state:
            res_pm = st.session_state["pm_search_result"]
            buy_c, sell_c = res_pm["buy_count"], res_pm["sell_count"]
            real_ids = res_pm["real_ids"]

            if buy_c == 0 and sell_c == 0:
                st.error(f"No se encontraron anuncios para '{res_pm['name']}' en {res_pm['fiat']}. Verificá el nombre exacto.")
            else:
                st.success(f"✅ '{res_pm['name']}' en {res_pm['fiat']}: **{buy_c}** anuncios en tab Comprar · **{sell_c}** en tab Vender")
                if real_ids:
                    st.info(f"IDs reales encontrados en Binance: `{'`, `'.join(real_ids)}`")
                from ui.table import _html_table
                rc1, rc2 = st.columns(2)
                with rc1:
                    st.caption("Tab Comprar (anunciantes vendiendo)")
                    if res_pm["sample_buy"]:
                        st.markdown(_html_table(res_pm["sample_buy"]), unsafe_allow_html=True)
                with rc2:
                    st.caption("Tab Vender (anunciantes comprando)")
                    if res_pm["sample_sell"]:
                        st.markdown(_html_table(res_pm["sample_sell"]), unsafe_allow_html=True)

                st.markdown("**Agregar al radar**")
                add2_col1, add2_col2, add2_col3 = st.columns(3)
                id_options = real_ids if real_ids else [res_pm["name"]]
                sel_real_id  = add2_col1.selectbox("ID real en Binance", id_options, key="pm_add_real_id")
                add2_name    = add2_col2.text_input("Nombre visible", value=res_pm["name"], key="pm_add_name")
                add2_fiat    = add2_col3.selectbox("Moneda", ["USD", "ARS", "EUR", "UYU"],
                                                   index=["USD","ARS","EUR","UYU"].index(res_pm["fiat"])
                                                   if res_pm["fiat"] in ["USD","ARS","EUR","UYU"] else 0,
                                                   key="pm_add_fiat")
                if st.button("➕ Agregar al radar", type="primary", key="pm_add_btn"):
                    method_id = sel_real_id.lower().replace(" ", "_").replace("-", "_")
                    custom = st.session_state.get("custom_methods", [])
                    already = any(m["id"] == method_id for m in custom) or \
                              any(m["id"] == method_id for m in METHODS_CATALOG)
                    if already:
                        st.warning(f"'{add2_name}' ya está en el radar.")
                    else:
                        custom = add_custom_method(custom, method_id, add2_name, add2_fiat, sel_real_id, exchange=exchange_name)
                        save_custom_methods(custom)
                        st.session_state["custom_methods"] = custom
                        st.success(f"✅ '{add2_name}' agregado. Presioná **Actualizar** para incluirlo.")
                        st.rerun()

        st.divider()
        _section("🔍", "Descubrir métodos de pago disponibles en Binance")
        st.caption(
            "Escanea Binance SIN filtro de comerciante para ver TODOS los métodos disponibles. "
            "Desde acá podés agregar cualquiera al radar con un click."
        )
        disc_fiats = st.multiselect(
            "Monedas a escanear",
            ["USD", "EUR", "ARS", "UYU"],
            default=["USD"],
            key="disc_fiats",
            help="Seleccioná una o varias monedas. Cada moneda hace 2 consultas a Binance."
        )
        disc_pm_filter = st.text_input(
            "Filtrar por método de pago (opcional)",
            placeholder="Ej: Prex, Zinli, Facebank… — dejá vacío para ver todos",
            key="disc_pm_filter",
        )
        disc_n = st.slider("Anuncios por moneda", 5, 20, 20, key="disc_n")
        if st.button("🔍 Escanear métodos disponibles", key="disc_btn"):
            if not disc_fiats:
                st.warning("Seleccioná al menos una moneda.")
            else:
                import time as _time
                all_by_fiat: Dict[str, Dict[str, int]] = {}
                errors = []
                prog = st.progress(0, text="Iniciando…")
                total = len(disc_fiats)
                for i, fiat_d in enumerate(disc_fiats):
                    prog.progress((i) / total, text=f"Consultando {fiat_d}…")
                    try:
                        # merchant_check=False: descubrimiento completo sin restricción de merchants
                        # (merchantCheck=True + rows>30 da error 000002 en la API de Binance)
                        buy_raw  = binance_ex.fetch_ads(asset=asset, fiat=fiat_d, trade_type="BUY",  pay_types=[], rows=disc_n, merchant_check=False)
                        _time.sleep(1.5)
                        sell_raw = binance_ex.fetch_ads(asset=asset, fiat=fiat_d, trade_type="SELL", pay_types=[], rows=disc_n, merchant_check=False)
                        _time.sleep(1.5)
                        methods: Dict[str, int] = {}
                        for ad in buy_raw + sell_raw:
                            for pm in ad.payment_methods:
                                if pm:
                                    methods[pm] = methods.get(pm, 0) + 1
                        if methods:
                            all_by_fiat[fiat_d] = methods
                        else:
                            errors.append(f"{fiat_d}: sin anuncios retornados por Binance")
                    except Exception as exc:
                        errors.append(f"{fiat_d}: {exc}")
                prog.progress(1.0, text="Listo")

                if errors:
                    for e in errors:
                        st.error(e)

                combined = []
                for fiat_d, methods in all_by_fiat.items():
                    for pm, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
                        combined.append({"Moneda": fiat_d, "Método de pago": pm, "Anuncios activos (liquidez)": count})

                if combined:
                    st.session_state["disc_methods_v2"] = combined
                else:
                    st.warning(
                        "Sin resultados. Posibles causas: Binance bloqueó la consulta (rate limit), "
                        "la moneda no tiene anuncios activos, o hubo un error de red. "
                        "Esperá 30 segundos y volvé a intentar."
                    )

        if "disc_methods_v2" in st.session_state:
            combined = st.session_state["disc_methods_v2"]
            pm_filter = st.session_state.get("disc_pm_filter", "").strip().lower()
            filtered_combined = [r for r in combined if pm_filter in r["Método de pago"].lower()] if pm_filter else combined
            st.success(f"✅ {len(filtered_combined)} método{'s' if len(filtered_combined) != 1 else ''} {'que coinciden' if pm_filter else 'encontrados'} ({len(combined)} total)")
            from ui.table import _html_table
            st.markdown(_html_table(filtered_combined), unsafe_allow_html=True)
            method_ids = list(dict.fromkeys(r["Método de pago"] for r in filtered_combined))
            disc_fiat_sel = filtered_combined[0]["Moneda"] if filtered_combined else "USD"

            st.divider()
            st.markdown("**Agregar método al radar**")
            st.caption("Seleccioná un método de la lista para monitorearlo.")
            add_col1, add_col2, add_col3 = st.columns(3)
            sel_pm   = add_col1.selectbox("Método de pago", method_ids, key="add_pm")
            # Auto-detect fiat from the combined results
            auto_fiat = next((r["Moneda"] for r in combined if r["Método de pago"] == sel_pm), disc_fiat_sel)
            add_name = add_col2.text_input("Nombre visible", value=sel_pm, key="add_name")
            add_fiat = add_col3.selectbox("Moneda", ["USD", "ARS", "EUR", "UYU"],
                                          index=["USD","ARS","EUR","UYU"].index(auto_fiat)
                                          if auto_fiat in ["USD","ARS","EUR","UYU"] else 0,
                                          key="add_fiat")

            if st.button("➕ Agregar al radar", type="primary", key="add_method_btn"):
                method_id = sel_pm.lower().replace(" ", "_").replace("-", "_")
                custom = st.session_state.get("custom_methods", [])
                already = any(m["id"] == method_id for m in custom) or \
                          any(m["id"] == method_id for m in METHODS_CATALOG)
                if already:
                    st.warning(f"'{add_name}' ya está en el radar.")
                else:
                    custom = add_custom_method(custom, method_id, add_name, add_fiat, sel_pm, exchange=exchange_name)
                    save_custom_methods(custom)
                    st.session_state["custom_methods"] = custom
                    st.success(f"✅ '{add_name}' agregado. Presioná **Actualizar** para incluirlo en el análisis.")
                    st.rerun()

        # Métodos custom activos
        custom_active = st.session_state.get("custom_methods", [])
        if custom_active:
            st.divider()
            st.markdown("**Métodos personalizados activos**")
            rows_c = [{"Método": m["human_name"], "Fiat": m["fiat"], "ID Binance": m["_payment_id"]} for m in custom_active]
            from ui.table import _html_table
            st.markdown(_html_table(rows_c), unsafe_allow_html=True)
            if st.button("🗑️ Eliminar todos los personalizados", key="del_custom"):
                st.session_state["custom_methods"] = []
                save_custom_methods([])
                st.rerun()



main()
