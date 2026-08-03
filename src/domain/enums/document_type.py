"""Tipo de operación del comprobante: compra o venta."""

from enum import StrEnum


class DocumentType(StrEnum):
    PURCHASE = "PURCHASE"  # Compras — proveedor emite el comprobante
    SALE = "SALE"          # Ventas  — la empresa emite el comprobante (SUNAT PDF)
