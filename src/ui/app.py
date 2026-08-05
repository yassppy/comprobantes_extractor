"""Aplicación principal de Streamlit para el Extractor de Comprobantes."""

import logging

import streamlit as st

from ui.components.classify_panel import render_classify_panel
from ui.components.company_manager import render_company_manager
from ui.components.consult_documents import render_consult_documents
from ui.components.file_selector import render_file_selector
from ui.components.file_table import render_file_table
from ui.components.summary_card import render_summary_card
from ui.components.toolbar import render_toolbar
from ui.state import AppState

logger = logging.getLogger(__name__)


@st.cache_resource(show_spinner=False)
def _run_category_sync() -> None:
    """
    Sincroniza las categorías YAML → PostgreSQL una sola vez por sesión
    de servidor (REQ-6 R1).

    El decorador @st.cache_resource garantiza que la función se ejecute
    una única vez aunque múltiples usuarios recarguen la app.
    """
    from use_cases.sync_categories import sync_categories

    result = sync_categories()

    if not result.success:
        logger.warning(
            "Sincronización de categorías completó con errores: %s",
            result.errors,
        )
    else:
        logger.info(
            "Categorías sincronizadas — creadas: %d, actualizadas: %d, desactivadas: %d",
            result.created,
            result.updated,
            result.deactivated,
        )


def main() -> None:
    st.set_page_config(
        page_title="Extractor de Comprobantes",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # REQ-6 R1: sincronizar categorías al iniciar la aplicación
    _run_category_sync()

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
    tab_process, tab_classify, tab_consult = st.tabs([
        "⚡ Procesar Comprobantes",
        "🤖 Clasificar por Lotes",
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

    with tab_classify:
        render_classify_panel()

    with tab_consult:
        render_consult_documents()


if __name__ == "__main__":
    main()
