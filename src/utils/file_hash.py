"""Utilidad para calcular el hash SHA-256 de un archivo (REQ-7 R2).

El hash se usa como clave única en `documents.file_hash` para evitar
almacenar el mismo comprobante más de una vez.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_sha256(path: Path) -> str:
    """
    Calcula el SHA-256 de un archivo en disco.

    Args:
        path: Ruta al archivo.

    Returns:
        Hash hexadecimal de 64 caracteres.

    Raises:
        FileNotFoundError: Si el archivo no existe.
    """
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    """Calcula el SHA-256 de bytes en memoria."""
    return hashlib.sha256(data).hexdigest()
