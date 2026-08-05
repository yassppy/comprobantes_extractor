"""Componente UI para la clasificación automática por lotes (REQ-5).

Permite al contador:
  - Seleccionar el tamaño del lote (10 a 30 documentos).
  - Iniciar la clasificación con Ollama.
  - Ver progreso en tiempo real dentro de Streamlit.
  - Ver el resumen final con velocidad y resultados.
"""

from __future__ import annotations

import streamlit as st


def render_classify_panel() -> None:
    """Renderiza el panel completo de clasificación automática."""

    st.subheader("🤖 Clasificación Automática con Ollama")
    st.markdown(
        "Asigna categorías a los comprobantes que aún no tienen ninguna, "
        "usando el modelo de lenguaje local configurado en `.env`."
    )

    # ── Configuración del lote ─────────────────────────────────────────────
    col_cfg1, col_cfg2, col_cfg3 = st.columns([1, 1, 2], gap="small")

    with col_cfg1:
        batch_size = st.slider(
            "Tamaño del lote",
            min_value=10,
            max_value=30,
            value=10,
            step=5,
            help="Cantidad de comprobantes a clasificar por ejecución. "
                 "Aumenta el lote para medir velocidad.",
            key="classify_batch_size",
        )

    with col_cfg2:
        # Filtro por empresa activa — por defecto la empresa seleccionada en el sidebar
        from ui.state import AppState as _AppState
        companies: list[dict] = st.session_state.get("companies", [])

        company_options: dict[str, int | None] = {}
        for c in companies:
            company_options[f"{c['ruc']} — {c['business_name']}"] = c.get("id")
        company_options["Todas las empresas"] = None

        # Preseleccionar la empresa activa del sidebar
        active = _AppState.get_active_company()
        default_label = "Todas las empresas"
        if active:
            candidate = f"{active['ruc']} — {active['business_name']}"
            if candidate in company_options:
                default_label = candidate

        label_list = list(company_options.keys())
        selected_company_label = st.selectbox(
            "Empresa",
            options=label_list,
            index=label_list.index(default_label),
            key="classify_company_filter",
        )
        company_id_filter: int | None = company_options[selected_company_label]

    with col_cfg3:
        st.caption(" ")  # espaciado visual
        st.info(
            f"Se cargarán hasta **{batch_size}** comprobantes sin categoría. "
            "Los resultados se guardan automáticamente en PostgreSQL.",
            icon="ℹ️",
        )

    st.divider()

    # ── Estado de la sesión para resultados ────────────────────────────────
    if "classify_result" not in st.session_state:
        st.session_state.classify_result = None
    if "classify_items_preview" not in st.session_state:
        st.session_state.classify_items_preview = None

    # ── Botones de acción ──────────────────────────────────────────────────
    col_btn1, col_btn2, col_spacer = st.columns([1, 1, 3], gap="small")

    with col_btn1:
        btn_preview = st.button(
            "🔎 Ver pendientes",
            help="Muestra los comprobantes sin categoría disponibles para clasificar.",
            key="btn_classify_preview",
        )

    with col_btn2:
        btn_run = st.button(
            "⚡ Clasificar ahora",
            type="primary",
            help="Envía las descripciones a Ollama y guarda los códigos de categoría.",
            key="btn_classify_run",
        )

    # ── Vista previa de pendientes ─────────────────────────────────────────
    if btn_preview:
        _load_and_show_preview(batch_size, company_id_filter)

    # ── Ejecutar clasificación ─────────────────────────────────────────────
    if btn_run:
        _run_classification(batch_size, company_id_filter)

    # ── Mostrar resultado previo si existe ─────────────────────────────────
    elif st.session_state.classify_result is not None:
        _render_result(st.session_state.classify_result)


# ─── Helpers privados ──────────────────────────────────────────────────────────

def _load_and_show_preview(batch_size: int, company_id: int | None) -> None:
    """Carga y muestra los documentos sin categoría disponibles."""
    from use_cases.classify_batch import load_unclassified_documents

    try:
        items = load_unclassified_documents(limit=batch_size, company_id=company_id)
    except Exception as exc:
        st.error(f"❌ No se pudo conectar a la BD: {exc}")
        return

    st.session_state.classify_items_preview = items

    if not items:
        st.success("✅ Todos los comprobantes ya tienen categoría asignada.")
        return

    st.caption(f"**{len(items)}** comprobante(s) sin categoría:")
    rows = [
        {"#": i + 1, "Doc ID": it.document_id, "Descripción": it.description[:100]}
        for i, it in enumerate(items)
    ]
    st.dataframe(rows, hide_index=True, width="stretch")


