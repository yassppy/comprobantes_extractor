"""Extractor de montos financieros: subtotal, IGV y total."""

from __future__ import annotations

import re


# ============================================================
# UTILIDAD INTERNA
# ============================================================


def _limpiar_monto(valor: str | None) -> float | None:
    """
    Normaliza un string de monto a float.

    Maneja formatos:
    - "1,234.56" → 1234.56   (separador de miles con coma)
    - "1.234,56" → 1234.56   (separador de miles con punto — Europa)
    - "1234.56"  → 1234.56
    """
    if not valor:
        return None

    # Quitar todo excepto dígitos, coma y punto
    valor = re.sub(r"[^\d.,]", "", valor)

    if not valor:
        return None

    # Si tiene ambos separadores → la coma es separador de miles
    if "," in valor and "." in valor:
        valor = valor.replace(",", "")
    elif "," in valor:
        # Solo coma → es el separador decimal (formato europeo)
        valor = valor.replace(",", ".")

    try:
        return float(valor)
    except ValueError:
        return None


def _buscar_regex(patrones: list[str], texto: str) -> str | None:
    """Aplica una lista de patrones y retorna el primer match."""
    for patron in patrones:
        m = re.search(patron, texto, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return None


# ============================================================
# EXTRACTORES PÚBLICOS
# ============================================================


def extraer_subtotal(texto: str) -> float | None:
    """
    Extrae el valor de venta / base imponible (sin IGV).

    Busca etiquetas: VALOR VENTA, SUBTOTAL, OP. GRAVADA, GRAVADA.
    """
    patrones = [
        r"VALOR\s+VENTA\s*:?\s*S[/I]?\s*([\d.,]+)",
        r"SUB\s*TOTAL.*?([\d,]+\.\d{2})",
        r"OP\.?\s*GRAVADA.*?([\d,]+\.\d{2})",
        r"GRAVADA\s*S[/I]?\s*([\d,]+\.\d{2})",
        r"GRAVADA.*?([\d,]+\.\d{2})",
    ]
    return _limpiar_monto(_buscar_regex(patrones, texto))


def extraer_igv(texto: str) -> float | None:
    """
    Extrae el monto de IGV.

    Busca etiquetas: IGV, I.G.V. con o sin símbolo de moneda.
    Maneja formatos soles (S/) y dólares ($ o sin símbolo).
    """
    patrones = [
        # Con S/ delante del monto
        r"I\.?G\.?V\.?\s*:?\s*S[/I]?\s*([\d,]+\.\d{2})",
        # Con $ delante del monto
        r"I\.?G\.?V\.?\s*:?\s*\$\s*([\d,]+\.\d{2})",
        # Sin símbolo de moneda (formato imagen/OCR)
        r"^\s*I\.?G\.?V\.?\s*[:\-]?\s*([\d,]+\.\d{2})\s*$",
        # Monto a la derecha en la misma línea
        r"I\.?G\.?V\.?[^\d\n]{0,20}([\d,]+\.\d{2})",
        # Monto antes de la etiqueta
        r"([\d,]+\.\d{2})\s*(?:S[/I]?\.?)?\s*I\.?G\.?V\.?",
    ]
    return _limpiar_monto(_buscar_regex(patrones, texto))


def extraer_total(texto: str) -> float | None:
    """
    Extrae el importe total del comprobante.

    Busca etiquetas: IMPORTE TOTAL, TOTAL A PAGAR, TOTAL S/.
    """
    patrones = [
        r"IMPORTE\s+TOTAL.*?([\d,]+\.\d{2})",
        r"TOTAL\s+A\s+PAGAR.*?([\d,]+\.\d{2})",
        r"TOTAL\s*S/?\.?\s*([\d,]+\.\d{2})",
    ]
    return _limpiar_monto(_buscar_regex(patrones, texto))
