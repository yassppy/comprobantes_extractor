from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from domain.enums.document_status import DocumentStatus
from domain.enums.document_type import DocumentType
from domain.enums.file_type import FileType


@dataclass(slots=True)
class Document:
    name: str
    path: Path
    file_type: FileType | None
    size: int
    status: DocumentStatus = DocumentStatus.READY
    error_message: str | None = None
    document_type: DocumentType = DocumentType.PURCHASE
    extracted_data: object | None = None  # ExtractedData — evita import circular

    @property
    def formatted_size(self) -> str:
        """Returns human readable file size in KB or MB."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / (1024 * 1024):.2f} MB"

    @property
    def is_image(self) -> bool:
        """True si el comprobante es imagen (PNG, JPG, JPEG)."""
        return self.file_type in {FileType.PNG, FileType.JPG, FileType.JPEG}

    @property
    def is_pdf(self) -> bool:
        """True si el comprobante es PDF."""
        return self.file_type == FileType.PDF

