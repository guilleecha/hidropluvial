"""
Funciones que imprimen directamente a la consola.
"""

from rich.panel import Panel
from rich.text import Text
from rich import box

from hidropluvial.cli.theme.palette import get_console, get_palette
from hidropluvial.cli.theme.styled import (
    styled_header, styled_label, styled_success, styled_warning,
    styled_error, styled_info, styled_note, styled_note_box,
    styled_suggestion, styled_suggestion_box,
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
    """Imprime indicador de paso del wizard con barra de progreso visual."""
    console = get_console()
    p = get_palette()

    # Barra de progreso visual más clara
    bar_width = 30
    filled_width = int((step_num / total) * bar_width)
    empty_width = bar_width - filled_width

    # Construir barra con bloques
    filled_bar = "█" * filled_width
    empty_bar = "░" * empty_width
    percentage = int((step_num / total) * 100)

    # Línea de progreso
    progress_line = Text()
    progress_line.append(filled_bar, style=p.primary)
    progress_line.append(empty_bar, style=p.muted)
    progress_line.append(f"  {percentage}%", style=p.muted)

    # Crear panel con el título del paso
    step_title = Text()
    step_title.append(f" Paso {step_num} de {total}", style=f"bold {p.secondary}")

    panel = Panel(
        progress_line,
        title=step_title,
        subtitle=Text(title, style=f"italic {p.muted}"),
        subtitle_align="left",
        title_align="left",
        border_style=p.border,
        box=box.ROUNDED,
        padding=(0, 1),
        width=50,
    )

    console.print()
    console.print(panel)


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


def print_note(text: str) -> None:
    """Imprime una nota informativa destacada."""
    console = get_console()
    console.print(styled_note(text))


def print_note_box(lines: list[str], title: str = "NOTA") -> None:
    """Imprime un panel de nota con múltiples líneas."""
    console = get_console()
    console.print(styled_note_box(lines, title))


def print_suggestion(text: str) -> None:
    """Imprime una sugerencia/recomendación destacada."""
    console = get_console()
    console.print(styled_suggestion(text))


def print_suggestion_box(lines: list[str], title: str = "SUGERENCIA") -> None:
    """Imprime un panel de sugerencia con múltiples líneas."""
    console = get_console()
    console.print(styled_suggestion_box(lines, title))


def print_section(title: str) -> None:
    """Imprime título de sección."""
    console = get_console()
    p = get_palette()
    console.print()
    console.print(f"-- {title} --", style=f"bold {p.secondary}")
    console.print()


def print_subheader(title: str, width: int = 45) -> None:
    """Imprime un subencabezado o separador con título."""
    console = get_console()
    p = get_palette()
    if title:
        console.print(f"\n  {title}", style=f"bold {p.secondary}")
    console.print(f"  {'-' * width}", style=p.border)


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


def print_basin_info(
    basin_name: str,
    basin_id: str,
    project_name: str = None,
    area_ha: float = None,
    slope_pct: float = None,
    n_analyses: int = None,
    return_periods: list[int] = None,
    c: float = None,
    cn: int = None,
) -> None:
    """
    Imprime información de cuenca en un panel estilizado.

    Args:
        basin_name: Nombre de la cuenca
        basin_id: ID de la cuenca
        project_name: Nombre del proyecto (opcional)
        area_ha: Área en hectáreas
        slope_pct: Pendiente en porcentaje
        n_analyses: Número de análisis
        return_periods: Lista de períodos de retorno
        c: Coeficiente de escorrentía
        cn: Número de curva
    """
    from rich.table import Table

    console = get_console()
    p = get_palette()

    # Crear tabla sin bordes para el contenido con mejor espaciado
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),  # Más espacio horizontal entre columnas
        expand=True,
        row_styles=["", ""],  # Alternar estilos si se desea
    )
    table.add_column("Label", style=p.label, width=12)
    table.add_column("Value", style=f"bold {p.number}")

    # Agregar filas según los datos disponibles
    if project_name:
        table.add_row("Proyecto", Text(project_name, style=p.secondary))

    if area_ha is not None:
        area_text = Text()
        area_text.append(f"{area_ha:.1f}", style=f"bold {p.number}")
        area_text.append(" ha", style=p.unit)
        table.add_row("Área", area_text)

    if slope_pct is not None:
        slope_text = Text()
        slope_text.append(f"{slope_pct:.2f}", style=f"bold {p.number}")
        slope_text.append(" %", style=p.unit)
        table.add_row("Pendiente", slope_text)

    if c is not None:
        table.add_row("Coef. C", f"{c:.2f}")

    if cn is not None:
        table.add_row("CN", str(cn))

    if n_analyses is not None:
        n_style = p.success if n_analyses > 0 else p.muted
        table.add_row("Análisis", Text(str(n_analyses), style=n_style))

    if return_periods:
        tr_str = ", ".join(str(tr) for tr in return_periods)
        table.add_row("Tr", Text(tr_str, style=p.muted))

    # Crear título con nombre e ID
    title_text = Text()
    title_text.append(f" {basin_name} ", style=f"bold {p.primary}")
    title_text.append(f"[{basin_id[:8]}]", style=p.muted)

    console.print()  # Espacio antes del panel
    panel = Panel(
        table,
        title=title_text,
        title_align="left",
        border_style=p.primary,
        box=box.ROUNDED,
        padding=(1, 2),  # Más padding interno
    )
    console.print(panel)


