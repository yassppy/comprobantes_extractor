"""Componente UI de barra de acciones (Toolbar)."""

import streamlit as st

from domain.entities.document import Document
from domain.entities.processing_result import BatchProcessSummary
from ui.state import AppState
from use_cases.process_batch import ProcessBatchUseCase


def _ensure_file_on_disk(doc: Document, uploaded_files_map: dict) -> None:
    """
    Si el archivo fue subido por el uploader (no existe en disco todavía),
    lo escribe en un directorio temporal para que los extractores puedan leerlo.
    """
    import tempfile
    from pathlib import Path

    if doc.path.exists():
        return  # Ya existe en disco (escaneo de carpeta local)

    file_obj = uploaded_files_map.get(doc.name)
    if file_obj is None:
        return

    # Crear directorio temporal si no existe en session_state
    if "tmp_dir" not in st.session_state or st.session_state.tmp_dir is None:
        st.session_state.tmp_dir = tempfile.mkdtemp(prefix="comprobantes_")

    tmp_path = Path(st.session_state.tmp_dir) / doc.name
    tmp_path.write_bytes(file_obj.getvalue())
    doc.path = tmp_path


def _run_with_progress(valid_docs: list[Document]) -> BatchProcessSummary:
    """
    Ejecuta el procesamiento por lote mostrando progreso por archivo (REQ-2 R1, R3).
    """
    import time

    from domain.entities.processing_result import BatchProcessSummary, DocumentProcessResult
    from domain.enums.document_status import DocumentStatus

    # Construir mapa de archivos subidos en memoria
    uploaded_files_map: dict = {}
    uploader_key = AppState.get_uploader_key()
    raw_files = st.session_state.get(uploader_key, []) or []
    for f in raw_files:
        uploaded_files_map[f.name] = f

    # Asegurar que todos los archivos existan en disco
    for doc in valid_docs:
        _ensure_file_on_disk(doc, uploaded_files_map)

    progress_bar = st.progress(0, text="Iniciando procesamiento…")
    status_text = st.empty()
    total = len(valid_docs)

    use_case = ProcessBatchUseCase()

    start_time = time.perf_counter()
    summary = BatchProcessSummary(total_count=total)

    for i, doc in enumerate(valid_docs):
        status_text.markdown(f"⚙️ Procesando **{doc.name}** ({i + 1}/{total})…")
        progress_bar.progress(i / total, text=f"Archivo {i + 1} de {total}")

        doc_start = time.perf_counter()
        doc.status = DocumentStatus.PROCESSING

        try:
            use_case.single_processor(doc)
            doc.status = DocumentStatus.PROCESSED
            doc.error_message = None
            elapsed = time.perf_counter() - doc_start
            res = DocumentProcessResult(document=doc, success=True, execution_time_seconds=elapsed)
            summary.results.append(res)
            summary.processed_count += 1
        except Exception as e:  # noqa: BLE001
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            elapsed = time.perf_counter() - doc_start
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
        btn_process = st.button(
            "⚡ Iniciar Procesamiento",
            type="primary",
            disabled=not can_process,
            use_container_width=True,
            help=(
                "Selecciona al menos un comprobante válido para habilitar el procesamiento."
                if not can_process
                else "Iniciar extracción automática por lote"
            ),
        )

        if btn_process:
            summary = _run_with_progress(valid_docs)
            AppState.set_batch_summary(summary)
            st.rerun()

    with col3:
        if st.button("🗑️ Limpiar", use_container_width=True):
            # Limpiar archivos temporales
            if "tmp_dir" in st.session_state and st.session_state.tmp_dir:
                import shutil
                shutil.rmtree(st.session_state.tmp_dir, ignore_errors=True)
                st.session_state.tmp_dir = None
            AppState.clear_selection()
            st.rerun()

