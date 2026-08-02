"""Pruebas unitarias para FileValidator."""

from pathlib import Path

from domain.enums.file_type import FileType
from infrastructure.scanner.file_validator import FileValidator, ValidationResult


def test_file_type_from_extension():
    assert FileType.from_extension("pdf") == FileType.PDF
    assert FileType.from_extension(".PNG") == FileType.PNG
    assert FileType.from_extension("jpg") == FileType.JPG
    assert FileType.from_extension("jpeg") == FileType.JPEG
    assert FileType.from_extension("docx") is None
    assert FileType.from_extension("txt") is None


def test_is_supported_extension():
    assert FileValidator.is_supported_extension("pdf") is True
    assert FileValidator.is_supported_extension("png") is True
    assert FileValidator.is_supported_extension("jpg") is True
    assert FileValidator.is_supported_extension("jpeg") is True
    assert FileValidator.is_supported_extension("exe") is False
    assert FileValidator.is_supported_extension("xlsx") is False


def test_validate_name_and_extension_supported():
    res: ValidationResult = FileValidator.validate_name_and_extension("factura_001.pdf", 1024)
    assert res.is_valid is True
    assert res.file_type == FileType.PDF
    assert res.error_message is None


def test_validate_name_and_extension_unsupported():
    res: ValidationResult = FileValidator.validate_name_and_extension("documento.docx", 2048)
    assert res.is_valid is False
    assert res.file_type is None
    assert res.error_message is not None
    assert "no soportado (.docx)" in res.error_message


def test_validate_file_non_existent(tmp_path: Path):
    non_existent = tmp_path / "comprobante.pdf"
    res = FileValidator.validate_file(non_existent)
    assert res.is_valid is False
    assert "no existe" in res.error_message
