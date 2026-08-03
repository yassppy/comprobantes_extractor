"""Componente UI: Gestión y validación SUNAT de empresas y socios (REQ-4).

Permite:
  1. Registrar empresas (companies) con RUC.
  2. Validar todas las empresas contra SUNAT con un solo botón.
  3. Ver el estado SUNAT de cada empresa.
  4. Validar socios de negocio (business_partners) extraídos de comprobantes.
"""

from __future__ import annotations

import streamlit as st

from use_cases.validate_ruc import (
    BatchRucValidationSummary,
    RucValidationResult,
    is_valid_ruc_format,
    validate_ruc_batch,
    validate_single_ruc,
)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _sunat_badge(result: RucValidationResult) -> str:
    """Retorna un emoji según el resultado de validación SUNAT."""
    if not result.success:
        return "⚠️ Error"
    if result.info and result.info.is_valid:
        return "✅ Válido"
    if result.info and result.info.is_active:
        return "🟡 Activo / No Habido"
    return "❌ Inactivo"


def _init_companies_state() -> None:
    if "companies" not in st.session_state:
        # Lista de dicts: {ruc, business_name, validation: RucValidationResult | None}
        st.session_state.companies = []
    if "partners_validation" not in st.session_state:
        # Dict ruc → RucValidationResult
        st.session_state.partners_validation: dict[str, RucValidationResult] = {}


# ─── Sección empresas ─────────────────────────────────────────────────────────

