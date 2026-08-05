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

    # Buscar una línea con sufijo empresarial en las primeras 10 líneas
    for i in range(min(10, len(lines))):
        line = lines[i]
        if any(s in line.upper() for s in _COMPANY_SUFFIXES) and not line.upper().startswith("SEÑOR") and not line.upper().startswith("SENOR"):
            return line

    ruc_index: int | None = None
    if ruc:
        for i, line in enumerate(lines):
            if ruc in line:
                ruc_index = i
                break

    if ruc_index is not None and ruc_index > 0:
        prev_line = lines[ruc_index - 1]
        if not any(k in prev_line.upper() for k in ("FACTURA", "BOLETA", "RUC", "TELEFONO", "FECHA")):
            return prev_line

    return ruc if ruc else (lines[0] if lines else None)
