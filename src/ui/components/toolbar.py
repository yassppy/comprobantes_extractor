"""Componente UI de barra de acciones (Toolbar)."""

from __future__ import annotations

import streamlit as st

from domain.entities.document import Document
from domain.entities.processing_result import BatchProcessSummary
from ui.state import AppState
from use_cases.process_batch import ProcessBatchUseCase

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _ensure_file_on_disk(doc: Document, uploaded_files_map: dict) -> None:
    """
    Si el archivo fue subido por el uploader (no existe en disco),
    lo escribe en un directorio temporal para que los extractores puedan leerlo.
    """
    import tempfile
    from pathlib import Path

    if doc.path.exists():
        return

    file_obj = uploaded_files_map.get(doc.name)
    if file_obj is None:
        return

    if "tmp_dir" not in st.session_state or st.session_state.tmp_dir is None:
        st.session_state.tmp_dir = tempfile.mkdtemp(prefix="comprobantes_")

    tmp_path = Path(st.session_state.tmp_dir) / doc.name
    tmp_path.write_bytes(file_obj.getvalue())
    doc.path = tmp_path


def _run_with_progress(
    valid_docs: list[Document], company_name: str = ""
) -> BatchProcessSummary:
    """Ejecuta el procesamiento por lote mostrando progreso en UI y en consola (REQ-11)."""
    import time

    from console.rich_logger import (
        finish_batch,
        log_error,
        log_processing,
        log_success,
        start_batch,
    )
    from domain.entities.processing_result import (
        BatchProcessSummary,
        DocumentProcessResult,
    )
    from domain.enums.document_status import DocumentStatus

    # Mapa de archivos subidos en memoria (solo para tab "Subir Archivos")
    uploaded_files_map: dict = {}
    uploader_key = AppState.get_uploader_key()
    raw_files = st.session_state.get(uploader_key, []) or []
    for f in raw_files:
        uploaded_files_map[f.name] = f

    # Solo escribir a tmp los archivos que no existen en disco (subidos por uploader)
    for doc in valid_docs:
        _ensure_file_on_disk(doc, uploaded_files_map)

    progress_bar = st.progress(0, text="Iniciando procesamiento…")
    status_text = st.empty()
    total = len(valid_docs)
    use_case = ProcessBatchUseCase()

    # REQ-11 R1 + R2: inicio de visualización con Rich en consola
    start_batch(total, company_name)

    start_time = time.perf_counter()
    summary = BatchProcessSummary(total_count=total)

    for i, doc in enumerate(valid_docs):
        status_text.markdown(f"⚙️ Procesando **{doc.name}** ({i + 1}/{total})…")
        progress_bar.progress(i / total, text=f"Archivo {i + 1} de {total}")

        doc_start = time.perf_counter()
        doc.status = DocumentStatus.PROCESSING

        # REQ-11 R2: log inicio en consola
        log_processing(doc.name, i + 1, total)

        try:
            use_case.single_processor(doc)
            doc.status = DocumentStatus.PROCESSED
            doc.error_message = None
            elapsed = time.perf_counter() - doc_start
            res = DocumentProcessResult(
                document=doc, success=True, execution_time_seconds=elapsed
            )
            summary.results.append(res)
            summary.processed_count += 1

            # REQ-11 R2: log éxito con detalle extraído
            log_success(doc.name, elapsed, doc.extracted_data)

        except Exception as e:  # noqa: BLE001
            doc.status = DocumentStatus.FAILED
            doc.error_message = str(e)
            elapsed = time.perf_counter() - doc_start
            res = DocumentProcessResult(
                document=doc,
                success=False,
                error_message=str(e),
                execution_time_seconds=elapsed,
            )
            summary.results.append(res)
            summary.error_count += 1

            # REQ-11 R2: log error en consola
            log_error(doc.name, str(e), elapsed)

        progress_bar.progress((i + 1) / total, text=f"Archivo {i + 1} de {total}")

    summary.total_time_seconds = time.perf_counter() - start_time
    progress_bar.empty()
    status_text.empty()

    # REQ-11 R3: resumen final en consola
    finish_batch(summary)

    return summary


