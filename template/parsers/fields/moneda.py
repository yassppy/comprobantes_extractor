"""Extractor de moneda del comprobante."""

from __future__ import annotations


def extraer_moneda(texto: str) -> str | None:
    """
    Detecta la moneda del comprobante.

    Retorna:
    - "SOLES"           → para PEN
    - "DOLAR AMERICANO" → para USD
    - None              → si no se identifica
    """
    texto_upper = texto.upper()

    if "SOLES" in texto_upper:
        return "SOLES"

    if "DOLAR" in texto_upper or "DOLLAR" in texto_upper or "USD" in texto_upper:
        return "DOLAR AMERICANO"

    return None
