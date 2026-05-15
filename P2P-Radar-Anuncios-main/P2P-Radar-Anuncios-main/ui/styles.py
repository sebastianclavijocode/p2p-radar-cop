"""CSS — diseño producto premium."""

# CSS inyectado en Streamlit (sidebar + chrome mínimo)
GLASS_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

body, p, span:not([class*="material"]), div, h1, h2, h3, h4, h5,
label, input, button, select, textarea, td, th, li, a {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
[data-testid="stIconMaterial"],
.material-icons,
[class*="material-icons"] {
  font-family: 'Material Icons' !important;
}

/* Ocultar íconos que se renderizan como texto literal */
[data-testid="stSidebarCollapseButton"] span,
[data-testid="stSidebarNavCollapseButton"] span,
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpanderToggleIcon"] span {
  display: none !important;
}

/* Fallback robusto: spans dentro de summary (solo el ícono, el label es <p>) */
details > summary span,
details > summary > span {
  font-size: 0 !important;
  color: transparent !important;
  width: 0 !important;
  overflow: hidden !important;
  display: inline-block !important;
}

/* ── Ocultar chrome de Streamlit ── */
#MainMenu { visibility: hidden !important; }
header[data-testid="stHeader"] { display: none !important; }
[data-testid="stToolbar"]      { display: none !important; }
footer                          { display: none !important; }
[data-testid="stDecoration"]   { display: none !important; }

/* ── App background ── */
.stApp { background: #0d1117 !important; }
.main .block-container {
  padding-top: 0.5rem !important;
  padding-bottom: 3rem !important;
  max-width: 100% !important;
  padding-left: 1.2rem !important;
  padding-right: 1.2rem !important;
}

/* ── Sidebar — app nav panel ── */
[data-testid="stSidebar"] {
  background: #090c14 !important;
  border-right: 1px solid rgba(255,255,255,0.04) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.4rem !important; }
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.58) !important; }
[data-testid="stSidebar"] h2 {
  font-size: 14px !important; font-weight: 800 !important;
  color: #fff !important; letter-spacing: -0.3px !important;
}
[data-testid="stSidebar"] .stMarkdown p strong,
[data-testid="stSidebar"] .stMarkdown strong {
  display: block !important; font-size: 8.5px !important;
  text-transform: uppercase !important; letter-spacing: 2.2px !important;
  color: rgba(255,255,255,0.15) !important; font-weight: 700 !important;
  padding: 16px 0 4px !important;
}

/* ── Inputs ── */
.stTextInput input, .stNumberInput input, .stTextArea textarea {
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 8px !important; color: #fff !important; font-size: 13px !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
  border-color: rgba(0,214,143,0.35) !important;
  box-shadow: 0 0 0 2px rgba(0,214,143,0.07) !important; outline: none !important;
}
.stSelectbox > div > div, .stMultiSelect > div > div {
  background: rgba(255,255,255,0.03) !important;
  border: 1px solid rgba(255,255,255,0.07) !important;
  border-radius: 8px !important; color: #fff !important;
}

