"""Componente UI para mostrar el resumen del procesamiento y guardado (REQ-2 R3 / REQ-7)."""

import streamlit as st

from ui.state import AppState


def render_summary_card() -> None:
    """
    Renderiza el resumen del lote cuando finaliza el procesamiento.
    Incluye métricas de extracción y resultado de persistencia en BD.
    """
    summary = AppState.get_batch_summary()
    if summary is None:
        return

    st.divider()
    st.subheader("📊 Resumen del Procesamiento")

    # ── Métricas de extracción ─────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total seleccionados", summary.total_count)
    with col2:
        st.metric(
            "Procesados ✅",
            summary.processed_count,
            delta="OK" if summary.processed_count > 0 else None,
        )
    with col3:
        st.metric(
            "Errores de extracción",
            summary.error_count,
            delta=f"⚠️ {summary.error_count}" if summary.error_count > 0 else None,
            delta_color="inverse",
        )
    with col4:
        st.metric("Tiempo total", f"{summary.total_time_seconds:.2f} s")

    # Detalle de errores de extracción
    if summary.has_errors:
        st.warning(
            f"Se registraron errores en {summary.error_count} comprobante(s). "
            "Los demás continuaron procesándose correctamente."
        )
        with st.expander("Ver detalle de errores de extracción"):
            for res in summary.results:
                if not res.success:
                    st.error(f"❌ **{res.document.name}**: {res.error_message}")
    else:
        st.success("Todos los comprobantes fueron extraídos correctamente.")

    # ── Resultado de persistencia en BD ───────────────────────────────────────
    save_result = AppState.get_save_result()
    if save_result is None:
        return

    st.divider()
    st.subheader("💾 Resultado del Guardado en Base de Datos")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Guardados en BD ✅", save_result.saved)
    with c2:
        st.metric(
            "Duplicados omitidos ⏭️",
            save_result.skipped_duplicates,
            help="Comprobantes ya existentes según su hash SHA-256 (REQ-7 R2).",
        )
    with c3:
        st.metric(
            "Errores al guardar",
            save_result.errors,
            delta=f"⚠️ {save_result.errors}" if save_result.errors > 0 else None,
            delta_color="inverse",
        )

    if save_result.errors > 0:
        with st.expander("Ver detalle de errores al guardar"):
            for detail in save_result.error_details:
                st.error(f"❌ {detail}")

    if save_result.skipped_duplicates > 0:
        st.info(
            f"ℹ️ {save_result.skipped_duplicates} comprobante(s) ya existían en la base de datos "
            "y fueron omitidos para evitar duplicados."
        )

    if save_result.saved > 0 and save_result.errors == 0:
        company = AppState.get_active_company()
        name = company["business_name"] if company else "la empresa"
        st.success(
            f"✅ {save_result.saved} comprobante(s) guardados exitosamente "
            f"para **{name}**."
        )
