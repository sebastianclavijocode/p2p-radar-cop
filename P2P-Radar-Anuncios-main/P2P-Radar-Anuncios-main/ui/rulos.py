"""Live COP route dashboard; transfers and costs are user configuration."""
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape
from itertools import permutations
import time
import pandas as pd
import streamlit as st
from core.routes import Edge, find_routes, number
from exchanges.live_routes import collect
from exchanges import criptoya, public_fx


def cop(value):
    return '$ ' + f'{float(value):,.0f}'.replace(',', '.') + ' COP'


@st.cache_data(ttl=30, show_spinner=False)
def snapshot(fees, methods, p2p, assets):
    return collect(fees, methods, p2p, assets)


@st.cache_data(ttl=60, show_spinner=False)
def comparison_snapshot(asset, volume):
    try:
        return criptoya.fetch_quotes(asset, volume), ''
    except Exception as exc:
        status = getattr(getattr(exc,'response',None),'status_code',None)
        return [], f'CriptoYa no disponible · HTTP {status}' if status else 'CriptoYa no disponible en esta consulta'


@st.cache_data(ttl=60, show_spinner=False)
def wallet_snapshot(capital):
    return public_fx.fetch_references(capital)


@st.cache_data(ttl=300, show_spinner=False)
def withdrawal_snapshot():
    try:
        return criptoya.fetch_fees(), ''
    except Exception:
        return {}, 'No fue posible consultar comisiones de retiro; se cargó el perfil inicial editable.'


STYLE = """<style>
:root{--cyan:#28c6ef;--green:#24d1a0;--muted:#8c9bb2;--line:#242b37}
.stApp{background:radial-gradient(ellipse at 0 0,#1a1529 0,transparent 55%),#0b0e14;color:#e9edf6}
.stApp:has(.st-key-radar-toolbar) [data-testid="stHeader"]{background:transparent;height:0;visibility:hidden}
.stApp:has(.st-key-radar-toolbar) [data-testid="stSidebar"],.stApp:has(.st-key-radar-toolbar) [data-testid="stSidebarCollapsedControl"]{display:none!important}
[data-testid="stMainBlockContainer"]{max-width:1140px;padding:20px 24px 65px}
[data-testid="stVerticalBlock"]{gap:.65rem}
.st-key-radar-toolbar{padding:4px 0 16px;border-bottom:1px solid #252631;margin-bottom:14px}
.brand{font-size:23px;font-weight:800;letter-spacing:-.5px;color:#27c7ef;white-space:nowrap}.brand span{color:#65def5}.brand small{display:block;font-size:9px;letter-spacing:2.2px;color:#6c7b92;margin-left:29px;margin-top:2px}
button[kind="secondary"],[data-testid="stPopoverButton"]{background:#191d26;border:1px solid #2c313e;border-radius:11px;color:#e4e8f0;min-height:37px;font-size:12px}
button[kind="secondary"]:hover,[data-testid="stPopoverButton"]:hover{border-color:#28c6ef;color:#28c6ef}
[data-testid="stExpander"]{border-color:#262d39;border-radius:12px;background:#111620}
[data-testid="stExpander"] summary p{font-size:12px;color:#9aacc2}
.radar-hero{border:1px solid #40384b;background:linear-gradient(110deg,#21192c,#172137);border-radius:18px;padding:22px 24px;margin:4px 0 18px}
.hero-eyebrow{color:#e8c257;font-weight:750;font-size:16px;margin-bottom:9px}.hero-route{color:#30d6a3;font-weight:750;font-size:15px}.hero-note{color:#99a6be;font-size:12px;margin-top:8px}
.quote-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:0 0 22px}
.usdt-grid{grid-template-columns:repeat(5,minmax(0,1fr))}.usdt-grid .quote-value{font-size:20px}
@media(max-width:760px){.quote-grid.usdt-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
.quote-box{border:1px solid #292c3b;background:linear-gradient(125deg,#1c1b2b,#151b27);border-radius:15px;padding:18px 10px;text-align:center;min-height:106px}
.quote-label{font-size:10px;letter-spacing:.5px;color:#97a3b8;font-weight:700;text-transform:uppercase}.quote-value{font-size:23px;font-weight:800;letter-spacing:-.5px;color:#2ed2a3;margin:5px 0}.quote-note{font-size:11px;color:#8995ac}.blue{color:#4fa5fa}.purple{color:#b278ee}.cyan{color:#2cc9e8}.amber{color:#edb54c}
.section-title{font-size:17px;font-weight:750;margin:22px 0 14px;display:flex;align-items:center;gap:11px}.section-icon{width:32px;height:32px;border-radius:10px;background:#22203a;color:#81a1fd;display:inline-grid;place-items:center}.section-count{margin-left:auto;color:#697b94;font-size:11px;font-weight:500}
.rulo-card{border:1px solid #252c38;background:#141a24;border-radius:16px;padding:19px 18px 16px;margin:0 0 10px}.rulo-card.best{border-color:#216349}.route-head{display:flex;align-items:center;justify-content:space-between;gap:15px}.route-name{font-size:17px;font-weight:750}.route-pct{font-size:24px;font-weight:850;color:#27d3a3;white-space:nowrap}.loss{color:#f69d9d!important}.route-steps{margin-top:13px;padding:11px 10px;border-radius:8px;background:#1c2230;color:#94a4bc;font-size:12px;line-height:1.7}.route-foot{border-top:1px solid #242a35;padding-top:11px;margin-top:10px;display:flex;justify-content:space-between;gap:15px;color:#25d1a1;font-size:13px;font-weight:700}.route-foot small{font-size:11px;color:#8091a9;font-weight:400}
.empty-group{color:#71839f;font-size:13px;padding:0 0 12px}.market-wrap{border:1px solid #252c39;border-radius:14px;overflow:auto;background:#121721}.market-table{width:100%;border-collapse:collapse;font-size:13px;white-space:nowrap}.market-table th{font-size:10px;letter-spacing:.7px;color:#7e8da6;background:#161c29;text-align:left;padding:13px 16px}.market-table td{padding:13px 16px;border-top:1px solid #232a36;color:#d9e2ef}.market-table td:nth-child(n+3){font-variant-numeric:tabular-nums}.market-table .bid{color:#2bcda4}.coin-badge{font-size:10px;color:#91aed0;background:#202c3b;padding:4px 8px;border-radius:5px}.radar-status{display:flex;justify-content:space-between;gap:12px;color:#71819b;font-size:11px;padding:15px 1px}.status-dot{color:#35caa6}.radar-note{font-size:11px;color:#6f819c;line-height:1.7;margin:17px 0}
@media(max-width:760px){[data-testid="stMainBlockContainer"]{padding:14px 16px 45px}.quote-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.quote-value{font-size:17px;white-space:nowrap}.quote-box{padding:15px 6px}.quote-note{font-size:10px}.st-key-radar-toolbar button p{font-size:11px!important}.st-key-radar-toolbar [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:7px}.st-key-radar-toolbar [data-testid="stColumn"]{min-width:65px!important;flex:1!important}.st-key-radar-toolbar [data-testid="stColumn"]:first-child{min-width:100%!important}.brand{font-size:22px}.brand small{display:inline;margin-left:12px}.route-name{font-size:14px}.route-pct{font-size:20px}.route-foot{font-size:12px}.radar-hero{padding:18px}.section-title{font-size:15px}}
</style>"""


