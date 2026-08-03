"""Pruebas unitarias para ProcessBatchUseCase (REQ-2: Procesamiento por lote)."""

from pathlib import Path

from domain.entities.document import Document
from domain.enums.document_status import DocumentStatus
from domain.enums.file_type import FileType
from use_cases.process_batch import ProcessBatchUseCase


# ─── Procesadores stub para tests ──────────────────────────────────────────────

def _ok_processor(doc: Document) -> None:
    """Simula procesamiento exitoso sin tocar el disco."""
    pass


def _error_processor(doc: Document) -> None:
    """Simula fallo en archivos cuyo nombre contiene 'error' o 'corrupto'."""
    if "error" in doc.name.lower() or "corrupto" in doc.name.lower():
        raise ValueError(f"Falla al procesar el contenido de '{doc.name}' (documento ilegible o corrupto).")


# ─── Tests ─────────────────────────────────────────────────────────────────────

def test_req2_r1_process_all_selected_documents():
    """R1: WHEN el contador inicia el procesamiento THEN SYSTEM SHALL procesar todos los archivos seleccionados."""
    docs = [
        Document(name="doc1.pdf", path=Path("doc1.pdf"), file_type=FileType.PDF, size=100),
        Document(name="doc2.png", path=Path("doc2.png"), file_type=FileType.PNG, size=200),
        Document(name="doc3.jpg", path=Path("doc3.jpg"), file_type=FileType.JPG, size=300),
    ]

    use_case = ProcessBatchUseCase(single_processor=_ok_processor)
    summary = use_case.execute(docs)

    assert summary.total_count == 3
    assert summary.processed_count == 3
    assert summary.error_count == 0
    assert summary.has_errors is False
    assert len(summary.results) == 3

    for res in summary.results:
        assert res.success is True
        assert res.document.status == DocumentStatus.PROCESSED


def test_req2_r2_continue_processing_on_error():
    """R2: WHEN ocurre un error durante el procesamiento THEN SYSTEM SHALL registrar el error y continuar procesando los demás."""
    docs = [
        Document(name="factura_valida_1.pdf", path=Path("factura_valida_1.pdf"), file_type=FileType.PDF, size=100),
        Document(name="documento_error.pdf", path=Path("documento_error.pdf"), file_type=FileType.PDF, size=100),
        Document(name="factura_valida_2.png", path=Path("factura_valida_2.png"), file_type=FileType.PNG, size=200),
    ]

    use_case = ProcessBatchUseCase(single_processor=_error_processor)
    summary = use_case.execute(docs)

    assert summary.total_count == 3
    assert summary.processed_count == 2
    assert summary.error_count == 1
    assert summary.has_errors is True

    # El archivo con error debe marcarse como FAILED
    doc_err = docs[1]
    assert doc_err.status == DocumentStatus.FAILED
    assert doc_err.error_message is not None
    assert "Falla al procesar" in doc_err.error_message

    # El tercer archivo debe haberse procesado exitosamente
    doc_last = docs[2]
    assert doc_last.status == DocumentStatus.PROCESSED


def test_req2_r3_summary_statistics():
    """R3: WHEN finaliza el procesamiento THEN SYSTEM SHALL mostrar un resumen con procesados, errores y tiempo total."""
    docs = [
        Document(name="a.pdf", path=Path("a.pdf"), file_type=FileType.PDF, size=100),
        Document(name="b_corrupto.pdf", path=Path("b_corrupto.pdf"), file_type=FileType.PDF, size=100),
    ]

    use_case = ProcessBatchUseCase(single_processor=_error_processor)
    summary = use_case.execute(docs)

    assert summary.total_count == 2
    assert summary.processed_count == 1
    assert summary.error_count == 1
    assert summary.total_time_seconds > 0.0
