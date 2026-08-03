"""Extractor de la descripción principal del bien o servicio."""

from __future__ import annotations

import re

# Encabezados de tabla que NO son descripción del producto
_IGNORAR = frozenset({
    "DESCRIPCION", "DESCRIPCIÓN",
    "CANTIDAD", "CANT.", "CANT",
    "UNIDAD", "UND", "UNI",
    "UNIDAD MEDIDA DESCRIPCION", "UNIDAD MEDIDA DESCRIPCIÓN",
    "UNIDAD MEDIDA", "VALOR UNITARIO",
    "CODIGO", "CÓDIGO",
    "V.UNIT", "P/U",
    "TOTAL", "SUBTOTAL", "IGV",
    "IMPORTE TOTAL", "TOTAL A PAGAR",
    "OP. GRAVADA", "GRAVADA",
    "BASE IMPONIBLE",
})

# Palabras de datos administrativos (no descripción)
_PALABRAS_EXCLUIR = (
    "FACTURA", "BOLETA", "RUC:", "RUC ",
    "DNI", "FECHA", "MONEDA", "CLIENTE",
    "DIRECCION", "DIRECCIÓN", "OBSERVACION", "OBSERVACIÓN",
    "ADQUIRIENTE", "VENDEDOR",
    # Datos de contacto / encabezado de empresa
    "TELEFON", "WHATSAPP", "WWW.", "HTTP", "CENTRAL ",
    "CORREO", "EMAIL", "@",
    # Términos financieros que aparecen en líneas mixtas (ej: "IGV: 18.00 %")
    "IGV:", "IGV ", "I.G.V",
    "IMPORTE", "VALOR VENTA", "VENC",
    "REGIMEN", "RETENCION",
    "INCORPORADO",
    # Metadata de ítems de tabla (ej: "[1]ZZ Serie: V449", "Nro orden: 6546599")
    "SERIE:", "NRO ORDEN", "CODIGO:", "PAQUETE",
)

# Sufijos legales de empresas — las líneas con estos sufijos son razón social, no descripción
_SUFIJOS_EMPRESA = (
    "S.A.C.", "S.A.C", "S.A.", "S.A",
    "E.I.R.L.", "E.I.R.L", "EIRL",
    "S.R.L.", "S.R.L", "SRL",
    "SAC", "CIA", "LTDA",
)

# Palabras de dirección/ubicación
_PALABRAS_DIRECCION = ("LIMA", "AV.", "CAL.", "URB.", "JR.", "CALLE", "NRO.")


def extraer_descripcion(texto: str) -> str | None:
    """
    Identifica la descripción principal del bien o servicio en el comprobante.

    Estrategia:
    1. Busca líneas que sigan patrones de ítems/productos SUNAT usando expresiones regulares.
       Si encuentra múltiples productos distintos, retorna "ACCESORIOS VARIOS".
       Si encuentra exactamente uno, retorna esa descripción.
    2. Como fallback, usa la estrategia de descarte línea por línea de candidatos.
    """
    # 1. Intentar buscar por patrones de ítems/productos
    patrones = [
        # Patrón para líneas con unidades (UNIDAD, UND, NIU, etc.)
        # Ej: "1.00 UNIDAD 77 CAPUCHON 10.169491525" or "UNIDAD\n868 JEBES +DIRECCIONALES+ SUICH\n25.4237288"
        r"(?:UNIDAD|UND|NIU|ZZ|GLO|PCS|UNI|CANTIDAD|CANT\.?)(?:\s+[A-Z0-9]+)?(?:\s+\d+)?\s+(.+?)\s+[\d,]+\.\d+",
        # Patrón para tickets sin unidades explícitas al inicio (ej: Mass): "7751271036245 GLOENTBL800M \n 2 X \n 4.50"
        # Usamos 12 a 14 dígitos para evitar falsos positivos con números de orden de 8 dígitos o DNIs.
        r"\b\d{12,14}\s+(.+?)(?:\s+\d+\s*X|\s+\d+\.\d{2})",
    ]

    items: list[str] = []
    for patron in patrones:
        coincidencias = re.findall(patron, texto, re.IGNORECASE)
        for c in coincidencias:
            primer_val: object = c[0] if isinstance(c, (tuple, list)) else c
            c_str: str = str(primer_val)

            c_limpio: str = c_str.replace("\n", " ").strip()
            # Remover código numérico inicial del ítem si se capturó (ej: "77 CAPUCHON" -> "CAPUCHON")
            c_limpio = re.sub(r"^\d+\s+", "", c_limpio)
            c_limpio = re.sub(r"\s+", " ", c_limpio)

            c_upper = c_limpio.upper()

            # Descartar si coincide con la fila de encabezados de la tabla
            if (
                c_upper in _IGNORAR
                or "MEDIDA DESCRIPCION" in c_upper
                or "MEDIDA DESCRIPCIÓN" in c_upper
                or any(
                    p in c_upper
                    for p in (
                        "DESCRIPCION",
                        "DESCRIPCIÓN",
                        "VALOR UNITARIO",
                        "IMPORTE TOTAL",
                    )
                )
            ):
                continue

            if len(c_limpio) > 3 and c_limpio not in items:
                items.append(c_limpio)

    if items:
        if len(items) == 1:
            return items[0]
        else:
            return "ACCESORIOS VARIOS"

    # 2. Fallback: Descarte línea por línea de candidatos
    lineas = [linea_texto.strip() for linea_texto in texto.splitlines() if linea_texto.strip()]

    # Recortar las líneas para descartar la cabecera y datos del cliente si se encuentra un encabezado de tabla
    for i, linea in enumerate(lineas):
        linea_upper = linea.upper()
        if any(h in linea_upper for h in ("DESCRIPCION", "DESCRIPCIÓN", "CANTIDAD", "DETALLE", "CONCEPTO")):
            lineas = lineas[i + 1:]
            break

    candidatos: list[str] = []

    for linea in lineas:
        linea_upper = linea.upper()

        # Descartar líneas puramente numéricas / fechas / códigos
        if re.fullmatch(r"[\d\s./:%-]+", linea):
            continue

        # Descartar líneas que terminan en monto
        if re.search(r"\d+\.\d{2}$", linea):
            continue

        # Descartar encabezados de tabla
        if linea_upper.strip() in _IGNORAR:
            continue

        # Descartar datos administrativos
        if any(p in linea_upper for p in _PALABRAS_EXCLUIR):
            continue

        # Descartar direcciones
        if any(p in linea_upper for p in _PALABRAS_DIRECCION):
            continue

        # Descartar razones sociales (líneas con sufijos empresariales)
        if any(s in linea_upper for s in _SUFIJOS_EMPRESA):
            continue

        # Descartar líneas que son exactamente una serie-número (ej: B459-103578, E001-5704)
        if re.fullmatch(r"[A-Z]{1,4}\d{0,4}-\d{3,12}", linea, re.IGNORECASE):
            continue

        # Descartar líneas que empiezan con corchete (metadata de ítem: "[1]ZZ Serie: V449")
        if linea.startswith("["):
            continue

        candidatos.append(linea)

    # Preferir línea con más de 8 caracteres
    for candidato in candidatos:
        if len(candidato) > 8:
            return candidato

    return None
