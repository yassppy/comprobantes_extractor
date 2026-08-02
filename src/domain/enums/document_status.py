from enum import StrEnum


class DocumentStatus(StrEnum):
    READY = "ready"
    PENDING = "pending"
    ERROR = "error"
    UNSUPPORTED = "unsupported"