def print_project_info(
    project_name: str,
    project_id: str,
    n_basins: int = None,
    n_analyses: int = None,
    description: str = None,
    author: str = None,
    location: str = None,
) -> None:
    """
    Imprime información de proyecto en un panel estilizado.

    Args:
        project_name: Nombre del proyecto
        project_id: ID del proyecto
        n_basins: Número de cuencas
        n_analyses: Número total de análisis
        description: Descripción del proyecto
        author: Autor
        location: Ubicación
    """
    from rich.table import Table

    console = get_console()
    p = get_palette()

    # Crear tabla sin bordes con mejor espaciado
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),  # Más espacio horizontal
        expand=True,
    )
    table.add_column("Label", style=p.label, width=12)
    table.add_column("Value")

    if description:
        table.add_row("Descripción", Text(description, style=p.muted))

    if author:
        table.add_row("Autor", Text(author, style=p.secondary))

    if location:
        table.add_row("Ubicación", Text(location, style=p.secondary))

    if n_basins is not None:
        n_style = p.success if n_basins > 0 else p.muted
        table.add_row("Cuencas", Text(str(n_basins), style=n_style))

    if n_analyses is not None:
        n_style = p.success if n_analyses > 0 else p.muted
        table.add_row("Análisis", Text(str(n_analyses), style=n_style))

    # Crear título
    title_text = Text()
    title_text.append(f" {project_name} ", style=f"bold {p.primary}")
    title_text.append(f"[{project_id[:8]}]", style=p.muted)

    console.print()  # Espacio antes del panel
    panel = Panel(
        table,
        title=title_text,
        title_align="left",
        border_style=p.accent,
        box=box.ROUNDED,
        padding=(1, 2),  # Más padding interno
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
    """Imprime el banner de HidroPluvial con ASCII art."""
    console = get_console()
    p = get_palette()

    # ASCII art logo estilizado
    logo = r"""
    ╦ ╦╦╔╦╗╦═╗╔═╗╔═╗╦  ╦ ╦╦  ╦╦╔═╗╦
    ╠═╣║ ║║╠╦╝║ ║╠═╝║  ║ ║╚╗╔╝║╠═╣║
    ╩ ╩╩═╩╝╩╚═╚═╝╩  ╩═╝╚═╝ ╚╝ ╩╩ ╩╩═╝
    """

    # Contenido del banner
    content = Text()
    content.append(logo, style=f"bold {p.primary}")
    content.append("\n")
    content.append("        ≋≋≋  ", style=f"{p.accent}")
    content.append("Cálculos Hidrológicos", style=f"bold {p.secondary}")
    content.append("  ≋≋≋\n", style=f"{p.accent}")
    content.append("             Uruguay", style=p.muted)

    # Panel con diseño mejorado
    panel = Panel(
        content,
        border_style=p.primary,
        box=box.DOUBLE,
        padding=(0, 2),
        width=54,
    )

    console.print()
    console.print(panel)
    console.print()


def print_completion_banner(n_analyses: int, session_id: str) -> None:
    """Imprime banner de finalización."""
    from rich.table import Table

    console = get_console()
    p = get_palette()

    # Contenido del panel
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        expand=True,
    )
    table.add_column("Label", style=p.label, width=18)
    table.add_column("Value")

    table.add_row("Análisis generados", Text(str(n_analyses), style=f"bold {p.number}"))
    table.add_row("Sesión guardada", Text(session_id, style=f"bold {p.accent}"))

    # Título
    title = Text()
    title.append("✓ ANÁLISIS COMPLETADO", style=f"bold {p.success}")

    panel = Panel(
        table,
        title=title,
        title_align="center",
        border_style=p.success,
        box=box.ROUNDED,
        padding=(1, 2),
    )

    console.print()
    console.print(panel)
    console.print()
