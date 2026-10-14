"""A manual, fixed-price buy planning panel, separate from Hold and instant arbitrage."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from core.patient_buy import history_window, plan_levels, scenario, review, positive


def render(results, history, exchange, asset, capital, age_seconds):
    st.subheader('Compra paciente · anuncio por debajo del mercado')
    st.caption('Planifica una compra con precio fijo mientras esperas operar desde las 17:00. La referencia es lo que ofrecen otros compradores del mismo método, no el precio de compra inmediata.')
    if asset != 'USDT':
        st.info('Esta primera versión usa USDT/COP. Selecciona USDT y COP en el radar.')
        return
    available = {r.method_id:r for r in results if r.fiat=='COP' and r.ref_sell_ad and positive(r.ref_sell_ad.price)}
    if not available:
        st.info('Necesitamos una cotización de compradores en COP. Activa COP y actualiza el radar.')
        return
    if age_seconds > 90:
        st.warning('La cotización tiene más de 90 segundos. Actualiza el radar antes de ajustar tu anuncio.')
        return
    choices = list(available)
    key = 'patient_method_'+exchange
    if st.session_state.get(key) not in choices:
        st.session_state[key] = choices[0]
    method = st.selectbox('Método para tu anuncio',choices,format_func=lambda mid:available[mid].method_human,key=key)
    result = available[method]
    now = datetime.now(timezone.utc)
    current = result.ref_sell_ad.price
    hours = st.selectbox('Historial a revisar (horas)',[24,48,72],key='patient_window')
    points = history_window(history,method,exchange,asset,now,hours)
    c1,c2 = st.columns(2)
    discount = c1.number_input('Descuento base sobre la referencia (%)',min_value=0.01,max_value=10.0,value=0.35,step=0.05,key='patient_discount')
    published = c2.number_input('Mi precio publicado (COP por USDT, opcional)',min_value=0.0,value=0.0,step=0.1,format='%.2f',key='patient_published_'+exchange+'_'+method)
    levels, usable = plan_levels(current,discount,points,now)
    st.caption('El precio fijo se calcula desde Compradores ahora: descuento base × 0,5 para Cerca, × 1 para Intermedia y × 1,75 para Más baja. Cambiar el descuento recalcula los tres niveles.')
    cols = st.columns(3)
    cols[0].metric('Compradores ahora',f'{current:,.2f} COP')
    cols[1].metric('Capital del radar (COP)',f'{capital:,.0f}')
    cols[2].metric('Registros recientes',len(points))
    if usable:
        latest = points[-1]['time'].astimezone(ZoneInfo('America/Bogota')).strftime('%d/%m %H:%M')
        st.caption(f'Historial del mismo método: Binance USDT/COP · último registro {latest}, hora de Colombia. Las zonas históricas se muestran aparte como referencia para revisar tu precio.')
    else:
        st.info('Sin historial reciente suficiente para este exchange y método. Los niveles usan únicamente el descuento sobre la cotización actual; no se toma prestado el historial de otro exchange.')
    table = [{'Nivel':p['name'],'Precio fijo (COP/USDT)':p['price'],'Debajo de compradores (%)':round(p['discount'],3),
              'Zona histórica (COP/USDT)':p['historical_reference'],
              'Registros con referencia igual o menor (%)':round(p['observed_pct'],1) if p['observed_pct'] is not None else None} for p in levels]
    st.dataframe(pd.DataFrame(table),hide_index=True,width='stretch',column_config={
        'Precio fijo (COP/USDT)':st.column_config.NumberColumn(format='%.2f'),
        'Zona histórica (COP/USDT)':st.column_config.NumberColumn(format='%.2f')})
    st.caption('Ese porcentaje describe cotizaciones pasadas; no mide órdenes ejecutadas ni la probabilidad de que te compren. Un precio más bajo puede quedar sin recibir operaciones.')
    profile = st.radio('Nivel de espera',[p['name'] for p in levels],index=1,horizontal=True,key='patient_profile')
    target = next(p['price'] for p in levels if p['name']==profile)
    action,_ = review(published,target)
    st.success(f'{action}. Objetivo del nivel: {target:,.2f} COP por USDT.')
    if published:
        st.caption(f'Tu anuncio: {published:,.2f} COP · ajuste al objetivo: {target-published:+,.2f} COP por USDT. La app no cambia el anuncio.')
    st.markdown('**Si compras a ese precio, ¿a cuánto necesitas vender después?**')
    st.caption(f'Los cálculos siguientes usan el precio objetivo del nivel: {target:,.2f} COP por USDT.')
    with st.expander('Comisiones y costos de este plan',expanded=False):
        f1,f2,f3 = st.columns(3)
        buy_fee = f1.number_input('Comisión de compra (%)',min_value=0.0,max_value=10.0,value=0.25,step=0.01,key='patient_buy_fee')
        sell_fee = f2.number_input('Comisión de venta (%)',min_value=0.0,max_value=10.0,value=0.25,step=0.01,key='patient_sell_fee')
        extra = f3.number_input('Otros costos (COP)',min_value=0.0,value=0.0,step=100.0,key='patient_extra')
        st.caption('Supuesto inicial: 0,25% al comprar y 0,25% al vender. Ajusta estos costos si tu operación cobra algo diferente.')
    if capital <= 0:
        st.info('Define un capital mayor a cero en la barra lateral para calcular cantidades y costos.')
        return
    reference_sale = result.ref_buy_ad.price if result.ref_buy_ad else current
    simulation = scenario(capital,target,reference_sale,buy_fee,sell_fee,extra)
    a,b = st.columns(2)
    a.metric('USDT si se completa todo el capital',f"{simulation['quantity']:,.2f}")
    b.metric('Venta mínima para cubrir costos',f"{simulation['breakeven']:,.2f} COP")
    sale = st.number_input('Precio de venta para simular a las 17:00 (COP/USDT)',min_value=0.01,value=float(reference_sale),step=0.1,key='patient_sale_'+exchange+'_'+method)
    outcomes=[]
    for label,price in [('Venta 0,5% más baja',sale*0.995),('Precio de venta elegido',sale),('Venta 0,5% más alta',sale*1.005)]:
        outcome=scenario(capital,target,price,buy_fee,sell_fee,extra)
        outcomes.append({'Escenario':label,'Venta (COP/USDT)':round(price,2),'Resultado neto (COP)':round(outcome['profit'],2),'Neto (%)':round(outcome['net_pct'],3)})
    st.dataframe(pd.DataFrame(outcomes),hide_index=True,width='stretch')
    st.caption('Son escenarios con todo el capital comprado y vendido, no pronósticos para las 17:00. Si no recibes compras, no se realiza ese resultado; si recibes solo una parte, el resultado cambia.')
    if usable:
        chart=pd.DataFrame({'Hora':[p['time'].astimezone(ZoneInfo('America/Bogota')) for p in points],
                            'Compradores del método':[p['buy'] for p in points],'Objetivo actual':[target]*len(points)}).set_index('Hora')
        if published:chart['Mi anuncio']=[published]*len(points)
        st.line_chart(chart,height=230)
    st.markdown('**Revisiones: 06:00 · 11:00 · 15:00 · operar desde 17:00 (Colombia).**')
    st.caption('En cada revisión actualiza el mercado, compara tu anuncio con el objetivo y revisa cuánto capital ya compraste. Un anuncio de precio fijo no sube automáticamente cuando sube el mercado; todavía requiere atender y pagar sus órdenes dentro del plazo del exchange.')
    st.markdown('[Cómo funcionan los anuncios de precio fijo en Binance](https://www.binance.com/en-IN/support/faq/detail/360042084072)')
