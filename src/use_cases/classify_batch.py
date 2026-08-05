"""Caso de uso: Clasificación automática por lotes usando un LLM local (REQ-5).

Backends soportados (variable LLM_BACKEND en .env):
  - lmstudio : usa /v1/chat/completions  (compatible con OpenAI)
  - ollama   : usa /api/chat

R1: WHEN exista una descripción del comprobante
    THEN SYSTEM SHALL enviar únicamente la descripción al modelo.

R2: WHEN el modelo responda correctamente
    THEN SYSTEM SHALL registrar únicamente el código de la categoría.

R3: WHEN el modelo no pueda determinar una categoría
    THEN SYSTEM SHALL dejar la categoría sin asignar.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

_BASE_URL: str  = os.getenv("BASE_URL",     "http://localhost:1234")
_MODEL: str     = os.getenv("MODEL",        "qwen2.5-1.5b-instruct")
_BACKEND: str   = os.getenv("LLM_BACKEND",  "lmstudio").lower()  # lmstudio | ollama

# Timeout generoso: LM Studio en CPU con modelos pequeños tarda ~5-20s
_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "60"))

_SYSTEM_PROMPT = """Eres un asistente contable especializado en clasificar comprobantes de una empresa que vende repuestos y accesorios para motos, bicicletas y vehículos.

Tu única tarea es devolver el código de categoría que mejor corresponda a la descripción del comprobante.

REGLAS ESTRICTAS:
1. Responde ÚNICAMENTE con el código exacto de la lista. Sin explicaciones, sin texto adicional.
2. Si ninguna categoría encaja, responde: SIN_CATEGORIA
3. El código debe ser exactamente uno de los proporcionados.

