"""Componente UI para mostrar la lista de archivos seleccionados y los errores de formato no soportado."""

import streamlit as st

from domain.enums.document_status import DocumentStatus
from domain.enums.document_type import DocumentType
from ui.state import AppState

_STATUS_LABEL: dict[DocumentStatus, str] = {
    DocumentStatus.READY:       "Listo 🟢",
    DocumentStatus.PENDING:     "Pendiente ⏳",
    DocumentStatus.PROCESSING:  "Procesando 🔄",
    DocumentStatus.PROCESSED:   "Procesado ✅",
    DocumentStatus.FAILED:      "Error ❌",
    DocumentStatus.ERROR:       "Error ❌",
    DocumentStatus.UNSUPPORTED: "No soportado ⛔",
}

_TYPE_LABEL = {
    DocumentType.PURCHASE: "Compra 🛒",
    DocumentType.SALE:     "Venta 🏷️",
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

    st.subheader("📄 Comprobantes Seleccionados")

    if not valid_docs:
        st.info("No hay ningún comprobante seleccionado actualmente. Selecciona uno o varios archivos arriba para comenzar.")
        return

    # Detectar si ya hay datos extraídos (post-procesamiento)
    has_extracted = any(doc.extracted_data is not None for doc in valid_docs)

    if has_extracted:
        _render_extracted_table(valid_docs)
    else:
        _render_pending_table(valid_docs)

    processed = sum(1 for d in valid_docs if d.status == DocumentStatus.PROCESSED)
    failed = sum(1 for d in valid_docs if d.status in {DocumentStatus.FAILED, DocumentStatus.ERROR})

    caption_parts = [f"Total: **{len(valid_docs)}**"]
    if processed:
        caption_parts.append(f"Procesados: **{processed}**")
    if failed:
        caption_parts.append(f"Errores: **{failed}**")

    st.caption("  |  ".join(caption_parts))


def _render_pending_table(valid_docs) -> None:
    """Tabla simple antes del procesamiento."""
    table_data = []
    for idx, doc in enumerate(valid_docs, start=1):
        label = _STATUS_LABEL.get(doc.status, doc.status.value.capitalize())
        table_data.append({
            "#":                  idx,
            "Nombre del Archivo": doc.name,
            "Tipo Arch.":         doc.file_type.value.upper() if doc.file_type else "?",
            "Operación":          _TYPE_LABEL.get(doc.document_type, doc.document_type),
            "Tamaño":             doc.formatted_size,
            "Estado":             label,
            "Error":              doc.error_message or "",
        })

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Error": st.column_config.TextColumn("Detalle de Error", width="large"),
        },
    )


def _render_extracted_table(valid_docs) -> None:
    """Tabla enriquecida con los datos extraídos post-procesamiento."""
    from domain.entities.extracted_data import ExtractedData

    table_data = []
    for idx, doc in enumerate(valid_docs, start=1):
        label = _STATUS_LABEL.get(doc.status, doc.status.value.capitalize())
        ed: ExtractedData | None = doc.extracted_data  # type: ignore[assignment]

        table_data.append({
            "#":           idx,
            "Archivo":     doc.name,
            "Operación":   _TYPE_LABEL.get(doc.document_type, doc.document_type),
            "Tipo":        (ed.invoice_type or "—") if ed else "—",
            "Serie":       (ed.series or "—") if ed else "—",
            "Número":      (ed.number or "—") if ed else "—",
            "Fecha":       (ed.issue_date or "—") if ed else "—",
            "Proveedor":   (ed.supplier_name or ed.supplier_ruc or "—") if ed else "—",
            "Subtotal":    (f"{ed.subtotal:.2f}" if ed and ed.subtotal is not None else "—"),
            "IGV":         (f"{ed.igv:.2f}" if ed and ed.igv is not None else "—"),
            "Total":       (f"{ed.total:.2f}" if ed and ed.total is not None else "—"),
            "Motor OCR":   (ed.ocr_engine or "—") if ed else "—",
            "Estado":      label,
            "Error":       doc.error_message or "",
        })

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Error": st.column_config.TextColumn("Detalle de Error", width="large"),
        },
    )
