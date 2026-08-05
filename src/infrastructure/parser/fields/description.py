"""Extractor de la descripción principal del bien o servicio."""

from __future__ import annotations

import re

_IGNORE_HEADERS = frozenset({
    "DESCRIPCION", "DESCRIPCIÓN",
    "CANTIDAD", "CANT.", "CANT",
    "UNIDAD", "UND", "UNI",
    "UNIDAD MEDIDA DESCRIPCION", "UNIDAD MEDIDA DESCRIPCIÓN",
    "UNIDAD MEDIDA", "UNIDADMEDIDA", "VALOR UNITARIO",
    "CODIGO", "CÓDIGO",
    "V.UNIT", "P/U",
    "TOTAL", "SUBTOTAL", "IGV",
    "IMPORTE TOTAL", "TOTAL A PAGAR",
    "OP. GRAVADA", "GRAVADA",
    "BASE IMPONIBLE",
})

_EXCLUDE_WORDS = (
    "FACTURA", "BOLETA", "RUC:", "RUC ",
    "DNI", "FECHA", "MONEDA", "CLIENTE",
    "DIRECCION", "DIRECCIÓN", "OBSERVACION", "OBSERVACIÓN",
    "ADQUIRIENTE", "VENDEDOR",
    "TELEFON", "WHATSAPP", "WWW.", "HTTP", "CENTRAL ",
    "CORREO", "EMAIL", "@",
    "IGV:", "IGV ", "I.G.V",
    "IMPORTE", "VALOR VENTA", "VENC",
    "REGIMEN", "RETENCION",
    "INCORPORADO",
    "SERIE:", "NRO ORDEN", "CODIGO:", "PAQUETE",
)

_COMPANY_SUFFIXES = (
    "S.A.C.", "S.A.C", "S.A.", "S.A",
    "E.I.R.L.", "E.I.R.L", "EIRL",
    "S.R.L.", "S.R.L", "SRL",
    "SAC", "CIA", "LTDA",
)

_ADDRESS_WORDS = ("LIMA", "AV.", "CAL.", "URB.", "JR.", "CALLE", "NRO.")


def extract_description(text: str) -> str | None:
    """
    Identifica la descripción principal del bien o servicio en el comprobante.

    Estrategia:
    1. Busca líneas que sigan patrones de ítems/productos SUNAT.
       Si encuentra múltiples productos distintos → "ACCESORIOS VARIOS".
       Si encuentra exactamente uno → retorna esa descripción.
    2. Fallback: descarte línea por línea de candidatos.
    """
    # 1. Intentar buscar por patrones de ítems
    item_patterns = [
        r"(?:UNIDAD|UND|NIU|ZZ|GLO|PCS|UNI|CANTIDAD|CANT\.?)(?:\s+[A-Z0-9]+)?(?:\s+\d+)?\s+(.+?)\s+[\d,]+\.\d+",
        r"\b\d{12,14}\s+(.+?)(?:\s+\d+\s*X|\s+\d+\.\d{2})",
    ]

    items: list[str] = []
    for pattern in item_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            raw: str = match[0] if isinstance(match, (tuple, list)) else match
            clean = raw.replace("\n", " ").strip()
            clean = re.sub(r"^\d+\s+", "", clean)
            clean = re.sub(r"\s+", " ", clean)
            upper = clean.upper()

            if (
                upper in _IGNORE_HEADERS
                or "MEDIDA DESCRIPCION" in upper
                or "MEDIDA DESCRIPCIÓN" in upper
                or any(k in upper for k in ("DESCRIPCION", "DESCRIPCIÓN", "VALOR UNITARIO", "IMPORTE TOTAL"))
            ):
                continue

            if len(clean) > 3 and clean not in items:
                items.append(clean)

    if items:
        return items[0] if len(items) == 1 else "ACCESORIOS VARIOS"

    # 2. Fallback: descarte línea por línea
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Recortar al bloque de detalle (después del encabezado de tabla)
    for i, line in enumerate(lines):
        if any(h in line.upper() for h in ("DESCRIPCION", "DESCRIPCIÓN", "CANTIDAD", "DETALLE", "CONCEPTO")):
            lines = lines[i + 1:]
            break

    candidates: list[str] = []
    for line in lines:
        upper = line.upper()

        if re.fullmatch(r"[\d\s./:%-]+", line):
            continue
        if re.search(r"\d+\.\d{2}$", line):
            continue
        clean_upper = upper.replace(" ", "")
        if any(h in clean_upper for h in ("UNIDADMEDIDA", "VALORUNITARIO", "ICBPER", "OBSERVACION", "OBSERVACIÓN", "CANTIDAD", "DESCRIPCION", "DESCRIPCIÓN")):
            continue
        if clean_upper in _IGNORE_HEADERS or upper.strip() in _IGNORE_HEADERS:
            continue
        if any(p in upper for p in _EXCLUDE_WORDS):
            continue
        if any(p in upper for p in _ADDRESS_WORDS):
            continue
        if any(s in upper for s in _COMPANY_SUFFIXES):
            continue
        if re.fullmatch(r"[A-Z]{1,4}\d{0,4}-\d{3,12}", line, re.IGNORECASE):
            continue
        if line.startswith("["):
            continue

        candidates.append(line)

    for candidate in candidates:
        if len(candidate) > 5:
            return candidate

    return None
