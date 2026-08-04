"""Manejo de estado de la aplicación Streamlit (Session State)."""

import streamlit as st

from domain.entities.document import Document
from use_cases.select_documents import SelectDocumentsResult


class AppState:
    @staticmethod
    def initialize() -> None:
        """
        Inicializa las claves en st.session_state si no existen.
        """
        if "selected_documents" not in st.session_state:
            st.session_state.selected_documents = []
        if "invalid_files" not in st.session_state:
            st.session_state.invalid_files = []
        if "processing_started" not in st.session_state:
            st.session_state.processing_started = False
        if "batch_summary" not in st.session_state:
            st.session_state.batch_summary = None
        if "uploader_reset_key" not in st.session_state:
            st.session_state.uploader_reset_key = 0
        if "_clearing" not in st.session_state:
            st.session_state._clearing = False
        if "document_type" not in st.session_state:
            st.session_state.document_type = "PURCHASE"
        if "active_company" not in st.session_state:
            # Dict: {ruc, business_name} | None
            st.session_state.active_company = None
        if "save_result" not in st.session_state:
            st.session_state.save_result = None

    @staticmethod
    def update_selection(result: SelectDocumentsResult) -> None:
        """
        Actualiza el estado con el resultado de la selección de comprobantes.
        """
        st.session_state.selected_documents = result.valid_documents
        st.session_state.invalid_files = result.invalid_files
        st.session_state.processing_started = False
        st.session_state.batch_summary = None

    @staticmethod
    def clear_selection() -> None:
        """
        Limpia la selección actual y resetea el file_uploader.
        """
        st.session_state.selected_documents = []
        st.session_state.invalid_files = []
        st.session_state.processing_started = False
        st.session_state.batch_summary = None
        st.session_state.save_result = None
        # Cambia la key del file_uploader para forzar su reset visual
        st.session_state.uploader_reset_key = st.session_state.get("uploader_reset_key", 0) + 1
        # Marca que se acaba de limpiar para que file_selector no re-cargue
        st.session_state._clearing = True

    @staticmethod
    def set_batch_summary(summary) -> None:
        """
        Guarda el resumen del procesamiento por lote.
        """
        st.session_state.batch_summary = summary
        st.session_state.processing_started = True

    @classmethod
    def get_batch_summary(cls):
        cls.initialize()
        return st.session_state.batch_summary

    @classmethod
    def get_selected_documents(cls) -> list[Document]:
        cls.initialize()
        return st.session_state.selected_documents

    @classmethod
    def get_invalid_files(cls) -> list[tuple[str, str]]:
        cls.initialize()
        return st.session_state.invalid_files

    @classmethod
    def can_start_processing(cls) -> bool:
        """
        R3: Retorna True solo si hay al menos un comprobante válido seleccionado.
        """
        cls.initialize()
        return len(st.session_state.selected_documents) > 0

    @classmethod
    def get_uploader_key(cls) -> str:
        """
        Retorna la key dinámica del file_uploader para forzar su reset al limpiar.
        """
        cls.initialize()
        return f"file_uploader_widget_{st.session_state.uploader_reset_key}"

    @classmethod
    def get_document_type(cls) -> str:
        """Retorna el tipo de operación seleccionado: PURCHASE | SALE."""
        cls.initialize()
        return st.session_state.document_type

    @staticmethod
    def set_document_type(doc_type: str) -> None:
        """Guarda el tipo de operación seleccionado."""
        st.session_state.document_type = doc_type

    @classmethod
    def get_active_company(cls) -> dict | None:
        """Retorna la empresa activa seleccionada para el lote: {ruc, business_name} | None."""
        cls.initialize()
        return st.session_state.active_company

    @staticmethod
    def set_active_company(company: dict | None) -> None:
        """Guarda la empresa activa. Recibe {ruc, business_name} o None."""
        st.session_state.active_company = company

    @classmethod
    def get_save_result(cls):
        """Retorna el resultado del último guardado en BD (SaveResult | None)."""
        cls.initialize()
        return st.session_state.save_result

    @staticmethod
    def set_save_result(result) -> None:
        """Guarda el resultado del guardado en BD."""
        st.session_state.save_result = result

