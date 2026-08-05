"""Módulo de visualización del procesamiento en consola con Rich (REQ-11).

R1: Mostrar progreso del procesamiento en tiempo real.
R2: Registrar detalle utilizando Rich en consola.
R3: Mostrar resumen general al finalizar.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from domain.entities.processing_result import BatchProcessSummary

console = Console(stderr=False)

_progress_display: Progress | None = None
_live: Live | None = None


def start_batch(total: int, company_name: str) -> None:
    """Inicia la visualización del procesamiento en consola."""
    global _progress_display, _live

    console.print()
    console.rule(f"[bold cyan]🧾 Inicio de Procesamiento — {company_name}[/bold cyan]")
    console.print(
        f"  [dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]  "
        f"[white]{total} comprobante(s) a procesar[/white]"
    )
    console.print()

    _progress_display = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )
    _live = Live(_progress_display, console=console, refresh_per_second=10)
    _live.start()


def log_processing(filename: str, index: int, total: int) -> None:
    """Registra el inicio del procesamiento de un archivo."""
    if _progress_display is None:
        return
    _progress_display.print(
        f"  [cyan]⚙[/cyan]  [{index}/{total}] Procesando: [bold]{filename}[/bold]"
    )


def log_success(filename: str, elapsed: float, extracted_data=None) -> None:
    """Registra el procesamiento exitoso de un archivo."""
    if _progress_display is None:
        return
    detail_parts = []
    if extracted_data:
        if extracted_data.invoice_type:
            detail_parts.append(extracted_data.invoice_type)
        if extracted_data.series and extracted_data.number:
            detail_parts.append(f"{extracted_data.series}-{extracted_data.number}")
        if extracted_data.total is not None:
            detail_parts.append(f"S/ {extracted_data.total:.2f}")

    detail = "  |  ".join(detail_parts) if detail_parts else ""
    _progress_display.print(
        f"  [green]✓[/green]  [bold]{filename}[/bold]  "
        f"[dim]{detail}[/dim]  [green]({elapsed:.2f}s)[/green]"
    )


def log_error(filename: str, error: str, elapsed: float) -> None:
    """Registra un error en el procesamiento de un archivo."""
    if _progress_display is None:
        return
    _progress_display.print(
        f"  [red]✗[/red]  [bold]{filename}[/bold]  "
        f"[red]{error[:80]}[/red]  [dim]({elapsed:.2f}s)[/dim]"
    )


def log_save_result(saved: int, skipped: int, errors: int) -> None:
    """Registra el resultado del guardado en base de datos."""
    if _progress_display is None:
        console.print(
            f"\n  [bold]BD:[/bold] Guardados=[green]{saved}[/green]  "
            f"Duplicados=[yellow]{skipped}[/yellow]  Errores=[red]{errors}[/red]"
        )
        return
    _progress_display.print(
        f"\n  [bold]BD:[/bold] Guardados=[green]{saved}[/green]  "
        f"Duplicados=[yellow]{skipped}[/yellow]  Errores=[red]{errors}[/red]"
    )


def finish_batch(summary: BatchProcessSummary) -> None:
    """Finaliza la visualización y muestra el resumen del lote (REQ-11 R3)."""
    global _progress_display, _live

    if _live:
        _live.stop()
        _live = None
    _progress_display = None

    # Resumen final con Rich
    table = Table(title="📊 Resumen de Procesamiento", show_lines=True, border_style="cyan")
    table.add_column("Campo", style="bold white", min_width=20)
    table.add_column("Valor", style="white")

    table.add_row("Total comprobantes", str(summary.total_count))
    table.add_row("✅ Procesados OK", f"[green]{summary.processed_count}[/green]")
    table.add_row("❌ Errores", f"[red]{summary.error_count}[/red]")
    table.add_row("⏱ Tiempo total", f"{summary.total_time_seconds:.2f}s")

    if summary.error_count > 0:
        failed_names = [
            r.document.name for r in summary.results if not r.success
        ]
        table.add_row("Archivos con error", "\n".join(failed_names))

    console.print()
    console.print(table)
    console.rule("[dim]Fin del procesamiento[/dim]")
    console.print()


# ─── Validación SUNAT ──────────────────────────────────────────────────────────

def start_sunat_validation(total: int, entity_type: str = "socios") -> None:
    """Encabezado en consola al iniciar validación SUNAT por lote."""
    console.print()
    console.rule(f"[bold yellow]🔍 Validación SUNAT — {entity_type}[/bold yellow]")
    console.print(
        f"  [dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]  "
        f"[white]{total} registro(s) a consultar[/white]"
    )
    console.print()


def log_sunat_item(
    document_number: str,
    document_type: str,
    name: str,
    index: int,
    total: int,
    success: bool,
    elapsed: float,
    status: str | None = None,
    condition: str | None = None,
    is_valid: bool = False,
    error: str | None = None,
) -> None:
    """Registra el resultado de una consulta SUNAT individual con tiempo."""
    st_upper = (status or "").upper()
    if success and is_valid:
        icon = "[green]✓[/green]"
        detail = f"[green]{status or ''}[/green]  [dim]{condition or ''}[/dim]"
    elif success and not is_valid:
        if "BAJA" in st_upper or "INACTIVO" in st_upper:
            icon = "[red]✗[/red]"
            detail = f"[red]{status or ''}[/red]  [dim]{condition or ''}[/dim]"
        else:
            icon = "[yellow]⚠[/yellow]"
            detail = f"[yellow]{status or ''}[/yellow]  [dim]{condition or ''}[/dim]"
    else:
        icon = "[red]✗[/red]"
        detail = f"[red]{(error or 'Error desconocido')[:80]}[/red]"

    console.print(
        f"  {icon}  [{index}/{total}] [bold]{document_number}[/bold]  "
        f"[dim]({document_type})[/dim]  {name[:40]}  {detail}  "
        f"[dim]({elapsed:.2f}s)[/dim]"
    )


def finish_sunat_validation(
    total: int,
    valid: int,
    invalid: int,
    errors: int,
    elapsed_total: float,
    entity_type: str = "socios",
) -> None:
    """Resumen final de la validación SUNAT con Rich."""
    table = Table(
        title=f"📋 Resumen Validación SUNAT — {entity_type}",
        show_lines=True,
        border_style="yellow",
    )
    table.add_column("Campo", style="bold white", min_width=22)
    table.add_column("Valor", style="white")

    table.add_row("Total consultados", str(total))
    table.add_row("✅ Válidos (Activo/Habido)", f"[green]{valid}[/green]")
    table.add_row("⚠ Inactivos/No Habido", f"[yellow]{invalid}[/yellow]")
    table.add_row("❌ Errores de consulta", f"[red]{errors}[/red]")
    table.add_row("⏱ Tiempo total", f"{elapsed_total:.2f}s")
    if total > 0:
        avg = elapsed_total / total
        table.add_row("⏱ Promedio por registro", f"{avg:.2f}s")

    console.print()
    console.print(table)
    console.rule("[dim]Fin de validación SUNAT[/dim]")
    console.print()



# ─── Clasificación automática con Ollama (REQ-5) ──────────────────────────────

def log_classify_start(
    total: int,
    batch_size: int,
    model: str,
    base_url: str,
) -> None:
    """Encabezado en consola al iniciar la clasificación por lotes."""
    console.print()
    console.rule("[bold magenta]🤖 Clasificación Automática con Ollama[/bold magenta]")
    console.print(
        f"  [dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]  "
        f"[white]{total} comprobante(s)[/white]  │  "
        f"[cyan]Lote de {batch_size}[/cyan]  │  "
        f"[yellow]{model}[/yellow]  │  "
        f"[dim]{base_url}[/dim]"
    )
    console.print()


def log_classify_item(
    index: int,
    total: int,
    doc_id: int,
    description: str,
    category_code: str | None,
    elapsed: float,
    skipped: bool = False,
    error: str | None = None,
) -> None:
    """Registra el resultado de clasificación de un documento individual."""
    desc_preview = (description[:60] + "…") if len(description) > 60 else description

    if skipped:
        console.print(
            f"  [dim]–[/dim]  [{index}/{total}] "
            f"[dim]doc#{doc_id}[/dim]  [dim]Sin descripción — omitido[/dim]"
        )
    elif error:
        console.print(
            f"  [red]✗[/red]  [{index}/{total}] "
            f"[dim]doc#{doc_id}[/dim]  [italic]{desc_preview}[/italic]  "
            f"[red]{error[:80]}[/red]  [dim]({elapsed:.2f}s)[/dim]"
        )
    elif category_code:
        console.print(
            f"  [green]✓[/green]  [{index}/{total}] "
            f"[dim]doc#{doc_id}[/dim]  [italic]{desc_preview}[/italic]  "
            f"→  [bold green]{category_code}[/bold green]  "
            f"[dim]({elapsed:.2f}s)[/dim]"
        )
    else:
        console.print(
            f"  [yellow]?[/yellow]  [{index}/{total}] "
            f"[dim]doc#{doc_id}[/dim]  [italic]{desc_preview}[/italic]  "
            f"→  [yellow]SIN_CATEGORIA[/yellow]  [dim]({elapsed:.2f}s)[/dim]"
        )


def log_classify_finish(result: Any) -> None:
    """Resumen final de la clasificación por lotes con Rich."""
    table = Table(
        title="🤖 Resumen de Clasificación Automática",
        show_lines=True,
        border_style="magenta",
    )
    table.add_column("Campo", style="bold white", min_width=24)
    table.add_column("Valor", style="white")

    table.add_row("Total documentos", str(result.total))
    table.add_row("✅ Clasificados", f"[green]{result.classified}[/green]")
    table.add_row("⏭ Omitidos (sin desc.)", f"[dim]{result.skipped}[/dim]")
    table.add_row("❌ Errores", f"[red]{result.errors}[/red]")
    table.add_row("⏱ Tiempo total", f"{result.total_seconds:.2f}s")
    if result.classified + result.errors > 0:
        table.add_row("⏱ Promedio por doc", f"{result.avg_seconds:.2f}s")

    console.print()
    console.print(table)
    console.rule("[dim]Fin de clasificación[/dim]")
    console.print()
