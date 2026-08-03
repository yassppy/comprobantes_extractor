"""Extractor de texto desde archivos PDF usando pdfplumber (REQ-3 R1).

Estrategia:
  1. Extrae texto digital de cada página con pdfplumber.
  2. Si el PDF no contiene texto (PDF escaneado), retorna None para que el
     llamador decida escalar a OCR.
"""

from __future__ import annotations

from pathlib import Path


def extract_pdf_text(path: Path) -> str | None:
    """
    Extrae texto de un PDF con texto digital.

    Returns:
        Texto concatenado de todas las páginas, o None si el PDF
        no contiene texto extraíble (PDF escaneado).

    Raises:
        Exception: Errores de lectura del archivo (propagados al llamador).
    """
    import pdfplumber

    text_pages: list[str] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                text_pages.append(text)

    if not text_pages:
        # PDF escaneado — sin texto digital extraíble
        return None

    return "\n".join(text_pages)
