"""Componente UI: Gestión y validación SUNAT de empresas y socios (REQ-4)."""

from __future__ import annotations

import logging

import streamlit as st

from use_cases.validate_ruc import (
    BatchRucValidationSummary,
    RucValidationResult,
    can_validate_sunat,
    is_valid_dni_format,
    is_valid_ruc_format,
    validate_ruc_batch,
    validate_single_ruc,
)

logger = logging.getLogger(__name__)


# ─── BD helpers ───────────────────────────────────────────────────────────────

def _db_upsert_company(
    ruc: str,
    business_name: str,
    trade_name: str | None = None,
    fiscal_address: str | None = None,
    sunat_status: str | None = None,
    sunat_condition: str | None = None,
    sunat_is_valid: bool = False,
    sunat_validated_at=None,
) -> str | None:
    """Persiste empresa en PostgreSQL. Retorna None si ok, mensaje si falla."""
    try:
        from Persistence.connection import get_conn
        from Persistence.repositories.company_repo import upsert_company
        with get_conn() as conn:
            upsert_company(
                conn=conn,
                ruc=ruc,
                business_name=business_name,
                trade_name=trade_name,
                fiscal_address=fiscal_address,
                sunat_status=sunat_status,
                sunat_condition=sunat_condition,
                sunat_is_valid=sunat_is_valid,
                sunat_validated_at=sunat_validated_at,
            )
        return None
    except Exception as exc:
        logger.error("Error al persistir empresa %s: %s", ruc, exc)
        return str(exc)


def _load_companies_from_db() -> list[dict]:
    """
    Carga empresas activas desde BD con todos sus campos SUNAT.
    Así el badge se muestra correctamente sin necesitar re-validar.
    """
    try:
        from Persistence.connection import get_conn
        from Persistence.repositories.company_repo import get_all_companies
        with get_conn() as conn:
            rows = get_all_companies(conn)
        return [
            {
                "id":            r["id"],
                "ruc":           r["ruc"],
                "business_name": r["business_name"],
                "trade_name":    r.get("trade_name"),
                "fiscal_address": r.get("fiscal_address"),
                "sunat_status":   r.get("sunat_status"),
                "sunat_condition": r.get("sunat_condition"),
                "sunat_is_valid":  r.get("sunat_is_valid", False),
                "sunat_validated_at": r.get("sunat_validated_at"),
                "validation": None,
            }
            for r in rows
        ]
    except Exception:
        return []


