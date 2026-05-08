"""Per-method fee configuration (persisted in data/method_fees.json)."""
import json
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
FEES_FILE = DATA_DIR / "method_fees.json"

DEFAULT_FEES: Dict[str, Any] = {
    "mercado_pago_ars": {"fee_method_pct": 0.0, "fee_method_fixed": 0.0},
    "facebank_usd":     {"fee_method_pct": 0.0, "fee_method_fixed": 0.0},
    "dukascopy_eur":    {"fee_method_pct": 0.0, "fee_method_fixed": 0.0},
    "zinli_usd":        {"fee_method_pct": 0.0, "fee_method_fixed": 0.0},
    "prex_uy_uyu":      {"fee_method_pct": 0.0, "fee_method_fixed": 0.0},
    "prex_uy_usd":      {"fee_method_pct": 0.0, "fee_method_fixed": 0.0},
}


def load_fees() -> Dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if FEES_FILE.exists():
        try:
            with open(FEES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for method_id, cfg in DEFAULT_FEES.items():
                if method_id not in data:
                    data[method_id] = cfg
            return data
        except Exception as exc:
            logger.warning(f"Failed to load method_fees.json: {exc}. Using defaults.")
    return json.loads(json.dumps(DEFAULT_FEES))


def save_fees(fees: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(FEES_FILE, "w", encoding="utf-8") as f:
            json.dump(fees, f, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.error(f"Failed to save method_fees.json: {exc}")
