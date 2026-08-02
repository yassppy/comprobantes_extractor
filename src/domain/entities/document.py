from dataclasses import dataclass
from pathlib import Path

from domain.enums.document_status import DocumentStatus
from domain.enums.file_type import FileType


@dataclass(slots=True)
class Document:
    name: str
    path: Path
    file_type: FileType | None
    size: int
    status: DocumentStatus = DocumentStatus.READY
    error_message: str | None = None

    @property
    def formatted_size(self) -> str:
        """Returns human readable file size in KB or MB."""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / (1024 * 1024):.2f} MB"

