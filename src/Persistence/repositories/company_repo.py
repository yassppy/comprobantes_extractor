"""Repositorio para la tabla `companies`."""

from __future__ import annotations

from typing import Any

import psycopg


def upsert_company(
    conn: psycopg.Connection,
    ruc: str,
    business_name: str,
    trade_name: str | None = None,
    fiscal_address: str | None = None,
    sunat_status: str | None = None,
    sunat_condition: str | None = None,
    sunat_is_valid: bool = False,
    sunat_validated_at=None,
) -> int:
    """
    Inserta o actualiza una empresa por RUC.

    Returns:
        ID de la empresa en la base de datos.
    """
    row = conn.execute(
        """
        INSERT INTO companies (
            ruc, business_name, trade_name, fiscal_address,
            sunat_status, sunat_condition, sunat_is_valid, sunat_validated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ruc) DO UPDATE SET
            business_name      = EXCLUDED.business_name,
            trade_name         = COALESCE(EXCLUDED.trade_name, companies.trade_name),
            fiscal_address     = COALESCE(EXCLUDED.fiscal_address, companies.fiscal_address),
            sunat_status       = COALESCE(EXCLUDED.sunat_status, companies.sunat_status),
            sunat_condition    = COALESCE(EXCLUDED.sunat_condition, companies.sunat_condition),
            sunat_is_valid     = EXCLUDED.sunat_is_valid,
            sunat_validated_at = COALESCE(EXCLUDED.sunat_validated_at, companies.sunat_validated_at),
            updated_at         = NOW()
        RETURNING id
        """,
        (
            ruc, business_name, trade_name, fiscal_address,
            sunat_status, sunat_condition, sunat_is_valid, sunat_validated_at,
        ),
    ).fetchone()
    return row["id"]


def get_company_by_ruc(conn: psycopg.Connection, ruc: str) -> dict[str, Any] | None:
    """Busca una empresa por RUC. Retorna None si no existe."""
    return conn.execute(
        "SELECT * FROM companies WHERE ruc = %s", (ruc,)
    ).fetchone()


def get_all_companies(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Retorna todas las empresas activas."""
    return conn.execute(
        "SELECT * FROM companies WHERE active = TRUE ORDER BY business_name"
    ).fetchall()


def update_sunat_info(
    conn: psycopg.Connection,
    company_id: int,
    business_name: str,
    trade_name: str | None,
    fiscal_address: str | None,
    sunat_status: str,
    sunat_condition: str,
    sunat_is_valid: bool,
    validated_at,
) -> None:
    """Actualiza los campos SUNAT de una empresa existente."""
    conn.execute(
        """
        UPDATE companies SET
            business_name      = %s,
            trade_name         = %s,
            fiscal_address     = %s,
            sunat_status       = %s,
            sunat_condition    = %s,
            sunat_is_valid     = %s,
            sunat_validated_at = %s,
            updated_at         = NOW()
        WHERE id = %s
        """,
        (
            business_name, trade_name, fiscal_address,
            sunat_status, sunat_condition, sunat_is_valid,
            validated_at, company_id,
        ),
    )
