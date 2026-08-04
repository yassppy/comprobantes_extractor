"""
Tests de integración para el flujo de extracción desde imágenes usando RapidOCR ONNX Runtime.
Procesa las imágenes de la carpeta comprobantes/test_imagenes/ y guarda los reportes MD y JSON en output_tests/.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from domain.enums.document_type import DocumentType
from infrastructure.extractor.image_extractor import extract_image_text
from infrastructure.parser.document_parser import parse_document
from utils.report_exporter import save_test_reports

# ── Rutas de prueba ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CARPETA_IMAGENES = BASE_DIR / "comprobantes" / "test_imagenes"

ARCHIVOS_IMAGEN = (
    list(CARPETA_IMAGENES.glob("*.png"))
    + list(CARPETA_IMAGENES.glob("*.jpg"))
    + list(CARPETA_IMAGENES.glob("*.jpeg"))
)


class TestExtractorImagenes:
    """Valida la lectura OCR de comprobantes en formato de imagen con RapidOCR."""

    @pytest.mark.parametrize(
        "imagen_path",
        ARCHIVOS_IMAGEN,
        ids=[img.name for img in ARCHIVOS_IMAGEN],
    )
    def test_flujo_completo_imagen_a_extracted_data(self, imagen_path: Path):
        if not imagen_path.exists():
            pytest.skip(f"No existe la imagen de prueba en {imagen_path}")

        # 1. Extraer texto plano con RapidOCR ONNX Runtime
        texto_extraido = extract_image_text(imagen_path)
        assert isinstance(texto_extraido, str)
        assert len(texto_extraido) > 0

        # 2. Parsear el texto extraído
        resultado = parse_document(
            text=texto_extraido,
            document_type=DocumentType.PURCHASE,
            ocr_engine="rapidocr",
            source_type="IMAGE",
        )
        assert resultado is not None

        # 3. Guardar reportes Markdown y JSON en output_tests/
        md_path, json_path = save_test_reports(
            filename=imagen_path.name,
            raw_text=texto_extraido,
            extracted_data=resultado,
        )

        assert md_path.exists()
        assert json_path.exists()
