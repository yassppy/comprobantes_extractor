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

    @staticmethod
    def update_selection(result: SelectDocumentsResult) -> None:
        """
        Actualiza el estado con el resultado de la selección de comprobantes.
        """
        st.session_state.selected_documents = result.valid_documents
        st.session_state.invalid_files = result.invalid_files
        st.session_state.processing_started = False

    @staticmethod
    def clear_selection() -> None:
        """
        Limpia la selección actual.
        """
        st.session_state.selected_documents = []
        st.session_state.invalid_files = []
        st.session_state.processing_started = False

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
