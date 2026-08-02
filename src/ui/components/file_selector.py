"""Componente de UI para la selección de comprobantes."""

from pathlib import Path

import streamlit as st

from ui.state import AppState
from use_cases.select_documents import SelectDocumentsUseCase


def render_file_selector() -> None:
    """
    Renderiza el widget de selección de archivos y carpetas.
    """
    st.subheader("📂 Selección de Comprobantes")

    use_case = SelectDocumentsUseCase()

    tab1, tab2 = st.tabs(["Subir Archivos", "Escanear Carpeta Local"])

    with tab1:
        uploaded_files = st.file_uploader(
            "Selecciona uno o varios comprobantes (PDF, JPG, PNG, JPEG)",
            accept_multiple_files=True,
            key=AppState.get_uploader_key(),
            help="Formatos soportados: PDF, JPG, PNG, JPEG"
        )

        # Si se acaba de limpiar, ignoramos lo que devuelve el uploader en este ciclo
        if st.session_state.get("_clearing", False):
            st.session_state._clearing = False
        elif uploaded_files is not None:
            result = use_case.execute_from_uploaded_files(uploaded_files)
            AppState.update_selection(result)

    with tab2:
        dir_input = st.text_input(
            "Ruta de la carpeta local",
            placeholder="Ejemplo: C:/Comprobantes/2026-08",
            key="dir_input_widget"
        )
        recursive_check = st.checkbox("Buscar en subcarpetas", value=False)

        if st.button("Escanear Carpeta", key="btn_scan_dir"):
            if dir_input.strip():
                dir_path = Path(dir_input.strip())
                if dir_path.exists() and dir_path.is_dir():
                    result = use_case.execute_from_directory(dir_path, recursive=recursive_check)
                    AppState.update_selection(result)
                    st.success(f"Carpeta escaneada. Se encontraron {len(result.valid_documents)} comprobantes válidos.")
                else:
                    st.error(f"La ruta '{dir_input}' no existe o no es una carpeta válida.")
            else:
                st.warning("Por favor ingresa una ruta de carpeta válida.")
