"""Responsabilidad: verifica si este archivo puede procesarse"""

from dataclasses import dataclass
from pathlib import Path

from domain.enums.file_type import FileType


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    file_type: FileType | None = None
    error_message: str | None = None


class FileValidator:
    @staticmethod
    def is_supported(path: Path) -> bool:
        """
        Verifica si el archivo existe y su extensión es soportada.
        """
        if not path.is_file():
            return False

        extension = path.suffix.lower().lstrip(".")
        return extension in FileType.values()

    @staticmethod
    def is_supported_extension(extension: str) -> bool:
        """
        Verifica si una extensión dada es soportada.
        """
        clean_ext = extension.lower().lstrip(".")
        return clean_ext in FileType.values()

    @classmethod
    def validate_file(cls, path: Path) -> ValidationResult:
        """
        Valida un archivo existente en el sistema de archivos.
        """
        if not path.exists():
            return ValidationResult(
                is_valid=False,
                error_message=f"El archivo '{path.name}' no existe."
            )

        if not path.is_file():
            return ValidationResult(
                is_valid=False,
                error_message=f"'{path.name}' no es un archivo válido."
            )

        extension = path.suffix.lower().lstrip(".")
        file_type = FileType.from_extension(extension)

        if not file_type:
            supported_exts = ", ".join(f".{ext}" for ext in sorted(FileType.values()))
            return ValidationResult(
                is_valid=False,
                error_message=f"El archivo '{path.name}' tiene un formato no soportado (.{extension}). Formatos soportados: {supported_exts}."
            )

        return ValidationResult(
            is_valid=True,
            file_type=file_type
        )

    @classmethod
    def validate_name_and_extension(cls, name: str, size: int) -> ValidationResult:
        """
        Valida un archivo a partir de su nombre y tamaño (para subidas de archivos en memoria).
        """
        extension = name.split(".")[-1].lower() if "." in name else ""
        file_type = FileType.from_extension(extension)

        if not file_type:
            supported_exts = ", ".join(f".{ext}" for ext in sorted(FileType.values()))
            return ValidationResult(
                is_valid=False,
                error_message=f"El archivo '{name}' tiene un formato no soportado (.{extension}). Formatos soportados: {supported_exts}."
            )

        return ValidationResult(
            is_valid=True,
            file_type=file_type
        )

