"""
Funciones que imprimen directamente a la consola.
"""

from rich.panel import Panel
from rich.text import Text
from rich import box

from hidropluvial.cli.theme.palette import get_console, get_palette
from hidropluvial.cli.theme.styled import (
    styled_header, styled_label, styled_success, styled_warning,
    styled_error, styled_info,
)


def format_number(value: float, decimals: int = 2) -> str:
    """Formatea un número con precisión especificada."""
    if abs(value) >= 1000:
        return f"{value:,.{decimals}f}"
    return f"{value:.{decimals}f}"


def print_separator(char: str = "-", width: int = 60) -> None:
    """Imprime un separador."""
    console = get_console()
    p = get_palette()
    console.print(char * width, style=p.border)


def print_header(text: str, subtitle: str = None) -> None:
    """Imprime un encabezado."""
    console = get_console()
    console.print(styled_header(text, subtitle))


def print_step(step_num: int, total: int, title: str) -> None:
    """Imprime indicador de paso del wizard."""
    console = get_console()
    p = get_palette()

    text = Text()
    text.append(f"[{step_num}/{total}] ", style=p.muted)
    text.append(title, style=f"bold {p.secondary}")
    console.print(text)


def print_field(label: str, value, unit: str = None, indent: int = 2) -> None:
    """Imprime un campo con valor."""
    console = get_console()
    prefix = " " * indent
    console.print(prefix, styled_label(label, value, unit))


def print_success(text: str) -> None:
    """Imprime mensaje de éxito."""
    console = get_console()
    console.print(styled_success(text))


def print_warning(text: str) -> None:
    """Imprime advertencia."""
    console = get_console()
    console.print(styled_warning(text))


def print_error(text: str) -> None:
    """Imprime error."""
    console = get_console()
    console.print(styled_error(text))


def print_info(text: str) -> None:
    """Imprime información."""
    console = get_console()
    console.print(styled_info(text))


def print_section(title: str) -> None:
    """Imprime título de sección."""
    console = get_console()
    p = get_palette()
    console.print()
    console.print(f"-- {title} --", style=f"bold {p.secondary}")
    console.print()


def print_result_row(label: str, value, unit: str = None, highlight: bool = False) -> None:
    """Imprime una fila de resultado."""
    console = get_console()
    p = get_palette()

    style = f"bold {p.accent}" if highlight else p.number
    text = Text()
    text.append(f"  {label}: ", style=p.label)
    text.append(str(value), style=style)
    if unit:
        text.append(f" {unit}", style=p.unit)
    console.print(text)


def print_summary_box(title: str, items: list[tuple[str, str, str]]) -> None:
    """Imprime un cuadro de resumen.

    Args:
        title: Título del cuadro
        items: Lista de tuplas (label, value, unit)
    """
    console = get_console()
    p = get_palette()

    lines = []
    for label, value, unit in items:
        line = Text()
        line.append(f"{label}: ", style=p.label)
        line.append(str(value), style=f"bold {p.number}")
        if unit:
            line.append(f" {unit}", style=p.unit)
        lines.append(line)

    content = Text("\n").join(lines)

    panel = Panel(
        content,
        title=title,
        title_align="left",
        border_style=p.border,
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)


def print_analysis_summary(
    cuenca: str,
    area: float,
    tc_method: str,
    tc_min: float,
    storm: str,
    tr: int,
    qpeak: float,
    volume: float,
    tp: float = None,
) -> None:
    """Imprime resumen de un análisis."""
    console = get_console()
    p = get_palette()

    # Título
    title = Text()
    title.append(f"Analisis: ", style=p.label)
    title.append(f"{cuenca}", style=f"bold {p.primary}")
    title.append(f" | ", style=p.muted)
    title.append(f"{tc_method}", style=p.secondary)
    title.append(f" | ", style=p.muted)
    title.append(f"{storm} Tr{tr}", style=p.secondary)

    console.print(title)

    # Resultados
    results = Text()
    results.append(f"  Qp = ", style=p.label)
    results.append(f"{qpeak:.2f}", style=f"bold {p.accent}")
    results.append(f" m3/s", style=p.unit)
    results.append(f"  |  ", style=p.muted)
    results.append(f"Vol = ", style=p.label)
    results.append(f"{volume:.4f}", style=f"bold {p.number}")
    results.append(f" hm3", style=p.unit)
    if tp:
        results.append(f"  |  ", style=p.muted)
        results.append(f"Tp = ", style=p.label)
        results.append(f"{tp:.1f}", style=f"bold {p.number}")
        results.append(f" min", style=p.unit)

    console.print(results)


def print_banner() -> None:
    """Imprime el banner de HidroPluvial."""
    console = get_console()
    p = get_palette()

    banner = """
+-------------------------------------------------------------+
|         HIDROPLUVIAL - Asistente de Analisis                |
|         Calculos hidrologicos para Uruguay                  |
+-------------------------------------------------------------+
"""
    console.print(banner, style=p.primary)


def print_completion_banner(n_analyses: int, session_id: str) -> None:
    """Imprime banner de finalización."""
    console = get_console()
    p = get_palette()

    console.print()
    console.print("=" * 60, style=p.border)

    title = Text()
    title.append("  ANALISIS COMPLETADO", style=f"bold {p.success}")
    console.print(title)

    console.print("=" * 60, style=p.border)

    info = Text()
    info.append(f"\n  Analisis generados: ", style=p.label)
    info.append(f"{n_analyses}", style=f"bold {p.number}")
    info.append(f"\n  Sesion guardada: ", style=p.label)
    info.append(f"{session_id}", style=f"bold {p.accent}")
    console.print(info)
    console.print()