def _load_partners_from_db() -> dict[str, dict]:
    """
    Carga socios de negocio ya validados desde BD.
    Retorna dict ruc → datos SUNAT.
    """
    try:
        from Persistence.connection import get_conn
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT document_number, business_name, trade_name, fiscal_address,
                       sunat_status, sunat_condition, sunat_is_valid, sunat_validated_at
                FROM business_partners
                WHERE document_type = 'RUC'
                  AND sunat_validated_at IS NOT NULL
                ORDER BY business_name
                """
            ).fetchall()
        return {r["document_number"]: dict(r) for r in rows}
    except Exception:
        return {}


# ─── Helpers UI ───────────────────────────────────────────────────────────────

def _badge_from_db(company: dict) -> str:
    """Badge basado en los campos SUNAT ya guardados en BD."""
    if company.get("sunat_validated_at") is None:
        return "— Sin validar"
    if company.get("sunat_is_valid"):
        return "✅ Válido"
    status = (company.get("sunat_status") or "").upper()
    if status == "ACTIVO":
        return "🟡 Activo / No Habido"
    return "❌ Inactivo"


def _sunat_badge(result: RucValidationResult) -> str:
    """Badge desde resultado de validación en sesión."""
    if not result.success:
        return "⚠️ Error"
    if result.info and result.info.is_valid:
        return "✅ Válido"
    if result.info and result.info.is_active:
        return "🟡 Activo / No Habido"
    return "❌ Inactivo"


def _init_companies_state() -> None:
    if "companies" not in st.session_state:
        st.session_state.companies = _load_companies_from_db()


# ─── Formulario de alta de empresa ────────────────────────────────────────────

def _render_company_form() -> None:
    with st.form("form_add_company", clear_on_submit=True):
        col1, col2 = st.columns([1, 2])
        with col1:
            ruc_input = st.text_input("RUC", max_chars=11, placeholder="20512528458")
        with col2:
            name_input = st.text_input("Nombre / Razón Social", placeholder="Mi Empresa S.A.C.")
        submitted = st.form_submit_button("➕ Agregar Empresa")

    if not submitted:
        return

    ruc = ruc_input.strip()
    name = name_input.strip()

    if not ruc or not name:
        st.warning("Completa el RUC y el nombre.")
        return
    if not is_valid_ruc_format(ruc):
        st.error(f"El RUC '{ruc}' debe tener 11 dígitos numéricos.")
        return
    if any(c["ruc"] == ruc for c in st.session_state.companies):
        st.warning(f"El RUC {ruc} ya está registrado.")
        return

    new_entry = {
        "id": None, "ruc": ruc, "business_name": name, "trade_name": None,
        "fiscal_address": None, "sunat_status": None, "sunat_condition": None,
        "sunat_is_valid": False, "sunat_validated_at": None, "validation": None,
    }
    st.session_state.companies.append(new_entry)

    db_error = _db_upsert_company(ruc=ruc, business_name=name)
    if db_error:
        st.warning(f"Empresa en sesión, pero error en BD: {db_error}")
    else:
        # Recargar desde BD para obtener el id real
        reloaded = _load_companies_from_db()
        found = next((c for c in reloaded if c["ruc"] == ruc), None)
        if found:
            new_entry.update(found)
        st.success(f"'{name}' agregada ✅")
    st.rerun()


# ─── Tabla de empresas ────────────────────────────────────────────────────────

def _persist_sunat_results(results_map: dict[str, RucValidationResult]) -> int:
    updated = 0
    for ruc, result in results_map.items():
        if result.success and result.info:
            info = result.info
            db_error = _db_upsert_company(
                ruc=info.ruc, business_name=info.business_name,
                trade_name=info.trade_name, fiscal_address=info.fiscal_address,
                sunat_status=info.status, sunat_condition=info.condition,
                sunat_is_valid=info.is_valid, sunat_validated_at=info.validated_at,
            )
            if not db_error:
                updated += 1
    return updated


def _sync_company_from_result(company: dict, result: RucValidationResult) -> None:
    """Actualiza los campos SUNAT del dict de empresa en session_state."""
    company["validation"] = result
    if result.success and result.info:
        info = result.info
        company["business_name"]    = info.business_name
        company["trade_name"]       = info.trade_name
        company["fiscal_address"]   = info.fiscal_address
        company["sunat_status"]     = info.status
        company["sunat_condition"]  = info.condition
        company["sunat_is_valid"]   = info.is_valid
        company["sunat_validated_at"] = info.validated_at


def _render_companies_table() -> None:
    # Mostrar mensaje de validación individual si viene de un rerun
    msg = st.session_state.pop("_company_msg", None)
    if msg:
        level, text = msg
        if level == "success":
            st.success(text)
        elif level == "warning":
            st.warning(text)
        else:
            st.error(text)

    companies = st.session_state.companies

    if not companies:
        st.info("No hay empresas registradas. Agrega al menos una empresa arriba.")
        return

    # Contar cuántas ya están validadas en BD
    already_valid = sum(1 for c in companies if c.get("sunat_validated_at") is not None)

    if already_valid > 0:
        st.caption(f"✅ {already_valid}/{len(companies)} empresa(s) validadas en SUNAT.")

    if st.button("🔍 Validar todas en SUNAT", type="primary", width="stretch"):
        import time as _time
        from console.rich_logger import (
            finish_sunat_validation,
            log_sunat_item,
            start_sunat_validation,
        )

        rucs = [c["ruc"] for c in companies]
        company_name_map = {c["ruc"]: c.get("business_name", c["ruc"]) for c in companies}

        start_sunat_validation(len(rucs), entity_type="Empresas")
        t_total_start = _time.perf_counter()

        def _on_company_validated(idx: int, r):
            info = r.info
            log_sunat_item(
                document_number=r.ruc,
                document_type="RUC",
                name=company_name_map.get(r.ruc, r.ruc),
                index=idx,
                total=len(rucs),
                success=r.success,
                elapsed=r.elapsed,
                status=info.status if info else None,
                condition=info.condition if info else None,
                is_valid=info.is_valid if info else False,
                error=r.error,
            )

        with st.spinner(f"Consultando {len(rucs)} empresa(s) en SUNAT…"):
            summary = validate_ruc_batch(rucs, on_item_validated=_on_company_validated)

        elapsed_total = _time.perf_counter() - t_total_start
        finish_sunat_validation(
            total=summary.total,
            valid=summary.valid,
            invalid=summary.invalid,
            errors=summary.errors,
            elapsed_total=elapsed_total,
            entity_type="Empresas",
        )

        results_map = {r.ruc: r for r in summary.results}
        for company in st.session_state.companies:
            result = results_map.get(company["ruc"])
            if result:
                _sync_company_from_result(company, result)

        updated = _persist_sunat_results(results_map)
        _show_batch_summary(summary, db_updated=updated)
        st.rerun()

    st.divider()

    for i, company in enumerate(companies):
        # Badge: usa datos de BD si están disponibles, si no usa validación de sesión
        v: RucValidationResult | None = company.get("validation")
        if v is not None:
            badge = _sunat_badge(v)
        else:
            badge = _badge_from_db(company)

        with st.expander(
            f"{badge}  |  {company['ruc']}  —  {company['business_name']}", expanded=False
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                # Mostrar datos SUNAT desde BD o desde validación de sesión
                has_sunat = company.get("sunat_validated_at") is not None
                info_src = v.info if (v and v.success and v.info) else None

                if info_src:
                    st.markdown(f"**Razón Social SUNAT:** {info_src.business_name}")
                    if info_src.trade_name:
                        st.markdown(f"**Nombre Comercial:** {info_src.trade_name}")
                    st.markdown(f"**Estado:** `{info_src.status}`  |  **Condición:** `{info_src.condition}`")
                    if info_src.fiscal_address:
                        st.markdown(f"**Domicilio Fiscal:** {info_src.fiscal_address}")
                    st.caption(f"Validado el {info_src.validated_at.strftime('%d/%m/%Y %H:%M')}")
                elif has_sunat:
                    st.markdown(f"**Razón Social:** {company['business_name']}")
                    if company.get("trade_name"):
                        st.markdown(f"**Nombre Comercial:** {company['trade_name']}")
                    st.markdown(
                        f"**Estado:** `{company.get('sunat_status', '—')}`  |  "
                        f"**Condición:** `{company.get('sunat_condition', '—')}`"
                    )
                    if company.get("fiscal_address"):
                        st.markdown(f"**Domicilio Fiscal:** {company['fiscal_address']}")
                    validated_at = company.get("sunat_validated_at")
                    if validated_at:
                        try:
                            st.caption(f"Validado el {validated_at.strftime('%d/%m/%Y %H:%M')}")
                        except Exception:
                            st.caption(f"Validado el {validated_at}")
                elif v and not v.success:
                    st.error(f"Error SUNAT: {v.error}")
                else:
                    st.info("Esta empresa no ha sido validada aún. Usa 'Re-validar'.")

            with col2:
                if st.button("🔄 Re-validar", key=f"revalidate_{i}"):
                    with st.spinner(f"Consultando RUC {company['ruc']}…"):
                        result = validate_single_ruc(company["ruc"])
                    _sync_company_from_result(company, result)

                    if result.success and result.info:
                        info = result.info
                        db_error = _db_upsert_company(
                            ruc=info.ruc, business_name=info.business_name,
                            trade_name=info.trade_name, fiscal_address=info.fiscal_address,
                            sunat_status=info.status, sunat_condition=info.condition,
                            sunat_is_valid=info.is_valid, sunat_validated_at=info.validated_at,
                        )
                        if info.is_valid:
                            st.session_state["_company_msg"] = ("success", f"✅ RUC válido — {info.business_name}")
                        else:
                            st.session_state["_company_msg"] = ("warning", f"SUNAT: {info.status} / {info.condition}")
                        if db_error:
                            st.session_state["_company_msg"] = ("warning", f"SUNAT OK pero error BD: {db_error}")
                    else:
                        st.session_state["_company_msg"] = ("error", f"Error SUNAT: {result.error}")
                    st.rerun()

                if st.button("🗑️ Eliminar", key=f"delete_company_{i}"):
                    st.session_state.companies.pop(i)
                    st.rerun()


def _show_batch_summary(summary: BatchRucValidationSummary, db_updated: int = 0) -> None:
    cols = st.columns(4)
    with cols[0]:
        st.metric("✅ Válidos (ACTIVO+HABIDO)", summary.valid)
    with cols[1]:
        st.metric("🟡 Inactivos / No Habidos", summary.invalid)
    with cols[2]:
        st.metric("⚠️ Errores de consulta", summary.errors)
    with cols[3]:
        st.metric("💾 Guardados en BD", db_updated)

    if summary.errors > 0:
        error_rucs = [r.ruc for r in summary.results if not r.success]
        st.warning(f"No se pudo consultar: {', '.join(error_rucs)}")
    if summary.invalid > 0:
        invalid_rucs = [r.ruc for r in summary.results if r.success and r.info and not r.info.is_valid]
        st.error(f"Estado inválido en SUNAT: {', '.join(invalid_rucs)}")


# ─── Socios de negocio ────────────────────────────────────────────────────────

def _load_all_partners_from_db() -> list[dict]:
    """Carga todos los socios de negocio desde BD."""
    try:
        from Persistence.connection import get_conn
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, document_type, document_number, business_name,
                       trade_name, fiscal_address, sunat_status, sunat_condition,
                       sunat_is_valid, sunat_validated_at
                FROM business_partners
                ORDER BY business_name
                """
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def _badge_partner(partner: dict) -> str:
    """Badge de socio basado en campos de BD."""
    if not partner.get("sunat_validated_at"):
        return "— Sin validar"
    status = (partner.get("sunat_status") or "").upper()
    condition = (partner.get("sunat_condition") or "").upper()
    if partner.get("sunat_is_valid"):
        return "✅ Válido (ACTIVO)"
    if "SIN RUC" in status or "NO ENCONTRADO" in status:
        return "❌ Sin RUC en SUNAT"
    if status == "BAJA DEFINITIVA" or status == "BAJA PROVISIONAL":
        return f"❌ {status}"
    if status == "ACTIVO":
        return f"🟡 Activo / {condition}"
    return f"❌ {status or 'Inválido'}"


