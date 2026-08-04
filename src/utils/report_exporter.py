"""Exportador de reportes de prueba (Markdown + JSON) para inspección y comparación de extracción.

Guarda reportes en la carpeta output_tests/ en la raíz del proyecto.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

# Buscar la raíz del proyecto (comprobantes_extractor)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_TESTS_DIR = BASE_DIR / "output_tests"


def _to_dict(obj: Any) -> dict[str, Any]:
    """Convierte dataclass o pydantic model a dict."""
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, dict):
        return obj
    return {"data": str(obj)}


def save_test_reports(
    filename: str,
    raw_text: str,
    extracted_data: Any,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """
    Genera y guarda reportes Markdown y JSON en la carpeta de salidas.

    Args:
        filename: Nombre del archivo procesado (ej. "prueba02.jpeg")
        raw_text: Texto crudo extraído por OCR/Extractor
        extracted_data: Objeto ExtractedData o InvoiceData con los datos parseados
        output_dir: Directorio de destino opcional (por defecto BASE_DIR/output_tests)

    Returns:
        Tupla con las rutas del archivo Markdown y el archivo JSON generados.
    """
    out_dir = output_dir or OUTPUT_TESTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(filename).stem

    md_path = out_dir / f"{stem}_report.md"
    json_path = out_dir / f"{stem}_report.json"

    data_dict = _to_dict(extracted_data)

    # 1. Generar JSON con sangría
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "file_name": filename,
                "raw_text": raw_text,
                "parsed_data": data_dict,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    # 2. Generar Markdown estructurado
    md_content = []
    md_content.append(f"# Reporte de Extracción - `{filename}`\n")
    md_content.append("## 1. Datos Extraídos Parseados\n")
    md_content.append("| Campo | Valor |")
    md_content.append("| :--- | :--- |")

    for k, v in data_dict.items():
        if k in ("raw_text", "extraction_warnings"):
            continue
        val_str = f"`{v}`" if v is not None else "*No encontrado*"
        md_content.append(f"| **{k}** | {val_str} |")

    warnings = data_dict.get("extraction_warnings")
    if warnings:
        md_content.append("\n### ⚠️ Advertencias")
        for w in warnings:
            md_content.append(f"- {w}")

    md_content.append("\n## 2. Texto Crudo Extraído (OCR/Extractor)\n")
    md_content.append("```txt")
    md_content.append(raw_text.strip() if raw_text else "(Sin texto extraído)")
    md_content.append("```\n")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content))

    return md_path, json_path
