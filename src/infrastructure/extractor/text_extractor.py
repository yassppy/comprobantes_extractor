"""Orquestador de extracción de texto (REQ-3).

Decide qué extractor usar según el tipo de archivo:
  - PDF con texto digital → pdfplumber         (R1)
  - PDF escaneado         → RapidOCR vía imagen (R2)
  - Imagen (PNG/JPG/JPEG) → RapidOCR           (R2)
  - Si RapidOCR falla     → propaga ValueError  (R3)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from domain.enums.file_type import FileType
from infrastructure.extractor.image_extractor import extract_image_text, extract_pdf_as_image_text
from infrastructure.extractor.pdf_extractor import extract_pdf_text


@dataclass(slots=True)
class ExtractionResult:
    text: str
    ocr_engine: str   # "pdfplumber" | "rapidocr"
    source_type: str  # "PDF" | "IMAGE"


def extract_text(path: Path, file_type: FileType) -> ExtractionResult:
    """
    Extrae el texto de un comprobante eligiendo el motor adecuado.

    Args:
        path:      Ruta al archivo en disco.
        file_type: Tipo de archivo validado.

    Returns:
        ExtractionResult con el texto y metadata del motor usado.

    Raises:
        ValueError: Si el archivo no contiene texto extraíble (REQ-3 R3).
        Exception:  Errores de lectura propagados al llamador (ProcessBatch).
    """
    is_image = file_type in {FileType.PNG, FileType.JPG, FileType.JPEG}

    if is_image:
        # R2: imagen → RapidOCR directamente
        text = extract_image_text(path)
        return ExtractionResult(text=text, ocr_engine="rapidocr", source_type="IMAGE")

    # Es PDF — intentar extracción digital primero
    text = extract_pdf_text(path)

    if text is not None:
        # R1: PDF con texto digital → pdfplumber
        return ExtractionResult(text=text, ocr_engine="pdfplumber", source_type="PDF")

    # PDF escaneado → R2: RapidOCR sobre páginas convertidas a imagen
    text = extract_pdf_as_image_text(path)
    return ExtractionResult(text=text, ocr_engine="rapidocr", source_type="PDF")