def _render_partners_validation() -> None:
    # Mostrar mensaje de validación individual si viene de un rerun
    msg = st.session_state.pop("_partner_msg", None)
    if msg:
        level, text = msg
        if level == "success":
            st.success(text)
        elif level == "warning":
            st.warning(text)
        else:
            st.error(text)

    # Recargar socios desde BD en cada render para mantener datos frescos
    partners: list[dict] = _load_all_partners_from_db()

    if not partners:
        st.info(
            "No hay socios de negocio registrados aún. "
            "Se agregan automáticamente al procesar comprobantes."
        )
        return

    # Contar pendientes
    pending = [p for p in partners if not p.get("sunat_validated_at")]
    validated = [p for p in partners if p.get("sunat_validated_at")]

    st.markdown(
        f"**{len(partners)}** socio(s) registrados — "
        f"✅ {len(validated)} validados, ⏳ {len(pending)} pendientes."
    )

    # Botón validar todos los pendientes
    if pending:
        if st.button(
            f"🔍 Validar {len(pending)} socio(s) pendiente(s) en SUNAT",
            type="primary",
            width="stretch",
        ):
            import time as _time
            from console.rich_logger import (
                finish_sunat_validation,
                log_sunat_item,
                start_sunat_validation,
            )

            ruc_list = [
                p["document_number"] for p in pending
                if p["document_type"] == "RUC" and is_valid_ruc_format(p["document_number"])
            ]
            dni_list_nums = [
                p["document_number"] for p in pending
                if p["document_type"] == "DNI" and is_valid_dni_format(p["document_number"])
            ]
            all_docs = ruc_list + dni_list_nums
            doc_type_map = {p["document_number"]: p["document_type"] for p in pending}
            partner_name_map = {p["document_number"]: p.get("business_name", "") for p in pending}
            errors: list[str] = []

            if all_docs:
                start_sunat_validation(len(all_docs), entity_type="Socios de Negocio")
                t_total_start = _time.perf_counter()

                def _on_partner_validated(idx: int, r):
                    info = r.info
                    dt = doc_type_map.get(r.ruc, "RUC")
                    log_sunat_item(
                        document_number=r.ruc,
                        document_type=dt,
                        name=partner_name_map.get(r.ruc, r.ruc),
                        index=idx,
                        total=len(all_docs),
                        success=r.success,
                        elapsed=r.elapsed,
                        status=info.status if info else None,
                        condition=info.condition if info else None,
                        is_valid=info.is_valid if info else False,
                        error=r.error,
                    )

                with st.spinner(f"Consultando {len(all_docs)} documento(s) en SUNAT…"):
                    summary = validate_ruc_batch(all_docs, on_item_validated=_on_partner_validated)

                elapsed_total = _time.perf_counter() - t_total_start
                finish_sunat_validation(
                    total=summary.total,
                    valid=summary.valid,
                    invalid=summary.invalid,
                    errors=summary.errors,
                    elapsed_total=elapsed_total,
                    entity_type="Socios de Negocio",
                )

                try:
                    from datetime import datetime
                    from Persistence.connection import get_conn
                    from Persistence.repositories.business_partner_repo import (
                        update_sunat_info,
                        upsert_business_partner,
                    )
                    with get_conn() as conn:
                        for r in summary.results:
                            dt = doc_type_map.get(r.ruc, "RUC")
                            if r.success and r.info:
                                info = r.info
                                pid = upsert_business_partner(
                                    conn=conn, document_type=dt,
                                    document_number=r.ruc, business_name=info.business_name,
                                )
                                update_sunat_info(
                                    conn=conn, partner_id=pid,
                                    business_name=info.business_name, trade_name=info.trade_name,
                                    fiscal_address=info.fiscal_address, sunat_status=info.status,
                                    sunat_condition=info.condition, sunat_is_valid=info.is_valid,
                                    validated_at=info.validated_at,
                                )
                            elif not r.success:
                                # Guardar también el estado de error o no encontrado en BD
                                name = partner_name_map.get(r.ruc, r.ruc)
                                pid = upsert_business_partner(
                                    conn=conn, document_type=dt,
                                    document_number=r.ruc, business_name=name,
                                )
                                err_msg = "SIN RUC EN SUNAT" if "no tiene RUC" in (r.error or "") else "ERROR CONSULTA"
                                update_sunat_info(
                                    conn=conn, partner_id=pid,
                                    business_name=name, trade_name=None,
                                    fiscal_address=None, sunat_status=err_msg,
                                    sunat_condition="NO REGISTRADO", sunat_is_valid=False,
                                    validated_at=datetime.now(),
                                )
                except Exception as exc:
                    errors.append(f"Error al guardar en BD: {exc}")
                _show_batch_summary(summary)
            else:
                st.warning("No hay documentos con formato válido para consultar SUNAT.")

            for e in errors:
                st.warning(e)

            st.rerun()
    else:
        st.success("Todos los socios ya están validados en SUNAT ✅")

    st.divider()

    # Tabla de todos los socios con estado
    for i, partner in enumerate(partners):
        badge = _badge_partner(partner)
        doc_type = partner.get("document_type", "")
        doc_num = partner.get("document_number", "")

        with st.expander(
            f"{badge}  |  {doc_num}  —  {partner.get('business_name', '—')}",
            expanded=False,
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"**Tipo documento:** `{doc_type}`")
                if partner.get("trade_name"):
                    st.markdown(f"**Nombre Comercial:** {partner['trade_name']}")
                if partner.get("sunat_status"):
                    st.markdown(
                        f"**Estado:** `{partner['sunat_status']}`  |  "
                        f"**Condición:** `{partner.get('sunat_condition', '—')}`"
                    )
                if partner.get("fiscal_address"):
                    st.markdown(f"**Domicilio Fiscal:** {partner['fiscal_address']}")
                validated_at = partner.get("sunat_validated_at")
                if validated_at:
                    try:
                        st.caption(f"Validado el {validated_at.strftime('%d/%m/%Y %H:%M')}")
                    except Exception:
                        st.caption(f"Validado el {validated_at}")
                else:
                    st.info("Sin validar aún en SUNAT.")

            with col2:
                # RUC → validar contra SUNAT (por RUC)
                # DNI → validar contra SUNAT (por Documento)
                can_validate = (
                    (doc_type == "RUC" and is_valid_ruc_format(doc_num)) or
                    (doc_type == "DNI" and is_valid_dni_format(doc_num))
                )

                if can_validate and st.button("🔄 Validar SUNAT", key=f"revalidate_partner_{i}"):
                    with st.spinner(f"Consultando {doc_type} {doc_num} en SUNAT…"):
                        result = validate_single_ruc(doc_num, doc_type)

                    if result.success and result.info:
                        info = result.info
                        db_err = None
                        try:
                            from Persistence.connection import get_conn
                            from Persistence.repositories.business_partner_repo import (
                                update_sunat_info,
                                upsert_business_partner,
                            )
                            with get_conn() as conn:
                                pid = upsert_business_partner(
                                    conn=conn,
                                    document_type=doc_type,
                                    document_number=doc_num,
                                    business_name=info.business_name,
                                )
                                update_sunat_info(
                                    conn=conn, partner_id=pid,
                                    business_name=info.business_name,
                                    trade_name=info.trade_name,
                                    fiscal_address=info.fiscal_address,
                                    sunat_status=info.status,
                                    sunat_condition=info.condition,
                                    sunat_is_valid=info.is_valid,
                                    validated_at=info.validated_at,
                                )
                        except Exception as exc:
                            db_err = str(exc)

                        # Guardar mensaje para mostrarlo tras el rerun
                        if db_err:
                            st.session_state["_partner_msg"] = ("warning", f"SUNAT OK pero error BD: {db_err}")
                        elif info.is_valid:
                            st.session_state["_partner_msg"] = ("success", f"✅ {doc_type} válido — {info.business_name}")
                        else:
                            st.session_state["_partner_msg"] = ("warning", f"SUNAT: {info.status} / {info.condition}")
                    else:
                        st.session_state["_partner_msg"] = ("error", f"Error SUNAT: {result.error}")
                    st.rerun()


# ─── Render principal ──────────────────────────────────────────────────────────

def render_company_manager() -> None:
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
