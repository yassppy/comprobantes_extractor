"""Pool de conexiones PostgreSQL usando psycopg3 + python-dotenv.

Lee DATABASE_URL desde el archivo .env ubicado en el mismo directorio
que este módulo (src/.env).

Uso:
    from Persistence.connection import get_conn

    with get_conn() as conn:
        conn.execute("SELECT 1")
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

# Carga variables del .env desde src/
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(_ENV_PATH)

_DATABASE_URL: str | None = os.getenv("DATABASE_URL")


def get_database_url() -> str:
    """Retorna la DATABASE_URL. Lanza error si no está configurada."""
    url = _DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. "
            f"Verifica el archivo .env en: {_ENV_PATH}"
        )
    return url


@contextmanager
def get_conn():
    """
    Context manager que abre y cierra una conexión PostgreSQL.
    Hace commit automático al salir sin error; rollback si hay excepción.

    Uso:
        with get_conn() as conn:
            conn.execute("INSERT ...")
    """
    conn = psycopg.connect(get_database_url(), row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def test_connection() -> bool:
    """
    Prueba la conexión a la base de datos.

    Returns:
        True si la conexión es exitosa, False si falla.
    """
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