def _run_classification(batch_size: int, company_id: int | None) -> None:
    """Ejecuta la clasificación y muestra progreso en tiempo real."""
    from use_cases.classify_batch import (
        ClassifyItemResult,
        classify_batch,
        load_unclassified_documents,
    )

    try:
        items = load_unclassified_documents(limit=batch_size, company_id=company_id)
    except Exception as exc:
        st.error(f"❌ No se pudo conectar a la BD: {exc}")
        return

    if not items:
        st.success("✅ No hay comprobantes pendientes de clasificar.")
        return

    total = len(items)
    st.info(f"🚀 Clasificando **{total}** comprobante(s) en lotes de {batch_size}…")

    progress_bar = st.progress(0, text="Conectando con Ollama…")
    status_placeholder = st.empty()
    results_placeholder = st.empty()
    live_rows: list[dict] = []

    def on_item_done(res: ClassifyItemResult, idx: int, tot: int) -> None:
        """Callback que actualiza la UI tras cada documento clasificado."""
        progress_bar.progress(idx / tot, text=f"Documento {idx} de {tot}…")

        if res.error:
            icon, cat_display = "❌", f"Error: {res.error[:50]}"
        elif res.category_code:
            icon, cat_display = "✅", res.category_code
        else:
            icon, cat_display = "⚠️", "SIN_CATEGORIA"

        live_rows.append({
            "#": idx,
            "Doc ID": res.document_id,
            "Descripción": res.description[:70] if res.description else "—",
            "Categoría": cat_display,
            "Tiempo (s)": f"{res.elapsed_seconds:.2f}",
            "": icon,
        })
        results_placeholder.dataframe(live_rows, hide_index=True, width="stretch")
        status_placeholder.markdown(
            f"⚙️ Procesando `doc#{res.document_id}` → "
            f"**{res.category_code or 'SIN_CATEGORIA'}** "
            f"({res.elapsed_seconds:.2f}s)"
        )

    try:
        result = classify_batch(
            items=items,
            batch_size=batch_size,
            save_to_db=True,
            progress_callback=on_item_done,
        )
    except Exception as exc:
        progress_bar.empty()
        status_placeholder.empty()
        st.error(f"❌ Error durante la clasificación: {exc}")
        return

    progress_bar.empty()
    status_placeholder.empty()

    st.session_state.classify_result = result
    _render_result(result)


def _render_result(result) -> None:
    """Muestra el resumen del resultado de clasificación."""
    st.divider()
    st.subheader("📊 Resultado de la Clasificación")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total", result.total)
    with col2:
        st.metric("Clasificados ✅", result.classified)
    with col3:
        st.metric("Sin categoría ⚠️", result.total - result.classified - result.skipped - result.errors)
    with col4:
        st.metric("Omitidos ⏭️", result.skipped, help="Sin descripción disponible")
    with col5:
        st.metric("Errores ❌", result.errors)

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.metric("⏱ Tiempo total", f"{result.total_seconds:.2f} s")
    with col_t2:
        if result.avg_seconds > 0:
            st.metric("⏱ Promedio por doc", f"{result.avg_seconds:.2f} s")

    if result.results:
        with st.expander("📋 Ver detalle completo", expanded=False):
            rows = []
            for r in result.results:
                if r.error:
                    icon, cat = "❌", f"Error: {r.error[:60]}"
                elif r.category_code:
                    icon, cat = "✅", r.category_code
                else:
                    icon, cat = "⚠️", "SIN_CATEGORIA"
                rows.append({
                    "": icon,
                    "Doc ID": r.document_id,
                    "Descripción": r.description[:80] if r.description else "—",
                    "Categoría asignada": cat,
                    "Tiempo (s)": f"{r.elapsed_seconds:.2f}" if r.elapsed_seconds else "—",
                })
            st.dataframe(rows, hide_index=True, width="stretch")

    if result.errors > 0:
        st.warning(
            f"⚠️ {result.errors} documento(s) no pudieron clasificarse por error de conexión "
            "con Ollama. Verifica que el servicio esté activo y que BASE_URL sea correcta en `.env`."
        )
    elif result.classified > 0:
        st.success(
            f"✅ {result.classified} comprobante(s) clasificados y guardados en la base de datos."
        )
