"""Caso de uso: Almacenamiento de comprobantes procesados (REQ-7).

R1: WHEN un comprobante haya sido procesado correctamente
    THEN SYSTEM SHALL almacenar toda la información en PostgreSQL.

R2: WHEN el comprobante ya exista según su hash
    THEN SYSTEM SHALL evitar almacenarlo nuevamente.

Flujo completo por lote:
  1. Upsert empresa (companies) → obtener company_id
  2. Crear processing_run → obtener run_id
  3. Para cada documento PROCESSED:
     a. Calcular SHA-256 del archivo
     b. Verificar si ya existe por hash (R2) → skip si duplicado
     c. Upsert business_partner → obtener partner_id
     d. Insertar document con todos los datos extraídos
  4. Completar processing_run con estadísticas finales
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date

from domain.entities.document import Document
from domain.entities.extracted_data import ExtractedData
from domain.entities.processing_result import BatchProcessSummary
from domain.enums.document_status import DocumentStatus

logger = logging.getLogger(__name__)


def _parse_issue_date(raw: str | None) -> date | None:
    """Convierte 'DD/MM/YYYY' a datetime.date. Retorna None si falla."""
    if not raw:
        return None
    try:
        day, month, year = raw.split("/")
        return date(int(year), int(month), int(day))
    except Exception:
        return None


@dataclass(slots=True)
class SaveResult:
    saved: int = 0
    skipped_duplicates: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)


def save_batch(
    summary: BatchProcessSummary,
    company_ruc: str,
    company_name: str,
) -> SaveResult:
    """
    Persiste en PostgreSQL todos los documentos exitosamente procesados del lote.

    Args:
        summary:       Resultado del ProcessBatchUseCase.
        company_ruc:   RUC de la empresa seleccionada.
        company_name:  Nombre de la empresa seleccionada.

    Returns:
        SaveResult con conteos de guardados, duplicados y errores.
    """
    from Persistence.connection import get_conn
    from Persistence.repositories.business_partner_repo import upsert_business_partner
    from Persistence.repositories.company_repo import upsert_company
    from Persistence.repositories.document_repo import hash_exists, insert_document
    from Persistence.repositories.processing_run_repo import complete_run, create_run
    from utils.file_hash import compute_sha256

    result = SaveResult()

    with get_conn() as conn:
        # ── 1. Empresa ────────────────────────────────────────────────────────
        company_id = upsert_company(
            conn=conn,
            ruc=company_ruc,
            business_name=company_name,
        )

        # ── 2. Processing run ─────────────────────────────────────────────────
        run_id = create_run(
            conn=conn,
            company_id=company_id,
            total_files=summary.total_count,
        )

        # ── 3. Documentos procesados ──────────────────────────────────────────
        for doc_result in summary.results:
            if not doc_result.success:
                continue  # Solo se persisten los exitosos (R1)

            doc: Document = doc_result.document
            ed: ExtractedData | None = doc.extracted_data  # type: ignore[assignment]

            try:
                # R2: verificar duplicado por hash
                file_hash = compute_sha256(doc.path)
                if hash_exists(conn, file_hash):
                    logger.info("Comprobante duplicado (hash ya existe): %s", doc.name)
                    result.skipped_duplicates += 1
                    continue

                # ── Socios de negocio ─────────────────────────────────────────
                # Se registran AMBOS (proveedor y cliente) en business_partners.
                # En documents.business_partner_id se guarda el principal:
                #   PURCHASE → proveedor (quien emite la factura/boleta)
                #   SALE     → cliente   (quien recibe el comprobante)

                supplier_partner_id: int | None = None
                customer_partner_id: int | None = None
                partner_id: int | None = None

                if ed:
                    # ── Proveedor ─────────────────────────────────────────────
                    sup_ruc = ed.supplier_ruc
                    if sup_ruc and sup_ruc != "00000000":
                        # Determinar tipo: 11 dígitos → RUC, 8 dígitos → DNI
                        sup_doc_type = "RUC" if len(sup_ruc) == 11 else "DNI"
                        sup_name = ed.supplier_name or sup_ruc
                        supplier_partner_id = upsert_business_partner(
                            conn=conn,
                            document_type=sup_doc_type,
                            document_number=sup_ruc,
                            business_name=sup_name,
                        )

                    # ── Cliente ───────────────────────────────────────────────
                    cust_ruc = ed.customer_ruc
                    cust_doc_type = ed.customer_doc_type or "RUC"
                    if cust_ruc == "00000000" or cust_doc_type == "VENTA MENOR":
                        # Venta al por menor: registro genérico compartido
                        customer_partner_id = upsert_business_partner(
                            conn=conn,
                            document_type="VENTA MENOR",
                            document_number="00000000",
                            business_name="VENTA MENOR",
                        )
                    elif cust_ruc:
                        cdt = cust_doc_type if cust_doc_type in ("RUC", "DNI") else (
                            "RUC" if len(cust_ruc) == 11 else "DNI"
                        )
                        cust_name = ed.customer_name or cust_ruc
                        customer_partner_id = upsert_business_partner(
                            conn=conn,
                            document_type=cdt,
                            document_number=cust_ruc,
                            business_name=cust_name,
                        )

                    # ── Partner principal del documento ───────────────────────
                    from domain.enums.document_type import DocumentType
                    if doc.document_type == DocumentType.PURCHASE:
                        partner_id = supplier_partner_id  # proveedor
                    else:
                        partner_id = customer_partner_id  # cliente

                # ── Insertar documento ────────────────────────────────────────
                insert_document(
                    conn=conn,
                    processing_run_id=run_id,
                    company_id=company_id,
                    business_partner_id=partner_id,
                    document_type=doc.document_type.value if doc.document_type else "PURCHASE",
                    source_type=(ed.source_type or "PDF") if ed else "PDF",
                    invoice_type=ed.invoice_type if ed else None,
                    issue_date=_parse_issue_date(ed.issue_date if ed else None),
                    currency=ed.currency if ed else None,
                    series=ed.series if ed else None,
                    number=ed.number if ed else None,
                    subtotal=ed.subtotal if ed else None,
                    igv=ed.igv if ed else None,
                    total=ed.total if ed else None,
                    description=ed.description if ed else None,
                    file_name=doc.name,
                    file_path=str(doc.path),
                    file_hash=file_hash,
                    ocr_engine=(ed.ocr_engine if ed else None),
                    status="PROCESSED",
                )
                result.saved += 1

            except Exception as exc:  # noqa: BLE001
                logger.error("Error al guardar '%s': %s", doc.name, exc)
                result.errors += 1
                result.error_details.append(f"{doc.name}: {exc}")

        # ── 4. Cerrar processing_run ──────────────────────────────────────────
        complete_run(
            conn=conn,
            run_id=run_id,
            processed_files=result.saved,
            failed_files=summary.error_count + result.errors,
            duration_seconds=int(summary.total_time_seconds),
        )

    return result
