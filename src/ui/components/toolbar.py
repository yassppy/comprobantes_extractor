"""Componente UI de barra de acciones (Toolbar)."""

import streamlit as st

from domain.entities.document import Document
from domain.entities.processing_result import BatchProcessSummary
from ui.state import AppState
from use_cases.process_batch import ProcessBatchUseCase


def _run_with_progress(valid_docs: list[Document]) -> BatchProcessSummary:
    """
    Ejecuta el procesamiento por lote mostrando progreso por archivo (REQ-2 R1, R3).
    """
    import time

    from domain.entities.processing_result import BatchProcessSummary, DocumentProcessResult
    from domain.enums.document_status import DocumentStatus

    progress_bar = st.progress(0, text="Iniciando procesamiento…")
    status_text = st.empty()
    total = len(valid_docs)

    use_case = ProcessBatchUseCase()

    # Ejecutamos el lote capturando el resultado global
    start_time = time.perf_counter()
    summary = BatchProcessSummary(total_count=total)

    for i, doc in enumerate(valid_docs):
        status_text.markdown(f"⚙️ Procesando **{doc.name}** ({i + 1}/{total})…")
        progress_bar.progress((i) / total, text=f"Archivo {i + 1} de {total}")

        import time as _time
        doc_start = _time.perf_counter()
        doc.status = DocumentStatus.PROCESSING

        try:
            use_case.single_processor(doc)
            doc.status = DocumentStatus.PROCESSED
            doc.error_message = None
            elapsed = _time.perf_counter() - doc_start
            res = DocumentProcessResult(document=doc, success=True, execution_time_seconds=elapsed)
            summary.results.append(res)
            summary.processed_count += 1
        except Exception as e:  # noqa: BLE001
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            elapsed = _time.perf_counter() - doc_start
            res = DocumentProcessResult(document=doc, success=False, error_message=str(e), execution_time_seconds=elapsed)
            summary.results.append(res)
            summary.error_count += 1

        progress_bar.progress((i + 1) / total, text=f"Archivo {i + 1} de {total}")

    summary.total_time_seconds = time.perf_counter() - start_time

    progress_bar.empty()
    status_text.empty()

    return summary


def render_toolbar() -> None:
    """
    Renderiza la barra de herramientas de acciones.
    """
    st.divider()

    col1, col2, col3 = st.columns([2, 2, 1])

    valid_docs = AppState.get_selected_documents()
    can_process = AppState.can_start_processing()

    with col1:
        st.write(f"**Seleccionados:** {len(valid_docs)} comprobante(s)")

    with col2:
        # R3: Impedir iniciar el procesamiento si no hay archivos válidos seleccionados
        btn_process = st.button(
            "⚡ Iniciar Procesamiento",
            type="primary",
            disabled=not can_process,
            use_container_width=True,
            help="Selecciona al menos un comprobante válido para habilitar el procesamiento." if not can_process else "Iniciar extracción automática por lote"
        )

        if btn_process:
            summary = _run_with_progress(valid_docs)
            AppState.set_batch_summary(summary)
            st.rerun()

    with col3:
        if st.button("🗑️ Limpiar", use_container_width=True):
            AppState.clear_selection()
            st.rerun()

