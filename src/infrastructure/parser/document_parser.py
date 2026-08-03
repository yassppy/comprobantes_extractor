"""Orquestador de parseo de texto → ExtractedData (REQ-4).

Coordina todos los extractores de campos individuales y produce
un objeto ExtractedData con los datos encontrados.
"""

from __future__ import annotations

from domain.entities.extracted_data import ExtractedData
from domain.enums.document_type import DocumentType
from infrastructure.parser.fields.amounts import extract_igv, extract_subtotal, extract_total
from infrastructure.parser.fields.currency import extract_currency
from infrastructure.parser.fields.customer import extract_customer
from infrastructure.parser.fields.description import extract_description
from infrastructure.parser.fields.invoice_type import extract_invoice_type
from infrastructure.parser.fields.issue_date import extract_issue_date
from infrastructure.parser.fields.ruc import extract_ruc
from infrastructure.parser.fields.series_number import extract_series_number
from infrastructure.parser.fields.supplier import extract_supplier_name


def parse_document(
    text: str,
    document_type: DocumentType = DocumentType.PURCHASE,
    ocr_engine: str = "pdfplumber",
    source_type: str = "PDF",
) -> ExtractedData:
    """
    Parsea texto plano extraído de un comprobante y retorna ExtractedData.

    REQ-4 R1: Identifica la información tributaria disponible.
    REQ-4 R2: Si algún dato no puede identificarse, se registra None.

    Args:
        text:          Texto crudo del comprobante.
        document_type: PURCHASE (compra) o SALE (venta).
        ocr_engine:    Motor de extracción usado ("pdfplumber" o "rapidocr").
        source_type:   Origen del archivo ("PDF" o "IMAGE").

    Returns:
        ExtractedData con todos los campos encontrados.
    """
    data = ExtractedData(
        document_type=document_type.value,
        ocr_engine=ocr_engine,
        source_type=source_type,
        raw_text=text,
    )

    # ── Campos genéricos ────────────────────────────────────────────────────
    data.invoice_type = extract_invoice_type(text)
    series, number = extract_series_number(text)
    data.series = series
    data.number = number
    data.issue_date = extract_issue_date(text)
    data.currency = extract_currency(text)
    data.subtotal = extract_subtotal(text)
    data.igv = extract_igv(text)
    data.total = extract_total(text)
    data.description = extract_description(text)

    # ── Socio de negocio según tipo de operación ────────────────────────────
    if document_type == DocumentType.SALE:
        # VENTAS: la empresa emite → el cliente es el receptor
        doc_type_str, doc_number = extract_customer(text)
        data.customer_doc_type = doc_type_str
        data.customer_ruc = doc_number
        # En ventas el emisor es la propia empresa — proveedor no aplica
    else:
        # COMPRAS: el proveedor emite → extraer RUC y razón social del emisor
        supplier_ruc = extract_ruc(text)
        data.supplier_ruc = supplier_ruc
        data.supplier_name = extract_supplier_name(text, supplier_ruc)

    # Advertencias si faltan datos clave
    missing: list[str] = []
    if not data.series:
        missing.append("serie")
    if not data.number:
        missing.append("número")
    if not data.issue_date:
        missing.append("fecha")
    if not data.total:
        missing.append("total")

    if missing:
        data.extraction_warnings = [f"No se pudo extraer: {', '.join(missing)}"]

    return data
