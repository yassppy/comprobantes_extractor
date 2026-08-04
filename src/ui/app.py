"""Aplicación principal de Streamlit para el Extractor de Comprobantes."""

import streamlit as st

from ui.components.company_manager import render_company_manager
from ui.components.consult_documents import render_consult_documents
from ui.components.file_selector import render_file_selector
from ui.components.file_table import render_file_table
from ui.components.summary_card import render_summary_card
from ui.components.toolbar import render_toolbar
from ui.state import AppState


def main() -> None:
    st.set_page_config(
        page_title="Extractor de Comprobantes",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    AppState.initialize()

    # ── Sidebar: Empresas y validación SUNAT ──────────────────────────────────
    with st.sidebar:
        render_company_manager()

    # ── Encabezado ────────────────────────────────────────────────────────────
    st.title("🧾 Extractor de Comprobantes de Compras y Ventas")
    st.markdown(
        "Automatización de lectura, extracción de datos y clasificación local de comprobantes."
    )
    st.divider()

    # ── Navegación por pestañas ───────────────────────────────────────────────
    tab_process, tab_consult = st.tabs([
        "⚡ Procesar Comprobantes",
        "🔍 Consultar Facturas Procesadas",
    ])

    with tab_process:
        col_left, col_right = st.columns([1, 1], gap="large")

        with col_left:
            render_file_selector()

        with col_right:
            render_file_table()

        render_toolbar()
        render_summary_card()

    with tab_consult:
        render_consult_documents()


if __name__ == "__main__":
    main()