def _render_company_form() -> None:
    """Formulario para agregar una empresa."""
    with st.form("form_add_company", clear_on_submit=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            ruc = st.text_input("RUC", max_chars=11, placeholder="20512528458")
        with col2:
            name = st.text_input("Nombre / Razón Social", placeholder="Mi Empresa S.A.C.")

        submitted = st.form_submit_button("➕ Agregar Empresa")

    if submitted:
        ruc = ruc.strip()
        name = name.strip()

        if not ruc or not name:
            st.warning("Completa el RUC y el nombre para agregar la empresa.")
            return

        if not is_valid_ruc_format(ruc):
            st.error(f"El RUC '{ruc}' no tiene el formato correcto (11 dígitos).")
            return

        existing_rucs = [c["ruc"] for c in st.session_state.companies]
        if ruc in existing_rucs:
            st.warning(f"El RUC {ruc} ya está registrado.")
            return

        st.session_state.companies.append({
            "ruc": ruc,
            "business_name": name,
            "validation": None,
        })
        st.success(f"Empresa '{name}' agregada correctamente.")
        st.rerun()


def _render_companies_table() -> None:
    """Tabla de empresas registradas con estado SUNAT."""
    companies = st.session_state.companies

    if not companies:
        st.info("No hay empresas registradas. Agrega al menos una empresa arriba.")
        return

    # Botón validar todas
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("🔍 Validar todas en SUNAT", type="primary", use_container_width=True):
            rucs = [c["ruc"] for c in companies]
            with st.spinner(f"Consultando {len(rucs)} empresa(s) en SUNAT…"):
                summary = validate_ruc_batch(rucs)

            # Actualizar resultados en session_state
            results_map = {r.ruc: r for r in summary.results}
            for company in st.session_state.companies:
                company["validation"] = results_map.get(company["ruc"])

            _show_batch_summary(summary)
            st.rerun()

    with col_info:
        validated_count = sum(1 for c in companies if c["validation"] is not None)
        if validated_count > 0:
            st.caption(f"Última validación: {validated_count}/{len(companies)} empresa(s) consultadas.")

    st.divider()

    # Tabla
    for i, company in enumerate(companies):
        v: RucValidationResult | None = company["validation"]
        badge = _sunat_badge(v) if v else "— Sin validar"

        with st.expander(f"{badge}  |  {company['ruc']}  —  {company['business_name']}", expanded=False):
            col1, col2 = st.columns([3, 1])

            with col1:
                if v and v.success and v.info:
                    info = v.info
                    st.markdown(f"**Razón Social SUNAT:** {info.business_name}")
                    if info.trade_name:
                        st.markdown(f"**Nombre Comercial:** {info.trade_name}")
                    st.markdown(f"**Estado:** `{info.status}`  |  **Condición:** `{info.condition}`")
                    if info.fiscal_address:
                        st.markdown(f"**Domicilio Fiscal:** {info.fiscal_address}")
                    st.caption(f"Validado el {info.validated_at.strftime('%d/%m/%Y %H:%M')}")
                elif v and not v.success:
                    st.error(f"Error SUNAT: {v.error}")
                else:
                    st.info("Esta empresa no ha sido validada aún.")

            with col2:
                # Validar individualmente
                if st.button("🔄 Re-validar", key=f"revalidate_{i}"):
                    with st.spinner(f"Consultando RUC {company['ruc']}…"):
                        result = validate_single_ruc(company["ruc"])
                    company["validation"] = result
                    if result.success and result.info and result.info.is_valid:
                        st.success("RUC válido ✅")
                    elif result.success:
                        st.warning(f"RUC consultado pero no válido: {result.info.status if result.info else ''}")
                    else:
                        st.error(f"Error: {result.error}")
                    st.rerun()

                # Eliminar empresa
                if st.button("🗑️ Eliminar", key=f"delete_company_{i}"):
                    st.session_state.companies.pop(i)
                    st.rerun()


def _show_batch_summary(summary: BatchRucValidationSummary) -> None:
    """Muestra un resumen del resultado de validación por lote."""
    cols = st.columns(3)
    with cols[0]:
        st.metric("✅ Válidos (ACTIVO + HABIDO)", summary.valid)
    with cols[1]:
        st.metric("🟡 Inactivos / No Habidos", summary.invalid)
    with cols[2]:
        st.metric("⚠️ Errores de consulta", summary.errors)

    if summary.errors > 0:
        error_rucs = [r.ruc for r in summary.results if not r.success]
        st.warning(
            f"No se pudo consultar SUNAT para {summary.errors} RUC(s): "
            f"{', '.join(error_rucs)}. Verifica tu conexión a internet."
        )
    if summary.invalid > 0:
        invalid_rucs = [
            r.ruc for r in summary.results
            if r.success and r.info and not r.info.is_valid
        ]
        st.error(
            f"⚠️ {summary.invalid} empresa(s) con estado inválido en SUNAT: "
            f"{', '.join(invalid_rucs)}"
        )


# ─── Sección socios de negocio ─────────────────────────────────────────────────

def _render_partners_validation() -> None:
    """
    Muestra los socios de negocio (RUCs) extraídos de los comprobantes
    y permite validarlos contra SUNAT.
    """
    from ui.state import AppState

    docs = AppState.get_selected_documents()

    # Recolectar RUCs únicos extraídos (solo 11 dígitos)
    partner_rucs: set[str] = set()
    for doc in docs:
        if doc.extracted_data:
            ed = doc.extracted_data
            ruc = getattr(ed, "supplier_ruc", None) or getattr(ed, "customer_ruc", None)
            if ruc and is_valid_ruc_format(ruc):
                partner_rucs.add(ruc)

    if not partner_rucs:
        st.info("Procesa comprobantes primero para ver los RUCs de proveedores/clientes.")
        return

    st.markdown(f"Se encontraron **{len(partner_rucs)}** RUC(s) únicos en los comprobantes procesados.")

    if st.button("🔍 Validar socios en SUNAT", use_container_width=True):
        ruc_list = sorted(partner_rucs)
        with st.spinner(f"Consultando {len(ruc_list)} RUC(s) en SUNAT…"):
            summary = validate_ruc_batch(ruc_list)

        for r in summary.results:
            st.session_state.partners_validation[r.ruc] = r

        _show_batch_summary(summary)
        st.rerun()

    # Tabla de resultados de socios
    if st.session_state.partners_validation:
        st.divider()
        rows = []
        for ruc in sorted(partner_rucs):
            v = st.session_state.partners_validation.get(ruc)
            if v:
                rows.append({
                    "RUC":          v.ruc,
                    "Razón Social": v.info.business_name if v.info else "—",
                    "Estado":       v.info.status if v.info else "—",
                    "Condición":    v.info.condition if v.info else "—",
                    "SUNAT":        _sunat_badge(v),
                })

        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)


# ─── Render principal ──────────────────────────────────────────────────────────

def render_company_manager() -> None:
    """
    Renderiza el panel completo de gestión de empresas y validación SUNAT.
    """
    _init_companies_state()

    st.subheader("🏢 Empresas y Validación SUNAT")

    tab_companies, tab_partners = st.tabs([
        "Empresas Registradas",
        "Socios de Negocio (Proveedores / Clientes)",
    ])

    with tab_companies:
        st.markdown("##### Registrar Empresa")
        _render_company_form()

        st.markdown("##### Empresas Registradas")
        _render_companies_table()

    with tab_partners:
        st.markdown("##### RUCs extraídos de comprobantes procesados")
        _render_partners_validation()
