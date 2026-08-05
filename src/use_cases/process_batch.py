"""Caso de uso: Procesamiento por lote de comprobantes (REQ-2 / HU02-batch-processing)."""

import time
from collections.abc import Callable

from domain.entities.document import Document
from domain.entities.processing_result import BatchProcessSummary, DocumentProcessResult
from domain.enums.document_status import DocumentStatus


def _extract_and_parse(doc: Document) -> None:
    """
    Procesador real: extrae texto (REQ-3) y parsea campos (REQ-4).
    El documento debe tener una ruta válida en disco (path).
    """
    from infrastructure.extractor.text_extractor import extract_text
    from infrastructure.parser.document_parser import parse_document

    if doc.file_type is None:
        raise ValueError(f"Tipo de archivo no determinado para '{doc.name}'.")

    # REQ-3: extracción de texto según tipo de archivo
    extraction = extract_text(doc.path, doc.file_type)

    # REQ-4: parseo de campos desde el texto extraído
    extracted = parse_document(
        text=extraction.text,
        document_type=doc.document_type,
        ocr_engine=extraction.ocr_engine,
        source_type=extraction.source_type,
    )

    doc.extracted_data = extracted


class ProcessBatchUseCase:
    def __init__(self, single_processor: Callable[[Document], None] | None = None) -> None:
        """
        single_processor: Función o servicio que procesa un comprobante individual.
        Por defecto usa el extractor real (pdfplumber / RapidOCR + parseo de campos).
        """
        self.single_processor = single_processor or _extract_and_parse

    def execute(self, documents: list[Document]) -> BatchProcessSummary:
        """
        Ejecuta el procesamiento por lote sobre todos los comprobantes seleccionados.
        R1: Procesar todos los archivos seleccionados.
        R2: Si ocurre un error en un comprobante, registrar el error y continuar.
        R3: Retornar resumen con procesados, errores y tiempo total.
        """
        start_time = time.perf_counter()
        summary = BatchProcessSummary(total_count=len(documents))

        for doc in documents:
            doc_start = time.perf_counter()
            doc.status = DocumentStatus.PROCESSING

            try:
                self.single_processor(doc)
                doc.status = DocumentStatus.PROCESSED
                doc.error_message = None
                doc_elapsed = time.perf_counter() - doc_start

                res = DocumentProcessResult(
                    document=doc,
                    success=True,
                    execution_time_seconds=doc_elapsed,
                )
                summary.results.append(res)
                summary.processed_count += 1

            except Exception as e:  # noqa: BLE001
                # R2: error aislado — registra y continúa con los demás
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                doc_elapsed = time.perf_counter() - doc_start

                res = DocumentProcessResult(
                    document=doc,
                    success=False,
                    error_message=str(e),
                    execution_time_seconds=doc_elapsed,
                )
                summary.results.append(res)
                summary.error_count += 1

        summary.total_time_seconds = time.perf_counter() - start_time
        return summary