/* ── Buttons ── */
.stButton > button {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 8px !important; color: rgba(255,255,255,0.5) !important;
  font-weight: 500 !important; font-size: 13px !important;
}
.stButton > button:hover { background: rgba(255,255,255,0.08) !important; color: #fff !important; }
.stButton > button[kind="primary"] {
  background: rgba(0,214,143,0.09) !important;
  border: 1px solid rgba(0,214,143,0.25) !important;
  color: #00d68f !important; font-weight: 600 !important;
}
.stButton > button[kind="primary"]:hover {
  background: rgba(0,214,143,0.15) !important; border-color: rgba(0,214,143,0.4) !important;
}

/* ── Tabs secundarias (debajo del dashboard) ── */
.stTabs [data-baseweb="tab-list"] {
  background: rgba(255,255,255,0.018) !important;
  border: 1px solid rgba(255,255,255,0.045) !important;
  border-radius: 10px !important; padding: 3px !important; gap: 1px !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important; color: rgba(255,255,255,0.25) !important;
  font-size: 11.5px !important; font-weight: 500 !important;
  padding: 6px 14px !important; border-radius: 7px !important; border: none !important;
}
.stTabs [data-baseweb="tab"]:hover { color: rgba(255,255,255,0.5) !important; }
.stTabs [aria-selected="true"] {
  color: rgba(255,255,255,0.82) !important;
  background: rgba(255,255,255,0.07) !important; font-weight: 600 !important;
}

/* ── Sliders, expanders, dataframes ── */
.stSlider [role="slider"] { background: #00d68f !important; }

[data-testid="stSidebar"] details {
  background: rgba(255,255,255,0.025) !important;
  border: 1px solid rgba(0,214,143,0.22) !important;
  border-radius: 10px !important;
  box-shadow:
    inset 3px 0 0 0 #00d68f,
    inset 5px 0 12px rgba(0,214,143,0.25),
    0 0 0 1px rgba(0,214,143,0.12) !important;
  overflow: hidden !important;
  margin-bottom: 6px !important;
}
[data-testid="stSidebar"] details summary {
  height: 46px !important;
  min-height: 46px !important;
  padding: 0 16px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  cursor: pointer !important;
  list-style: none !important;
  /* Primeros 3px transparentes → deja pasar el stripe verde del details */
  background: linear-gradient(to right, transparent 3px, rgba(255,255,255,0.04) 3px) !important;
}
/* Ocultar solo el ícono flecha (span anidado dentro del wrapper) */
[data-testid="stSidebar"] details summary span span,
[data-testid="stSidebar"] details summary [data-testid="stExpanderToggleIcon"] {
  font-size: 0 !important;
  width: 0 !important;
  overflow: hidden !important;
  position: absolute !important;
}
[data-testid="stSidebar"] details summary p {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1 !important;
  text-align: center !important;
  width: 100% !important;
  color: rgba(255,255,255,0.82) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.6px !important;
}
[data-testid="stSidebar"] details[open] {
  border-color: rgba(0,214,143,0.35) !important;
  border-left-color: #00d68f !important;
  background: rgba(0,214,143,0.03) !important;
}
[data-testid="stSidebar"] details > div[data-testid="stVerticalBlock"],
[data-testid="stSidebar"] details > div > div:first-child {
  padding-top: 0 !important;
  margin-top: 0 !important;
}
/* Widgets dentro de expanders: sin borde propio (la card ya provee el marco) */
[data-testid="stSidebar"] details .stSelectbox > div > div,
[data-testid="stSidebar"] details .stNumberInput [data-baseweb="input"],
[data-testid="stSidebar"] details .stNumberInput,
[data-testid="stSidebar"] details .stToggle,
[data-testid="stSidebar"] details .stSlider {
  background: transparent !important;
  border: none !important;
  border-left: none !important;
  box-shadow: none !important;
  border-radius: 0 !important;
  margin-bottom: 0 !important;
}
[data-testid="stSidebar"] details .stToggle {
  min-height: 38px !important;
  padding: 2px 8px !important;
}
[data-testid="stSidebar"] details .stNumberInput [data-baseweb="input"] {
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 8px !important;
  margin: 2px 0 !important;
}
[data-testid="stSidebar"] details .stSelectbox > div > div {
  background: transparent !important;
  border: none !important;
  border-bottom: 1px solid rgba(255,255,255,0.06) !important;
  border-radius: 0 !important;
  min-height: 40px !important;
  padding: 0 4px !important;
}
/* Valor seleccionado (Binance / USDT) → protagonista */
[data-testid="stSidebar"] details .stSelectbox [data-baseweb="select"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] details .stSelectbox [data-baseweb="select"] span,
[data-testid="stSidebar"] details .stSelectbox [data-baseweb="select"] div[class*="ValueContainer"] {
  font-size: 15px !important;
  font-weight: 700 !important;
  color: rgba(255,255,255,0.92) !important;
  letter-spacing: -0.2px !important;
}
.streamlit-expanderHeader {
  background: rgba(255,255,255,0.02) !important;
  border: 1px solid rgba(255,255,255,0.05) !important;
  border-radius: 8px !important; color: rgba(255,255,255,0.35) !important; font-size: 12px !important;
}
[data-testid="stDataFrame"] {
  border: 1px solid rgba(255,255,255,0.05) !important; border-radius: 12px !important; overflow: hidden !important;
}
[data-testid="stInfo"]    { background: rgba(0,214,143,0.03)  !important; border: 1px solid rgba(0,214,143,0.1)  !important; border-radius: 10px !important; }
[data-testid="stSuccess"] { background: rgba(0,214,143,0.04)  !important; border: 1px solid rgba(0,214,143,0.14) !important; border-radius: 10px !important; }
[data-testid="stWarning"] { background: rgba(255,215,64,0.03)  !important; border: 1px solid rgba(255,215,64,0.12) !important; border-radius: 10px !important; }
[data-testid="stError"]   { background: rgba(239,83,80,0.03)   !important; border: 1px solid rgba(239,83,80,0.12)  !important; border-radius: 10px !important; }

hr { border: none !important; border-top: 1px solid rgba(255,255,255,0.04) !important; }
.stCaption { color: rgba(255,255,255,0.2) !important; font-size: 11px !important; }
.stCheckbox > label, .stToggle > label { color: rgba(255,255,255,0.5) !important; font-size: 13px !important; }

::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 3px; }

/* ── Iconos ? de ayuda — sin fondo neon, amarillo discreto ── */
/* Regla universal: cualquier elemento con data-testid que contenga "Tooltip" */
[data-testid="stSidebar"] [data-testid*="Tooltip"],
[data-testid="stSidebar"] [data-testid*="tooltip"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  border-left: none !important;
  outline: none !important;
  min-width: unset !important;
  padding: 2px !important;
  color: transparent !important;
}
[data-testid="stSidebar"] [data-testid*="Tooltip"] svg,
[data-testid="stSidebar"] [data-testid*="tooltip"] svg {
  fill: #FFC107 !important;
  opacity: 0.65 !important;
}
[data-testid="stSidebar"] [data-testid*="Tooltip"]:hover svg,
[data-testid="stSidebar"] [data-testid*="tooltip"]:hover svg {
  opacity: 1 !important;
}

/* ═══════════════════════════════════════════════════════
   SIDEBAR — SISTEMA VISUAL UNIFICADO
   Referencia: misma lógica de las cards de expander
   Tokens: bg=rgba(255,255,255,0.025) · border=rgba(0,214,143,0.22)
           accent=#00d68f · radius=10px · height=46px
   ═══════════════════════════════════════════════════════ */

/* ── Section labels (los **FILTROS DE OPORTUNIDAD** etc.) ── */
[data-testid="stSidebar"] .stMarkdown p strong,
[data-testid="stSidebar"] .stMarkdown strong {
  display: block !important;
  font-size: 9px !important;
  text-transform: uppercase !important;
  letter-spacing: 2px !important;
  color: rgba(255,255,255,0.28) !important;
  font-weight: 700 !important;
  padding: 14px 0 6px !important;
  border-bottom: 1px solid rgba(255,255,255,0.05) !important;
  margin-bottom: 10px !important;
}

/* ── Selectbox ── */
[data-testid="stSidebar"] .stSelectbox > div > div {
  background: rgba(255,255,255,0.025) !important;
  border: 1px solid rgba(0,214,143,0.22) !important;
  border-left: 3px solid rgba(0,214,143,0.6) !important;
  border-radius: 10px !important;
  color: rgba(255,255,255,0.85) !important;
  min-height: 46px !important;
  padding: 0 14px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  display: flex !important;
  align-items: center !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div:hover {
  border-color: rgba(0,214,143,0.4) !important;
  background: rgba(0,214,143,0.03) !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label {
  font-size: 10px !important;
  text-transform: uppercase !important;
  letter-spacing: 1.2px !important;
  color: rgba(255,255,255,0.3) !important;
  font-weight: 700 !important;
  margin-bottom: 4px !important;
}

/* ── Number input ── */
[data-testid="stSidebar"] .stNumberInput [data-baseweb="input"] {
  background: rgba(255,255,255,0.025) !important;
  border: 1px solid rgba(0,214,143,0.22) !important;
  border-left: 3px solid rgba(0,214,143,0.6) !important;
  border-radius: 10px !important;
  min-height: 46px !important;
  overflow: hidden !important;
}
[data-testid="stSidebar"] .stNumberInput input {
  background: transparent !important;
  border: none !important;
  color: rgba(255,255,255,0.9) !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  text-align: center !important;
}
[data-testid="stSidebar"] .stNumberInput [data-baseweb="input"] button {
  background: rgba(0,214,143,0.06) !important;
  border: none !important;
  border-left: 1px solid rgba(0,214,143,0.15) !important;
  color: #00d68f !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  min-width: 36px !important;
}
[data-testid="stSidebar"] .stNumberInput [data-baseweb="input"] button:hover {
  background: rgba(0,214,143,0.14) !important;
}
[data-testid="stSidebar"] .stNumberInput label {
  font-size: 10px !important;
  text-transform: uppercase !important;
  letter-spacing: 1.2px !important;
  color: rgba(255,255,255,0.3) !important;
  font-weight: 700 !important;
  margin-bottom: 4px !important;
}

/* ── Toggles ── */
[data-testid="stSidebar"] .stToggle {
  background: rgba(255,255,255,0.025) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-left: 3px solid rgba(255,255,255,0.15) !important;
  border-radius: 10px !important;
  padding: 0 14px !important;
  min-height: 46px !important;
  display: flex !important;
  align-items: center !important;
  margin-bottom: 6px !important;
}
[data-testid="stSidebar"] .stToggle label {
  width: 100% !important;
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  padding: 0 !important;
  margin: 0 !important;
  min-height: 46px !important;
}
[data-testid="stSidebar"] .stToggle label p {
  font-size: 12.5px !important;
  font-weight: 600 !important;
  color: rgba(255,255,255,0.75) !important;
  margin: 0 !important;
  line-height: 1.3 !important;
}
/* Toggle activo → borde verde */
[data-testid="stSidebar"] .stToggle:has(input:checked) {
  border-color: rgba(0,214,143,0.28) !important;
  border-left-color: #00d68f !important;
  background: rgba(0,214,143,0.03) !important;
}

/* ── Slider ── */
[data-testid="stSidebar"] .stSlider {
  background: rgba(255,255,255,0.025) !important;
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-left: 3px solid rgba(255,255,255,0.15) !important;
  border-radius: 10px !important;
  padding: 10px 16px 12px !important;
  margin-bottom: 6px !important;
}
[data-testid="stSidebar"] .stSlider label {
  font-size: 10px !important;
  text-transform: uppercase !important;
  letter-spacing: 1.2px !important;
  color: rgba(255,255,255,0.3) !important;
  font-weight: 700 !important;
}
[data-testid="stSidebar"] .stSlider [role="slider"] {
  background: #00d68f !important;
  border: 2px solid #00d68f !important;
  box-shadow: 0 0 8px rgba(0,214,143,0.4) !important;
}

/* ── Botón Actualizar — amarillo neon (CTA diferenciado) ── */
[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: rgba(255,193,7,0.08) !important;
  border: 1px solid rgba(255,193,7,0.35) !important;
  border-radius: 10px !important;
  box-shadow:
    inset 3px 0 0 0 #FFC107,
    inset 5px 0 12px rgba(255,193,7,0.2),
    0 0 0 1px rgba(255,193,7,0.1) !important;
  color: #FFC107 !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  text-transform: uppercase !important;
  letter-spacing: 1px !important;
  height: 46px !important;
  width: 100% !important;
}
[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
  background: rgba(255,193,7,0.14) !important;
  border-color: rgba(255,193,7,0.55) !important;
  box-shadow:
    inset 3px 0 0 0 #FFC107,
    inset 5px 0 16px rgba(255,193,7,0.3),
    0 0 16px rgba(255,193,7,0.15) !important;
}

/* ══════════════════════════════════════════════
   CARD VERDE — ::before absoluto dentro del wrapper
   position:relative en wrapper + ::before interno
   no se corta con overflow:hidden porque queda
   completamente dentro del bounding box del padre.
   ══════════════════════════════════════════════ */
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stSidebar"] .stVerticalBlockBorderWrapper {
  position: relative !important;
  background: rgba(255,255,255,0.025) !important;
  border: 1px solid rgba(0,214,143,0.22) !important;
  border-radius: 10px !important;
  box-shadow: 0 0 20px rgba(0,214,143,0.06) !important;
  padding: 0 !important;
  margin-bottom: 4px !important;
  overflow: hidden !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"]::before,
[data-testid="stSidebar"] .stVerticalBlockBorderWrapper::before {
  content: "" !important;
  display: block !important;
  position: absolute !important;
  left: 0 !important;
  top: 0 !important;
  width: 3px !important;
  height: 100% !important;
  background: linear-gradient(180deg, #00d68f, rgba(0,214,143,0.5)) !important;
  z-index: 9999 !important;
  pointer-events: none !important;
}
/* Padding izq en el bloque interno para que el contenido
   no quede tapado por la franja de 3px */
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {
  padding: 8px 8px 8px 12px !important;
}
/* Dentro del container: widgets sin borde propio */
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] .stSelectbox > div > div,
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] .stNumberInput [data-baseweb="input"],
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] .stNumberInput,
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] .stToggle,
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] .stSlider {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  border-radius: 0 !important;
  margin-bottom: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] .stToggle {
  min-height: 38px !important;
  padding: 2px 8px !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] .stNumberInput [data-baseweb="input"] {
  border: 1px solid rgba(255,255,255,0.08) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  margin: 2px 0 !important;
}

