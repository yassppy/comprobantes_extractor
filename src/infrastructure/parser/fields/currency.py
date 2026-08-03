"""Extractor de moneda del comprobante."""

from __future__ import annotations


def extract_currency(text: str) -> str | None:
    """
    Detecta la moneda del comprobante.

    Returns:
        "SOLES"           → para PEN
        "DOLAR AMERICANO" → para USD
        None              → si no se identifica
    """
    text_upper = text.upper()

    if "SOLES" in text_upper:
        return "SOLES"

    if "DOLAR" in text_upper or "DOLLAR" in text_upper or "USD" in text_upper:
        return "DOLAR AMERICANO"

    return None