def _save_to_db(summary: BatchProcessSummary) -> None:
    """
    Persiste el lote en PostgreSQL (REQ-7).
    Muestra resultado inline sin bloquear el flujo si la BD no está disponible.
    """
    from use_cases.save_batch import save_batch

    company = AppState.get_active_company()
    if not company:
        st.warning(
            "⚠️ No hay empresa seleccionada. Los comprobantes fueron procesados "
            "pero **no se guardaron en la base de datos**. "
            "Selecciona una empresa en el panel lateral y vuelve a procesar."
        )
        return

    save_placeholder = st.empty()
    save_placeholder.info("💾 Guardando en base de datos…")

    try:
        result = save_batch(
            summary=summary,
            company_ruc=company["ruc"],
            company_name=company["business_name"],
        )
        AppState.set_save_result(result)
        save_placeholder.empty()

        # REQ-11 R2: registrar resultado de guardado en consola
        from console.rich_logger import log_save_result

        log_save_result(result.saved, result.skipped_duplicates, result.errors)

    except Exception as exc:  # noqa: BLE001
        save_placeholder.empty()
        st.error(
            f"❌ No se pudo conectar a la base de datos: {exc}. "
            "Verifica que PostgreSQL esté activo y que DATABASE_URL en .env sea correcta."
        )


# ─── Selector de empresa activa ───────────────────────────────────────────────


def _render_company_selector() -> None:
    """
    Muestra un selector de empresa activa para el lote.
    Las empresas vienen de st.session_state.companies (registradas en el sidebar).
    """
    companies: list[dict] = st.session_state.get("companies", [])

    if not companies:
        st.caption("⚠️ Sin empresa — regístrala en el panel lateral para guardar en BD.")
        AppState.set_active_company(None)
        return

    options = {f"{c['ruc']} — {c['business_name']}": c for c in companies}
    label_list = list(options.keys())

    # Mantener selección previa si sigue siendo válida
    current = AppState.get_active_company()
    current_label = None
    if current:
        key = f"{current['ruc']} — {current['business_name']}"
        if key in options:
            current_label = key

    selected_label = st.selectbox(
        "Empresa",
        label_list,
        index=label_list.index(current_label) if current_label else 0,
        key="company_selector",
        label_visibility="collapsed",
    )
    AppState.set_active_company(options[selected_label])


# ─── Render principal ──────────────────────────────────────────────────────────


def render_toolbar() -> None:
    """Renderiza la barra de herramientas de acciones."""
    st.divider()

    valid_docs = AppState.get_selected_documents()
    active_company = AppState.get_active_company()
    has_docs = len(valid_docs) > 0
    has_company = active_company is not None

    # Determinar si se puede procesar y el motivo si no
    can_process = has_docs and has_company
    if not has_docs and not has_company:
        block_reason = "Selecciona comprobantes y una empresa para comenzar."
    elif not has_company:
        block_reason = "Registra y selecciona una empresa en el panel lateral."
    elif not has_docs:
        block_reason = "Selecciona al menos un comprobante válido."
    else:
        block_reason = None

    # Fila: empresa + contador + botones
    col_company, col_count, col_process, col_clear = st.columns([2, 1, 2, 1])

    with col_company:
        st.caption("**Empresa activa**")
        _render_company_selector()

    with col_count:
        st.metric("Comprobantes", len(valid_docs))

    with col_process:
        btn_process = st.button(
            "⚡ Iniciar Procesamiento",
            type="primary",
            disabled=not can_process,
            width="stretch",
            help=block_reason
            if block_reason
            else "Extraer, parsear y guardar en base de datos",
        )

        if btn_process:
            summary = _run_with_progress(
                valid_docs,
                company_name=active_company.get("business_name", "")
                if active_company
                else "",
            )
            AppState.set_batch_summary(summary)
            _save_to_db(summary)
            st.rerun()

    with col_clear:
        if st.button("🗑️ Limpiar", width="stretch"):
            if "tmp_dir" in st.session_state and st.session_state.tmp_dir:
                import shutil

                shutil.rmtree(st.session_state.tmp_dir, ignore_errors=True)
                st.session_state.tmp_dir = None
            AppState.clear_selection()
            st.rerun()
