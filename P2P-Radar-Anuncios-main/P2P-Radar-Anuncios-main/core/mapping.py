"""
Method mapping layer — maps human method IDs to exchange-specific payment identifiers.
Persisted in data/method_mapping.json.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
MAPPING_FILE = DATA_DIR / "method_mapping.json"

# Legacy path fallback (previous version stored here)
_LEGACY_MAPPING = Path(__file__).parent.parent / "mapping_config.json"

DEFAULT_MAPPINGS: Dict[str, Any] = {
    "binance": {
        "mercado_pago_ars": {"payment_ids": ["Mercadopago"], "available": True, "note": ""},
        "facebank_usd":     {"payment_ids": ["Facebank International"], "available": False, "note": "Reemplazado por método manual con ID correcto"},
        "dukascopy_eur":    {"payment_ids": ["Dukascopy Bank"], "available": True, "note": ""},
        "zinli_usd":        {"payment_ids": ["Zinli"],        "available": True,  "note": ""},
        "prex_uy_uyu":      {"payment_ids": ["Prex", "PREX"], "available": True,  "note": "Puede variar; editar si no hay resultados"},
        "prex_uy_usd":      {"payment_ids": ["Prex", "PREX"], "available": True,  "note": "Puede variar; editar si no hay resultados"},
    },
    "bybit": {
        "mercado_pago_ars": {"payment_ids": ["8"],  "available": True,  "note": "ID 8 = Mercado Pago"},
        "facebank_usd":     {"payment_ids": [],     "available": False, "note": "No confirmado en Bybit P2P"},
        "dukascopy_eur":    {"payment_ids": [],     "available": False, "note": "No confirmado en Bybit P2P"},
        "zinli_usd":        {"payment_ids": [],     "available": False, "note": "No confirmado en Bybit P2P"},
        "prex_uy_uyu":      {"payment_ids": [],     "available": False, "note": "No confirmado en Bybit P2P"},
        "prex_uy_usd":      {"payment_ids": [],     "available": False, "note": "No confirmado en Bybit P2P"},
    },
    "bingx": {
        "mercado_pago_ars": {"payment_ids": [], "available": False, "note": "BingX: sin API P2P pública"},
        "facebank_usd":     {"payment_ids": [], "available": False, "note": "BingX: sin API P2P pública"},
        "dukascopy_eur":    {"payment_ids": [], "available": False, "note": "BingX: sin API P2P pública"},
        "zinli_usd":        {"payment_ids": [], "available": False, "note": "BingX: sin API P2P pública"},
        "prex_uy_uyu":      {"payment_ids": [], "available": False, "note": "BingX: sin API P2P pública"},
        "prex_uy_usd":      {"payment_ids": [], "available": False, "note": "BingX: sin API P2P pública"},
    },
}


def _merge_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    for exchange, methods in DEFAULT_MAPPINGS.items():
        if exchange not in data:
            data[exchange] = methods
        else:
            for method_id, cfg in methods.items():
                if method_id not in data[exchange]:
                    data[exchange][method_id] = cfg
    return data


def load_mappings() -> Dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Try new path, then legacy
    for path in [MAPPING_FILE, _LEGACY_MAPPING]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return _merge_defaults(data)
            except Exception as exc:
                logger.warning(f"Failed to load {path}: {exc}")

    return json.loads(json.dumps(DEFAULT_MAPPINGS))


def save_mappings(mappings: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.error(f"Failed to save mappings: {exc}")


def get_method_config(
    exchange: str, method_id: str, mappings: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    return mappings.get(exchange, {}).get(method_id)


def get_payment_ids(
    exchange: str, method_id: str, mappings: Dict[str, Any]
) -> List[str]:
    cfg = get_method_config(exchange, method_id, mappings)
    if cfg and cfg.get("available", False):
        return cfg.get("payment_ids", [])
    return []
