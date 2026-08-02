"""Pruebas unitarias para SelectDocumentsUseCase (REQ-1: Selección de comprobantes)."""

from dataclasses import dataclass
from pathlib import Path

from domain.enums.document_status import DocumentStatus
from domain.enums.file_type import FileType
from use_cases.select_documents import SelectDocumentsResult, SelectDocumentsUseCase


@dataclass
class MockUploadedFile:
    name: str
    size: int


def test_req1_r1_select_valid_documents():
    """R1: WHEN el contador selecciona uno o varios archivos compatibles THEN SYSTEM SHALL mostrar la lista de archivos listos."""
    use_case = SelectDocumentsUseCase()
    files = [
        MockUploadedFile(name="factura_1.pdf", size=5000),
        MockUploadedFile(name="boleta_2.png", size=12000),
        MockUploadedFile(name="ticket_3.jpg", size=8000),
    ]

    result: SelectDocumentsResult = use_case.execute_from_uploaded_files(files)

    assert len(result.valid_documents) == 3
    assert len(result.invalid_files) == 0
    assert result.can_start_processing is True

    doc1 = result.valid_documents[0]
    assert doc1.name == "factura_1.pdf"
    assert doc1.file_type == FileType.PDF
    assert doc1.status == DocumentStatus.READY

    doc2 = result.valid_documents[1]
    assert doc2.name == "boleta_2.png"
    assert doc2.file_type == FileType.PNG
    assert doc2.status == DocumentStatus.READY


def test_req1_r2_select_unsupported_document():
    """R2: WHEN el contador selecciona un archivo con formato no soportado THEN SYSTEM SHALL mostrar un mensaje indicando que no puede procesarse."""
    use_case = SelectDocumentsUseCase()
    files = [
        MockUploadedFile(name="factura.pdf", size=5000),
        MockUploadedFile(name="resumen.xlsx", size=15000),
        MockUploadedFile(name="nota.txt", size=200),
    ]

    result: SelectDocumentsResult = use_case.execute_from_uploaded_files(files)

    assert len(result.valid_documents) == 1
    assert len(result.invalid_files) == 2

    invalid_names = [item[0] for item in result.invalid_files]
    assert "resumen.xlsx" in invalid_names
    assert "nota.txt" in invalid_names

    for _, err in result.invalid_files:
        assert "no soportado" in err


def test_req1_r3_prevent_processing_when_no_files_selected():
    """R3: WHEN el contador no selecciona ningún archivo THEN SYSTEM SHALL impedir iniciar el procesamiento."""
    use_case = SelectDocumentsUseCase()

    # Caso 1: Lista vacía
    result_empty = use_case.execute_from_uploaded_files([])
    assert len(result_empty.valid_documents) == 0
    assert result_empty.can_start_processing is False

    # Caso 2: Solo archivos no soportados
    files_unsupported = [MockUploadedFile(name="documento.doc", size=100)]
    result_unsupported = use_case.execute_from_uploaded_files(files_unsupported)
    assert len(result_unsupported.valid_documents) == 0
    assert result_unsupported.can_start_processing is False


def test_select_documents_from_directory(tmp_path: Path):
    # Crear archivos temporales válidos e inválidos
    valid_pdf = tmp_path / "comprobante1.pdf"
    valid_pdf.write_bytes(b"PDF content")

    valid_jpg = tmp_path / "comprobante2.jpg"
    valid_jpg.write_bytes(b"JPG content")

    invalid_txt = tmp_path / "readme.txt"
    invalid_txt.write_bytes(b"Text content")

    use_case = SelectDocumentsUseCase()
    result = use_case.execute_from_directory(tmp_path)

    assert len(result.valid_documents) == 2
    assert len(result.invalid_files) == 1
    assert result.can_start_processing is True
