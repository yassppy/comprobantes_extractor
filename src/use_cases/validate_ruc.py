"""Caso de uso: Validación de RUC contra SUNAT (REQ-4).

Aplica a cualquier entidad con RUC de 11 dígitos:
  - companies         (empresas del contador)
  - business_partners (proveedores/clientes extraídos de comprobantes)

Los DNI (8 dígitos) y 'VENTA MENOR' se omiten — SUNAT no los valida.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from infrastructure.sunat.ruc_scraper import SunatRucInfo, scrape_ruc


def is_valid_ruc_format(value: str | None) -> bool:
    """True si el string tiene exactamente 11 dígitos numéricos."""
    return bool(value and re.match(r"^\d{11}$", str(value).strip()))


@dataclass(slots=True)
class RucValidationResult:
    ruc: str
    success: bool
    info: SunatRucInfo | None = None
    error: str | None = None


@dataclass(slots=True)
class BatchRucValidationSummary:
    total: int = 0
    valid: int = 0        # ACTIVO + HABIDO
    invalid: int = 0      # ACTIVO pero NO HABIDO, o BAJA, etc.
    errors: int = 0       # No se pudo consultar SUNAT
    results: list[RucValidationResult] = field(default_factory=list)


def validate_single_ruc(ruc: str) -> RucValidationResult:
    """
    Consulta un RUC en SUNAT y retorna el resultado.

    Args:
        ruc: Número de RUC de 11 dígitos.

    Returns:
        RucValidationResult con los datos de SUNAT o el error.
    """
    if not is_valid_ruc_format(ruc):
        return RucValidationResult(
            ruc=ruc,
            success=False,
            error=f"Formato inválido: se esperan 11 dígitos, se recibió '{ruc}'.",
        )

    try:
        info = scrape_ruc(ruc)
        return RucValidationResult(ruc=ruc, success=True, info=info)
    except ValueError as e:
        return RucValidationResult(ruc=ruc, success=False, error=str(e))
    except RuntimeError as e:
        return RucValidationResult(ruc=ruc, success=False, error=str(e))


def validate_ruc_batch(ruc_list: list[str]) -> BatchRucValidationSummary:
    """
    Valida una lista de RUCs contra SUNAT secuencialmente.

    Args:
        ruc_list: Lista de RUCs únicos a validar.

    Returns:
        BatchRucValidationSummary con todos los resultados.
    """
    summary = BatchRucValidationSummary(total=len(ruc_list))

    for ruc in ruc_list:
        result = validate_single_ruc(ruc)
        summary.results.append(result)

        if not result.success:
            summary.errors += 1
        elif result.info and result.info.is_valid:
            summary.valid += 1
        else:
            summary.invalid += 1

    return summary
