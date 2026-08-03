"""Extractor del nombre del proveedor (razón social del emisor)."""

from __future__ import annotations

import re

_COMPANY_SUFFIXES = (
    "S.A.C",
    "S.A.",
    "E.I.R.L",
    "EIRL",
    "S.R.L",
    "SRL",
    "SAC",
    "S.A",
)


def extract_supplier_name(text: str, ruc: str | None) -> str | None:
    """
    Busca la razón social del proveedor buscando líneas cerca del RUC.

    Estrategia:
    1. Localiza la línea donde aparece el RUC.
    2. Busca hacia arriba (máx 5 líneas) una que contenga sufijo empresarial.
    3. Fallback: la línea inmediatamente anterior al RUC.
    """
    if not ruc:
        return None

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    ruc_index: int | None = None
    for i, line in enumerate(lines):
        if ruc in line:
            ruc_index = i
            break

    if ruc_index is None:
        return None

    # Buscar hacia arriba una línea con sufijo empresarial
    for i in range(max(0, ruc_index - 5), ruc_index):
        if any(s in lines[i].upper() for s in _COMPANY_SUFFIXES):
            return lines[i]

    # Fallback: línea anterior al RUC
    if ruc_index > 0:
        return lines[ruc_index - 1]

    return lines[0]
