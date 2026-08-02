"""Caso de uso: Procesamiento por lote de comprobantes (REQ-2 / HU02-batch-processing)."""

import time
from collections.abc import Callable

from domain.entities.document import Document
from domain.entities.processing_result import BatchProcessSummary, DocumentProcessResult
from domain.enums.document_status import DocumentStatus


class ProcessBatchUseCase:
    def __init__(self, single_processor: Callable[[Document], None] | None = None) -> None:
        """
        single_processor: Función o servicio que procesa un comprobante individual.
        Si es None, ejecuta una simulación/procesamiento por defecto.
        """
        self.single_processor = single_processor or self._default_processor

    def _default_processor(self, doc: Document) -> None:
        """
        Procesamiento por defecto. Si el nombre del archivo contiene 'error' o 'corrupto', simula una falla.
        """
        if "error" in doc.name.lower() or "corrupto" in doc.name.lower():
            raise ValueError(f"Falla al procesar el contenido de '{doc.name}' (documento ilegible o corrupto).")
        # Simulación de lectura exitosa
        time.sleep(0.01)

    def execute(self, documents: list[Document]) -> BatchProcessSummary:
        """
        Ejecuta el procesamiento por lote sobre todos los comprobantes seleccionados.
        R1: Procesar todos los archivos seleccionados.
        R2: Si ocurre un error en un comprobante, registrar el error y continuar con los demás.
        R3: Mostrar resumen con comprobantes procesados, errores y tiempo total.
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
                    execution_time_seconds=doc_elapsed
                )
                summary.results.append(res)
                summary.processed_count += 1

            except Exception as e:  # noqa: BLE001
                # R2: Error aislado por comprobante; registra error y continua con los demás

                doc.status = DocumentStatus.FAILED
                doc.error_message = str(e)
                doc_elapsed = time.perf_counter() - doc_start

                res = DocumentProcessResult(
                    document=doc,
                    success=False,
                    error_message=str(e),
                    execution_time_seconds=doc_elapsed
                )
                summary.results.append(res)
                summary.error_count += 1

        summary.total_time_seconds = time.perf_counter() - start_time
        return summary