def route_title(route):
    itinerary = [route.steps[0].source[0]]
    for edge in route.steps:
        if edge.target[0] != itinerary[-1]:
            itinerary.append(edge.target[0])
    coins = list(dict.fromkeys(e.target[1] for e in route.steps if e.target[1] != 'COP'))
    return ' → '.join(itinerary) + ' (' + ' / '.join(coins) + ')'


def route_card(route, best=False):
    steps = ' · '.join(f'{i+1}. {escape(e.label)}' for i,e in enumerate(route.steps))
    loss = ' loss' if route.profit < 0 else ''
    return (f'<article class="rulo-card {"best" if best else ""}"><div class="route-head">'
        f'<div class="route-name">{escape(route_title(route))}</div><div class="route-pct{loss}">{float(route.pct):+.2f}%</div></div>'
        f'<div class="route-steps">{steps}</div><div class="route-foot{loss}"><span>Ganancia neta estimada / operación<br>'
        f'<small>Capital {cop(route.capital)} · {len(route.steps)} pasos</small></span>'
        f'<span>{cop(route.profit)}<br><small>Saldo final {cop(route.final)}</small></span></div></article>')


def default_transfers(fee_data=None):
    fee_data = fee_data or {}
    networks = {'USDT':'Tron (TRC20)', 'BTC':'Bitcoin', 'ETH':'Ethereum', 'SOL':'Solana', 'USDC':'Ethereum (ERC20)'}
    rows=[]
    for asset in networks:
        for a,b in permutations(criptoya.VENUE_KEYS,2):
            origin=fee_data.get(criptoya.VENUE_KEYS[a],{}).get(asset,{})
            target=fee_data.get(criptoya.VENUE_KEYS[b],{}).get(asset,{})
            if not isinstance(origin,dict): origin={}
            if not isinstance(target,dict): target={}
            options=[]
            for chain in set(origin).intersection(target):
                try:
                    rate=number(origin[chain]['withdraw'])
                    if rate>=0: options.append((rate,chain))
                except (KeyError,ValueError,TypeError,ArithmeticError): pass
            rate,chain=min(options) if options else (0.0,networks[asset])
            stamp=origin.get(chain,{}).get('time',0)
            try:
                date=datetime.fromtimestamp(float(stamp),ZoneInfo('America/Bogota')).strftime('%d/%m/%Y %H:%M') if stamp else 'sin fecha del proveedor'
            except (ValueError,TypeError,OverflowError,OSError):
                date='sin fecha válida del proveedor'
            source=f'CriptoYa · retiro {date}; mínimo inicial 0' if options else 'Valores iniciales 0 · revisar en tu cuenta'
            rows.append({'Origen':a,'Destino':b,'Activo':asset,'Red':chain,'Comisión en activo':float(rate),
                         'Mínimo de retiro':0.0,'Confirmada':False,'Referencia':source})
    return pd.DataFrame(rows)


