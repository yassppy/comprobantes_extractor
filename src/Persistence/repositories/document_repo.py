"""Repositorio para la tabla `documents`."""

from __future__ import annotations

from datetime import date
from typing import Any

import psycopg


def hash_exists(conn: psycopg.Connection, file_hash: str) -> bool:
    """
    REQ-7 R2: Verifica si el hash del archivo ya existe en la BD.
    Evita almacenar el mismo comprobante dos veces.
    """
    row = conn.execute(
        "SELECT 1 FROM documents WHERE file_hash = %s LIMIT 1",
        (file_hash,),
    ).fetchone()
    return row is not None


def insert_document(
    conn: psycopg.Connection,
    processing_run_id: int,
    company_id: int,
    business_partner_id: int | None,
    document_type: str,       # SALE | PURCHASE
    source_type: str,         # PDF | IMAGE
    invoice_type: str | None,
    issue_date: date | None,
    currency: str | None,
    series: str | None,
    number: str | None,
    subtotal: float | None,
    igv: float | None,
    total: float | None,
    description: str | None,
    file_name: str,
    file_path: str,
    file_hash: str,
    ocr_engine: str | None,
    status: str,              # PROCESSED | ERROR
) -> int:
    """
    Inserta un documento procesado en la base de datos.

    Returns:
        ID del documento insertado.

    Raises:
        psycopg.errors.UniqueViolation: Si el file_hash ya existe (duplicado).
    """
    row = conn.execute(
        """
        INSERT INTO documents (
            processing_run_id, company_id, business_partner_id,
            document_type, source_type,
            invoice_type, issue_date, currency, series, number,
            subtotal, igv, total, description,
            file_name, file_path, file_hash, ocr_engine, status
        ) VALUES (
            %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        RETURNING id
        """,
        (
            processing_run_id, company_id, business_partner_id,
            document_type, source_type,
            invoice_type, issue_date, currency, series, number,
            subtotal, igv, total, description,
            file_name, file_path, file_hash, ocr_engine, status,
        ),
    ).fetchone()
    return row["id"]


def get_documents_by_run(
    conn: psycopg.Connection, run_id: int
) -> list[dict[str, Any]]:
    """Retorna todos los documentos de una ejecución."""
    return conn.execute(
        "SELECT * FROM documents WHERE processing_run_id = %s ORDER BY id",
        (run_id,),
    ).fetchall()


def search_documents(
    conn: psycopg.Connection,
    search_query: str | None = None,
    document_type: str | None = None,
    year: int | None = None,
    month: int | None = None,
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """
    Busca comprobantes almacenados en la BD con filtros y paginación.

    Args:
        search_query:  Búsqueda por cliente, proveedor, RUC/DNI o serie-número.
        document_type: 'PURCHASE' (compras), 'SALE' (ventas) o None (todos).
        year:          Año de emisión (ej. 2026).
        month:         Mes de emisión (1-12).
        limit:         Cantidad de registros por página.
        offset:        Desplazamiento para paginación.

    Returns:
        Tupla con (lista de registros, total de coincidencias).
    """
    where_clauses: list[str] = ["1=1"]
    params: list[Any] = []

    if document_type and document_type != "ALL":
        where_clauses.append("d.document_type = %s")
        params.append(document_type)

    if year:
        where_clauses.append("EXTRACT(YEAR FROM d.issue_date) = %s")
        params.append(year)

    if month:
        where_clauses.append("EXTRACT(MONTH FROM d.issue_date) = %s")
        params.append(month)

    if search_query and search_query.strip():
        q = f"%{search_query.strip()}%"
        where_clauses.append(
            "(d.series ILIKE %s OR d.number ILIKE %s OR "
            "CONCAT(d.series, '-', d.number) ILIKE %s OR "
            "bp.document_number ILIKE %s OR bp.business_name ILIKE %s OR "
            "d.file_name ILIKE %s)"
        )
        params.extend([q, q, q, q, q, q])

    where_sql = " AND ".join(where_clauses)

    count_sql = f"""
        SELECT COUNT(*) as total
        FROM documents d
        LEFT JOIN business_partners bp ON d.business_partner_id = bp.id
        WHERE {where_sql}
    """
    total_row = conn.execute(count_sql, params).fetchone()
    total_count = total_row["total"] if total_row else 0

    query_sql = f"""
        SELECT
            d.id,
            d.file_name,
            d.document_type,
            d.invoice_type,
            d.series,
            d.number,
            d.issue_date,
            d.currency,
            d.subtotal,
            d.igv,
            d.total,
            d.description,
            d.ocr_engine,
            d.status,
            bp.document_number AS partner_doc,
            bp.business_name AS partner_name,
            bp.document_type AS partner_doc_type
        FROM documents d
        LEFT JOIN business_partners bp ON d.business_partner_id = bp.id
        WHERE {where_sql}
        ORDER BY d.issue_date DESC NULLS LAST, d.id DESC
        LIMIT %s OFFSET %s
    """
    exec_params = list(params) + [limit, offset]
    rows = conn.execute(query_sql, exec_params).fetchall()

    return rows, total_count
