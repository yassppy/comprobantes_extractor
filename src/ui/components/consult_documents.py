"""Componente UI para la vista "Consultar Facturas / Comprobantes Procesados"."""

from datetime import datetime

import streamlit as st

from Persistence.connection import get_conn
from Persistence.repositories.document_repo import search_documents
from ui.state import AppState

_MONTH_NAMES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def render_consult_documents() -> None:
    """
    Renderiza la vista de consulta y exportación de comprobantes procesados.
    Permite filtrar por búsqueda textual, tipo, mes y año.
    Incluye exportación a Excel (REQ-10) filtrada por empresa activa.
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

    # ── Barra de exportación Excel (REQ-10) ───────────────────────────────────
    _render_export_bar(
        search_query=search_query,
        process_type=process_type,
        selected_year=selected_year,
        selected_month=selected_month,
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

    # ── Resumen de resultados y paginador ─────────────────────────────────────
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
            st.markdown(
                f"<p style='text-align:center;margin-top:5px;'>"
                f"Pág. <b>{current_page}</b> / <b>{total_pages}</b></p>",
                unsafe_allow_html=True,
            )
        with c3:
            if st.button("▶", disabled=(current_page >= total_pages), key="btn_next_page"):
                st.session_state["consult_page"] = min(total_pages, current_page + 1)
                st.rerun()

    # ── Tabla de comprobantes ─────────────────────────────────────────────────
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

    st.dataframe(table_data, width="stretch", hide_index=True)


# ─── Barra de exportación Excel ───────────────────────────────────────────────

def _render_export_bar(
    search_query: str | None,
    process_type: str,
    selected_year: int,
    selected_month: int,
) -> None:
    """
    Renderiza la sección de exportación a Excel (REQ-10).
    Solo habilita la descarga si hay una empresa activa seleccionada.
    """
    active_company = AppState.get_active_company()

    with st.container():
        col_emp, col_btn = st.columns([3, 1], gap="small")

        with col_emp:
            if active_company:
                st.success(
                    f"📊 Exportar comprobantes de **{active_company['business_name']}** "
                    f"— {_MONTH_NAMES[selected_month - 1]} {selected_year}",
                    icon="✅",
                )
            else:
                st.warning(
                    "Selecciona una empresa en el panel lateral para habilitar la exportación a Excel.",
                    icon="⚠️",
                )

        with col_btn:
            st.caption(" ")  # alineación vertical
            if not active_company:
                st.button(
                    "📥 Exportar a Excel",
                    disabled=True,
                    help="Debes seleccionar una empresa en el panel lateral.",
                    key="btn_export_excel_disabled",
                )
            else:
                # Generar el Excel solo cuando se hace clic
                if st.button(
                    "📥 Exportar a Excel",
                    type="primary",
                    key="btn_export_excel",
                    help=f"Descarga todos los comprobantes de {_MONTH_NAMES[selected_month - 1]} "
                         f"{selected_year} con los filtros aplicados.",
                ):
                    _generate_and_offer_download(
                        active_company=active_company,
                        search_query=search_query,
                        process_type=process_type,
                        selected_year=selected_year,
                        selected_month=selected_month,
                    )


def _generate_and_offer_download(
    active_company: dict,
    search_query: str | None,
    process_type: str,
    selected_year: int,
    selected_month: int,
) -> None:
    """Consulta todos los registros (sin paginar) y genera el Excel para descarga."""
    from Persistence.repositories.document_repo import export_documents
    from utils.excel_exporter import build_excel

    company_id: int | None = active_company.get("id")
    company_name: str = active_company.get("business_name", "Empresa")

    if not company_id:
        st.error("❌ La empresa activa no tiene ID registrado. Vuelve a seleccionarla.")
        return

    with st.spinner("Generando Excel…"):
        try:
            with get_conn() as conn:
                rows = export_documents(
                    conn=conn,
                    company_id=company_id,
                    search_query=search_query,
                    document_type=process_type if process_type != "ALL" else None,
                    year=selected_year,
                    month=selected_month,
                )
        except Exception as exc:
            st.error(f"❌ Error al consultar la base de datos: {exc}")
            return

        if not rows:
            st.info("No hay comprobantes que coincidan con los filtros para exportar.")
            return

        try:
            xlsx_bytes = build_excel(
                rows=rows,
                company_name=company_name,
                month=selected_month,
                year=selected_year,
                document_type=process_type,
            )
        except Exception as exc:
            st.error(f"❌ Error al generar el archivo Excel: {exc}")
            return

    # ── Nombre del archivo ─────────────────────────────────────────────────
    tipo_sufijo = {"PURCHASE": "compras", "SALE": "ventas", "ALL": "todos"}.get(
        process_type, "comprobantes"
    )
    ruc = active_company.get("ruc", "")
    filename = (
        f"{ruc}_{tipo_sufijo}_{selected_year}{selected_month:02d}.xlsx"
    )

    st.success(f"✅ Excel generado — {len(rows)} comprobante(s).")
    st.download_button(
        label=f"⬇️ Descargar {filename}",
        data=xlsx_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_excel_btn",
    )