def comparison_html(rows, asset):
    table=[]
    for row in rows:
        stamp=datetime.fromtimestamp(row['timestamp'],ZoneInfo('America/Bogota')).strftime('%H:%M:%S')
        fmt=lambda x: '$ '+f'{x:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
        table.append(f'<tr><td>{escape(row["Plataforma"])}</td><td><span class="coin-badge">{escape(asset)}</span></td><td class="bid">{fmt(row["Venta COP"])}</td><td>{fmt(row["Compra COP"])}</td><td>{row["Spread %"]:+.2f}%</td><td>{stamp}</td></tr>')
    return '<div class="market-wrap"><table class="market-table"><thead><tr><th>PLATAFORMA</th><th>ACTIVO</th><th>VENTA COP</th><th>COMPRA COP</th><th>SPREAD</th><th>HORA COLOMBIA</th></tr></thead><tbody>'+''.join(table)+'</tbody></table></div>'


def comparison_tiles(rows):
    fmt=lambda x: '$ '+f'{x:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
    return '<div class="quote-grid usdt-grid">'+''.join(f'<a class="quote-box" href="https://criptoya.com/co#{escape(row["Activo"])}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;display:block"><div class="quote-label">{escape(row["Plataforma"])} · {escape(row["Activo"])}</div><div class="quote-value">{fmt(row["Compra COP"])}</div><div class="quote-note">Venta {fmt(row["Venta COP"])}<br>CriptoYa · COP</div></a>' for row in rows[:5])+'</div>'


def usdt_tiles(edges, manual=None):
    links = {'Binance':'https://p2p.binance.com/es/trade/all-payments/USDT?fiat=COP',
             'Bitso':'https://bitso.com/', 'Bybit':'https://www.bybit.com/fiat/trade/otc/?actionType=1&token=USDT&fiat=COP',
             'OKX':'https://www.okx.com/es-es/p2p-markets/cop/buy-usdt',
             'MEXC':'https://www.mexc.com/buy-crypto/p2p/buy/USDT/COP'}
    cards = []
    for venue, link in links.items():
        buy = [e for e in edges if e.source == (venue,'COP') and e.target == (venue,'USDT')]
        sell = [e for e in edges if e.source == (venue,'USDT') and e.target == (venue,'COP')]
        fmt = lambda v: ('$ '+f'{float(v):,.2f}'.replace(',','X').replace('.',',').replace('X','.')) if v is not None else '—'
        ask = min((e.levels[0][0] for e in buy), default=None)
        bid = max((e.levels[0][0] for e in sell), default=None)
        note = 'COP / USDT · spot' if venue == 'Bitso' else 'COP / USDT · P2P'
        if ask is None: note = 'Cotización COP no conectada'
        if ask is None and manual is not None:
            entry = manual[(manual['Plataforma'] == venue + ' P2P') & (manual['Activo'] == 'USDT')]
            if not entry.empty:
                ask, bid = entry.iloc[0]['Compra COP'], entry.iloc[0]['Venta COP']
                note = 'COP / USDT · entrada manual'
        cards.append(f'<a class="quote-box" href="{escape(link,quote=True)}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;display:block"><div class="quote-label">{venue} · comprar USDT</div><div class="quote-value">{fmt(ask)}</div><div class="quote-note">Venta {fmt(bid)}<br>{note}</div></a>')
    return '<div class="quote-grid usdt-grid">'+''.join(cards)+'</div>'


