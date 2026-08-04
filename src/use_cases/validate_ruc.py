"""Caso de uso: Validación de documentos (RUC / DNI) contra SUNAT.

- RUC (11 dígitos) → scrape_ruc  → devuelve estado, condición, domicilio
- DNI (8 dígitos)  → scrape_dni  → devuelve RUC asociado, nombre, ubicación, estado
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from infrastructure.sunat.ruc_scraper import SunatRucInfo, scrape_document


def is_valid_ruc_format(value: str | None) -> bool:
    """True si el string tiene exactamente 11 dígitos numéricos."""
    return bool(value and re.match(r"^\d{11}$", str(value).strip()))


def is_valid_dni_format(value: str | None) -> bool:
    """True si el string tiene exactamente 8 dígitos numéricos."""
    return bool(value and re.match(r"^\d{8}$", str(value).strip()))


def can_validate_sunat(document_number: str | None, document_type: str | None) -> bool:
    """True si el documento puede consultarse en SUNAT."""
    if not document_number:
        return False
    dt = (document_type or "").upper()
    if dt == "RUC":
        return is_valid_ruc_format(document_number)
    if dt == "DNI":
        return is_valid_dni_format(document_number)
    # Autodetectar por longitud
    return is_valid_ruc_format(document_number) or is_valid_dni_format(document_number)


@dataclass(slots=True)
class RucValidationResult:
    ruc: str
    success: bool
    info: SunatRucInfo | None = None
    error: str | None = None
    elapsed: float = 0.0  # tiempo de consulta en segundos


@dataclass(slots=True)
class BatchRucValidationSummary:
    total: int = 0
    valid: int = 0
    invalid: int = 0
    errors: int = 0
    results: list[RucValidationResult] = field(default_factory=list)


def validate_single_ruc(document_number: str, document_type: str = "RUC") -> RucValidationResult:
    """
    Consulta un RUC o DNI en SUNAT.

    Args:
        document_number: RUC (11 dígitos) o DNI (8 dígitos).
        document_type:   'RUC' | 'DNI' — si se omite se autodetecta por longitud.

    Returns:
        RucValidationResult con los datos de SUNAT o el error.
    """
    doc = document_number.strip()
    dt = document_type.upper().strip()

    if not can_validate_sunat(doc, dt):
        return RucValidationResult(
            ruc=doc,
            success=False,
            error=(
                f"Formato inválido para SUNAT: se esperan 11 dígitos (RUC) "
                f"u 8 dígitos (DNI), se recibió '{doc}'."
            ),
        )

    try:
        info = scrape_document(doc, dt)
        return RucValidationResult(ruc=doc, success=True, info=info)
    except ValueError as e:
        return RucValidationResult(ruc=doc, success=False, error=str(e))
    except RuntimeError as e:
        return RucValidationResult(ruc=doc, success=False, error=str(e))


def validate_ruc_batch(
    document_list: list[str],
    document_type: str = "RUC",
    on_item_validated: callable | None = None,
) -> BatchRucValidationSummary:
    """
    Valida una lista de documentos contra SUNAT secuencialmente.

    Args:
        document_list: Lista de RUCs o DNIs únicos a validar.
        document_type: Tipo por defecto si no se puede autodetectar.
        on_item_validated: Callback opcional func(index, result) para registrar en tiempo real.
    """
    import time

    summary = BatchRucValidationSummary(total=len(document_list))

    for idx, doc in enumerate(document_list, start=1):
        # Autodetectar tipo según longitud
        dt = "DNI" if is_valid_dni_format(doc) else "RUC"
        t_start = time.perf_counter()
        result = validate_single_ruc(doc, dt)
        result.elapsed = time.perf_counter() - t_start
        summary.results.append(result)

        if not result.success:
            summary.errors += 1
        elif result.info and result.info.is_valid:
            summary.valid += 1
        else:
            summary.invalid += 1

        if on_item_validated:
            try:
                on_item_validated(idx, result)
            except Exception:
                pass

    return summary
