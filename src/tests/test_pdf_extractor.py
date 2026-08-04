"""
Tests de integración para el flujo de extracción desde PDFs (pdfplumber / RapidOCR).
Procesa los archivos PDF de la carpeta comprobantes/test_pdfs/ y guarda los reportes MD y JSON en output_tests/.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from domain.enums.document_type import DocumentType
from domain.enums.file_type import FileType
from infrastructure.extractor.text_extractor import extract_text
from infrastructure.parser.document_parser import parse_document
from utils.report_exporter import save_test_reports

# ── Rutas de prueba ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CARPETA_PDFS = BASE_DIR / "comprobantes" / "test_pdfs"

ARCHIVOS_PDF = list(CARPETA_PDFS.glob("*.pdf"))


class TestExtractorPDFs:
    """Valida la lectura y parsing de comprobantes en formato PDF."""

    @pytest.mark.parametrize(
        "pdf_path",
        ARCHIVOS_PDF,
        ids=[pdf.name for pdf in ARCHIVOS_PDF],
    )
    def test_flujo_completo_pdf_a_extracted_data(self, pdf_path: Path):
        if not pdf_path.exists():
            pytest.skip(f"No existe el archivo PDF en {pdf_path}")

        # 1. Extraer texto plano (digital o RapidOCR si es escaneado)
        extraction = extract_text(pdf_path, file_type=FileType.PDF)
        assert isinstance(extraction.text, str)
        assert len(extraction.text) > 0

        # 2. Parsear el texto extraído
        resultado = parse_document(
            text=extraction.text,
            document_type=DocumentType.SALE,
            ocr_engine=extraction.ocr_engine,
            source_type=extraction.source_type,
        )
        assert resultado is not None

        # 3. Guardar reportes Markdown y JSON en output_tests/
        md_path, json_path = save_test_reports(
            filename=pdf_path.name,
            raw_text=extraction.text,
            extracted_data=resultado,
        )

        assert md_path.exists()
        assert json_path.exists()
