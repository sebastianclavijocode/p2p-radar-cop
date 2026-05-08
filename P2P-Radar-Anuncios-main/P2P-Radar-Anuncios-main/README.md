# 📡 P2P Spread Radar

Radar de spreads en mercados P2P de exchanges cripto.
Consulta anuncios BUY/SELL y calcula spreads netos por método de pago + moneda fiat.

## Exchanges soportados

| Exchange | Estado P2P | Notas |
|----------|-----------|-------|
| Binance  | ✅ Soportado | API pública sin key |
| Bybit    | ✅ Soportado | API pública sin key. Solo Mercado Pago confirmado. |
| BingX    | ❌ No soportado | Sin API P2P pública documentada |

## Métodos de pago configurados

| Método           | Fiat | Binance | Bybit |
|-----------------|------|---------|-------|
| Mercado Pago    | ARS  | ✅      | ✅ (ID 8) |
| Facebank        | USD  | ✅ *    | ❌ sin confirmar |
| Dukascopy       | EUR  | ✅ *    | ❌ sin confirmar |
| Zinli           | USD  | ✅ *    | ❌ sin confirmar |
| Prex Uruguay    | UYU  | ✅ *    | ❌ sin confirmar |
| Prex Uruguay    | USD  | ✅ *    | ❌ sin confirmar |

\* Los identificadores exactos pueden variar. Editarlos en el panel **Mapeo de Métodos** si no hay resultados.

## Requisitos

- Python 3.10+
- Windows 10/11 (o Linux/macOS)
- Conexión a internet

## Instalación (Windows)

```bash
# 1. Clonar / descargar el proyecto
cd p2p-radar

# 2. Crear entorno virtual
python -m venv .venv

# 3. Activar entorno virtual
.venv\Scripts\activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Ejecutar la aplicación
streamlit run app.py
```

La app abrirá en el navegador en `http://localhost:8501`.

## Instalación (Linux / macOS)

```bash
cd p2p-radar
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Estructura del proyecto

```
p2p-radar/
├── app.py                  # UI principal (Streamlit)
├── requirements.txt
├── README.md
├── mapping_config.json     # Generado automáticamente al guardar mapeos
├── core/
│   ├── models.py           # Dataclasses: P2PAd, SpreadResult, METHODS_CATALOG
│   ├── cache.py            # Cache TTL en memoria (thread-safe)
│   ├── mapping.py          # Mapeo de métodos humanos → IDs de exchange
│   └── spread.py           # Cálculo de spreads bruto y neto
└── exchanges/
    ├── binance.py          # Binance P2P (POST /bapi/c2c/v2/friendly/c2c/adv/search)
    ├── bybit.py            # Bybit P2P  (POST /fiat/otc/item/online)
    └── bingx.py            # BingX P2P  (no soportado — sin API pública)
```

## Uso

1. **Seleccionar exchange** en el sidebar (Binance recomendado para empezar).
2. **Hacer clic en "Actualizar datos"**.
3. Ver la tabla ordenada por **Spread neto descendente**.
4. Ajustar fees / slippage en el sidebar según corresponda.
5. Editar el **Mapeo de Métodos** en el sidebar si algún método no arroja resultados.

## Panel de Mapeo de Métodos

Cada exchange tiene un bloque JSON editable en el sidebar:

```json
{
  "mercado_pago_ars": {
    "payment_ids": ["Mercado Pago"],
    "available": true,
    "note": ""
  }
}
```

- `payment_ids`: lista de identificadores enviados al API del exchange.
  Para Binance: strings (e.g. `"Mercado Pago"`).
  Para Bybit: strings numéricas (e.g. `"8"`).
- `available`: `true` para habilitarlo, `false` para deshabilitarlo.
- `note`: nota descriptiva visible en la UI.

El mapeo se persiste en `mapping_config.json` al hacer clic en **Guardar**.

## Fees y spread neto

```
spread_bruto = (precio_venta - precio_compra) / precio_compra
spread_neto  = spread_bruto - fee_exchange_pct - fee_extra_pct - slippage_pct
```

Defaults: `fee_exchange=0.10%`, `fee_extra=0.00%`, `slippage=0.00%`.

## Cache

Las respuestas se cachean 45 segundos en memoria para no saturar los endpoints.
El caché se limpia automáticamente con cada nueva consulta fuera del TTL.

## Notas sobre los endpoints

### Binance
- Endpoint: `POST https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search`
- No requiere API key.
- `payTypes` acepta strings como `"Mercado Pago"`, `"Zinli"`, etc.

### Bybit
- Endpoint: `POST https://api2.bybit.com/fiat/otc/item/online`
- No requiere API key.
- `payment` acepta una lista de IDs numéricos como strings: `["8"]`.

### BingX
- No tiene API P2P pública documentada.
- Marcado como no soportado hasta que Bybit publique documentación oficial.

## Troubleshooting

| Problema | Solución |
|---------|---------|
| Sin resultados para un método | Editar el `payment_ids` en el panel Mapeo |
| Error de conexión | Verificar conectividad; los endpoints son públicos sin VPN |
| `ModuleNotFoundError` | Asegurarse de correr `streamlit run app.py` desde el directorio `p2p-radar/` con el venv activado |
