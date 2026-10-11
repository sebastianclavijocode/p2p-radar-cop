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


def cop(value):
    return '$ ' + f'{float(value):,.0f}'.replace(',', '.') + ' COP'


@st.cache_data(ttl=30, show_spinner=False)
def snapshot(fees, methods, p2p, assets):
    return collect(fees, methods, p2p, assets)


STYLE = """<style>
:root{--cyan:#28c6ef;--green:#24d1a0;--muted:#8c9bb2;--line:#242b37}
.stApp{background:radial-gradient(ellipse at 0 0,#1a1529 0,transparent 55%),#0b0e14;color:#e9edf6}
[data-testid="stHeader"]{background:transparent;height:0;visibility:hidden}
[data-testid="stSidebarCollapsedControl"]{display:none}
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


def render():
    st.markdown(STYLE, unsafe_allow_html=True)
    with st.container(key='radar-toolbar'):
        brand, filters, simulation, refresh_col, views = st.columns([3.6, 1.1, 1.2, .65, 1.35], vertical_alignment='center')
        brand.markdown('<div class="brand">⇄ Arbitraje<span>COP</span><small>COLOMBIA</small></div>', unsafe_allow_html=True)
        with filters.popover('Filtros', width='stretch'):
            assets = st.multiselect('Criptomonedas del recorrido', ['BTC','ETH','SOL','USDC'], default=['BTC'])
            st.caption('USDT conecta la entrada y salida en COP.')
            max_venues = st.selectbox('Máximo de exchanges', [2,3], index=1)
            threshold = st.number_input('Rendimiento mínimo (%)', value=0.0, min_value=-100.0, max_value=100.0, step=0.1)
            p2p = st.checkbox('Incluir Binance P2P', value=True)
            methods = st.multiselect('Métodos de pago que puedo usar', ['BancolombiaSA','Nequi','Davivienda','BancoDeBogota'], default=['BancolombiaSA','Nequi'])
            automatic = st.checkbox('Actualizar precios cada 30 segundos', value=False)
        with simulation.popover('Simular', width='stretch'):
            capital = st.number_input('Capital inicial (COP)', min_value=1000.0, max_value=1e12, value=2000000.0, step=100000.0)
            cash_cost = st.number_input('Otros costos totales (COP)', min_value=0.0, value=0.0, step=1000.0)
            slippage = st.number_input('Margen adicional por cambio de precio (%) por conversión', min_value=0.0, max_value=10.0, value=0.1, step=0.05)
            st.caption('Incluye profundidad del libro. Ajusta estas tarifas a tu cuenta.')
            fees = {name: st.number_input(name, min_value=0.0, max_value=20.0, value=default, step=0.01, key='rulo-fee-' + name)
                    for name, default in [('Bitso',0.65),('Binance',0.10),('Bybit',0.10),('Binance P2P',0.0)]}
            costs_ok = st.checkbox('Confirmé mis comisiones y otros costos')
        if refresh_col.button('↻', help='Actualizar cotizaciones', width='stretch'):
            snapshot.clear()
        views.button('P2P', help='Abrir Radar original · Yo publico', width='stretch', on_click=lambda: st.session_state.update({'radar-view':'Radar original · Yo publico'}))
    live_slot = st.container()
    network_slot = st.container()
    with network_slot.expander('⚙  Redes y transferencias · configurar', expanded=False):
        st.write('1. Busca la dirección que usarás. 2. Escribe la red compatible en ambas cuentas. 3. Completa comisión y mínimo de retiro. 4. Marca Confirmada solo en esa fila.')
        st.caption('Puedes confirmar una fila o todas las completas. El botón solo incluye las monedas seleccionadas y no completa costos por ti.')
        st.caption('Red debe coincidir en retiro y depósito. Confirmada significa que tú revisaste disponibilidad, '
                   'comisión y mínimo hoy; la aplicación no consulta tu cuenta. Sin confirmación no se usa la transferencia.')
        rows = [{'Origen': a, 'Destino': b, 'Activo': asset, 'Red': {'USDT':'Tron (TRC20)', 'BTC':'Bitcoin', 'ETH':'Ethereum', 'SOL':'Solana', 'USDC':'Ethereum (ERC20)'}[asset], 'Comisión en activo': None,
                 'Mínimo de retiro': None, 'Confirmada': False}
                for asset in ('USDT', 'BTC', 'ETH', 'SOL', 'USDC') for a, b in permutations(('Binance', 'Bitso', 'Bybit'), 2)]
        st.info('Redes sugeridas, aún no verificadas en tus cuentas. Confirma que existan en retiro y depósito; completa comisión y mínimo. No se supone costo cero.')
        st.markdown('[Redes publicadas por Bitso](https://support.bitso.com/hc/en-us/articles/4419901801748-Which-network-to-use-to-deposit-or-withdraw-crypto-on-Bitso) · Verifica también el otro exchange.')
        transfer_frame = pd.DataFrame(rows).astype({'Comisión en activo': 'float64', 'Mínimo de retiro':'float64'})
        transfer_frame = st.session_state.get('rulo-transfer-base', transfer_frame)
        revision = st.session_state.get('rulo-transfer-revision', 0)
        editor_key = 'rulo-transfers-v2' if revision == 0 else f'rulo-transfers-bulk-{revision}'
        config = st.data_editor(transfer_frame, hide_index=True, width='stretch',
            disabled=['Origen', 'Destino', 'Activo'], key=editor_key,
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
        st.caption('Para calcular también debes marcar «Confirmé mis comisiones y otros costos» en la barra lateral.')
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
        now = time.time()
        fresh = [e for e in edges if -5 <= now-e.observed <= 90]
        ready = costs_ok and bool(transfers)
        routes = find_routes(fresh+transfers, capital, max_venues, cash_cost, slippage, now) if ready else []
        visible = [r for r in routes if float(r.pct) >= threshold]
        best = visible[0] if visible else None
        hero_title = '◇ Mejor ruta de esta consulta' if best else '◇ Tu radar en pesos colombianos'
        hero_route = escape(route_title(best)) + f' · {float(best.pct):+.2f}% neto estimado' if best else 'COP → Cripto → COP'
        hero_note = 'Incluye los costos y las redes que configuraste.' if ready else 'Abre Simular para confirmar costos y configura tus transferencias al final de esta página.'
        st.markdown(f'<div class="radar-hero"><div class="hero-eyebrow">{hero_title}</div><div class="hero-route">{hero_route}</div><div class="hero-note">{hero_note}</div></div>', unsafe_allow_html=True)
        buys = [e for e in fresh if e.source[1]=='COP' and e.target[1]=='USDT']
        sells = [e for e in fresh if e.target[1]=='COP' and e.source[1]=='USDT']
        buy = min(buys,key=lambda e:e.levels[0][0]) if buys else None
        sell = max(sells,key=lambda e:e.levels[0][0]) if sells else None
        quote_price = lambda edge: ('$ '+f'{float(edge.levels[0][0]):,.2f}'.replace(',','X').replace('.',',').replace('X','.')) if edge else '—'
        source_count = sum(s['Estado']=='OK' for s in statuses)
        summaries = [('COMPRA USDT',quote_price(buy),buy.source[0] if buy else 'Sin cotización',''),('VENTA USDT',quote_price(sell),sell.source[0] if sell else 'Sin cotización','blue'),('CAPITAL',cop(capital).replace(' COP',''),'Pesos colombianos','purple'),('FUENTES',f'{source_count} / {len(statuses)}','Con respuesta en esta consulta','cyan'),('RECORRIDOS',str(len(routes)) if ready else '—','Hasta '+str(max_venues)+' exchanges','amber')]
        st.markdown('<div class="quote-grid">'+''.join(f'<div class="quote-box"><div class="quote-label">{a}</div><div class="quote-value {d}">{b}</div><div class="quote-note">{c}</div></div>' for a,b,c,d in summaries)+'</div>',unsafe_allow_html=True)
        export=[]
        for venues, icon, title in [(2,'⇄','Arbitrajes entre exchanges'),(3,'↻','Rulos de tres exchanges')]:
            if venues>max_venues: continue
            group=[r for r in visible if len(r.venues)==venues][:10]
            st.markdown(f'<div class="section-title"><span class="section-icon">{icon}</span>{title}<span class="section-count">{len(group)} rutas</span></div>',unsafe_allow_html=True)
            if not group:
                note='Pendiente de configurar redes y confirmar costos.' if not ready else 'Sin oportunidades que cumplan tus filtros en esta consulta.'
                st.markdown(f'<div class="empty-group">{note}</div>',unsafe_allow_html=True)
            for i,r in enumerate(group):
                st.markdown(route_card(r,r is best),unsafe_allow_html=True)
                with st.expander(f'Detalle de la ruta · {venues} exchanges · {i+1}'):
                    detail=[{'Paso':j+1,'Operación':e.label,'Desde':' / '.join(e.source),'Hasta':' / '.join(e.target),'Saldo antes':f'{r.balances[j]:.8f}','Saldo después':f'{r.balances[j+1]:.8f}','Comisión %':str(e.fee_pct),'Costo fijo':str(e.fixed)} for j,e in enumerate(r.steps)]
                    st.dataframe(pd.DataFrame(detail),hide_index=True,width='stretch')
                export.append({'Ruta':route_title(r),'Capital_COP':str(r.capital),'Final_COP':str(r.final),'Resultado_COP':str(r.profit),'Porcentaje':str(r.pct)})
        st.markdown('<div class="section-title"><span class="section-icon">≡</span>Cotizaciones por exchange</div>',unsafe_allow_html=True)
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
        st.markdown('<div class="market-wrap"><table class="market-table"><thead><tr><th>EXCHANGE</th><th>PAR</th><th>VENTA / BID</th><th>COMPRA / ASK</th><th>SPREAD</th></tr></thead><tbody>'+''.join(table)+'</tbody></table></div>',unsafe_allow_html=True)
        stamp=datetime.fromtimestamp(received,ZoneInfo('America/Bogota')).strftime('%H:%M:%S')
        st.markdown(f'<div class="radar-status"><span><span class="status-dot">●</span> Última consulta {stamp} · Colombia</span><span>{len(fresh)} cotizaciones vigentes</span></div>',unsafe_allow_html=True)
        with st.expander('Estado de las conexiones y alcance de los precios'):
            st.dataframe(pd.DataFrame(statuses),hide_index=True,width='stretch')
            st.caption('Primer nivel de precio, sin comisiones, sujeto a límites y liquidez. El cálculo de rutas sí consume profundidad y aplica tus costos. Binance P2P consulta hasta 20 anuncios por lado; su endpoint web no garantiza estabilidad. Cotizaciones mayores de 90 segundos quedan excluidas.')
        if export:
            st.download_button('Descargar rutas (CSV)',pd.DataFrame(export).to_csv(index=False).encode('utf-8-sig'),file_name='rulos-cop.csv',mime='text/csv')
        st.markdown('<p class="radar-note">Resultados estimados, no ganancias garantizadas. Verifica requisitos del anuncio, redes, mínimos de orden y disponibilidad de depósitos y retiros. Este radar no ejecuta operaciones.</p>',unsafe_allow_html=True)
    with live_slot:
        live_panel()
