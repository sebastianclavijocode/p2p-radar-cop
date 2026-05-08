"""Custom methods — métodos de pago agregados por el usuario, persistidos en data/custom_methods.json."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CUSTOM_METHODS_FILE = DATA_DIR / "custom_methods.json"


def load_custom_methods() -> List[Dict[str, Any]]:
    """Retorna lista de métodos custom en el mismo formato que METHODS_CATALOG."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CUSTOM_METHODS_FILE.exists():
        try:
            with open(CUSTOM_METHODS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.warning(f"Failed to load custom_methods.json: {exc}")
    return []


def save_custom_methods(methods: List[Dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(CUSTOM_METHODS_FILE, "w", encoding="utf-8") as f:
            json.dump(methods, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.error(f"Failed to save custom_methods.json: {exc}")


def add_custom_method(
    methods: List[Dict[str, Any]],
    method_id: str,
    human_name: str,
    fiat: str,
    payment_id: str,
    exchange: str = "Binance",
) -> List[Dict[str, Any]]:
    """Agrega un método si no existe ya. Retorna la lista actualizada."""
    if any(m["id"] == method_id for m in methods):
        return methods
    methods.append({
        "id": method_id,
        "human_name": human_name,
        "fiat": fiat,
        "_payment_id": payment_id,
        "_exchange": exchange,
    })
    return methods
