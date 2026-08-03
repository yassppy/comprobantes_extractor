"""Extractor de serie y número correlativo del comprobante."""

from __future__ import annotations

import re

_PATTERN_MAIN = re.compile(r"\b([A-Z]{1,4}\d{1,4})-(\d{3,12})\b", re.IGNORECASE)
_PATTERN_ALT  = re.compile(r"\b([FEB][A-Z0-9]{2,4})-(\d{3,12})\b", re.IGNORECASE)


def extract_series_number(text: str) -> tuple[str | None, str | None]:
    """
    Extrae la serie y el número correlativo del comprobante.

    Returns:
        (series, number) o (None, None) si no se encuentra.

    Ejemplos reconocidos:
        F001-123456  → ("F001", "123456")
        B459-103578  → ("B459", "103578")
        E001-5704    → ("E001", "5704")
    """
    for pattern in (_PATTERN_MAIN, _PATTERN_ALT):
        m = pattern.search(text)
        if m:
            return (m.group(1).upper(), m.group(2))
    return (None, None)
