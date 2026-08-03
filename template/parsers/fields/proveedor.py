"""Extractor del nombre del proveedor."""

from __future__ import annotations

import re

# Sufijos legales peruanos que identifican una empresa en el texto
_SUFIJOS_EMPRESA = (
    "S.A.C",
    "S.A.",
    "E.I.R.L",
    "EIRL",
    "S.R.L",
    "SRL",
    "SAC",
    "S.A",
)


def extraer_proveedor(texto: str, ruc: str | None) -> str | None:
    """
    Busca la razón social del proveedor buscando líneas cerca del RUC.

    Estrategia:
    1. Localiza la línea donde aparece el RUC.
    2. Busca hacia arriba (máx 5 líneas) una que contenga sufijo empresarial.
    3. Fallback: la línea inmediatamente anterior al RUC.
    """
    if not ruc:
        return None

    lineas = [l.strip() for l in texto.splitlines() if l.strip()]

    indice_ruc: int | None = None
    for i, linea in enumerate(lineas):
        if ruc in linea:
            indice_ruc = i
            break

    if indice_ruc is None:
        return None

    # Buscar hacia arriba una línea con sufijo empresarial
    for i in range(max(0, indice_ruc - 5), indice_ruc):
        if any(s in lineas[i].upper() for s in _SUFIJOS_EMPRESA):
            return lineas[i]

    # Fallback: línea anterior al RUC
    if indice_ruc > 0:
        return lineas[indice_ruc - 1]

    return lineas[0]
