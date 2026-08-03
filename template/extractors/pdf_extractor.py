"""
Extractor de texto desde archivos PDF.

Usa pdfplumber para extraer texto plano de cada página del PDF.
El texto resultante se pasa luego al markdown_parser.

No usa IA — extracción puramente basada en estructura del PDF.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber


def extraer_texto_pdf(ruta: Path) -> str:
    """
    Extrae todo el texto de un PDF página por página.

    Args:
        ruta: Path al archivo PDF.

    Returns:
        Texto concatenado de todas las páginas.

    Raises:
        ValueError: Si el PDF no contiene texto extraíble.
        Exception: Errores de lectura del archivo (propagados al service).
    """
    texto_total: list[str] = []

    with pdfplumber.open(ruta) as pdf:
        for num_pagina, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text()
            if texto:
                texto_total.append(texto)

    if not texto_total:
        raise ValueError(
            f"El PDF '{ruta.name}' no contiene texto extraíble. "
            "Puede ser un PDF escaneado — usa el extractor de imágenes."
        )

    return "\n".join(texto_total)
