"""Repositorio para la tabla `processing_runs`."""

from __future__ import annotations

import psycopg


def create_run(conn: psycopg.Connection, company_id: int, total_files: int) -> int:
    """
    Crea una nueva ejecución con estado RUNNING.

    Returns:
        ID del processing_run creado.
    """
    row = conn.execute(
        """
        INSERT INTO processing_runs (company_id, total_files, status)
        VALUES (%s, %s, 'RUNNING')
        RETURNING id
        """,
        (company_id, total_files),
    ).fetchone()
    return row["id"]


def complete_run(
    conn: psycopg.Connection,
    run_id: int,
    processed_files: int,
    failed_files: int,
    duration_seconds: int,
) -> None:
    """
    Marca la ejecución como COMPLETED o FAILED según si hubo errores.
    """
    status = "FAILED" if failed_files > 0 else "COMPLETED"
    conn.execute(
        """
        UPDATE processing_runs SET
            finished_at      = NOW(),
            processed_files  = %s,
            failed_files     = %s,
            duration_seconds = %s,
            status           = %s
        WHERE id = %s
        """,
        (processed_files, failed_files, duration_seconds, status, run_id),
    )
