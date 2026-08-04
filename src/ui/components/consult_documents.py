"""Componente UI para la vista "Consultar Facturas / Comprobantes Procesados".""".strip()

from datetime import datetime
import streamlit as st

from Persistence.connection import get_conn
from Persistence.repositories.document_repo import search_documents

_MONTH_NAMES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]


def render_consult_documents() -> None:
    """
    Renderiza la vista de consulta de comprobantes procesados.
    Permite filtrar por:
    - Búsqueda textual: cliente, proveedor, RUC/DNI o serie-número
    - Tipo de proceso: Compras / Ventas / Todos
    - Mes: por defecto el mes actual
    - Año: por defecto el año actual
    Y muestra una tabla paginada.
    """
    st.subheader("🔍 Consultar Facturas y Comprobantes Procesados")
    st.markdown("Busca y filtra todos los comprobantes registrados en el sistema.")

    now = datetime.now()
    current_year = now.year
    current_month = now.month

    # ── Filtros ───────────────────────────────────────────────────────────────
    with st.container():
        col1, col2, col3, col4 = st.columns([2, 1.2, 1, 1], gap="small")

        with col1:
            search_query = st.text_input(
                "🔎 Buscar por Cliente, Proveedor, RUC/DNI o Serie-Número",
                placeholder="Ej. 20610320351, E001-443, D&T...",
                key="consult_search_query",
            )

        with col2:
            process_type = st.selectbox(
                "🛒 Tipo de Proceso",
                options=["ALL", "PURCHASE", "SALE"],
                format_func=lambda x: {
                    "ALL": "Todos los procesos",
                    "PURCHASE": "Compras 🛒",
                    "SALE": "Ventas 🏷️",
                }[x],
                key="consult_process_type",
            )

        with col3:
            # Lista de años disponible (año actual +- 3 años)
            years_options = list(range(current_year - 3, current_year + 2))
            selected_year = st.selectbox(
                "📅 Año",
                options=years_options,
                index=years_options.index(current_year) if current_year in years_options else 0,
                key="consult_selected_year",
            )

        with col4:
            selected_month = st.selectbox(
                "🗓️ Mes",
                options=list(range(1, 13)),
                index=current_month - 1,
                format_func=lambda m: _MONTH_NAMES[m - 1],
                key="consult_selected_month",
            )

    st.divider()

    # ── Paginación y Carga de datos ───────────────────────────────────────────
    page_size = 10
    if "consult_page" not in st.session_state:
        st.session_state["consult_page"] = 1

    current_page = st.session_state["consult_page"]
    offset = (current_page - 1) * page_size

    try:
        with get_conn() as conn:
            docs, total_count = search_documents(
                conn=conn,
                search_query=search_query,
                document_type=process_type if process_type != "ALL" else None,
                year=selected_year,
                month=selected_month,
                limit=page_size,
                offset=offset,
            )
    except Exception as e:
        st.warning(f"⚠️ No se pudo consultar la base de datos PostgreSQL: {e}")
        st.info("💡 Asegúrate de tener configurado `.env` con la base de datos PostgreSQL activa.")
        return

    total_pages = max(1, (total_count + page_size - 1) // page_size)

    # ── Resumen de Resultados y Paginador Superior ────────────────────────────
    col_info, col_page_controls = st.columns([2, 1])

    with col_info:
        st.caption(
            f"Mostrando **{len(docs)}** de **{total_count}** comprobante(s) "
            f"para **{_MONTH_NAMES[selected_month - 1]} {selected_year}**"
        )

    with col_page_controls:
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("◀", disabled=(current_page <= 1), key="btn_prev_page"):
                st.session_state["consult_page"] = max(1, current_page - 1)
                st.rerun()
        with c2:
            st.markdown(f"<p style='text-align: center; margin-top: 5px;'>Pág. <b>{current_page}</b> / <b>{total_pages}</b></p>", unsafe_allow_html=True)
        with c3:
            if st.button("▶", disabled=(current_page >= total_pages), key="btn_next_page"):
                st.session_state["consult_page"] = min(total_pages, current_page + 1)
                st.rerun()

    # ── Tabla de Comprobantes ─────────────────────────────────────────────────
    if not docs:
        st.info("No se encontraron comprobantes procesados con los filtros seleccionados.")
        return

    table_data = []
    for idx, doc in enumerate(docs, start=offset + 1):
        doc_type_label = "Compra 🛒" if doc.get("document_type") == "PURCHASE" else "Venta 🏷️"
        partner_doc = doc.get("partner_doc") or "00000000"
        partner_name = doc.get("partner_name") or partner_doc

        table_data.append({
            "#": idx,
            "Archivo": doc.get("file_name"),
            "Operación": doc_type_label,
            "Tipo": doc.get("invoice_type") or "—",
            "Serie": doc.get("series") or "—",
            "Número": doc.get("number") or "—",
            "Fecha": doc.get("issue_date").strftime("%d/%m/%Y") if doc.get("issue_date") else "—",
            "RUC/DNI": partner_doc,
            "Socio / Cliente": partner_name,
            "Descripción": doc.get("description") or "—",
            "Total": f"{doc.get('total'):.2f}" if doc.get("total") is not None else "—",
            "Motor": doc.get("ocr_engine") or "—",
            "Estado": doc.get("status") or "—",
        })

    st.dataframe(
        table_data,
        width="stretch",
        hide_index=True,
    )
