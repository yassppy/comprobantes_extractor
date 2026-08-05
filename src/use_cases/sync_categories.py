"""Caso de uso: Sincronización de categorías desde YAML → PostgreSQL (REQ-6).

R1: WHEN la aplicación inicie
    THEN SYSTEM SHALL sincronizar automáticamente las categorías del archivo
    YAML con PostgreSQL.

R2: WHEN exista una categoría nueva en el archivo YAML
    THEN SYSTEM SHALL crearla en la base de datos.

R3: WHEN una categoría sea eliminada del YAML
    THEN SYSTEM SHALL marcarla como inactiva.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

# Ruta canónica al archivo de categorías (relativa al repo raíz).
# Se resuelve desde la ubicación de este módulo: src/use_cases/ → ../../resources/
_DEFAULT_YAML_PATH = (
    Path(__file__).parent.parent.parent / "resources" / "categories.yaml"
)


@dataclass(slots=True)
class SyncResult:
    """Resultado de la sincronización."""

    created: int = 0
    updated: int = 0
    deactivated: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    def __str__(self) -> str:
        return (
            f"SyncResult(creadas={self.created}, "
            f"actualizadas={self.updated}, "
            f"desactivadas={self.deactivated}, "
            f"errores={len(self.errors)})"
        )


def _load_yaml(path: Path) -> list[dict]:
    """
    Carga y valida el YAML de categorías.

    Returns:
        Lista de dicts con keys: code, name, description (opcional).

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError:        Si el formato no es válido.
    """
    if not path.exists():
        raise FileNotFoundError(f"Archivo de categorías no encontrado: {path}")

    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "categories" not in data:
        raise ValueError(
            f"El archivo YAML debe tener una clave raíz 'categories'. "
            f"Archivo: {path}"
        )

    entries = data["categories"]
    if not isinstance(entries, list):
        raise ValueError(
            f"'categories' debe ser una lista de entradas. Archivo: {path}"
        )

    return entries


def sync_categories(yaml_path: Path | None = None) -> SyncResult:
    """
    Sincroniza las categorías del archivo YAML con la tabla `categories` en PostgreSQL.

    Pasos:
      1. Carga las entradas del YAML.
      2. Por cada entrada: upsert (INSERT o UPDATE name/description).
      3. Detecta los códigos que ya no están en el YAML y los desactiva (active=FALSE).

    Args:
        yaml_path: Ruta al archivo YAML. Si es None usa la ruta por defecto.

    Returns:
        SyncResult con estadísticas de la operación.
    """
    from Persistence.connection import get_conn
    from Persistence.repositories.category_repo import (
        deactivate_categories,
        get_all_category_codes,
        upsert_category,
    )

    path = yaml_path or _DEFAULT_YAML_PATH
    result = SyncResult()

    # ── 1. Cargar YAML ────────────────────────────────────────────────────────
    try:
        entries = _load_yaml(path)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Error al cargar categorías: %s", exc)
        result.errors.append(str(exc))
        return result

    # ── 2 & 3. Sincronizar con la BD ─────────────────────────────────────────
    yaml_codes: set[str] = set()

    try:
        with get_conn() as conn:
            # Códigos existentes en la BD antes de sincronizar
            db_codes = get_all_category_codes(conn)

            for entry in entries:
                code = str(entry.get("code", "")).strip()
                name = str(entry.get("name", "")).strip()
                description_raw = entry.get("description")
                description = str(description_raw).strip() if description_raw else None

                # Validaciones básicas
                if not code:
                    msg = f"Entrada sin 'code' ignorada: {entry}"
                    logger.warning(msg)
                    result.errors.append(msg)
                    continue

                if not name:
                    msg = f"Categoría '{code}' sin 'name' ignorada."
                    logger.warning(msg)
                    result.errors.append(msg)
                    continue

                if len(code) > 20:
                    msg = f"Código '{code}' supera los 20 caracteres; ignorado."
                    logger.warning(msg)
                    result.errors.append(msg)
                    continue

                yaml_codes.add(code)

                # R2: nueva → INSERT; existente → UPDATE (reactiva si estaba inactiva)
                upsert_category(conn, code, name, description)

                if code in db_codes:
                    result.updated += 1
                    logger.debug("Categoría actualizada/reactivada: %s", code)
                else:
                    result.created += 1
                    logger.info("Categoría creada: %s — %s", code, name)

            # R3: desactivar las que ya no están en el YAML
            removed_codes = db_codes - yaml_codes
            if removed_codes:
                deactivated = deactivate_categories(conn, removed_codes)
                result.deactivated = deactivated
                for code in removed_codes:
                    logger.info("Categoría desactivada (no encontrada en YAML): %s", code)

    except Exception as exc:  # noqa: BLE001
        logger.error("Error al sincronizar categorías con la BD: %s", exc)
        result.errors.append(f"Error de BD: {exc}")

    logger.info("Sincronización completada → %s", result)
    return result
