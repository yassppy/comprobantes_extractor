"""Extractor de montos financieros: subtotal, IGV y total."""

from __future__ import annotations

import re


# ─────────────────────────────────────────────
# Utilidades internas
# ─────────────────────────────────────────────

def _clean_amount(value: str | None) -> float | None:
    """
    Normaliza un string de monto a float.

    Maneja formatos:
    - "1,234.56" → 1234.56  (miles con coma)
    - "1.234,56" → 1234.56  (miles con punto, decimal con coma — europeo)
    - "1234.56"  → 1234.56
    """
    if not value:
        return None

    value = re.sub(r"[^\d.,]", "", value)

    if not value:
        return None

    if "," in value and "." in value:
        value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return None


def _first_match(patterns: list[str], text: str) -> str | None:
    """Aplica una lista de patrones y retorna el primer match."""
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return None


# ─────────────────────────────────────────────
# Extractores públicos
# ─────────────────────────────────────────────

def extract_subtotal(text: str) -> float | None:
    """Extrae el valor de venta / base imponible (sin IGV)."""
    patterns = [
        r"VALOR\s+VENTA\s*:?\s*S[/I]?\s*([\d.,]+)",
        r"SUB\s*TOTAL.*?([\d,]+\.\d{2})",
        r"OP\.?\s*GRAVADA.*?([\d,]+\.\d{2})",
        r"GRAVADA\s*S[/I]?\s*([\d,]+\.\d{2})",
        r"GRAVADA.*?([\d,]+\.\d{2})",
    ]
    return _clean_amount(_first_match(patterns, text))


def extract_igv(text: str) -> float | None:
    """Extrae el monto de IGV."""
    patterns = [
        r"I\.?G\.?V\.?\s*:?\s*S[/I]?\s*([\d,]+\.\d{2})",
        r"I\.?G\.?V\.?\s*:?\s*\$\s*([\d,]+\.\d{2})",
        r"^\s*I\.?G\.?V\.?\s*[:\-]?\s*([\d,]+\.\d{2})\s*$",
        r"I\.?G\.?V\.?[^\d\n]{0,20}([\d,]+\.\d{2})",
        r"([\d,]+\.\d{2})\s*(?:S[/I]?\.?)?\s*I\.?G\.?V\.?",
    ]
    return _clean_amount(_first_match(patterns, text))


def extract_total(text: str) -> float | None:
    """Extrae el importe total del comprobante."""
    patterns = [
        r"IMPORTE\s+TOTAL.*?([\d,]+\.\d{2})",
        r"TOTAL\s+A\s+PAGAR.*?([\d,]+\.\d{2})",
        r"TOTAL\s*S/?\.?\s*([\d,]+\.\d{2})",
    ]
    return _clean_amount(_first_match(patterns, text))
