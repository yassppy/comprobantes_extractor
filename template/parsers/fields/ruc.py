"""Extractor del RUC del proveedor (emisor) del comprobante."""

from __future__ import annotations

import re


def extraer_ruc(texto: str) -> str | None:
    """
    Extrae el RUC del proveedor/emisor del comprobante.

    Estrategia:
    1. Busca el RUC explícito en el bloque de cabecera del emisor
       (antes de la línea 'Señor(es)' o 'Adquiriente').
    2. Fallback: primer RUC de empresa (20...) en el texto.
    3. Último fallback: primer RUC de persona natural (10...).
    """
    lineas = texto.splitlines()

    # Detectar hasta dónde llega el bloque del emisor
    # (antes de la sección "Señor(es)" que marca el inicio del receptor)
    bloque_emisor: list[str] = []
    for linea in lineas:
        if re.search(r"se(ñ|n)or(es)?\s*[:(]", linea, re.IGNORECASE):
            break
        bloque_emisor.append(linea)

    texto_emisor = "\n".join(bloque_emisor) if bloque_emisor else texto

    # 1. RUC explícito con etiqueta "RUC:" en bloque emisor
    m = re.search(r"\bRUC\s*:?\s*(\d{11})\b", texto_emisor, re.IGNORECASE)
    if m:
        return m.group(1)

    # 2. Cualquier secuencia de 11 dígitos que comience con 10 o 20 en el bloque emisor
    rucs = re.findall(r"\b((?:20|10)\d{9})\b", texto_emisor)
    if rucs:
        # Preferir RUC de empresa (20...)
        for r in rucs:
            if r.startswith("20"):
                return r
        return rucs[0]

    # 3. Fallback: buscar en todo el texto
    rucs_total = re.findall(r"\b((?:20|10)\d{9})\b", texto)
    if rucs_total:
        for r in rucs_total:
            if r.startswith("20"):
                return r
        return rucs_total[0]

    return None
