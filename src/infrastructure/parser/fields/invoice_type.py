"""Extractor del tipo de comprobante (FACTURA ELECTRONICA, BOLETA DE VENTA, etc.)."""

from __future__ import annotations

# Mapeo ordenado de más específico a más general
_TYPES: dict[str, str] = {
    "FACTURA ELECTRONICA": "FACTURA ELECTRONICA",
    "FACTURA ELECTRÓNICA": "FACTURA ELECTRONICA",
    "BOLETA DE VENTA ELECTRONICA": "BOLETA DE VENTA ELECTRONICA",
    "BOLETA DE VENTA ELECTRÓNICA": "BOLETA DE VENTA ELECTRONICA",
    "BOLETA DE VENTA": "BOLETA DE VENTA",
    "NOTA DE CREDITO": "NOTA DE CREDITO",
    "NOTA DE DÉBITO": "NOTA DE DEBITO",
    "NOTA DE DEBITO": "NOTA DE DEBITO",
    "FACTURA": "FACTURA",
    "BOLETA": "BOLETA",
}


def extract_invoice_type(text: str) -> str | None:
    """
    Identifica el tipo de comprobante buscando las frases más específicas primero.
    """
    text_upper = text.upper()
    for key, value in _TYPES.items():
        if key in text_upper:
            return value
    return None