/* ── Dividers ── */
[data-testid="stSidebar"] hr {
  border-top: 1px solid rgba(255,255,255,0.05) !important;
  margin: 10px 0 !important;
}

/* ── Caption ── */
[data-testid="stSidebar"] .stCaption {
  font-size: 10.5px !important;
  color: rgba(255,255,255,0.22) !important;
  line-height: 1.5 !important;
}

</style>"""


# CSS para el dashboard principal (components.html iframe)
DASHBOARD_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: #0d1117;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: #c9d1d9;
    font-size: 13px;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Top bar ── */
.topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 20px 28px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    background: rgba(255,255,255,0.01);
}
.prod-name { font-size: 16px; font-weight: 800; color: #fff; letter-spacing: -0.4px; }
.prod-sub  { font-size: 10.5px; color: rgba(255,255,255,0.2); text-transform: uppercase; letter-spacing: 1.2px; margin-left: 10px; }
.tb-right  { display: flex; align-items: center; gap: 18px; }
.status-pill {
    display: flex; align-items: center; gap: 6px;
    background: rgba(0,214,143,0.07); border: 1px solid rgba(0,214,143,0.2);
    border-radius: 20px; padding: 5px 14px; font-size: 11.5px; color: #00d68f; font-weight: 600;
}
.sdot { width: 6px; height: 6px; background: #00d68f; border-radius: 50%; animation: blink 2s ease infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
.upd-label { font-size: 10.5px; color: rgba(255,255,255,0.17); }

/* ── KPI strip ── */
.kpi-strip {
    display: grid; grid-template-columns: 2fr 1fr 1fr;
    gap: 10px; padding: 16px 28px;
}
.kpi {
    background: rgba(255,255,255,0.028);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 16px 20px;
    position: relative; overflow: hidden;
}
.kpi.main {
    background: linear-gradient(140deg, rgba(0,214,143,0.07) 0%, rgba(255,255,255,0.02) 60%);
    border-color: rgba(0,214,143,0.2);
}
.kpi.main::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent 5%, rgba(0,214,143,0.55) 50%, transparent 95%);
}
.kpi-lbl { font-size: 9px; color: rgba(255,255,255,0.2); text-transform: uppercase; letter-spacing: 2.5px; font-weight: 700; margin-bottom: 14px; }
.kpi-big { font-size: 42px; font-weight: 900; letter-spacing: -2.5px; line-height: 1; font-variant-numeric: tabular-nums; }
.kpi-num { font-size: 26px; font-weight: 800; letter-spacing: -1px; color: #fff; font-variant-numeric: tabular-nums; }
.kpi-sub { font-size: 10px; color: rgba(255,255,255,0.18); margin-top: 6px; }

/* ── Section header ── */
.sec-hd { display: flex; align-items: center; gap: 10px; padding: 4px 28px 14px; }
.sec-title { font-size: 9.5px; font-weight: 700; color: rgba(255,255,255,0.22); text-transform: uppercase; letter-spacing: 2.2px; }
.sec-badge { font-size: 9.5px; color: rgba(255,255,255,0.25); background: rgba(255,255,255,0.05); border-radius: 20px; padding: 1px 9px; font-weight: 600; }

/* ── Alert cards ── */
.alerts { padding: 0 28px 28px; display: flex; flex-direction: column; gap: 8px; }

.al {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; overflow: hidden;
    transition: border-color .18s ease, box-shadow .18s ease;
    animation: fadeUp .4s cubic-bezier(0.16,1,0.3,1) both;
}
.al:nth-child(1){ animation-delay: .04s; }
.al:nth-child(2){ animation-delay: .10s; }
.al:nth-child(3){ animation-delay: .15s; }
.al:nth-child(n+4){ animation-delay: .20s; }
.al:hover { border-color: rgba(255,255,255,0.18); box-shadow: 0 8px 32px rgba(0,0,0,0.5); background: rgba(255,255,255,0.05); }

.hi  { border-left: 3px solid #00d68f; }
.mid { border-left: 3px solid #69f0ae; }
.low { border-left: 3px solid #ffd740; }
.neg { border-left: 3px solid #ef5350; }

/* Alert header */
.al-hd {
    display: flex; align-items: flex-start; justify-content: space-between;
    padding: 14px 20px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.al-name { font-size: 15px; font-weight: 700; color: #fff; letter-spacing: -0.2px; }
.al-meta { font-size: 10px; color: rgba(255,255,255,0.35); text-transform: uppercase; letter-spacing: 0.8px; margin-top: 3px; }
.al-right { text-align: right; flex-shrink: 0; }
.ex-tag  {
    display: inline-block; font-size: 9px; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.5px;
    padding: 2px 8px; border-radius: 20px; margin-bottom: 6px;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
    color: rgba(255,255,255,0.3);
}
.al-gain { font-size: 32px; font-weight: 900; letter-spacing: -1.5px; line-height: 1; font-variant-numeric: tabular-nums; }
.al-glbl { font-size: 9px; color: rgba(255,255,255,0.3); margin-top: 4px; text-transform: uppercase; letter-spacing: 1px; }

.chi { color: #00d68f; }
.cmi { color: #69f0ae; }
.clo { color: #ffd740; }
.cne { color: #ef5350; }

/* Alert body: oculto por defecto, visible al hover */
.al-body { display: none; }
.al:hover .al-body { display: flex; }
.al-col  { flex: 1; padding: 14px 20px 16px; }
.al-col + .al-col { border-left: 1px solid rgba(255,255,255,0.05); }

/* Alert footer: oculto por defecto, visible al hover */
.al-ft {
    display: none; align-items: center; flex-wrap: wrap;
    padding: 8px 20px; border-top: 1px solid rgba(255,255,255,0.04);
    background: rgba(0,0,0,0.14); font-size: 10.5px;
}
.al:hover .al-ft { display: flex; }

.al-dir  { display: inline-block; font-size: 8px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; padding: 2px 8px; border-radius: 4px; margin-bottom: 5px; }
.dv { color: #4fc3f7; background: rgba(79,195,247,0.08); }
.dc { color: #00d68f;  background: rgba(0,214,143,0.08); }

.al-hint  { font-size: 9px; color: rgba(255,255,255,0.3); margin-bottom: 8px; }
.al-filt  { display: inline-block; font-size: 8px; color: #ffd740; background: rgba(255,215,64,.07); border: 1px solid rgba(255,215,64,.15); padding: 2px 8px; border-radius: 20px; margin-bottom: 8px; }
.al-price { font-size: 24px; font-weight: 800; color: #fff; letter-spacing: -0.8px; line-height: 1; font-variant-numeric: tabular-nums; }
.al-curr  { font-size: 12px; color: rgba(255,255,255,0.4); font-weight: 500; margin-left: 2px; }
.al-ref   { font-size: 9px; color: rgba(255,255,255,0.25); margin: 5px 0 10px; }

.al-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.al-row:last-child { border-bottom: none; }
.al-k { font-size: 10px; color: rgba(255,255,255,0.72); text-transform: uppercase; letter-spacing: 0.4px; font-weight: 600; flex-shrink: 0; }
.al-v { font-size: 11.5px; color: rgba(255,255,255,0.88); font-weight: 500; text-align: right; max-width: 62%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.fl { color: rgba(255,255,255,0.18); }
.fv { color: rgba(255,255,255,0.45); font-weight: 600; margin-left: 3px; }
.fn { font-weight: 700; margin-left: 3px; }
.fm { color: rgba(255,255,255,0.13); font-size: 9px; margin-left: 3px; }
.fs { color: rgba(255,255,255,0.07); padding: 0 10px; }
.ftime { margin-left: auto; color: rgba(255,255,255,0.1); font-size: 9.5px; }

/* Empty state */
.empty-st { text-align: center; padding: 80px 24px; color: rgba(255,255,255,0.08); font-size: 14px; line-height: 3; }
"""


