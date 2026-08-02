"""Componente UI para mostrar la lista de archivos seleccionados y los errores de formato no soportado."""

import streamlit as st

from domain.enums.document_status import DocumentStatus
from ui.state import AppState

_STATUS_LABEL: dict[DocumentStatus, str] = {
    DocumentStatus.READY:      "Listo 🟢",
    DocumentStatus.PENDING:    "Pendiente ⏳",
    DocumentStatus.PROCESSING: "Procesando 🔄",
    DocumentStatus.PROCESSED:  "Procesado ✅",
    DocumentStatus.FAILED:     "Error ❌",
    DocumentStatus.ERROR:      "Error ❌",
    DocumentStatus.UNSUPPORTED:"No soportado ⛔",
}


def render_file_table() -> None:
    """
    Renderiza la tabla de comprobantes válidos y las alertas de archivos no soportados.
    """
    valid_docs = AppState.get_selected_documents()
    invalid_files = AppState.get_invalid_files()

    # R2: Mostrar mensaje indicando que archivos no soportados no pueden procesarse
    if invalid_files:
        st.error(f"⚠️ Se encontraron {len(invalid_files)} archivo(s) no soportado(s) o inválido(s):")
        for filename, error_msg in invalid_files:
            st.warning(f"❌ **{filename}**: {error_msg}")

    # R1: Mostrar la lista de archivos listos para procesar
    st.subheader("📄 Comprobantes Seleccionados")

    if not valid_docs:
        st.info("No hay ningún comprobante seleccionado actualmente. Selecciona uno o varios archivos arriba para comenzar.")
        return

    table_data = []
    for idx, doc in enumerate(valid_docs, start=1):
        label = _STATUS_LABEL.get(doc.status, doc.status.value.capitalize())
        table_data.append({
            "#": idx,
            "Nombre del Archivo": doc.name,
            "Tipo": doc.file_type.value.upper() if doc.file_type else "Desconocido",
            "Tamaño": doc.formatted_size,
            "Estado": label,
            "Error": doc.error_message or "",
        })

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Error": st.column_config.TextColumn("Detalle de Error", width="large"),
        },
    )

    processed = sum(1 for d in valid_docs if d.status == DocumentStatus.PROCESSED)
    failed = sum(1 for d in valid_docs if d.status in {DocumentStatus.FAILED, DocumentStatus.ERROR})

    caption_parts = [f"Total: **{len(valid_docs)}**"]
    if processed:
        caption_parts.append(f"Procesados: **{processed}**")
    if failed:
        caption_parts.append(f"Errores: **{failed}**")

    st.caption("  |  ".join(caption_parts))
