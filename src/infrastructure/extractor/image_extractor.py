"""Extractor de texto desde imágenes y PDFs escaneados usando RapidOCR (REQ-3 R2/R3).

Flujo:
  Imagen (PNG/JPG/JPEG) o PDF escaneado (como imagen)
    → RapidOCR ONNX Runtime
    → texto plano

RapidOCR se inicializa una sola vez (singleton) para evitar recargar modelos ONNX.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Singleton del motor OCR — se carga solo cuando se necesita por primera vez
_ocr_engine: Any | None = None


def _get_ocr_engine() -> Any:
    """Carga RapidOCR una única vez y lo reutiliza en todas las llamadas."""
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    return _ocr_engine


def extract_image_text(path: Path) -> str:
    """
    Aplica OCR a una imagen y retorna el texto extraído como string plano.

    Args:
        path: Ruta a la imagen (PNG, JPG, JPEG).

    Returns:
        Texto plano con el contenido reconocido.

    Raises:
        ValueError: Si RapidOCR no puede extraer texto (REQ-3 R3).
        Exception: Errores de lectura del archivo (propagados al llamador).
    """
    ocr = _get_ocr_engine()

    result, _ = ocr(str(path))

    if not result:
        raise ValueError(
            f"RapidOCR no pudo extraer texto de '{path.name}'. "
            "Verifica que la imagen tenga buena resolución y contraste."
        )

    # result es una lista de [bbox, text, confidence]
    lines = [item[1] for item in result if item[1] and item[1].strip()]

    if not lines:
        raise ValueError(
            f"RapidOCR procesó '{path.name}' pero no encontró texto legible."
        )

    return "\n".join(lines)


def extract_pdf_as_image_text(path: Path) -> str:
    """
    Convierte un PDF escaneado a imágenes y aplica OCR página por página.

    Requiere: pdf2image + poppler instalado en el sistema.

    Args:
        path: Ruta al PDF escaneado.

    Returns:
        Texto OCR de todas las páginas concatenado.

    Raises:
        ValueError: Si no se extrae texto de ninguna página.
        ImportError: Si pdf2image no está instalado.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError as e:
        raise ImportError(
            "pdf2image es requerido para procesar PDFs escaneados. "
            "Instálalo con: uv add pdf2image"
        ) from e

    import tempfile

    pages = convert_from_path(str(path), dpi=200)
    all_text: list[str] = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for i, page_img in enumerate(pages):
            tmp_path = Path(tmp_dir) / f"page_{i}.png"
            page_img.save(str(tmp_path), "PNG")
            try:
                page_text = extract_image_text(tmp_path)
                all_text.append(page_text)
            except ValueError:
                # Página sin texto — continuar con las demás
                continue

    if not all_text:
        raise ValueError(
            f"RapidOCR no pudo extraer texto del PDF escaneado '{path.name}'."
        )

    return "\n".join(all_text)
