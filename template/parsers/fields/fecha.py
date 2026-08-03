"""Extractor de fecha de emisión del comprobante."""

from __future__ import annotations

import re


def extraer_fecha(texto: str) -> str | None:
    """
    Extrae la fecha de emisión del comprobante.

    Formatos soportados:
    - DD/MM/YYYY  → devuelve tal cual  (ej: 17/05/2025)
    - DD.MM.YY    → convierte a DD/MM/20YY (ej: 23.02.26 → 23/02/2026)
    """
    # Formato estándar SUNAT: DD/MM/YYYY
    m = re.search(r"(\d{2}/\d{2}/\d{4})", texto)
    if m:
        return m.group(1)

    # Formato ticket corto: DD.MM.YY
    m = re.search(r"\b(\d{2})\.(\d{2})\.(\d{2})\b", texto)
    if m:
        dia, mes, anio_corto = m.group(1), m.group(2), m.group(3)
        return f"{dia}/{mes}/20{anio_corto}"

    return None
