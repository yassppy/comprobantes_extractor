from enum import StrEnum


class DocumentStatus(StrEnum):
    READY = "ready"
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    ERROR = "error"
    UNSUPPORTED = "unsupported"