def render():
    st.markdown(STYLE, unsafe_allow_html=True)
    with st.container(key='radar-toolbar'):
        brand, filters, simulation, refresh_col, views = st.columns([3.6, 1.1, 1.2, .65, 1.35], vertical_alignment='center')
        brand.markdown('<div class="brand">⇄ Arbitraje<span>COP</span><small>COLOMBIA</small></div>', unsafe_allow_html=True)
        with filters.popover('Filtros', width='stretch'):
            quote_asset = st.selectbox('Activo de la comparación COP', ['USDT','USDC','BTC','ETH','SOL'])
            quote_volume = st.number_input('Volumen de referencia en cripto',min_value=0.000001, value=1000.0 if quote_asset in ('USDT','USDC') else 0.1, key='quote-volume-'+quote_asset, format='%.6f')
            assets = st.multiselect('Criptomonedas del recorrido', ['BTC','ETH','SOL','USDC'], default=['BTC','ETH','SOL','USDC'])
            st.caption('USDT conecta la entrada y salida en COP.')
            max_venues = st.selectbox('Máximo de exchanges', [2,3], index=1)
            threshold = st.number_input('Rendimiento mínimo (%)', value=0.0, min_value=-100.0, max_value=100.0, step=0.1)
            p2p = st.checkbox('Incluir Binance P2P', value=True)
            methods = st.multiselect('Métodos de pago · consulta directa Binance', ['BancolombiaSA','Nequi','Davivienda','BancoDeBogota'], default=['BancolombiaSA','Nequi'])
            st.caption('CriptoYa no devuelve filtros por banco ni condiciones del anuncio; el modo automático muestra oportunidades estimadas.')
            automatic = st.checkbox('Actualizar precios cada 30 segundos', value=True)
        with simulation.popover('Simular', width='stretch'):
            auto_mode = st.checkbox('Detectar rulos automáticamente con datos publicados',value=True)
            capital = st.number_input('Capital inicial (COP)', min_value=1000.0, max_value=1e12, value=2000000.0, step=100000.0)
            cash_cost = st.number_input('Otros costos totales (COP)', min_value=0.0, value=0.0, step=1000.0)
            slippage = st.number_input('Margen adicional por cambio de precio (%) por conversión', min_value=0.0, max_value=10.0, value=0.1, step=0.05)
            st.caption('Incluye profundidad del libro. Ajusta estas tarifas a tu cuenta.')
            fees = {name: st.number_input(name, min_value=0.0, max_value=20.0, value=default, step=0.01, key='rulo-fee-' + name)
                    for name, default in [('Bitso',0.65),('Binance',0.10),('Bybit',0.10),('OKX',0.10),('MEXC',0.10),('Binance P2P',0.0)]}
            costs_ok = st.checkbox('Confirmé mis comisiones y otros costos')
        if refresh_col.button('↻', help='Actualizar cotizaciones', width='stretch'):
            snapshot.clear()
            comparison_snapshot.clear()
            withdrawal_snapshot.clear()
            wallet_snapshot.clear()
        views.button('P2P', help='Abrir Radar original · Yo publico', width='stretch', on_click=lambda: st.session_state.update({'radar-view':'Radar original · Yo publico'}))
    live_slot = st.container()
    with st.expander('Cotizaciones manuales · respaldo opcional', expanded=False):
        st.caption('La comparación principal usa CriptoYa automáticamente. Aquí puedes registrar un precio de tu cuenta como referencia adicional; estas entradas manuales no alimentan rutas.')
        st.markdown('[Belo Colombia](https://www.belo.app/blog/como-cargar-pesos-colombianos-en-tu-cuenta-digital) · [Lemon Colombia](https://www.wiki.lemon.me/es-co/novedades/comprar-dolar-digital-colombia) · [MEXC COP](https://www.mexc.com/buy-crypto/p2p/buy/USDT/COP) · [OKX COP](https://www.okx.com/es-es/p2p-markets/cop/buy-usdt)')
        manual = st.data_editor(pd.DataFrame([{'Plataforma':v,'Activo':'USDC' if v=='ARQ' else 'USDT','Compra COP':None,'Venta COP':None} for v in ['MEXC P2P','OKX P2P','Bybit P2P','Belo','Lemon Cash','ARQ','Fiwind','Cocos Crypto','Buenbit','Ripio','Satoshi Tango','Astropay','Tienda Crypto','Decrypto',"Let’s Bit"]]), hide_index=True, width='stretch', key='manual-cop-quotes', disabled=['Plataforma'], column_config={'Compra COP':st.column_config.NumberColumn(min_value=0.01),'Venta COP':st.column_config.NumberColumn(min_value=0.01),'Activo':st.column_config.SelectboxColumn(options=['USDT','USDC'])})
        st.caption('En las demás plataformas de la lista debes comprobar primero disponibilidad de COP y requisitos de tu cuenta.')
        valid_manual = manual.dropna(subset=['Compra COP','Venta COP']).copy()
        if not valid_manual.empty:
            valid_manual = valid_manual[(valid_manual['Compra COP']>0)&(valid_manual['Venta COP']>0)]
            valid_manual['Spread %']=(valid_manual['Venta COP']/valid_manual['Compra COP']-1)*100
            st.dataframe(valid_manual.sort_values('Venta COP',ascending=False),hide_index=True,width='stretch')
    network_slot = st.container()
    with network_slot.expander('⚙  Costos y redes avanzados · opcional', expanded=False):
        st.caption('El modo automático no requiere rellenar esta tabla. Estos ajustes solo se usan si desactivas el cálculo automático en Simular.')
        st.write('1. Busca la dirección que usarás. 2. Escribe la red compatible en ambas cuentas. 3. Completa comisión y mínimo de retiro. 4. Marca Confirmada solo en esa fila.')
        st.caption('Perfil inicial incluido: redes sugeridas, comisiones y mínimos editables. Confirmar todas incluye las monedas seleccionadas.')
        st.caption('Red debe coincidir en retiro y depósito. Confirmada significa que tú revisaste disponibilidad, '
                   'comisión y mínimo hoy; la aplicación no consulta tu cuenta. Sin confirmación no se usa la transferencia.')
        fee_data,fee_error=withdrawal_snapshot()
        if fee_error: st.warning(fee_error)
        st.info('Comisiones de retiro rellenadas desde CriptoYa. Se elige la red de menor costo publicada en ambas plataformas; debes verificar también depósito y disponibilidad. La API no informa mínimos: quedan en 0 como valor inicial editable, no como mínimo verificado. Las filas sin tarifa publicada usan 0 y están identificadas.')
        st.markdown('[Fuente de comisiones: CriptoYa](https://docs.criptoya.com/colombia/operations/get-fees.html) · [Tarifas Bitso](https://bitso.com/fees/transactions) · [Redes Bitso](https://support.bitso.com/hc/en-us/articles/4419901801748-Which-network-to-use-to-deposit-or-withdraw-crypto-on-Bitso)')
        with st.expander('Comisiones publicadas · redes de todas las plataformas'):
            published=[]
            for provider,name in criptoya.NAMES.items():
                for coin in ['USDT']+assets:
                    for chain,entry in fee_data.get(provider,{}).get(coin,{}).items():
                        try:
                            fee=number(entry['withdraw'])
                            if fee<0: continue
                            stamp=float(entry.get('time',0))
                            date=datetime.fromtimestamp(stamp,ZoneInfo('America/Bogota')).strftime('%d/%m/%Y %H:%M') if stamp else 'Sin fecha'
                            published.append({'Plataforma':name,'Activo':coin,'Red':chain,'Comisión en activo':float(fee),'Fecha del proveedor':date})
                        except (KeyError,ValueError,TypeError,ArithmeticError,OSError): continue
            if published:
                st.dataframe(pd.DataFrame(published),hide_index=True,width='stretch')
            st.caption('Fuente: CriptoYa. La presencia de una red de retiro no certifica que el depósito esté habilitado en tu cuenta. Las fechas antiguas o ausentes requieren revisión.')
        transfer_frame = default_transfers(fee_data)
        if 'rulo-transfer-base' not in st.session_state:
            st.session_state['rulo-transfer-base'] = transfer_frame.copy(deep=True)
        if 'rulo-transfer-base' in st.session_state:
            old = st.session_state['rulo-transfer-base'].set_index(['Origen','Destino','Activo'])
            merged = transfer_frame.set_index(['Origen','Destino','Activo'])
            merged.update(old)
            transfer_frame = merged.reset_index()
        revision = st.session_state.get('rulo-transfer-revision', 0)
        editor_key = 'rulo-transfers-v2' if revision == 0 else f'rulo-transfers-bulk-{revision}'
        config = st.data_editor(transfer_frame, hide_index=True, width='stretch',
            disabled=['Origen', 'Destino', 'Activo', 'Referencia'], key=editor_key,
            column_config={'Red': st.column_config.TextColumn(help='Nombre de la misma red en retiro y depósito. No es el nombre del exchange.'), 'Confirmada': st.column_config.CheckboxColumn(help='Marca después de completar red, comisión y mínimo de retiro.'), 'Comisión en activo': st.column_config.NumberColumn(min_value=0.0, format='%.8f'),
                           'Mínimo de retiro': st.column_config.NumberColumn(min_value=0.0, format='%.8f')})
        confirm_col, clear_col = st.columns(2)
        confirm_all = confirm_col.button('Confirmar todas', key='rulo-confirm-all',
            help='Confirma las filas completas de las monedas seleccionadas. Al pulsar declaras que revisaste sus redes y costos.')
        clear_all = clear_col.button('Desmarcar todas', key='rulo-clear-all')
        if confirm_all or clear_all:
            updated = config.copy(deep=True)
            selected = updated['Activo'].isin(['USDT'] + assets)
            valid = selected.copy()
            valid &= updated['Red'].fillna('').astype(str).str.strip().str.lower().isin(['', 'none', 'nan']) == False
            for field in ('Comisión en activo', 'Mínimo de retiro'):
                values = pd.to_numeric(updated[field], errors='coerce')
                valid &= values.notna() & values.ge(0) & values.lt(float('inf'))
            if clear_all:
                updated['Confirmada'] = False
                message = 'Se desmarcaron todas las transferencias.'
            else:
                updated.loc[selected, 'Confirmada'] = valid[selected]
                count, pending = int(valid.sum()), int((selected & ~valid).sum())
                message = f'{count} transferencias confirmadas. {pending} pendientes de red, comisión o mínimo.'
            st.session_state['rulo-transfer-base'] = updated
            st.session_state['rulo-transfer-revision'] = revision + 1
            st.session_state['rulo-transfer-message'] = message
            st.rerun()
        if 'rulo-transfer-message' in st.session_state:
            st.info(st.session_state.pop('rulo-transfer-message'))
        st.download_button('Descargar configuración de redes', config.to_csv(index=False).encode('utf-8-sig'), file_name='redes-rulos-cop.csv', mime='text/csv')
        st.caption('Solo para el modo manual: marca «Confirmé mis comisiones y otros costos» en Simular. El modo automático funciona sin esta confirmación.')
        st.caption('La configuración se conserva durante esta sesión. No se envía dinero ni se guardan claves de exchanges.')

    transfers, errors = [], []
    for row in config.to_dict('records'):
        if row['Activo'] not in ['USDT'] + assets or not row['Confirmada']:
            continue
        try:
            network = str(row['Red']).strip()
            if not network or network.lower() in ('none', 'nan'):
                raise ValueError('falta la red')
            if pd.isna(row['Comisión en activo']) or pd.isna(row['Mínimo de retiro']):
                raise ValueError('falta comisión o mínimo de retiro')
            fee, minimum = number(row['Comisión en activo']), number(row['Mínimo de retiro'])
            if fee < 0 or minimum < 0:
                raise ValueError('costos negativos')
            transfers.append(Edge((row['Origen'], row['Activo']), (row['Destino'], row['Activo']),
                'transfer', fixed=fee, minimum=minimum, verified=True,
                label=f"Transferir {row['Activo']} por {network} · confirmación manual", reference='Configuración del usuario'))
        except (ValueError, ArithmeticError) as exc:
            errors.append(f"{row['Origen']} → {row['Destino']} ({row['Activo']}): {exc}")
    if errors:
        st.warning(f'{len(errors)} transferencias incompletas se excluyeron. Completa su red y costos o desmarca Confirmada. Las demás siguen disponibles.')
        with st.expander('Ver transferencias pendientes'):
            for error in errors:
                st.write(error)

    @st.fragment(run_every=30 if automatic else None)
    def live_panel():
        with st.spinner('Actualizando mercado…'):
            edges, statuses, received = snapshot(fees, tuple(methods), p2p, tuple(assets))
            comparisons,comparison_error=comparison_snapshot(quote_asset,quote_volume)
            auto_usdt,usdt_error = comparison_snapshot('USDT',1000.0)
            auto_usdc,usdc_error = comparison_snapshot('USDC',1000.0)
        now = time.time()
        comparisons = [r for r in comparisons if -5 <= now-r['timestamp'] <= 180]
        fresh = [e for e in edges if -5 <= now-e.observed <= 90]
        if auto_mode:
            current_fee_data,current_fee_error=withdrawal_snapshot()
            auto_rows=auto_usdt+(auto_usdc if 'USDC' in assets else [])
            if not p2p: auto_rows=[r for r in auto_rows if r['id']!='binancep2p']
            aggregate,automatic_transfers=criptoya.automatic_edges(auto_rows,current_fee_data,now)
            spot=[e for e in fresh if 'COP' not in (e.source[1],e.target[1])]
            routes=find_routes(spot+aggregate+automatic_transfers,capital,max_venues,cash_cost,slippage,now,max_age=180,allow_indicative=True)
            ready=True
        else:
            ready = costs_ok and bool(transfers)
            routes = find_routes(fresh+transfers, capital, max_venues, cash_cost, slippage, now) if ready else []
        visible = [r for r in routes if float(r.pct) >= threshold]
        best = visible[0] if visible else None
        hero_title = '◇ Mejor ruta estimada de esta consulta' if best else '◇ Radar automático COP' if auto_mode else '◇ Tu radar en pesos colombianos'
        hero_route = escape(route_title(best)) + f' · {float(best.pct):+.2f}% neto estimado' if best else 'Sin oportunidades positivas con los datos disponibles.' if auto_mode else 'COP → Cripto → COP'
        hero_note = 'Precios y comisiones publicados. Depósitos, mínimos y condiciones de cuenta sin verificar; no incluye impuestos o cargos bancarios adicionales.' if auto_mode else 'Incluye los costos y las redes que configuraste.' if ready else 'Abre Simular para confirmar costos y configura tus transferencias al final de esta página.'
        st.markdown(f'<div class="radar-hero"><div class="hero-eyebrow">{hero_title}</div><div class="hero-route">{hero_route}</div><div class="hero-note">{hero_note}</div></div>', unsafe_allow_html=True)
        source_count = sum(s['Estado']=='OK' for s in statuses)
        st.markdown(comparison_tiles(comparisons) if comparisons else usdt_tiles(fresh, valid_manual), unsafe_allow_html=True)
        st.caption(f'Capital {cop(capital)} · {source_count}/{len(statuses)} fuentes directas · Hasta {max_venues} exchanges · {len(comparisons)} plataformas en comparación COP.')
        export=[]
        for venues, icon, title in [(2,'⇄','Arbitrajes entre exchanges'),(3,'↻','Rulos de tres exchanges')]:
            if venues>max_venues: continue
            group=[r for r in visible if len(r.venues)==venues][:10]
            st.markdown(f'<div class="section-title"><span class="section-icon">{icon}</span>{title}<span class="section-count">{len(group)} rutas</span></div>',unsafe_allow_html=True)
            if not group:
                note='Sin oportunidades que cumplan tus filtros con los precios y comisiones disponibles.' if auto_mode else 'Pendiente de configurar redes y confirmar costos.' if not ready else 'Sin oportunidades que cumplan tus filtros en esta consulta.'
                st.markdown(f'<div class="empty-group">{note}</div>',unsafe_allow_html=True)
            for i,r in enumerate(group):
                st.markdown(route_card(r,r is best),unsafe_allow_html=True)
                if auto_mode:
                    st.caption('Oportunidad estimada: red y comisión publicadas; revisa depósitos, mínimos, límites y métodos de pago antes de operar.')
                with st.expander(f'Detalle de la ruta · {venues} exchanges · {i+1}'):
                    detail=[{'Paso':j+1,'Operación':e.label,'Desde':' / '.join(e.source),'Hasta':' / '.join(e.target),'Saldo antes':f'{r.balances[j]:.8f}','Saldo después':f'{r.balances[j+1]:.8f}','Comisión %':str(e.fee_pct),'Costo fijo':str(e.fixed)} for j,e in enumerate(r.steps)]
                    st.dataframe(pd.DataFrame(detail),hide_index=True,width='stretch')
                export.append({'Ruta':route_title(r),'Capital_COP':str(r.capital),'Final_COP':str(r.final),'Resultado_COP':str(r.profit),'Porcentaje':str(r.pct)})
        st.markdown(f'<div class="section-title"><span class="section-icon">≡</span>{escape(quote_asset)} en Colombia · compra y venta</div>',unsafe_allow_html=True)
        if comparison_error: st.warning(comparison_error)
        if comparisons:
            st.markdown(comparison_html(comparisons,quote_asset),unsafe_allow_html=True)
            st.caption(f'Fuente: CriptoYa · Volumen consultado {quote_volume:g} {quote_asset} · Campos totalAsk / totalBid · Precios con antigüedad máxima de 3 minutos. Spread = venta / compra − 1. El modo automático usa estas referencias para estimar rulos; no incluye mínimos ni condiciones del anuncio, método de pago o profundidad ejecutable.')
            st.markdown('[Ver fuente y redes por plataforma](https://criptoya.com/co#USDT) · [Documentación de la API](https://docs.criptoya.com/colombia/)')
            st.download_button('Descargar comparación COP',pd.DataFrame(comparisons).drop(columns=['id','timestamp']).to_csv(index=False).encode('utf-8-sig'),file_name='cotizaciones-cop.csv',mime='text/csv')
        elif not comparison_error:
            st.info('Sin cotizaciones vigentes para este activo y volumen.')
        arq=[r for r in auto_usdc if r['id']=='dolarapp' and -5<=now-r['timestamp']<=180]
        if arq and quote_asset!='USDC':
            st.markdown('<div class="section-title"><span class="section-icon">$</span>ARQ · referencia USDc / COP</div>',unsafe_allow_html=True)
            st.markdown(comparison_html(arq,'USDC'),unsafe_allow_html=True)
            st.caption('CriptoYa identifica esta cotización como USDC. El saldo USDc de ARQ y sus transferencias deben comprobarse antes de conectarlo a una ruta on-chain; no se supone que sea un retiro USDC disponible.')
        wallet_rows,wallet_errors=wallet_snapshot(float(capital))
        wallet_rows=[r for r in wallet_rows if -5<=now-r['timestamp']<=180]
        st.markdown('<div class="section-title"><span class="section-icon">$</span>Global66 y AstroPay · dólares / COP</div>',unsafe_allow_html=True)
        if wallet_rows:
            wallet_table=pd.DataFrame(wallet_rows).drop(columns=['timestamp']).rename(columns={'Costo compra':'Costo compra (COP)'})
            for col in ('Costo compra (COP)','Costo venta USD'):
                wallet_table[col]=wallet_table[col].map(lambda v:'Incluido en tasa' if pd.isna(v) else f'{v:,.2f}')
            st.dataframe(wallet_table,hide_index=True,width='stretch')
            st.caption(f'Compra: {cop(capital)}. Venta: 1.000 USD. Global66 usa el importe final cotizado, con costo incluido; no se descuenta dos veces. AstroPay usa la tasa cliente, con spread incluido. Consulta pública, no cotización garantizada para tu cuenta. Los USD son saldos de estas aplicaciones: no se asumen USDT ni transferencias gratuitas a exchanges.')
        for error in wallet_errors: st.info(error)
        st.caption('Estas cotizaciones se muestran automáticamente. Las rutas bancarias hacia exchanges no se incorporan a los rulos hasta disponer de sus condiciones de transferencia y conversión.')
        st.markdown('<div class="section-title"><span class="section-icon">≡</span>Mercados directos utilizados por los rulos</div>',unsafe_allow_html=True)
        markets={}
        for e in fresh:
            if e.kind not in ('buy','sell'):continue
            base=e.target[1] if e.kind=='buy' else e.source[1]
            quote=e.source[1] if e.kind=='buy' else e.target[1]
            venue=e.source[0]+(' P2P' if 'P2P' in e.label else '')
            row=markets.setdefault((venue,base,quote),{})
            side='ask' if e.kind=='buy' else 'bid'
            price=float(e.levels[0][0])
            row[side]=(min(row[side],price) if side=='ask' else max(row[side],price)) if side in row else price
        table=[]
        for (venue,base,quote),row in sorted(markets.items()):
            fmt=lambda v: f'{v:,.4f}' if v is not None else '—'
            spread=(row['bid']/row['ask']-1)*100 if row.get('ask') and row.get('bid') else None
            table.append(f'<tr><td>{escape(venue)}</td><td><span class="coin-badge">{escape(base)} / {escape(quote)}</span></td><td class="bid">{fmt(row.get("bid"))}</td><td>{fmt(row.get("ask"))}</td><td>{f"{spread:+.2f}%" if spread is not None else "—"}</td></tr>')
        for _, row in valid_manual.iterrows():
            table.append(f'<tr><td>{escape(row["Plataforma"])} · manual</td><td><span class="coin-badge">{escape(row["Activo"])} / COP</span></td><td class="bid">{row["Venta COP"]:,.2f}</td><td>{row["Compra COP"]:,.2f}</td><td>{row["Spread %"]:+.2f}%</td></tr>')
        st.markdown('<div class="market-wrap"><table class="market-table"><thead><tr><th>EXCHANGE</th><th>PAR</th><th>VENTA / BID</th><th>COMPRA / ASK</th><th>SPREAD</th></tr></thead><tbody>'+''.join(table)+'</tbody></table></div>',unsafe_allow_html=True)
        stamp=datetime.fromtimestamp(received,ZoneInfo('America/Bogota')).strftime('%H:%M:%S')
        st.markdown(f'<div class="radar-status"><span><span class="status-dot">●</span> Última consulta {stamp} · Colombia</span><span>{len(fresh)} cotizaciones vigentes</span></div>',unsafe_allow_html=True)
        with st.expander('Estado de las conexiones y alcance de los precios'):
            st.dataframe(pd.DataFrame(statuses),hide_index=True,width='stretch')
            app_states=[{'Aplicación':'Lemon','Estado':'Cotización COP vía CriptoYa' if any(r['id']=='lemoncash' for r in auto_usdt) else 'Sin precio COP vigente'},
                        {'Aplicación':'ARQ','Estado':'Cotización USDc/COP vía CriptoYa' if arq else 'Sin precio USDc/COP vigente'},
                        {'Aplicación':'AstroPay','Estado':'API pública USD/COP conectada' if any(r['Aplicación']=='AstroPay' for r in wallet_rows) else 'Sin cotización pública disponible'},
                        {'Aplicación':'Global66','Estado':'API pública USD/COP conectada' if any(r['Aplicación']=='Global66' for r in wallet_rows) else 'Sin cotización pública disponible'}]
            st.dataframe(pd.DataFrame(app_states),hide_index=True,width='stretch')
            st.markdown('[API AstroPay](https://developers.astropay.com/docs/platform/partners-services) · [API Global66](https://documents-b2b.global66.com/transactional-api/destinations/)')
            for error in set(e for e in (usdt_error,usdc_error) if e): st.warning(error)
            if auto_mode and current_fee_error: st.warning(current_fee_error)
            st.caption('Los libros directos consumen profundidad y aplican tarifas spot. Las referencias CriptoYa son precios agregados para el volumen consultado, sin mínimos o métodos del anuncio verificables. Se excluyen libros mayores de 90 segundos y referencias mayores de 3 minutos. Binance P2P consulta hasta 20 anuncios por lado; su endpoint web no garantiza estabilidad.')
        if export:
            st.download_button('Descargar rutas (CSV)',pd.DataFrame(export).to_csv(index=False).encode('utf-8-sig'),file_name='rulos-cop.csv',mime='text/csv')
        st.markdown('<p class="radar-note">Resultados estimados, no ganancias garantizadas. Verifica requisitos del anuncio, redes, mínimos de orden y disponibilidad de depósitos y retiros. Este radar no ejecuta operaciones.</p>',unsafe_allow_html=True)
    with live_slot:
        live_panel()
