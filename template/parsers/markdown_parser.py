"""Parser de Markdown / Texto plano → InvoiceData.

Orquesta todos los extractores de campos individuales (fields/)
para producir un objeto con los datos extraídos del comprobante.
"""

from __future__ import annotations

from typing import Literal

from features.documents.parsers.fields.cliente import extraer_cliente
from features.documents.parsers.fields.descripcion import extraer_descripcion
from features.documents.parsers.fields.fecha import extraer_fecha
from features.documents.parsers.fields.moneda import extraer_moneda
from features.documents.parsers.fields.montos import (
    extraer_igv,
    extraer_subtotal,
    extraer_total,
)
from features.documents.parsers.fields.proveedor import extraer_proveedor
from features.documents.parsers.fields.ruc import extraer_ruc
from features.documents.parsers.fields.serie_numero import extraer_serie_numero
from features.documents.parsers.fields.tipo_factura import extraer_tipo_factura
from features.documents.schemas import InvoiceData, OperationType


def parse_texto(
    texto: str,
    nombre_archivo: str,
    operation_type: OperationType = OperationType.PURCHASE,
) -> InvoiceData:
    """Parsea texto plano (Markdown o extraído de PDF/imagen) y retorna InvoiceData.

    Args:
        texto: Contenido textual del comprobante.
        nombre_archivo: Nombre del archivo fuente (para trazabilidad).
        operation_type: PURCHASE (Compra) o SALE (Venta).

    Returns:
        InvoiceData con todos los campos extraídos según el tipo de operación.
    """
    # 1. Extraer datos genéricos del documento
    tipo_factura = extraer_tipo_factura(texto)
    serie, numero = extraer_serie_numero(texto)
    fecha = extraer_fecha(texto)
    moneda = extraer_moneda(texto)
    subtotal = extraer_subtotal(texto)
    igv = extraer_igv(texto)
    total = extraer_total(texto)
    descripcion = extraer_descripcion(texto)

    # 2. Determinar el socio de negocio según la operación (PURCHASE vs SALE)
    doc_socio: str | None = None
    # 💡 Usamos Literal["RUC", "DNI"] | None para que coincida con el Schema
    tipo_doc_socio: Literal["RUC", "DNI"] | None = None

    if operation_type == OperationType.SALE:
        # En VENTAS, el socio es el CLIENTE (Segundo RUC o DNI)
        tipo_cliente, doc_cliente = extraer_cliente(texto)

        if doc_cliente:
            doc_socio = doc_cliente
            # Validamos que tipo_cliente sea uno de los valores válidos
            tipo_doc_socio = "RUC" if tipo_cliente == "RUC" else "DNI"
        else:
            # VENTA MENOR (Sin documento de cliente)
            doc_socio = "00000000"
            tipo_doc_socio = "DNI"
    else:
        # En COMPRAS (default), el socio es el PROVEEDOR (Primer RUC/Emisor)
        ruc_emisor = extraer_ruc(texto)
        if ruc_emisor:
            doc_socio = ruc_emisor
            tipo_doc_socio = "RUC" if len(ruc_emisor) == 11 else "DNI"

    return InvoiceData(
        documento_socio=doc_socio,
        tipo_documento_socio=tipo_doc_socio,
        operation_type=operation_type,
        tipo_factura=tipo_factura,
        serie=serie,
        numero=numero,
        fecha_emision=fecha,
        moneda=moneda,
        subtotal=subtotal,
        igv=igv,
        total=total,
        descripcion=descripcion,
        ruta=nombre_archivo,
    )
