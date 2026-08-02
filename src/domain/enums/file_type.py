from enum import StrEnum


class FileType(StrEnum):
    PDF = "pdf"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"

    @classmethod
    def values(cls) -> set[str]:
        return {member.value for member in cls}

    @classmethod
    def from_extension(cls, extension: str) -> "FileType | None":
        ext = extension.lower().lstrip(".")
        try:
            return cls(ext)
        except ValueError:
            return None