CATEGORÍAS DISPONIBLES:
{categories}"""

_USER_PROMPT = "Descripción del comprobante: {description}"


# ─── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass(slots=True)
class ClassifyItem:
    """Ítem individual a clasificar."""
    document_id: int
    description: str
    current_category: str | None = None


@dataclass(slots=True)
class ClassifyItemResult:
    """Resultado de clasificación de un ítem."""
    document_id: int
    description: str
    category_code: str | None
    raw_response: str | None
    elapsed_seconds: float = 0.0
    success: bool = True
    error: str | None = None


@dataclass(slots=True)
class ClassifyBatchResult:
    """Resultado agregado del lote de clasificación."""
    total: int = 0
    classified: int = 0
    skipped: int = 0
    errors: int = 0
    results: list[ClassifyItemResult] = field(default_factory=list)
    total_seconds: float = 0.0

    @property
    def avg_seconds(self) -> float:
        processed = self.classified + self.errors
        return self.total_seconds / processed if processed > 0 else 0.0


# ─── Comunicación con el LLM ──────────────────────────────────────────────────

def _build_categories_text(categories: list[dict[str, Any]]) -> str:
    lines = []
    for cat in categories:
        desc = f" — {cat['description'][:80]}" if cat.get("description") else ""
        lines.append(f"  {cat['code']}: {cat['name']}{desc}")
    return "\n".join(lines)


def _call_lmstudio(
    description: str,
    categories_text: str,
    base_url: str,
    model: str,
    timeout: float,
) -> str:
    """
    Llama al endpoint de LM Studio (compatible OpenAI).
    Prueba /v1/chat/completions primero; si falla con 404 intenta /api/v1/chat/completions.
    Retorna la respuesta cruda del modelo.
    """
    payload = {
        "model": model,
        "temperature": 0,
        "max_tokens": 30,   # solo necesitamos el código de categoría
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT.format(categories=categories_text)},
            {"role": "user",   "content": _USER_PROMPT.format(description=description)},
        ],
    }

    # LM Studio expone /v1/ en versiones recientes; versiones antiguas usan /api/v1/
    endpoints = ["/v1/chat/completions", "/api/v1/chat/completions"]
    last_exc: Exception | None = None

    for endpoint in endpoints:
        try:
            resp = httpx.post(
                f"{base_url.rstrip('/')}{endpoint}",
                json=payload,
                timeout=timeout,
            )
            if resp.status_code == 404:
                last_exc = httpx.HTTPStatusError(
                    f"404 en {endpoint}", request=resp.request, response=resp
                )
                continue
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            logger.debug("LM Studio raw response: %r", raw)
            return raw
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                last_exc = exc
                continue
            raise

    raise last_exc or RuntimeError("No se encontró endpoint válido en LM Studio")


def _call_ollama(
    description: str,
    categories_text: str,
    base_url: str,
    model: str,
    timeout: float,
) -> str:
    """
    Llama al endpoint /api/chat de Ollama.
    Retorna la respuesta cruda del modelo.
    """
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT.format(categories=categories_text)},
            {"role": "user",   "content": _USER_PROMPT.format(description=description)},
        ],
    }
    resp = httpx.post(
        f"{base_url.rstrip('/')}/api/chat",
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "").strip()


def _call_llm(
    description: str,
    categories_text: str,
    base_url: str,
    model: str,
    backend: str,
    timeout: float,
) -> str:
    """Despacha al backend correcto y retorna la respuesta cruda."""
    try:
        if backend == "lmstudio":
            return _call_lmstudio(description, categories_text, base_url, model, timeout)
        else:
            return _call_ollama(description, categories_text, base_url, model, timeout)
    except httpx.TimeoutException:
        raise TimeoutError(
            f"El modelo no respondió en {timeout}s. "
            "Aumenta LLM_TIMEOUT en .env o usa un modelo más pequeño."
        )
    except httpx.ConnectError:
        raise ConnectionError(
            f"No se pudo conectar a {base_url}. "
            "Verifica que LM Studio/Ollama esté corriendo y que BASE_URL sea correcta en .env."
        )
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"HTTP {exc.response.status_code}: {exc.response.text[:200]}")
    except Exception as exc:
        raise RuntimeError(f"Error inesperado: {exc}") from exc


def _parse_category_code(raw: str | None, valid_codes: set[str]) -> str | None:
    """Valida que la respuesta sea un código conocido. Retorna None si no lo es."""
    if not raw:
        return None
    clean = raw.strip().strip('"\'').split()[0].upper() if raw.strip() else ""
    if clean == "SIN_CATEGORIA" or clean not in valid_codes:
        if clean != "SIN_CATEGORIA":
            logger.warning("Respuesta no reconocida como código válido: %r → clean=%r", raw[:80], clean)
        return None
    return clean


# ─── Persistencia ─────────────────────────────────────────────────────────────

def _update_category_in_db(conn, document_id: int, category_code: str | None) -> None:
    conn.execute(
        "UPDATE documents SET category_code = %s, updated_at = NOW() WHERE id = %s",
        (category_code, document_id),
    )


# ─── Caso de uso principal ────────────────────────────────────────────────────

def classify_batch(
    items: list[ClassifyItem],
    batch_size: int = 10,
    base_url: str | None = None,
    model: str | None = None,
    backend: str | None = None,
    save_to_db: bool = True,
    progress_callback=None,
) -> ClassifyBatchResult:
    """
    Clasifica una lista de documentos usando un LLM local en lotes.

    Args:
        items:             Lista de ClassifyItem (document_id + description).
        batch_size:        Documentos por lote (10-30 recomendado).
        base_url:          URL base del servidor. Si None usa BASE_URL del .env.
        model:             Nombre del modelo. Si None usa MODEL del .env.
        backend:           'lmstudio' o 'ollama'. Si None usa LLM_BACKEND del .env.
        save_to_db:        Si True persiste el category_code en PostgreSQL.
        progress_callback: Función callback(item_result, index, total).

    Returns:
        ClassifyBatchResult con estadísticas completas.
    """
    from Persistence.connection import get_conn
    from Persistence.repositories.category_repo import get_active_categories
    from console.rich_logger import log_classify_finish, log_classify_item, log_classify_start

    effective_url     = base_url or _BASE_URL
    effective_model   = model    or _MODEL
    effective_backend = (backend or _BACKEND).lower()

    aggregate = ClassifyBatchResult(total=len(items))
    start_global = time.perf_counter()

    # ── Cargar categorías activas ──────────────────────────────────────────
    try:
        with get_conn() as conn:
            active_cats = get_active_categories(conn)
    except Exception as exc:
        logger.error("No se pudieron cargar categorías: %s", exc)
        aggregate.errors = len(items)
        return aggregate

    valid_codes: set[str] = {c["code"] for c in active_cats}
    categories_text = _build_categories_text(active_cats)

    log_classify_start(
        total=len(items),
        batch_size=batch_size,
        model=effective_model,
        base_url=effective_url,
    )

    # ── Procesar en lotes ──────────────────────────────────────────────────
    for batch_start in range(0, len(items), batch_size):
        batch = items[batch_start: batch_start + batch_size]
        batch_results: list[ClassifyItemResult] = []

        for item in batch:
            index = aggregate.classified + aggregate.errors + aggregate.skipped + 1

            # R1: sin descripción → skip
            if not item.description or not item.description.strip():
                res = ClassifyItemResult(
                    document_id=item.document_id,
                    description="",
                    category_code=None,
                    raw_response=None,
                    success=True,
                    error="Sin descripción",
                )
                aggregate.skipped += 1
                aggregate.results.append(res)
                log_classify_item(
                    index=index, total=len(items), doc_id=item.document_id,
                    description="", category_code=None, elapsed=0.0, skipped=True,
                )
                if progress_callback:
                    progress_callback(res, index, len(items))
                continue

            # ── Llamar al LLM ──────────────────────────────────────────────
            t0 = time.perf_counter()
            raw_response: str | None = None
            category_code: str | None = None
            error_msg: str | None = None
            success = True

            try:
                raw_response = _call_llm(
                    description=item.description,
                    categories_text=categories_text,
                    base_url=effective_url,
                    model=effective_model,
                    backend=effective_backend,
                    timeout=_TIMEOUT,
                )
                # R2: validar código retornado
                category_code = _parse_category_code(raw_response, valid_codes)
                aggregate.classified += 1

            except Exception as exc:  # noqa: BLE001
                # R3: fallo → sin categoría
                error_msg = str(exc)
                success = False
                aggregate.errors += 1
                logger.warning("Error clasificando doc %d: %s", item.document_id, exc)

            elapsed = time.perf_counter() - t0

            res = ClassifyItemResult(
                document_id=item.document_id,
                description=item.description,
                category_code=category_code,
                raw_response=raw_response,
                elapsed_seconds=elapsed,
                success=success,
                error=error_msg,
            )
            batch_results.append(res)
            aggregate.results.append(res)

            log_classify_item(
                index=index, total=len(items), doc_id=item.document_id,
                description=item.description, category_code=category_code,
                elapsed=elapsed, skipped=False, error=error_msg,
            )

            if progress_callback:
                progress_callback(res, index, len(items))

        # ── Persistir lote en BD ───────────────────────────────────────────
        if save_to_db and batch_results:
            try:
                with get_conn() as conn:
                    for r in batch_results:
                        if r.success:
                            _update_category_in_db(conn, r.document_id, r.category_code)
            except Exception as exc:  # noqa: BLE001
                logger.error("Error al guardar clasificación en BD: %s", exc)

    aggregate.total_seconds = time.perf_counter() - start_global
    log_classify_finish(aggregate)
    return aggregate


# ─── Helper para cargar ítems desde la BD ─────────────────────────────────────

def load_unclassified_documents(
    limit: int = 30,
    company_id: int | None = None,
) -> list[ClassifyItem]:
    """
    Carga documentos sin categoría (category_code IS NULL) desde la BD.

    Args:
        limit:      Máximo de documentos a cargar.
        company_id: Filtrar por empresa (opcional).

    Returns:
        Lista de ClassifyItem listos para clasificar.
    """
    from Persistence.connection import get_conn

    params: list[Any] = []
    where = "category_code IS NULL AND description IS NOT NULL AND description <> ''"

    if company_id:
        where += " AND company_id = %s"
        params.append(company_id)

    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT id, description FROM documents WHERE {where} "  # noqa: S608
            f"ORDER BY id DESC LIMIT %s",
            params,
        ).fetchall()

    return [
        ClassifyItem(document_id=row["id"], description=row["description"])
        for row in rows
    ]