# CSS para Telegram preview (iframe separado)
CARD_CSS = DASHBOARD_CSS + """
/* ── Telegram ── */
.tg-wrap { background: linear-gradient(160deg,#141928,#1b2133); border-radius: 16px; padding: 20px 18px; }
.tg-bubble { background: #2b5278; border-radius: 16px 16px 16px 3px; padding: 16px 18px 13px; max-width: 440px; color: #fff; font-size: 13.5px; line-height: 1.7; box-shadow: 0 6px 28px rgba(0,0,0,0.5); margin-bottom: 20px; }
.tg-header { font-weight: 700; font-size: 13px; color: rgba(255,255,255,.46); margin-bottom: 2px; }
.tg-diff   { color: #00d68f; font-weight: 800; font-size: 24px; margin: 4px 0 13px; letter-spacing: -0.5px; }
.tg-divider { border: none; border-top: 1px solid rgba(255,255,255,.1); margin: 10px 0; }
.tg-section { font-weight: 700; color: #90caf9; margin: 11px 0 5px; text-transform: uppercase; font-size: 10.5px; letter-spacing: 1.2px; }
.tg-row { display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,.05); }
.tg-row:last-of-type { border-bottom: none; }
.tg-key { font-size: 11px; color: rgba(255,255,255,.42); flex-shrink: 0; }
.tg-val { font-size: 12.5px; color: rgba(255,255,255,.9); font-weight: 500; text-align: right; max-width: 60%; }
.tg-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 11px; }
.tg-time   { font-size: 10px; color: rgba(255,255,255,.28); }
.tg-copy { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.14); color: rgba(255,255,255,.6); font-size: 11px; border-radius: 8px; padding: 5px 12px; cursor: pointer; transition: all .12s ease; font-family: inherit; }
.tg-copy:hover  { background: rgba(255,255,255,.14); color: #fff; }
.tg-copy.copied { background: rgba(0,214,143,.14); border-color: rgba(0,214,143,.28); color: #00d68f; }
"""

# kept for backward compat — ahora apunta al mismo CSS
HERO_CSS = DASHBOARD_CSS
