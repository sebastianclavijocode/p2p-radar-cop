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
def snapshot(fees, methods, p2p):
    return collect(fees, methods, p2p)


def render():
    st.markdown('''<style>
    .stApp{background:#0b111b;color:#e6f0fa}
    [data-testid="stMetric"]{background:#13202d;border:1px solid #25394c;border-radius:12px;padding:16px}
    [data-testid="stAlert"] p{color:#d5e7f7}
    .rulo-card{border:1px solid #284958;background:linear-gradient(120deg,#13252b,#121b29);border-radius:14px;padding:22px;margin:16px 0 5px}
    .rulo-card h3{margin:0;color:#ebf3fc;font-size:20px}.rulo-card p{color:#9eb3c7;font-size:13px}
    .rulo-result{font-size:25px;color:#42d9b0;font-weight:700}.loss{color:#fa9fa8}
    </style>''', unsafe_allow_html=True)
    st.caption('COLOMBIA / DATOS REALES / CONSULTA SIN EJECUCIÓN')
    st.title('⇄ Rulos en COP')
    st.write('Compara recorridos de dos o tres exchanges, desde tus pesos hasta volver a COP.')
    st.info('Los precios provienen de APIs. Las comisiones y redes las confirmas tú. '
            'El resultado es una estimación para los precios observados, no una ganancia garantizada.')
    with st.sidebar:
        st.header('Tu operación')
        capital = st.number_input('Capital inicial (COP)', min_value=1000.0, max_value=1e12, value=2000000.0, step=100000.0)
        max_venues = st.selectbox('Máximo de exchanges', [2, 3], index=1)
        threshold = st.number_input('Rendimiento mínimo (%)', value=0.0, min_value=-100.0, max_value=100.0, step=0.1)
        cash_cost = st.number_input('Otros costos totales (COP)', min_value=0.0, value=0.0, step=1000.0,
                                    help='Incluye aquí retiro fiat, costos bancarios e impuestos aplicables a tu operación.')
        slippage = st.number_input('Margen adicional por cambio de precio (%) por conversión', min_value=0.0, max_value=10.0, value=0.1, step=0.05)
        st.caption('La profundidad del libro ya se aplica al monto. Este margen es adicional.')
        with st.expander('Comisiones por conversión (%)', expanded=True):
            st.caption('Valores iniciales orientativos; reemplázalos con las tarifas de tu cuenta. Se descuentan del activo recibido.')
            fees = {name: st.number_input(name, min_value=0.0, max_value=20.0, value=default, step=0.01, key='rulo-fee-' + name)
                    for name, default in [('Bitso', 0.65), ('Binance', 0.10), ('Bybit', 0.10), ('Binance P2P', 0.0)]}
            costs_ok = st.checkbox('Confirmé mis comisiones y otros costos')
        p2p = st.checkbox('Incluir Binance P2P', value=True)
        methods = st.multiselect('Métodos de pago que puedo usar', ['BancolombiaSA', 'Nequi', 'Davivienda', 'BancoDeBogota'],
                                 default=['BancolombiaSA', 'Nequi'])
        st.caption('IDs de la plataforma. Solo se incluyen anuncios cuyo método coincide exactamente.')
        automatic = st.checkbox('Actualizar precios cada 30 segundos', value=False)
        if st.button('Actualizar cotizaciones', type='primary', width='stretch'):
            snapshot.clear()

    with st.expander('1 · Configurar transferencias entre exchanges', expanded=True):
        st.write('Completa únicamente las rutas de retiro que tengas habilitadas. Cada dirección tiene su propia comisión.')
        st.caption('Red debe coincidir en retiro y depósito. Confirmada significa que tú revisaste disponibilidad, '
                   'comisión y mínimo hoy; la aplicación no consulta tu cuenta. Sin confirmación no se usa la transferencia.')
        rows = [{'Origen': a, 'Destino': b, 'Activo': asset, 'Red': '', 'Comisión en activo': 0.0,
                 'Mínimo de retiro': 0.0, 'Confirmada': False}
                for asset in ('USDT', 'BTC') for a, b in permutations(('Binance', 'Bitso', 'Bybit'), 2)]
        config = st.data_editor(pd.DataFrame(rows), hide_index=True, width='stretch',
            disabled=['Origen', 'Destino', 'Activo'], key='rulo-transfers',
            column_config={'Comisión en activo': st.column_config.NumberColumn(min_value=0.0, format='%.8f'),
                           'Mínimo de retiro': st.column_config.NumberColumn(min_value=0.0, format='%.8f')})
        st.caption('La configuración se conserva durante esta sesión. No se envía dinero ni se guardan claves de exchanges.')

    transfers, errors = [], []
    for row in config.to_dict('records'):
        if not row['Confirmada']:
            continue
        try:
            network = str(row['Red']).strip()
            if not network or network.lower() in ('none', 'nan'):
                raise ValueError('falta la red')
            fee, minimum = number(row['Comisión en activo']), number(row['Mínimo de retiro'])
            if fee < 0 or minimum < 0:
                raise ValueError('costos negativos')
            transfers.append(Edge((row['Origen'], row['Activo']), (row['Destino'], row['Activo']),
                'transfer', fixed=fee, minimum=minimum, verified=True,
                label=f"Transferir {row['Activo']} por {network} · confirmación manual", reference='Configuración del usuario'))
        except (ValueError, ArithmeticError) as exc:
            errors.append(f"{row['Origen']} → {row['Destino']} ({row['Activo']}): {exc}")
    for error in errors:
        st.error(error)

    @st.fragment(run_every=30 if automatic else None)
    def live_panel():
        with st.spinner('Consultando libros y anuncios…'):
            edges, statuses, received = snapshot(fees, tuple(methods), p2p)
        now = time.time()
        fresh = [e for e in edges if -5 <= now - e.observed <= 90]
        c1, c2, c3 = st.columns(3)
        c1.metric('Fuentes con respuesta', f"{sum(s['Estado']=='OK' for s in statuses)} / {len(statuses)}")
        c2.metric('Conversiones vigentes', len(fresh))
        c3.metric('Capital de cálculo', cop(capital))
        st.caption('Consulta: ' + datetime.fromtimestamp(received, ZoneInfo('America/Bogota')).strftime('%d/%m/%Y %H:%M:%S') + ' · Colombia. Se excluyen cotizaciones con más de 90 segundos.')
        if len(fresh) != len(edges):
            st.warning('Se excluyeron cotizaciones vencidas. Revisa el estado de las fuentes o actualiza.')
        with st.expander('Estado de APIs y precios observados', expanded=not fresh):
            st.dataframe(pd.DataFrame(statuses), hide_index=True, width='stretch')
            if edges:
                st.dataframe(pd.DataFrame([{'Exchange': e.source[0], 'Entrada': e.source[1], 'Salida': e.target[1],
                    'Operación': e.label, 'Primer precio': float(e.levels[0][0]),
                    'Edad (segundos)': round(now-e.observed, 1), 'Vigente': e in fresh, 'Referencia': e.reference} for e in edges]),
                    hide_index=True, width='stretch')
            st.caption('Binance P2P usa un endpoint del sitio web, sin garantía de estabilidad. '
                       'Binance spot y P2P registran hora de recepción; Bitso y Bybit spot usan la hora del libro. '
                       'No se sustituye una respuesta fallida por datos de ejemplo. Se consulta una página de hasta 20 anuncios por lado.')
        st.subheader('2 · Rutas y resultado estimado')
        if not costs_ok or not transfers or errors:
            st.warning('Para calcular, confirma tus costos y al menos una transferencia válida en la tabla.')
            return
        routes = find_routes(fresh + transfers, capital, max_venues, cash_cost, slippage, now)
        visible = [r for r in routes if float(r.pct) >= threshold]
        st.caption(f'{len(routes)} rutas calculadas (máximo 100 mejores) · {len(visible)} sobre tu umbral. '
                   'Una ruta puede tener más pasos que exchanges; cada compra, venta y transferencia aparece abajo.')
        if not visible:
            st.info('No hay rutas que cumplan tus condiciones en esta consulta. '
                    'Puedes bajar el umbral para ver resultados negativos o revisar conexiones y límites.')
        export = []
        for i, r in enumerate(visible[:20]):
            itinerary = [r.steps[0].source[0]]
            for edge in r.steps:
                if edge.target[0] != itinerary[-1]:
                    itinerary.append(edge.target[0])
            path = ' → '.join(itinerary)
            st.markdown(f'<div class="rulo-card"><h3>{escape(path)}</h3>'
                f'<p>{len(r.venues)} exchanges · {len(r.steps)} pasos · capital {cop(r.capital)}</p>'
                f'<div class="rulo-result {"loss" if r.profit < 0 else ""}">{cop(r.profit)} · {float(r.pct):+.2f}%</div>'
                f'<p>Saldo final estimado: {cop(r.final)} · Redes y costos declarados por ti</p></div>', unsafe_allow_html=True)
            with st.expander(f'Ver recorrido y saldos · ruta {i+1}'):
                detail = [{'Paso': j+1, 'Operación': edge.label,
                    'Desde': ' / '.join(edge.source), 'Hasta': ' / '.join(edge.target),
                    'Saldo antes': f'{r.balances[j]:.8f}', 'Saldo después': f'{r.balances[j+1]:.8f}',
                    'Comisión %': str(edge.fee_pct), 'Costo fijo (activo de salida)': str(edge.fixed),
                    'Referencia': edge.reference} for j, edge in enumerate(r.steps)]
                st.dataframe(pd.DataFrame(detail), hide_index=True, width='stretch')
                st.caption(f'Otros costos al cierre: {cop(r.cash_cost)}. Incluye profundidad y margen adicional por conversión. '
                           'No valida precisión de orden, mínimos spot, estado de tu cuenta ni tiempo de llegada de transferencias; '
                           'compruébalos antes de operar. Los requisitos particulares del anunciante P2P también deben revisarse.')
            export.append({'Ruta': path, 'Pasos': len(r.steps), 'Capital_COP': str(r.capital),
                           'Final_COP': str(r.final), 'Resultado_COP': str(r.profit), 'Porcentaje': str(r.pct)})
        if export:
            st.download_button('Descargar resultados visibles (CSV)', pd.DataFrame(export).to_csv(index=False).encode('utf-8-sig'),
                               file_name='rulos-cop.csv', mime='text/csv')
    live_panel()
