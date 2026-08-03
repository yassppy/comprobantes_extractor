"""Extractor del documento e identificación del cliente (receptor)."""

from __future__ import annotations

import re


def extract_customer(text: str) -> tuple[str, str]:
    """
    Detecta el tipo e identificación del cliente (receptor).

    Estrategia:
    1. Busca el bloque receptor (a partir de 'Señor(es)').
    2. En ese bloque busca etiqueta RUC: o DNI:.
    3. Fallback: segundo RUC en el texto completo.

    Retorna una tupla (tipo_documento, numero_documento):
    - ("DNI", "12345678")           → cliente persona natural
    - ("RUC", "20xxxxxxxxx")        → cliente empresa (factura)
    - ("VENTA MENOR", "00000000")   → boleta sin identificación
    """
    lines = text.splitlines()

    # Localizar inicio del bloque receptor
    receptor_start = 0
    for i, line in enumerate(lines):
        if re.search(r"se(ñ|n)or(es)?\s*[:(]", line, re.IGNORECASE):
            receptor_start = i
            break

    receptor_block = "\n".join(lines[receptor_start:])

    # 1. DNI explícito
    m = re.search(r"\bDNI\s*:?\s*(\d{8})\b", receptor_block, re.IGNORECASE)
    if m:
        return ("DNI", m.group(1))

    # 2. RUC explícito en bloque receptor
    m = re.search(r"\bRUC\s*:?\s*(\d{11})\b", receptor_block, re.IGNORECASE)
    if m:
        return ("RUC", m.group(1))

    # 3. Segundo RUC de empresa (20...) en todo el texto
    rucs_20 = re.findall(r"\b20\d{9}\b", text)
    if len(rucs_20) >= 2:
        return ("RUC", rucs_20[1])

    # 4. RUC de persona natural (10...) en bloque receptor
    rucs_10 = re.findall(r"\b10\d{9}\b", receptor_block)
    if rucs_10:
        return ("RUC", rucs_10[0])

    # 5. Venta menor (boleta sin identificación)
    return ("VENTA MENOR", "00000000")
