"""
Extractor de texto desde imágenes usando docTR (OCR).

Flujo:
  Imagen (PNG/JPG/JPEG)
    → docTR OCR
    → texto en formato Markdown-like
    → markdown_parser

docTR está configurado para usar CPU por defecto.
Si hay GPU disponible, la detecta automáticamente.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

# Importación lazy: docTR tarda en cargar (carga modelos de IA).
# Se importa solo cuando se necesita por primera vez.
_predictor: Any | None = None


def _get_predictor() -> Any:
    """Carga el predictor de docTR una sola vez (singleton)."""
    global _predictor

    if _predictor is None:
        from doctr.models import ocr_predictor

        _predictor = ocr_predictor(pretrained=True)

    return _predictor


def extraer_texto_imagen(ruta: Path) -> str:
    """
    Aplica OCR a una imagen y retorna el texto extraído como string plano.

    Args:
        ruta: Path a la imagen (PNG, JPG, JPEG, TIFF, BMP).

    Returns:
        Texto plano con el contenido reconocido, una línea por bloque.

    Raises:
        ValueError: Si la imagen no puede leerse o el OCR no extrae texto.
        Exception: Errores de docTR (propagados al service).
    """
    from doctr.io import DocumentFile

    # Cargar imagen
    doc = cast(Any, DocumentFile.from_images([str(ruta)]))

    # Aplicar OCR
    predictor = _get_predictor()
    resultado = cast(Any, predictor(doc))

    # Convertir resultado a texto plano
    lineas: list[str] = []

    for pagina in resultado.pages:
        for bloque in pagina.blocks:
            for linea in bloque.lines:
                palabras = [palabra.value for palabra in linea.words]
                if palabras:
                    lineas.append(" ".join(palabras))

    if not lineas:
        raise ValueError(
            f"No se pudo extraer texto de la imagen '{ruta.name}'. "
            f"Verifica que la imagen tenga buena resolución y contraste."
        )

    return "\n".join(lineas)


# Extensiones de imagen soportadas
EXTENSIONES_IMAGEN = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
    }
)
