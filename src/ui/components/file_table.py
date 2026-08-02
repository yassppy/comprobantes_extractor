"""Componente UI para mostrar la lista de archivos seleccionados y los errores de formato no soportado."""

import streamlit as st

from ui.state import AppState


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
    st.subheader("📄 Comprobantes Listos para Procesar")

    if not valid_docs:
        st.info("No hay ningún comprobante seleccionado actualmente. Selecciona uno o varios archivos arriba para comenzar.")
        return

    table_data = []
    for idx, doc in enumerate(valid_docs, start=1):
        table_data.append({
            "#": idx,
            "Nombre del Archivo": doc.name,
            "Tipo": doc.file_type.value.upper() if doc.file_type else "Desconocido",
            "Tamaño": doc.formatted_size,
            "Estado": "Listo 🟢" if doc.status == "ready" else doc.status.value.capitalize(),
            "Ruta": str(doc.path)
        })

    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True
    )

    st.caption(f"Total de comprobantes listos: **{len(valid_docs)}**")
