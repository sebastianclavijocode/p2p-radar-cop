"""Custom methods — métodos de pago agregados por el usuario, persistidos en data/custom_methods.json."""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
CUSTOM_METHODS_FILE = DATA_DIR / "custom_methods.json"


def primary_catalog(exchange='Binance'):
    """User's selected methods; IDs are specific to each exchange and fiat."""
    if exchange == 'Binance':
        entries = [('bancolombia_cop_custom','Bancolombia','COP','BancolombiaSA'),
                   ('nequi_cop_custom','Nequi','COP','Nequi'),
                   ('daviplata_cop_custom','Daviplata','COP','Daviplata'),
                   ('breb_cop_custom','Llaves Bre-B','COP','BreBKeys'),
                   ('facebank','Facebank','USD','Facebank'),
                   ('zinli_usd','Zinli','USD','Zinli')]
    elif exchange == 'Bybit':
        entries = [('bybit_cop_126','Bancolombia','COP','126'),
                   ('bybit_cop_209','Nequi','COP','209'),
                   ('bybit_cop_236','Daviplata','COP','236'),
                   ('bybit_cop_703','Llaves Bre-B','COP','703'),
                   ('bybit_usd_189','Zinli','USD','189')]
    else:
        entries = []
    return [{'id':mid,'human_name':name,'fiat':fiat,'_payment_id':pid,'_exchange':exchange}
            for mid,name,fiat,pid in entries]


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
