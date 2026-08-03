"""Extractor del tipo de comprobante (FACTURA, BOLETA, etc.)."""

from __future__ import annotations

# Mapeo de palabras clave → tipo normalizado
_TIPOS = {
    "FACTURA ELECTRONICA": "FACTURA ELECTRONICA",
    "FACTURA ELECTRÓNICA": "FACTURA ELECTRONICA",
    "BOLETA DE VENTA ELECTRONICA": "BOLETA DE VENTA ELECTRONICA",
    "BOLETA DE VENTA ELECTRÓNICA": "BOLETA DE VENTA ELECTRONICA",
    "BOLETA DE VENTA": "BOLETA DE VENTA",
    "FACTURA": "FACTURA",
    "BOLETA": "BOLETA",
}


def extraer_tipo_factura(texto: str) -> str | None:
    """
    Identifica el tipo de comprobante buscando las frases más específicas primero.
    El orden en _TIPOS importa: las más largas se buscan antes.
    """
    texto_upper = texto.upper()
    for clave, valor in _TIPOS.items():
        if clave in texto_upper:
            return valor
    return None
