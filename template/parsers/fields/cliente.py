"""Extractor del documento e identificación del cliente (receptor)."""

from __future__ import annotations

import re


def extraer_cliente(texto: str) -> tuple[str, str]:
    """
    Detecta el tipo e identificación del cliente (receptor).

    Estrategia:
    1. Busca el bloque receptor (a partir de 'Señor(es)').
    2. En ese bloque busca etiqueta RUC: o DNI:.
    3. Fallback: segundo RUC en el texto completo.

    Retorna una tupla (tipo_documento, numero_documento):
    - ("DNI", "12345678")         → cliente persona natural
    - ("RUC", "20xxxxxxxxx")      → cliente empresa (factura)
    - ("VENTA MENOR", "00000000") → boleta sin identificación
    """
    lineas = texto.splitlines()

    # Localizar inicio del bloque receptor
    inicio_receptor = 0
    for i, linea in enumerate(lineas):
        if re.search(r"se(ñ|n)or(es)?\s*[:(]", linea, re.IGNORECASE):
            inicio_receptor = i
            break

    bloque_receptor = "\n".join(lineas[inicio_receptor:])

    # 1. Buscar DNI explícito
    m = re.search(r"\bDNI\s*:?\s*(\d{8})\b", bloque_receptor, re.IGNORECASE)
    if m:
        return ("DNI", m.group(1))

    # 2. Buscar RUC explícito en bloque receptor
    m = re.search(r"\bRUC\s*:?\s*(\d{11})\b", bloque_receptor, re.IGNORECASE)
    if m:
        return ("RUC", m.group(1))

    # 3. Segundo RUC de empresa (20...) en todo el texto
    rucs_20 = re.findall(r"\b20\d{9}\b", texto)
    if len(rucs_20) >= 2:
        return ("RUC", rucs_20[1])

    # 4. RUC de persona natural (10...) en bloque receptor
    rucs_10 = re.findall(r"\b10\d{9}\b", bloque_receptor)
    if rucs_10:
        return ("RUC", rucs_10[0])

    # 5. Venta menor (boleta sin identificación)
    return ("VENTA MENOR", "00000000")
