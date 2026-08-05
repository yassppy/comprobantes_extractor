"""Repositorio para la tabla `categories`.

REQ-6: Gestión de categorías sincronizadas desde YAML.
"""

from __future__ import annotations

from typing import Any

import psycopg


def get_all_category_codes(conn: psycopg.Connection) -> set[str]:
    """Retorna el conjunto de códigos que existen actualmente en la BD."""
    rows = conn.execute("SELECT code FROM categories").fetchall()
    return {row["code"] for row in rows}


def upsert_category(
    conn: psycopg.Connection,
    code: str,
    name: str,
    description: str | None,
) -> None:
    """
    Inserta la categoría si no existe, o actualiza name, description y active
    si ya existe. Si la categoría estaba inactiva (fue eliminada del YAML
    previamente) y vuelve a aparecer, se reactiva automáticamente.
    """
    conn.execute(
        """
        INSERT INTO categories (code, name, description, active)
        VALUES (%s, %s, %s, TRUE)
        ON CONFLICT (code) DO UPDATE SET
            name        = EXCLUDED.name,
            description = EXCLUDED.description,
            active      = TRUE,
            updated_at  = NOW()
        """,
        (code, name, description),
    )


def deactivate_categories(conn: psycopg.Connection, codes: set[str]) -> int:
    """
    Marca como inactivas todas las categorías cuyos códigos estén en `codes`.

    REQ-6 R3: categoría eliminada del YAML → active = FALSE.

    Returns:
        Número de filas actualizadas.
    """
    if not codes:
        return 0
    # psycopg admite tuplas directamente para IN (%s) con adaptadores,
    # pero es más seguro construir placeholders explícitos.
    placeholders = ", ".join(["%s"] * len(codes))
    result = conn.execute(
        f"UPDATE categories SET active = FALSE, updated_at = NOW() "  # noqa: S608
        f"WHERE code IN ({placeholders}) AND active = TRUE",
        tuple(codes),
    )
    return result.rowcount


def get_active_categories(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Retorna todas las categorías activas ordenadas por código."""
    return conn.execute(
        "SELECT code, name, description FROM categories "
        "WHERE active = TRUE ORDER BY code"
    ).fetchall()


def get_all_categories(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Retorna todas las categorías (activas e inactivas) ordenadas por código."""
    return conn.execute(
        "SELECT code, name, description, active FROM categories ORDER BY code"
    ).fetchall()
