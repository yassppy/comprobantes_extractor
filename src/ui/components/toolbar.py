"""Componente UI de barra de acciones (Toolbar)."""

import streamlit as st

from ui.state import AppState


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
            help="Selecciona al menos un comprobante válido para habilitar el procesamiento." if not can_process else "Iniciar extracción automática"
        )

        if btn_process:
            st.session_state.processing_started = True
            st.success(f"¡Iniciando procesamiento de {len(valid_docs)} comprobante(s)!")

    with col3:
        if st.button("🗑️ Limpiar", use_container_width=True):
            AppState.clear_selection()
            st.rerun()
