"""Datos extraídos de un comprobante (REQ-3 / REQ-4).

Mapea directamente a la tabla `documents` del esquema PostgreSQL.
Todos los campos son opcionales porque la extracción puede ser parcial (REQ-4 R2).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ExtractedData:
    # --- Tipo de operación ---
    document_type: str | None = None          # SALE | PURCHASE

    # --- Identificación del comprobante ---
    invoice_type: str | None = None           # FACTURA ELECTRONICA, BOLETA DE VENTA, etc.
    series: str | None = None                 # F001, B459, E001…
    number: str | None = None                 # Número correlativo

    # --- Fechas y moneda ---
    issue_date: str | None = None             # DD/MM/YYYY
    currency: str | None = None               # SOLES | DOLAR AMERICANO

    # --- Proveedor (emisor) ---
    supplier_ruc: str | None = None
    supplier_name: str | None = None

    # --- Cliente (receptor) ---
    customer_ruc: str | None = None
    customer_doc_type: str | None = None      # RUC | DNI | VENTA MENOR
    customer_name: str | None = None

    # --- Montos ---
    subtotal: float | None = None
    igv: float | None = None
    total: float | None = None

    # --- Descripción del bien/servicio ---
    description: str | None = None

    # --- Metadata de extracción ---
    raw_text: str | None = None               # Texto crudo antes del parseo
    ocr_engine: str | None = None             # "pdfplumber" | "rapidocr"
    source_type: str | None = None            # "PDF" | "IMAGE"
    extraction_warnings: list[str] = field(default_factory=list)
