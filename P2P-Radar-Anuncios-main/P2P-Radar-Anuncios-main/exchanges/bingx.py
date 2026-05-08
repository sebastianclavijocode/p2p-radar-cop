"""
BingX P2P exchange module.

STATUS: NO SOPORTADO
────────────────────
BingX tiene una sección P2P en su plataforma web, pero NO expone una API
REST pública documentada para consultar anuncios P2P (al contrario de
Binance y Bybit, que tienen endpoints HTTP accesibles sin autenticación).

Los endpoints observados en el sitio web de BingX requieren tokens de
sesión / cookies de autenticación y no están documentados públicamente.
No se usa Selenium ni scraping de navegador por restricciones del proyecto.

Si en el futuro BingX documenta una API P2P pública, este módulo puede
ser extendido. Por ahora, todas las llamadas retornan listas vacías y el
exchange se muestra como "No soportado" en la UI.
"""

import logging
from typing import List, Optional

from core.models import P2PAd

logger = logging.getLogger(__name__)


def fetch_ads(
    asset: str,
    fiat: str,
    trade_type: str,
    pay_types: Optional[List[str]] = None,
    rows: int = 10,
    max_retries: int = 3,
    merchant_check: bool = True,  # ignorado, solo para compatibilidad de firma
) -> List[P2PAd]:
    """
    BingX P2P no está soportado. Retorna lista vacía siempre.
    """
    logger.warning(
        "BingX P2P no está soportado: no existe API pública documentada."
    )
    return []


def is_supported() -> bool:
    return False


EXCHANGE_NOTE = (
    "BingX NO está soportado en este radar.\n\n"
    "Razón: BingX P2P no expone una API REST pública documentada para "
    "consultar anuncios sin autenticación de sesión. Los endpoints internos "
    "que usa su sitio web requieren cookies/tokens de login y no son "
    "accesibles de forma pública (y el proyecto prohíbe usar Selenium).\n\n"
    "Alternativa: si BingX publica una API P2P oficial en el futuro, "
    "se puede implementar en exchanges/bingx.py."
)
