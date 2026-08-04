"""Componente de UI para la selección de comprobantes."""

from pathlib import Path

import streamlit as st

from domain.enums.document_type import DocumentType
from ui.state import AppState
from use_cases.select_documents import SelectDocumentsUseCase

_TYPE_OPTIONS = {
    "🛒 Compras  (facturas/boletas de proveedores)": DocumentType.PURCHASE,
    "🏷️ Ventas   (comprobantes emitidos por SUNAT)": DocumentType.SALE,
}


def _apply_document_type(result, doc_type: DocumentType):
    """Asigna el tipo de operación a todos los documentos seleccionados."""
    for doc in result.valid_documents:
        doc.document_type = doc_type
    return result


def render_file_selector() -> None:
    """
    Renderiza el widget de selección de archivos con tipo de operación (Compras/Ventas).
    """
    st.subheader("📂 Selección de Comprobantes")

    # ── Tipo de operación ────────────────────────────────────────────────────
    st.markdown("**Tipo de operación**")
    selected_label = st.radio(
        label="tipo_operacion",
        options=list(_TYPE_OPTIONS.keys()),
        index=0,
        horizontal=True,
        label_visibility="collapsed",
        key="radio_document_type",
    )
    doc_type = _TYPE_OPTIONS[selected_label]
    AppState.set_document_type(doc_type.value)

    st.divider()

    use_case = SelectDocumentsUseCase()

    tab1, tab2 = st.tabs(["Subir Archivos", "Escanear Carpeta Local"])

    with tab1:
        uploaded_files = st.file_uploader(
            "Selecciona uno o varios comprobantes (PDF, JPG, PNG, JPEG)",
            accept_multiple_files=True,
            key=AppState.get_uploader_key(),
            help="Formatos soportados: PDF, JPG, PNG, JPEG",
        )

        # Si se acaba de limpiar, ignoramos lo que devuelve el uploader en este ciclo
        if st.session_state.get("_clearing", False):
            st.session_state._clearing = False
        elif uploaded_files:
            # Solo actualizar si hay archivos seleccionados en el uploader
            # (no borrar la selección de carpeta cuando el uploader está vacío)
            result = use_case.execute_from_uploaded_files(uploaded_files)
            result = _apply_document_type(result, doc_type)
            AppState.update_selection(result)

    with tab2:
        dir_input = st.text_input(
            "Ruta de la carpeta local",
            placeholder="Ejemplo: C:/Comprobantes/2026-08",
            key="dir_input_widget",
        )
        recursive_check = st.checkbox("Buscar en subcarpetas", value=False)

        if st.button("Escanear Carpeta", key="btn_scan_dir"):
            if dir_input.strip():
                dir_path = Path(dir_input.strip())
                if dir_path.exists() and dir_path.is_dir():
                    result = use_case.execute_from_directory(dir_path, recursive=recursive_check)
                    result = _apply_document_type(result, doc_type)
                    AppState.update_selection(result)
                    st.success(
                        f"Carpeta escaneada. Se encontraron {len(result.valid_documents)} comprobante(s) válido(s)."
                    )
                else:
                    st.error(f"La ruta '{dir_input}' no existe o no es una carpeta válida.")
            else:
                st.warning("Por favor ingresa una ruta de carpeta válida.")
