"""Extractor de serie y número correlativo del comprobante."""

from __future__ import annotations

import re

# Patrón principal: SERIE-NÚMERO (ej: F001-123456, B459-103578, E001-5704)
_PATRON_SERIE_NUMERO = re.compile(
    r"\b([A-Z]{1,4}\d{1,4})-(\d{3,12})\b",
    re.IGNORECASE,
)

# Patrón alternativo más permisivo
_PATRON_ALTERNATIVO = re.compile(
    r"\b([FEB][A-Z0-9]{2,4})-(\d{3,12})\b",
    re.IGNORECASE,
)


def extraer_serie_numero(texto: str) -> tuple[str | None, str | None]:
    """
    Extrae la serie y el número correlativo del comprobante.

    Retorna (serie, numero) o (None, None) si no se encuentra.

    Ejemplos reconocidos:
      - F001-123456  → ("F001", "123456")
      - B459-103578  → ("B459", "103578")
      - E001-5704    → ("E001", "5704")
    """
    for patron in (_PATRON_SERIE_NUMERO, _PATRON_ALTERNATIVO):
        m = patron.search(texto)
        if m:
            return (m.group(1).upper(), m.group(2))

    return (None, None)
