"""Componente UI para mostrar el resumen del procesamiento por lote (REQ-2 R3)."""

import streamlit as st

from ui.state import AppState


def render_summary_card() -> None:
    """
    Renderiza el resumen del lote cuando finaliza el procesamiento.
    """
    summary = AppState.get_batch_summary()
    if summary is None:
        return

    st.divider()
    st.subheader("📊 Resumen del Procesamiento por Lote")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Seleccionados", summary.total_count)
    with col2:
        st.metric("Procesados con Éxito", summary.processed_count, delta="🟢 OK" if summary.processed_count > 0 else None)
    with col3:
        st.metric("Errores", summary.error_count, delta=f"⚠️ {summary.error_count}" if summary.error_count > 0 else "0", delta_color="inverse")
    with col4:
        st.metric("Tiempo Total", f"{summary.total_time_seconds:.2f} s")

    if summary.has_errors:
        st.warning(f"Se registraron errores en {summary.error_count} comprobante(s). Los demás continuaron procesándose correctamente.")
        with st.expander("Ver detalles de errores"):
            for res in summary.results:
                if not res.success:
                    st.error(f"❌ **{res.document.name}**: {res.error_message}")
    else:
        st.success("¡Todos los comprobantes fueron procesados exitosamente sin errores!")
