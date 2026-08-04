"""Scraper del portal SUNAT - Consulta RUC usando Playwright.

Soporta dos modos de búsqueda:
  - Por RUC (11 dígitos)     → URL ?accion=consPorRuc
  - Por DNI (8 dígitos)      → URL ?accion=consPorDocumento (tab "Por Documento")

El resultado de buscar por DNI devuelve el RUC asociado, nombre completo,
ubicación y estado del contribuyente.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

_BASE_URL = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc"
SUNAT_RUC_URL = f"{_BASE_URL}/jcrS00Alias?accion=consPorRuc"
SUNAT_DOC_URL = f"{_BASE_URL}/FrameCritrioBusquedaWeb.jsp"


@dataclass(slots=True)
class SunatRucInfo:
    ruc: str
    business_name: str
    trade_name: str | None
    status: str               # ACTIVO | BAJA DEFINITIVA | …
    condition: str            # HABIDO | NO HABIDO | NO HALLADO | N/A (DNI)
    fiscal_address: str | None
    is_active: bool
    is_habido: bool
    is_valid: bool            # True si ACTIVO + HABIDO
    validated_at: datetime
    # Campos extra cuando se busca por DNI
    dni: str | None = None
    location: str | None = None


# ─── Scraper por RUC ──────────────────────────────────────────────────────────

def scrape_ruc(ruc_number: str) -> SunatRucInfo:
    """
    Consulta un RUC de 11 dígitos en SUNAT.

    Raises:
        ValueError: RUC inválido o no encontrado.
        RuntimeError: Error de conectividad.
    """
    if len(ruc_number) != 11 or not ruc_number.isdigit():
        raise ValueError(
            f"El RUC '{ruc_number}' debe contener exactamente 11 dígitos numéricos."
        )

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=_UA)
        page = context.new_page()

        invalid_detected = False
        dialog_msg = ""

        def _handle_dialog(dialog) -> None:
            nonlocal invalid_detected, dialog_msg
            invalid_detected = True
            dialog_msg = dialog.message
            dialog.accept()

        page.on("dialog", _handle_dialog)

        try:
            logger.info("Consultando RUC %s en SUNAT…", ruc_number)
            page.goto(SUNAT_RUC_URL, timeout=15_000)
            page.locator("#txtRuc").fill(ruc_number)
            page.get_by_role("button", name="Buscar").click()
            page.wait_for_timeout(1_000)

            if invalid_detected:
                raise ValueError(
                    f"SUNAT rechazó el RUC {ruc_number}: "
                    f"{dialog_msg or 'Número de RUC no válido'}"
                )

            try:
                page.wait_for_selector("div.list-group-item", timeout=5_000)
            except Exception:
                body = page.inner_text("body").lower()
                if "ingrese número de ruc válido" in body or "no se encontró" in body:
                    raise ValueError(
                        f"El RUC '{ruc_number}' no existe en los registros de SUNAT."
                    )
                raise RuntimeError(
                    "No se pudo obtener respuesta del portal SUNAT. "
                    "Verifica tu conexión a internet."
                )

            raw_title = (
                page.locator("div.list-group-item")
                .filter(has_text="Número de RUC:")
                .locator("h4")
                .last.inner_text()
            )
            parts = [x.strip() for x in raw_title.split("-", 1)]
            business_name = parts[1] if len(parts) > 1 else raw_title

            trade_name = (
                page.locator("div.list-group-item")
                .filter(has_text="Nombre Comercial:")
                .locator("p").last.inner_text().strip()
            )
            status = (
                page.locator("div.list-group-item")
                .filter(has_text="Estado del Contribuyente:")
                .locator("p").last.inner_text().strip()
            )
            condition = (
                page.locator("div.list-group-item")
                .filter(has_text="Condición del Contribuyente:")
                .locator("p").last.inner_text().strip()
            )
            fiscal_address = (
                page.locator("div.list-group-item")
                .filter(has_text="Domicilio Fiscal:")
                .locator("p").last.inner_text().strip()
            )

            is_active = status.upper() == "ACTIVO"
            is_habido = condition.upper() == "HABIDO"

            return SunatRucInfo(
                ruc=ruc_number,
                business_name=business_name,
                trade_name=trade_name if trade_name not in ("-", "") else None,
                status=status,
                condition=condition,
                fiscal_address=" ".join(fiscal_address.split()) or None,
                is_active=is_active,
                is_habido=is_habido,
                is_valid=is_active and is_habido,
                validated_at=datetime.now(),
            )

        except ValueError:
            raise
        except Exception as exc:
            logger.error("Error scraping RUC %s: %s", ruc_number, exc)
            raise RuntimeError(f"Error consultando SUNAT para RUC {ruc_number}: {exc}") from exc
        finally:
            browser.close()


# ─── Scraper por DNI ──────────────────────────────────────────────────────────

def scrape_dni(dni_number: str) -> SunatRucInfo:
    """
    Busca el RUC asociado a un DNI usando el tab "Por Documento" de SUNAT.

    Args:
        dni_number: DNI de 8 dígitos.

    Returns:
        SunatRucInfo con el RUC encontrado y datos del contribuyente.

    Raises:
        ValueError: DNI no encontrado o sin RUC asociado.
        RuntimeError: Error de conectividad.
    """
    if len(dni_number) != 8 or not dni_number.isdigit():
        raise ValueError(
            f"El DNI '{dni_number}' debe contener exactamente 8 dígitos numéricos."
        )

    from playwright.sync_api import sync_playwright

    SUNAT_FRAME_URL = (
        "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/"
        "FrameCriterioBusquedaWeb.jsp"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=_UA)
        page = context.new_page()

        try:
            logger.info("Consultando DNI %s en SUNAT…", dni_number)
            page.goto(SUNAT_FRAME_URL, timeout=20_000)
            page.wait_for_timeout(1_500)

            # Click en tab "Por Documento"
            page.get_by_role("button", name="Por Documento").click()
            page.wait_for_timeout(800)

            # Seleccionar "Documento Nacional de Identidad" (value='1')
            page.select_option("#cmbTipoDoc", value="1")

            # Ingresar el DNI en el campo correcto
            page.locator("#txtNumeroDocumento").fill(dni_number)
            page.get_by_role("button", name="Buscar").click()
            page.wait_for_timeout(3_000)

            body = page.inner_text("body")

            # Verificar si no encontró resultado
            body_lower = body.lower()
            if "no se encontró" in body_lower or "no existen" in body_lower or "no hay" in body_lower:
                raise ValueError(
                    f"El DNI '{dni_number}' no tiene RUC asociado en SUNAT."
                )

            if "relación de contribuyentes" not in body_lower:
                raise ValueError(
                    f"El DNI '{dni_number}' no tiene RUC asociado en SUNAT."
                )

            # Parsear resultado — formato:
            # "RUC: 10735122075\nNOMBRE COMPLETO\nUbicación: LIMA\nEstado: ACTIVO"
            import re

            ruc_match = re.search(r"RUC:\s*(\d{11})", body)
            if not ruc_match:
                raise ValueError(
                    f"No se encontró RUC en la respuesta de SUNAT para DNI '{dni_number}'."
                )
            ruc_found = ruc_match.group(1)

            # Nombre: línea después del RUC
            lines = [l.strip() for l in body.splitlines() if l.strip()]
            business_name = ""
            for idx, line in enumerate(lines):
                if ruc_found in line:
                    # El nombre está en la misma línea después del RUC o en la siguiente
                    rest = line.replace(f"RUC: {ruc_found}", "").strip()
                    if rest:
                        business_name = rest
                    elif idx + 1 < len(lines):
                        business_name = lines[idx + 1]
                    break

            # Ubicación
            loc_match = re.search(r"Ubicaci[oó]n:\s*(.+)", body, re.IGNORECASE)
            location = loc_match.group(1).strip() if loc_match else None

            # Estado
            status_match = re.search(r"Estado:\s*(.+)", body, re.IGNORECASE)
            status = status_match.group(1).strip() if status_match else "ACTIVO"

            is_active = status.upper() == "ACTIVO"

            return SunatRucInfo(
                ruc=ruc_found,
                business_name=business_name or dni_number,
                trade_name=None,
                status=status,
                condition="N/A",
                fiscal_address=None,
                is_active=is_active,
                is_habido=True,
                is_valid=is_active,
                validated_at=datetime.now(),
                dni=dni_number,
                location=location,
            )

        except ValueError:
            raise
        except Exception as exc:
            logger.error("Error scraping DNI %s: %s", dni_number, exc)
            raise RuntimeError(
                f"Error consultando SUNAT para DNI {dni_number}: {exc}"
            ) from exc
        finally:
            browser.close()


# ─── Dispatcher ──────────────────────────────────────────────────────────────

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def scrape_document(document_number: str, document_type: str = "RUC") -> SunatRucInfo:
    """
    Dispatcher: enruta a `scrape_ruc` o `scrape_dni` según el tipo de documento.

    Args:
        document_number: RUC (11 dígitos) o DNI (8 dígitos).
        document_type:   'RUC' | 'DNI'

    Returns:
        SunatRucInfo con los datos del contribuyente.
    """
    doc_type = document_type.upper().strip()

    if doc_type == "RUC" or len(document_number) == 11:
        return scrape_ruc(document_number)

    if doc_type == "DNI" or len(document_number) == 8:
        return scrape_dni(document_number)

    raise ValueError(
        f"Tipo de documento no soportado: '{document_type}' "
        f"(número: '{document_number}'). Se esperan RUC (11 dígitos) o DNI (8 dígitos)."
    )
