# Rulos COP — actualización sobre tu radar

La misma entrada de Streamlit sigue funcionando:
`P2P-Radar-Anuncios-main/P2P-Radar-Anuncios-main/app.py`.

La barra lateral permite elegir **Rulos COP · datos reales** o el **Radar original · Yo publico**. El módulo nuevo no envía órdenes, transferencias ni mensajes. No necesita claves para estas consultas públicas.

## Datos y recorridos

- Bitso: libros públicos USDT/COP y BTC/USDT.
- Binance: libro spot BTC/USDT; anuncios P2P USDT/COP para comprar y vender desde la perspectiva del usuario.
- Bybit: libro spot BTC/USDT. Su P2P no se utiliza en el módulo nuevo: la API oficial requiere acceso de anunciante. El adaptador heredado permanece en el radar original.
- Binance P2P es un endpoint del sitio web, no una API pública con garantía contractual de estabilidad. Errores HTTP, bloqueos y respuestas inválidas aparecen como **No disponible**. No se evade un bloqueo ni se agregan datos ficticios.
- Cada consulta P2P toma una página de hasta 20 anuncios por lado; no representa todo el mercado.
- La búsqueda recorre hasta 3 exchanges distintos y 7 pasos, termina en COP y evita repetir saldos intermedios o encadenar transferencias sin conversión. Ejemplo estructural: COP en A → USDT en A → USDT en B → BTC en B → BTC en C → USDT en C → USDT en A → COP en A. Esto no afirma que esa ruta sea rentable o esté habilitada.
- Se conserva la identidad de cada exchange y activo. BTC nunca se transfiere como USDT ni se asume paridad USD/USDT.

## Antes de calcular

1. Elige capital, métodos de pago y máximo de exchanges.
2. Sustituye las comisiones orientativas por tus tarifas reales. El porcentaje se cobra sobre el activo recibido en cada conversión.
3. En transferencias, indica la red compatible en ambos extremos, comisión en unidades del activo y mínimo de retiro. Marca Confirmada solo después de verificarlo en tus cuentas. Cada dirección se configura por separado.
4. Confirma costos. Los parámetros son de esta sesión; al reiniciar deberás configurarlos otra vez.
5. Actualiza o activa actualización cada 30 segundos. Datos cacheados por 30 segundos; precios con antigüedad mayor de 90 segundos se excluyen. Binance marca hora de recepción, no hora de creación de la orden.

Las conversiones consumen niveles de profundidad completos para el capital indicado. Los anuncios P2P son alternativas individuales: no se mezcla liquidez de anunciantes para fingir una orden. Los límites de venta se aplican al importe fiat de la venta, no al capital inicial. Se resta el costo de cada transferencia, el margen adicional por conversión y los otros costos COP al cierre.

**Limitaciones:** estimaciones, no rutas validadas para ejecución. No verifica estados de depósitos/retiros por API, precisión y mínimos spot, elegibilidad de tu cuenta ni requisitos particulares de cada anuncio. La confirmación de redes es manual. Los precios pueden cambiar durante las transferencias. La ausencia de una ruta positiva es un resultado válido.

## Instalar y probar

Desde el directorio que contiene `app.py`:

```sh
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Para las pruebas del motor y adaptadores:

```sh
python -m pip install pytest
python -m pytest tests -q
```

En Streamlit Cloud, conserva el repositorio, rama y archivo de entrada existentes. Publica estos cambios en la rama que utiliza tu aplicación; Cloud reconstruirá las dependencias. No se requiere configurar Secrets para el módulo nuevo.

## Referencias

- https://docs.bitso.com/bitso-api/docs/list-order-book
- https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints
- https://bybit-exchange.github.io/docs/v5/market/orderbook
- https://bybit-exchange.github.io/docs/p2p/guide

Se conservan las funciones y atribuciones del proyecto original.
