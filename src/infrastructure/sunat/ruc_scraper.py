"""Scraper de RUC en el portal SUNAT usando Playwright (REQ-4).

Consulta https://e-consultaruc.sunat.gob.pe y retorna los datos
del contribuyente: razón social, estado, condición y domicilio fiscal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

SUNAT_RUC_URL = (
    "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
    "?accion=consPorRuc"
)


@dataclass(slots=True)
class SunatRucInfo:
    ruc: str
    business_name: str
    trade_name: str | None
    status: str               # ACTIVO | BAJA DEFINITIVA | …
    condition: str            # HABIDO | NO HABIDO | NO HALLADO
    fiscal_address: str | None
    is_active: bool
    is_habido: bool
    is_valid: bool            # True si ACTIVO + HABIDO
    validated_at: datetime


def scrape_ruc(ruc_number: str) -> SunatRucInfo:
    """
    Consulta los datos de un RUC en el portal SUNAT usando Playwright headless.

    Args:
        ruc_number: RUC de 11 dígitos.

    Returns:
        SunatRucInfo con todos los datos del contribuyente.

    Raises:
        ValueError: RUC inválido o no encontrado en SUNAT.
        RuntimeError: Error de conectividad o respuesta inesperada del portal.
    """
    if len(ruc_number) != 11 or not ruc_number.isdigit():
        raise ValueError(
            f"El RUC '{ruc_number}' debe contener exactamente 11 dígitos numéricos."
        )

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        invalid_detected = False
        dialog_msg = ""

        def _handle_dialog(dialog) -> None:
            nonlocal invalid_detected, dialog_msg
            invalid_detected = True
            dialog_msg = dialog.message
            logger.warning("Alerta SUNAT para RUC %s: %s", ruc_number, dialog_msg)
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

            # ── Extracción de datos ──────────────────────────────────────
            raw_title = (
                page.locator("div.list-group-item")
                .filter(has_text="Número de RUC:")
                .locator("h4")
                .last.inner_text()
            )
            parts = [p.strip() for p in raw_title.split("-", 1)]
            business_name = parts[1] if len(parts) > 1 else raw_title

            trade_name = (
                page.locator("div.list-group-item")
                .filter(has_text="Nombre Comercial:")
                .locator("p")
                .last.inner_text()
                .strip()
            )

            status = (
                page.locator("div.list-group-item")
                .filter(has_text="Estado del Contribuyente:")
                .locator("p")
                .last.inner_text()
                .strip()
            )

            condition = (
                page.locator("div.list-group-item")
                .filter(has_text="Condición del Contribuyente:")
                .locator("p")
                .last.inner_text()
                .strip()
            )

            fiscal_address = (
                page.locator("div.list-group-item")
                .filter(has_text="Domicilio Fiscal:")
                .locator("p")
                .last.inner_text()
                .strip()
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
            logger.error(
                "Error inesperado en scraping SUNAT para RUC %s: %s",
                ruc_number,
                exc,
            )
            raise RuntimeError(
                f"Error consultando SUNAT para RUC {ruc_number}: {exc}"
            ) from exc
        finally:
            browser.close()
