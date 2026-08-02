"""Responsabilidad: escanea un directorio o conjunto de archivos y genera las entidades Document."""

from dataclasses import dataclass, field
from pathlib import Path

from domain.entities.document import Document
from domain.enums.document_status import DocumentStatus
from infrastructure.scanner.file_validator import FileValidator, ValidationResult


@dataclass(slots=True)
class ScanResult:
    valid_documents: list[Document] = field(default_factory=list)
    invalid_files: list[tuple[str, str]] = field(default_factory=list)  # List of (filename, error_message)


class DirectoryScanner:
    def __init__(self, validator: type[FileValidator] = FileValidator) -> None:
        self.validator = validator

    def scan_directory(self, dir_path: Path, recursive: bool = False) -> ScanResult:
        """
        Escanea una carpeta en búsqueda de archivos de comprobantes.
        """
        result = ScanResult()

        if not dir_path.exists() or not dir_path.is_dir():
            result.invalid_files.append((dir_path.name, f"La carpeta '{dir_path}' no existe o no es un directorio."))
            return result

        pattern = "**/*" if recursive else "*"
        entries = [p for p in dir_path.glob(pattern) if p.is_file()]

        for path in entries:
            self._process_path(path, result)

        return result

    def scan_paths(self, paths: list[Path]) -> ScanResult:
        """
        Escanea una lista de rutas de archivos.
        """
        result = ScanResult()
        for path in paths:
            self._process_path(path, result)
        return result

    def _process_path(self, path: Path, result: ScanResult) -> None:
        validation: ValidationResult = self.validator.validate_file(path)
        if validation.is_valid:
            size = path.stat().st_size if path.exists() else 0
            doc = Document(
                name=path.name,
                path=path,
                file_type=validation.file_type,
                size=size,
                status=DocumentStatus.READY
            )
            result.valid_documents.append(doc)
        else:
            error_msg = validation.error_message or f"El archivo '{path.name}' no puede procesarse."
            result.invalid_files.append((path.name, error_msg))
