"""Dashboard HTML — diseño SaaS premium, una sola página custom."""
import base64
import io
import os
from datetime import datetime
from typing import List, Optional

from core.models import P2PAd, SpreadResult
from ui.styles import CARD_CSS, DASHBOARD_CSS


def _logo_data_uri() -> str:
    """Lee static/logo.png, lo redimensiona a 100x100 y devuelve data URI base64."""
    path = os.path.join(os.path.dirname(__file__), "..", "static", "logo.png")
    try:
        from PIL import Image
        img = Image.open(path).convert("RGBA")
        img = img.resize((100, 100), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""


# ── helpers ───────────────────────────────────────────────────────────────────

def _fp(price: float, fiat: str) -> str:
    if price >= 1000: return f"{price:,.2f}"
    if price >= 1:    return f"{price:.4g}"
    return f"{price:.4f}"

def _gc(pct: float) -> tuple:
    """Retorna (clase CSS de color, clase de acento izquierdo)."""
    if pct >= 2.0: return "chi", "hi"
    if pct >= 0.5: return "cmi", "mid"
    if pct >= 0.0: return "clo", "low"
    return "cne", "neg"

def _pays(ad: P2PAd, n: int = 3) -> str:
    if not ad.payment_methods: return "sin datos"
    methods = [m for m in ad.payment_methods if m][:n]
    extra = len(ad.payment_methods) - len(methods)
    return ", ".join(methods) + (f" +{extra}" if extra > 0 else "")

# kept for compat
def _side_html(label, css_class, ad, price_eff, fiat, asset, filtered, skipped):
    return ""


# ── Alert card HTML (dentro del dashboard) ────────────────────────────────────

def _alert_html(r: SpreadResult) -> str:
    pct   = r.net_profit_pct or 0.0
    pct_s = f"+{pct:.4f}%" if pct >= 0 else f"{pct:.4f}%"
    gc, ac = _gc(pct)
    ts    = r.timestamp.strftime("%H:%M") if r.timestamp else "--"

    ba = r.ref_buy_ad
    bp = _fp(r.buy_price_effective, r.fiat) if r.buy_price_effective else "—"
    bn = (f"Ref. mercado: {_fp(ba.price, r.fiat)} {r.fiat}"
          if r.buy_price_effective and ba and abs(r.buy_price_effective - ba.price) > 0.0001
          else "= precio actual top mercado")
    bf = f'<div class="al-filt">Ad filtrado #{r.buy_ads_skipped + 1}</div>' if r.ads_filtered_buy else ""

    sa = r.ref_sell_ad
    sp = _fp(r.sell_price_effective, r.fiat) if r.sell_price_effective else "—"
    sn = (f"Ref. mercado: {_fp(sa.price, r.fiat)} {r.fiat}"
          if r.sell_price_effective and sa and abs(r.sell_price_effective - sa.price) > 0.0001
          else "= precio actual top mercado")
    sf = f'<div class="al-filt">Ad filtrado #{r.sell_ads_skipped + 1}</div>' if r.ads_filtered_sell else ""

    cap     = r.capital_recommended_fiat
    gross   = r.spread_gross_pct
    fee_pct = r.fee_exchange_pct
    cap_s   = f"{cap:,.0f} {r.fiat}" if cap else "—"
    gross_s = f"{gross:.4f}%" if gross is not None else "—"
    fee_s   = f"{fee_pct:.2f}%" if fee_pct else "0%"
    net_amt = f"≈ {cap * pct / 100:,.2f} {r.fiat}" if cap else ""

    return f"""<div class="al {ac}">

  <div class="al-hd">
    <div>
      <div class="al-name">{r.method_human}</div>
      <div class="al-meta">{r.fiat} &nbsp;/&nbsp; {r.asset}</div>
    </div>
    <div class="al-right">
      <div><span class="ex-tag">{r.exchange}</span></div>
      <div class="al-gain {gc}">{pct_s}</div>
      <div class="al-glbl">ganancia neta</div>
    </div>
  </div>

  <div class="al-body">

    <div class="al-col">
      <div class="al-dir dv">VENTA</div>
      <div class="al-hint">publicás en tab Comprar</div>
      {bf}
      <div class="al-price">{bp}<span class="al-curr"> {r.fiat}</span></div>
      <div class="al-ref">{bn}</div>
      <div class="al-row"><span class="al-k">Anunciante</span><span class="al-v">{ba.advertiser_name[:28] if ba else "—"}</span></div>
      <div class="al-row"><span class="al-k">Disponible</span><span class="al-v">{f"{ba.available_amount:,.2f} {r.asset}" if ba else "—"}</span></div>
      <div class="al-row"><span class="al-k">Método</span><span class="al-v">{_pays(ba) if ba else "—"}</span></div>
    </div>

    <div class="al-col">
      <div class="al-dir dc">COMPRA</div>
      <div class="al-hint">publicás en tab Vender</div>
      {sf}
      <div class="al-price">{sp}<span class="al-curr"> {r.fiat}</span></div>
      <div class="al-ref">{sn}</div>
      <div class="al-row"><span class="al-k">Anunciante</span><span class="al-v">{sa.advertiser_name[:28] if sa else "—"}</span></div>
      <div class="al-row"><span class="al-k">Disponible</span><span class="al-v">{f"{sa.available_amount:,.2f} {r.asset}" if sa else "—"}</span></div>
      <div class="al-row"><span class="al-k">Método</span><span class="al-v">{_pays(sa) if sa else "—"}</span></div>
    </div>

  </div>

  <div class="al-ft">
    <span class="fl">Capital</span><span class="fv">{cap_s}</span>
    <span class="fs">&middot;</span>
    <span class="fl">Spread</span><span class="fv">{gross_s}</span>
    <span class="fs">&middot;</span>
    <span class="fl">Comisión</span><span class="fv">{fee_s}</span>
    <span class="fs">&middot;</span>
    <span class="fl">Neta</span><span class="fn {gc}">{pct_s}</span>
    <span class="fm">{net_amt}</span>
    <span class="ftime">{ts}</span>
  </div>

</div>"""


# ── Dashboard principal — toda la pantalla como un HTML ───────────────────────

def build_dashboard_html(
    results: List[SpreadResult],
    exchange_name: str,
    asset: str,
    last_upd,
) -> str:
    """
    Renderiza el dashboard completo: topbar + KPIs + alert cards.
    Diseñado para ser embebido como un único components.html().
    """
    ok = sorted(
        [r for r in results if r.status == "OK"],
        key=lambda r: r.net_profit_pct or 0,
        reverse=True,
    )
    ok_count = len(ok)
    best_net = ok[0].net_profit_pct if ok else None

    best_cap_r = next((r for r in ok if r.capital_recommended_fiat), None)
    if best_cap_r and best_cap_r.capital_recommended_usdt:
        cap_str = f"~{best_cap_r.capital_recommended_usdt:,.0f} USDT"
    elif best_cap_r:
        cap_str = f"{best_cap_r.capital_recommended_fiat:,.0f} {best_cap_r.fiat}"
    else:
        cap_str = "—"

    upd_s = last_upd.strftime("%H:%M:%S") if last_upd else "—"

    if best_net is None:
        gain_s, gain_cls = "—", "clo"
    elif best_net >= 2.0:
        gain_s, gain_cls = f"+{best_net:.4f}%", "chi"
    elif best_net >= 0.5:
        gain_s, gain_cls = f"+{best_net:.4f}%", "cmi"
    elif best_net >= 0.0:
        gain_s, gain_cls = f"+{best_net:.4f}%", "clo"
    else:
        gain_s, gain_cls = f"{best_net:.4f}%", "cne"

    cards_html = (
        "\n".join(_alert_html(r) for r in ok)
        if ok
        else '<div class="empty-st">Sin oportunidades activas.<br>Bajá el umbral o usá el Escaneo.</div>'
    )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>{DASHBOARD_CSS}</style>
</head>
<body>

  <!-- Top bar -->
  <div class="topbar">
    <div style="display:flex;align-items:baseline;gap:0">
      <span class="prod-name">P2P Radar</span>
      <span class="prod-sub">&nbsp;&nbsp;{exchange_name} &middot; {asset}</span>
    </div>
    <div class="tb-right">
      <div class="status-pill">
        <span class="sdot"></span>
        {ok_count} alerta{"s" if ok_count != 1 else ""} activa{"s" if ok_count != 1 else ""}
      </div>
      <span class="upd-label">Actualizado {upd_s}</span>
    </div>
  </div>

  <!-- KPI strip: 3 bloques -->
  <div class="kpi-strip">

    <div class="kpi main">
      <div class="kpi-lbl">Mejor ganancia disponible</div>
      <div class="kpi-big {gain_cls}">{gain_s}</div>
      <div class="kpi-sub">ganancia neta estimada &mdash; modo Yo Publico</div>
    </div>

    <div class="kpi">
      <div class="kpi-lbl">Alertas activas</div>
      <div class="kpi-num">{ok_count}</div>
      <div class="kpi-sub">sobre el umbral configurado</div>
    </div>

    <div class="kpi">
      <div class="kpi-lbl">Capital recomendado</div>
      <div class="kpi-num">{cap_str}</div>
      <div class="kpi-sub">basado en liquidez del mercado</div>
    </div>

  </div>

  <!-- Section: alertas -->
  <div class="sec-hd">
    <span class="sec-title">Alertas activas</span>
    <span class="sec-badge">{ok_count}</span>
  </div>

  <div class="alerts">
    {cards_html}
  </div>

</body>
</html>"""


# ── Feed HTML (compat — redirige al mismo diseño) ─────────────────────────────

def single_card_html(r: SpreadResult) -> str:
    return _alert_html(r)


def build_feed_html(results: List[SpreadResult]) -> str:
    ok = sorted([r for r in results if r.status == "OK"],
                key=lambda r: r.net_profit_pct or 0, reverse=True)
    if not ok:
        body = '<div class="empty-st">Sin oportunidades activas.</div>'
    else:
        body = "\n".join(_alert_html(r) for r in ok)
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{DASHBOARD_CSS}</style></head><body><div style="padding:4px 2px 8px">{body}</div></body></html>'


# ── Helpers legacy ─────────────────────────────────────────────────────────────

def build_hero_html(ok_count, best_net, cap_str, upd_s) -> str:
    """Legacy: ahora usamos build_dashboard_html."""
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{DASHBOARD_CSS}</style></head><body><p style="color:rgba(255,255,255,.3);padding:20px">—</p></body></html>'


def build_kpi_html(
    results: List[SpreadResult],
    exchange_name: str,
    asset: str,
    last_upd,
) -> str:
    """Solo el topbar + KPI strip (sin alertas)."""
    ok = [r for r in results if r.status == "OK"]
    ok_count = len(ok)
    best_net = max((r.net_profit_pct or 0 for r in ok), default=None) if ok else None

    best_cap_r = next((r for r in ok if r.capital_recommended_fiat), None)
    if best_cap_r and best_cap_r.capital_recommended_usdt:
        cap_str = f"~{best_cap_r.capital_recommended_usdt:,.0f} USDT"
    elif best_cap_r:
        cap_str = f"{best_cap_r.capital_recommended_fiat:,.0f} {best_cap_r.fiat}"
    else:
        cap_str = "—"

    upd_s = last_upd.strftime("%H:%M:%S") if last_upd else "—"

    if best_net is None:
        gain_s, gain_cls = "—", "clo"
    elif best_net >= 2.0:
        gain_s, gain_cls = f"+{best_net:.4f}%", "chi"
    elif best_net >= 0.5:
        gain_s, gain_cls = f"+{best_net:.4f}%", "cmi"
    elif best_net >= 0.0:
        gain_s, gain_cls = f"+{best_net:.4f}%", "clo"
    else:
        gain_s, gain_cls = f"{best_net:.4f}%", "cne"

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>{DASHBOARD_CSS}</style>
</head>
<body>

  <!-- ── YouTube Banner ── -->
  <style>
    .yt-btn {{
      display:flex;align-items:center;gap:8px;
      background:linear-gradient(180deg,#ff1a1a,#cc0000);
      border-radius:7px;padding:10px 18px;flex-shrink:0;
      border:1px solid #ff4444;
      box-shadow:0 5px 0 #880000, 0 7px 14px rgba(0,0,0,0.35);
      transition:transform 0.08s, box-shadow 0.08s;
      cursor:pointer;
    }}
    .yt-btn:active {{
      transform:translateY(3px);
      box-shadow:0 2px 0 #880000, 0 3px 6px rgba(0,0,0,0.3);
    }}
  </style>
  <a href="https://www.youtube.com/@EzequielSack" target="_blank"
     style="display:flex;align-items:center;justify-content:space-between;
            background:#fff;border-radius:12px;padding:12px 20px;
            margin-bottom:8px;text-decoration:none;gap:20px;
            box-shadow:0 2px 16px rgba(0,0,0,0.22);">

    <!-- Logo izquierda -->
    <div style="display:flex;align-items:center;gap:12px;flex-shrink:0;">
      <img src="{_logo_data_uri()}"
           style="width:52px;height:52px;border-radius:50%;object-fit:contain;object-position:center center;
                  background:#c8892a;flex-shrink:0;box-shadow:0 2px 8px rgba(0,0,0,0.25);display:block;"/>
      <div>
        <div style="font-size:14px;font-weight:800;color:#111;
                    letter-spacing:-0.3px;line-height:1.1;">Ezequiel Sack</div>
        <div style="font-size:10px;color:#999;font-weight:500;margin-top:2px;">
          @EzequielSack</div>
      </div>
    </div>

    <!-- Texto centro -->
    <div style="font-size:19px;font-weight:900;color:#111;
                text-align:center;line-height:1.25;letter-spacing:-0.3px;
                text-transform:uppercase;">
      Sub por info de calidad<br>
      <span style="color:#e00;font-size:21px;">GRATIS</span>
      <span style="font-size:18px;"> ;)</span>
    </div>

    <!-- Botón Subscribe -->
    <div class="yt-btn">
      <svg width="20" height="14" viewBox="0 0 20 14">
        <rect width="20" height="14" rx="3" fill="none"/>
        <polygon points="7,2 17,7 7,12" fill="white"/>
      </svg>
      <span style="color:#fff;font-size:13px;font-weight:900;
                   letter-spacing:1px;text-transform:uppercase;">Suscribite</span>
    </div>

  </a>

  <div class="topbar">
    <div style="display:flex;align-items:baseline;gap:0">
      <span class="prod-name">P2P Radar</span>
      <span class="prod-sub">&nbsp;&nbsp;{exchange_name} &middot; {asset}</span>
    </div>
    <div class="tb-right">
      <div class="status-pill">
        <span class="sdot"></span>
        {ok_count} alerta{"s" if ok_count != 1 else ""} activa{"s" if ok_count != 1 else ""}
      </div>
      <span class="upd-label">Actualizado {upd_s}</span>
    </div>
  </div>
  <div class="kpi-strip">
    <div class="kpi main">
      <div class="kpi-lbl">Mejor ganancia disponible</div>
      <div class="kpi-big {gain_cls}">{gain_s}</div>
      <div class="kpi-sub">ganancia neta estimada &mdash; modo Yo Publico</div>
    </div>
    <div class="kpi">
      <div class="kpi-lbl">Alertas activas</div>
      <div class="kpi-num">{ok_count}</div>
      <div class="kpi-sub">sobre el umbral configurado</div>
    </div>
    <div class="kpi">
      <div class="kpi-lbl">Capital recomendado</div>
      <div class="kpi-num">{cap_str}</div>
      <div class="kpi-sub">basado en liquidez del mercado</div>
    </div>
  </div>
</body>
</html>"""


def build_alerts_html(results: List[SpreadResult]) -> str:
    """Solo las tarjetas de alertas (sin topbar ni KPIs)."""
    ok = sorted(
        [r for r in results if r.status == "OK"],
        key=lambda r: r.net_profit_pct or 0,
        reverse=True,
    )
    cards_html = (
        "\n".join(_alert_html(r) for r in ok)
        if ok
        else '<div class="empty-st">Sin oportunidades activas.<br>Bajá el umbral o usá el Escaneo.</div>'
    )
    ok_count = len(ok)
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>{DASHBOARD_CSS}</style>
</head>
<body>
  <div class="sec-hd">
    <span class="sec-title">Alertas activas</span>
    <span class="sec-badge">{ok_count}</span>
  </div>
  <div class="alerts">
    {cards_html}
  </div>
</body>
</html>"""


def _tg_row(key: str, val: str) -> str:
    return f'<div class="tg-row"><span class="tg-key">{key}</span><span class="tg-val">{val}</span></div>'


def _tg_side(label: str, ad: Optional[P2PAd], price_eff: Optional[float], fiat: str, asset: str) -> str:
    if ad is None:
        return f'<div class="tg-section">{label}</div>{_tg_row("Estado", "Sin datos")}'
    pays = ", ".join([m for m in ad.payment_methods if m][:3]) if ad.payment_methods else "--"
    price_s = f"{_fp(price_eff or ad.price, fiat)} {fiat}"
    return f"""<div class="tg-section">{label}</div>
{_tg_row("Precio", price_s)}
{_tg_row("Anunciante", ad.advertiser_name)}
{_tg_row("Disponible", f"{ad.available_amount:,.2f} {asset}")}
{_tg_row("Método de pago", pays)}"""


def _tg_plain_text(r: SpreadResult) -> str:
    pct = r.net_profit_pct or 0
    buy, sell = r.ref_buy_ad, r.ref_sell_ad
    pays_b = ", ".join([m for m in buy.payment_methods if m][:3]) if buy and buy.payment_methods else "--"
    pays_s = ", ".join([m for m in sell.payment_methods if m][:3]) if sell and sell.payment_methods else "--"
    lines = [
        f"🤖 Bot de Alertas P2P — {r.method_human} ({r.fiat})",
        f"💰 Ganancia estimada: +{pct:.2f}%",
        f"",
        f"📗 VENTA P2P (publicás en tab Comprar)",
        f"  Precio:      {_fp(r.buy_price_effective or 0, r.fiat)} {r.fiat}",
        f"  Anunciante:  {buy.advertiser_name if buy else '--'}",
        f"  Disponible:  {buy.available_amount:,.2f} {r.asset}" if buy else "  Disponible:  --",
        f"  Método:      {pays_b}",
        f"",
        f"📕 COMPRA P2P (publicás en tab Vender)",
        f"  Precio:      {_fp(r.sell_price_effective or 0, r.fiat)} {r.fiat}",
        f"  Anunciante:  {sell.advertiser_name if sell else '--'}",
        f"  Disponible:  {sell.available_amount:,.2f} {r.asset}" if sell else "  Disponible:  --",
        f"  Método:      {pays_s}",
    ]
    return "\\n".join(lines)


def build_telegram_html(results: List[SpreadResult]) -> str:
    ok = [r for r in results if r.status == "OK"]
    if not ok:
        bubbles = '<div style="color:rgba(255,255,255,.3);text-align:center;padding:40px">Sin alertas activas</div>'
    else:
        ts = datetime.now().strftime("%H:%M")
        parts = []
        for i, r in enumerate(ok):
            pct = r.net_profit_pct or 0
            pct_s = f"+{pct:.2f}%"
            venta_s  = _tg_side("📗 VENTA — publicás en tab Comprar", r.ref_buy_ad,  r.buy_price_effective,  r.fiat, r.asset)
            compra_s = _tg_side("📕 COMPRA — publicás en tab Vender", r.ref_sell_ad, r.sell_price_effective, r.fiat, r.asset)
            plain  = _tg_plain_text(r)
            btn_id = f"copy_{i}"
            parts.append(f"""<div class="tg-bubble">
  <div class="tg-header">🤖 Bot de Alertas P2P &nbsp;·&nbsp; {r.method_human} ({r.fiat})</div>
  <div class="tg-diff">{pct_s} ganancia estimada</div>
  <hr class="tg-divider">
  {venta_s}
  <hr class="tg-divider">
  {compra_s}
  <div class="tg-footer">
    <span class="tg-time">{ts}</span>
    <button class="tg-copy" id="{btn_id}" onclick="copyAlert('{btn_id}', `{plain}`)">
      📋 Copiar alerta
    </button>
  </div>
</div>""")
        bubbles = "\n".join(parts)

    copy_js = """
<script>
function copyAlert(btnId, text) {
    navigator.clipboard.writeText(text.replace(/\\\\n/g, '\\n')).then(function() {
        var btn = document.getElementById(btnId);
        btn.textContent = '✅ Copiado';
        btn.classList.add('copied');
        setTimeout(function() {
            btn.textContent = '📋 Copiar alerta';
            btn.classList.remove('copied');
        }, 2000);
    });
}
</script>"""

    return (f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CARD_CSS}</style></head>'
            f'<body><div class="tg-wrap">'
            f'<div style="font-size:10px;color:rgba(255,255,255,.2);margin-bottom:16px;letter-spacing:.8px;text-transform:uppercase">Preview Telegram</div>'
            f'{bubbles}</div>{copy_js}</body></html>')


# ── Taker-Taker card HTML ─────────────────────────────────────────────────────

def build_taker_cards_html(taker_opportunities: list) -> str:
    if not taker_opportunities:
        return ""

    cards = []
    for t in taker_opportunities:
        pct      = t["ganancia_pct"]
        pct_s    = f"+{pct:.3f}%"
        fiat     = t["fiat"]
        asset    = t["asset"]
        liq_cop  = t.get("capital_operable_cop", t["capital"])
        liq_usdt = t.get("cantidad_usdt_real", t["cantidad_usdt"])
        gan_real = t.get("ganancia_real_cop", t["ganancia_cop"])
        gan_cfg  = t["ganancia_cop"]
        cap_cfg  = t["capital"]
        usdt_cfg = t["cantidad_usdt"]
        dentro   = t.get("dentro_limites", False)
        buy_min  = t.get("buy_min", 0)
        buy_max  = t.get("buy_max", 0)
        sell_min = t.get("sell_min", 0)
        sell_max = t.get("sell_max", 0)
        lim_color  = "rgba(0,214,143,0.08)"  if dentro else "rgba(255,68,68,0.08)"
        lim_border = "rgba(0,214,143,0.25)"  if dentro else "rgba(255,68,68,0.25)"
        lim_text   = "#00d68f" if dentro else "#ff4444"
        lim_msg    = "✅ Capital dentro de límites — podés operar" if dentro else "⚠️ Capital fuera de límites"
        gan_color  = "00d68f" if gan_real > 0 else "ff4444"
        card = f"""<div style="background:linear-gradient(135deg,rgba(255,140,0,0.12),rgba(255,100,0,0.06));border:1px solid rgba(255,140,0,0.45);border-left:4px solid #ff8c00;border-radius:14px;padding:16px 20px;margin-bottom:14px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">
    <div>
      <div style="font-size:13px;font-weight:800;color:#fff;">🟠 {t['method_human']}</div>
      <div style="font-size:10px;color:rgba(255,255,255,0.45);margin-top:2px;">{fiat} / {asset} · TAKER-TAKER (sin anuncio)</div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:22px;font-weight:900;color:#ff8c00;">{pct_s}</div>
      <div style="font-size:9px;color:rgba(255,140,0,0.6);text-transform:uppercase;">spread bruto</div>
    </div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px;">
    <div style="background:rgba(0,200,100,0.08);border:1px solid rgba(0,200,100,0.2);border-radius:8px;padding:10px 12px;">
      <div style="font-size:9px;color:rgba(255,255,255,0.4);text-transform:uppercase;margin-bottom:4px;">📗 Comprás directamente</div>
      <div style="font-size:18px;font-weight:800;color:#00d68f;">{t['taker_buy']:,.2f} <span style="font-size:11px;color:rgba(255,255,255,0.5);">{fiat}</span></div>
      <div style="font-size:9px;color:rgba(255,255,255,0.3);margin-top:2px;">tab Comprar · límite: {buy_min:,.0f}–{buy_max:,.0f} {fiat}</div>
    </div>
    <div style="background:rgba(255,80,80,0.08);border:1px solid rgba(255,80,80,0.2);border-radius:8px;padding:10px 12px;">
      <div style="font-size:9px;color:rgba(255,255,255,0.4);text-transform:uppercase;margin-bottom:4px;">📕 Vendés directamente</div>
      <div style="font-size:18px;font-weight:800;color:#ff6b6b;">{t['taker_sell']:,.2f} <span style="font-size:11px;color:rgba(255,255,255,0.5);">{fiat}</span></div>
      <div style="font-size:9px;color:rgba(255,255,255,0.3);margin-top:2px;">tab Vender · límite: {sell_min:,.0f}–{sell_max:,.0f} {fiat}</div>
    </div>
  </div>
  <div style="background:rgba(255,140,0,0.06);border:1px solid rgba(255,140,0,0.2);border-radius:8px;padding:10px 14px;margin-bottom:10px;">
    <div style="font-size:9px;color:rgba(255,140,0,0.7);text-transform:uppercase;letter-spacing:0.8px;margin-bottom:8px;">💧 Liquidez real del mercado</div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
      <div>
        <div style="font-size:9px;color:rgba(255,255,255,0.35);margin-bottom:2px;">Capital operable</div>
        <div style="font-size:14px;font-weight:700;color:#ff8c00;">{liq_cop:,.0f} {fiat}</div>
        <div style="font-size:9px;color:rgba(255,255,255,0.3);">≈ {liq_usdt:.1f} USDT</div>
      </div>
      <div>
        <div style="font-size:9px;color:rgba(255,255,255,0.35);margin-bottom:2px;">Ganancia con liquidez real</div>
        <div style="font-size:14px;font-weight:700;color:#{gan_color};">{gan_real:,.0f} {fiat}</div>
        <div style="font-size:9px;color:rgba(255,255,255,0.3);">comisión $0.14 incluida</div>
      </div>
      <div>
        <div style="font-size:9px;color:rgba(255,255,255,0.35);margin-bottom:2px;">Ganancia con tu capital</div>
        <div style="font-size:14px;font-weight:700;color:rgba(255,255,255,0.7);">{gan_cfg:,.0f} {fiat}</div>
        <div style="font-size:9px;color:rgba(255,255,255,0.3);">{cap_cfg:,.0f} {fiat} · {usdt_cfg:.1f} USDT</div>
      </div>
    </div>
  </div>
  <div style="padding:8px 10px;border-radius:8px;background:{lim_color};border:1px solid {lim_border};font-size:10px;display:flex;justify-content:space-between;align-items:center;">
    <span style="color:{lim_text};font-weight:700;">{lim_msg}</span>
    <span style="color:rgba(255,255,255,0.35);">Cuello de botella: {min(buy_max,sell_max):,.0f} {fiat}</span>
  </div>
</div>"""
        cards.append(card)

    body = "
".join(cards)
    return (
        f'<!DOCTYPE html><html><head><meta charset="utf-8">'
        f'<style>body{{margin:0;padding:4px 2px 8px;background:transparent;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}}</style>'
        f'</head><body>{body}</body></html>'
    )
