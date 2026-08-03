"""Extractor del RUC del proveedor (emisor) del comprobante."""

from __future__ import annotations

import re


def extract_ruc(text: str) -> str | None:
    """
    Extrae el RUC del proveedor/emisor del comprobante.

    Estrategia:
    1. Busca RUC explícito en el bloque de cabecera del emisor
       (antes de 'Señor(es)' o 'Adquiriente').
    2. Fallback: primer RUC de empresa (20...) en el texto.
    3. Último fallback: primer RUC de persona natural (10...).
    """
    lines = text.splitlines()

    # Detectar hasta dónde llega el bloque del emisor
    emitter_block: list[str] = []
    for line in lines:
        if re.search(r"se(ñ|n)or(es)?\s*[:(]", line, re.IGNORECASE):
            break
        emitter_block.append(line)

    emitter_text = "\n".join(emitter_block) if emitter_block else text

    # 1. RUC explícito con etiqueta "RUC:" en bloque emisor
    m = re.search(r"\bRUC\s*:?\s*(\d{11})\b", emitter_text, re.IGNORECASE)
    if m:
        return m.group(1)

    # 2. Secuencia de 11 dígitos que comience con 10 o 20 en el bloque emisor
    rucs = re.findall(r"\b((?:20|10)\d{9})\b", emitter_text)
    if rucs:
        for r in rucs:
            if r.startswith("20"):
                return r
        return rucs[0]

    # 3. Fallback: buscar en todo el texto
    rucs_all = re.findall(r"\b((?:20|10)\d{9})\b", text)
    if rucs_all:
        for r in rucs_all:
            if r.startswith("20"):
                return r
        return rucs_all[0]

    return None
