"""Entidades de dominio para representar los resultados del procesamiento por lote."""

from dataclasses import dataclass, field

from domain.entities.document import Document


@dataclass(slots=True)
class DocumentProcessResult:
    document: Document
    success: bool
    error_message: str | None = None
    execution_time_seconds: float = 0.0


@dataclass(slots=True)
class BatchProcessSummary:
    total_count: int = 0
    processed_count: int = 0
    error_count: int = 0
    total_time_seconds: float = 0.0
    results: list[DocumentProcessResult] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0
