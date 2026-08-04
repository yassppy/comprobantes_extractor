"""Repositorio para la tabla `business_partners`."""

from __future__ import annotations

from typing import Any

import psycopg


def upsert_business_partner(
    conn: psycopg.Connection,
    document_type: str,       # 'RUC' | 'DNI' | 'VENTA MENOR'
    document_number: str,
    business_name: str,
) -> int:
    """
    Inserta o actualiza un socio de negocio por número de documento.
    Solo actualiza business_name si el existente estaba vacío o es diferente.

    Returns:
        ID del business_partner.
    """
    row = conn.execute(
        """
        INSERT INTO business_partners (document_type, document_number, business_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (document_number) DO UPDATE SET
            business_name = CASE
                WHEN business_partners.business_name = ''
                THEN EXCLUDED.business_name
                ELSE business_partners.business_name
            END,
            updated_at = NOW()
        RETURNING id
        """,
        (document_type, document_number, business_name),
    ).fetchone()
    return row["id"]


def update_sunat_info(
    conn: psycopg.Connection,
    partner_id: int,
    business_name: str,
    trade_name: str | None,
    fiscal_address: str | None,
    sunat_status: str,
    sunat_condition: str,
    sunat_is_valid: bool,
    validated_at,
) -> None:
    """Actualiza los campos SUNAT de un socio de negocio."""
    conn.execute(
        """
        UPDATE business_partners SET
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
            validated_at, partner_id,
        ),
    )


def get_by_document_number(
    conn: psycopg.Connection, document_number: str
) -> dict[str, Any] | None:
    """Busca un socio por número de documento."""
    return conn.execute(
        "SELECT * FROM business_partners WHERE document_number = %s",
        (document_number,),
    ).fetchone()
