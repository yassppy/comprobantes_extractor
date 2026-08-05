"""Use case: Selección de comprobantes para procesamiento (REQ-1 / HU01-select-documents)."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from domain.entities.document import Document
from domain.enums.document_status import DocumentStatus
from infrastructure.scanner.directory_scanner import DirectoryScanner
from infrastructure.scanner.file_validator import FileValidator, ValidationResult


class UploadedFileProtocol(Protocol):
    name: str
    size: int


@dataclass(slots=True)
class SelectDocumentsResult:
    valid_documents: list[Document] = field(default_factory=list)
    invalid_files: list[tuple[str, str]] = field(default_factory=list)  # (filename, reason)

    @property
    def total_count(self) -> int:
        return len(self.valid_documents) + len(self.invalid_files)

    @property
    def can_start_processing(self) -> bool:
        """
        R3: Impide iniciar el procesamiento si no se selecciona ningún archivo válido.
        """
        return len(self.valid_documents) > 0


class SelectDocumentsUseCase:
    def __init__(self, scanner: DirectoryScanner | None = None) -> None:
        self.scanner = scanner or DirectoryScanner()

    def execute_from_paths(self, file_paths: list[Path]) -> SelectDocumentsResult:
        """
        Procesa una lista de rutas locales de archivos.
        """
        scan_res = self.scanner.scan_paths(file_paths)
        return SelectDocumentsResult(
            valid_documents=scan_res.valid_documents,
            invalid_files=scan_res.invalid_files
        )

    def execute_from_directory(self, dir_path: Path, recursive: bool = False) -> SelectDocumentsResult:
        """
        Procesa una carpeta local.
        """
        scan_res = self.scanner.scan_directory(dir_path, recursive=recursive)
        return SelectDocumentsResult(
            valid_documents=scan_res.valid_documents,
            invalid_files=scan_res.invalid_files
        )

    def execute_from_uploaded_files(self, uploaded_files: list[Any]) -> SelectDocumentsResult:
        """
        Procesa una lista de archivos subidos desde la interfaz (ej. Streamlit file_uploader).
        """
        result = SelectDocumentsResult()

        for file_obj in uploaded_files:
            name = getattr(file_obj, "name", "archivo_desconocido")
            size = getattr(file_obj, "size", 0)

            validation: ValidationResult = FileValidator.validate_name_and_extension(name, size)

            if validation.is_valid:
                doc = Document(
                    name=name,
                    path=Path(name),
                    file_type=validation.file_type,
                    size=size,
                    status=DocumentStatus.READY
                )
                result.valid_documents.append(doc)
            else:
                error_msg = validation.error_message or f"El archivo '{name}' no puede procesarse."
                result.invalid_files.append((name, error_msg))

        return result
