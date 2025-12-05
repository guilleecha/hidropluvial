"""
Funciones para crear e imprimir tablas Rich.
"""

from rich.table import Table
from rich.text import Text
from rich import box

from hidropluvial.cli.theme.palette import get_console, get_palette


def create_results_table(
    title: str = None,
    columns: list[tuple[str, str]] = None,  # [(nombre, justify), ...]
) -> Table:
    """Crea una tabla estilizada para resultados."""
    p = get_palette()

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    if columns:
        for name, justify in columns:
            table.add_column(name, justify=justify)

    return table


def create_analysis_table(show_method: bool = True) -> Table:
    """Crea tabla para resultados de análisis."""
    p = get_palette()

    columns = []
    if show_method:
        columns.append(("Metodo Tc", "left"))
    columns.extend([
        ("Tr", "center"),
        ("Tc", "right"),
        ("tp", "right"),
        ("Tp", "right"),
        ("Qp", "right"),
        ("Vol", "right"),
    ])

    table = Table(
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.SIMPLE,
        show_header=True,
        padding=(0, 1),
    )

    for name, justify in columns:
        table.add_column(name, justify=justify)

    return table


def create_projects_table(title: str = None) -> Table:
    """Crea tabla para listar proyectos."""
    p = get_palette()

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("ID", style=p.accent, justify="left")
    table.add_column("Nombre", justify="left")
    table.add_column("Cuencas", justify="right", style=p.number)
    table.add_column("Analisis", justify="right", style=p.number)

    return table


def create_basins_table(title: str = None) -> Table:
    """Crea tabla para listar cuencas."""
    p = get_palette()

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("ID", style=p.accent, justify="left")
    table.add_column("Nombre", justify="left")
    table.add_column("Area (ha)", justify="right", style=p.number)
    table.add_column("Analisis", justify="right", style=p.number)

    return table


def create_sessions_table(title: str = None) -> Table:
    """Crea tabla para listar sesiones legacy."""
    p = get_palette()

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("ID", style=p.accent, justify="left")
    table.add_column("Nombre", justify="left")
    table.add_column("Analisis", justify="right", style=p.number)

    return table


def print_projects_table(projects: list[dict], title: str = "PROYECTOS") -> None:
    """Imprime tabla de proyectos."""
    console = get_console()
    p = get_palette()

    if not projects:
        console.print("  No hay proyectos.", style=p.muted)
        return

    table = create_projects_table(title)

    for proj in projects:
        name = proj['name'][:35] if len(proj['name']) > 35 else proj['name']
        table.add_row(
            proj['id'],
            name,
            str(proj.get('n_basins', 0)),
            str(proj.get('total_analyses', 0)),
        )

    console.print(table)


def print_basins_table(basins, title: str = "CUENCAS") -> None:
    """Imprime tabla de cuencas (version compacta)."""
    console = get_console()
    p = get_palette()

    if not basins:
        console.print("  No hay cuencas.", style=p.muted)
        return

    table = create_basins_table(title)

    for basin in basins:
        name = basin.name[:35] if len(basin.name) > 35 else basin.name
        table.add_row(
            basin.id,
            name,
            f"{basin.area_ha:.1f}",
            str(len(basin.analyses)),
        )

    console.print(table)


def print_basins_detail_table(basins, title: str = "CUENCAS") -> None:
    """Imprime tabla detallada de cuencas con mas informacion."""
    console = get_console()
    p = get_palette()

    if not basins:
        console.print("  No hay cuencas.", style=p.muted)
        return

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("ID", style=p.accent, justify="left")
    table.add_column("Nombre", justify="left")
    table.add_column("Area", justify="right", style=p.number)
    table.add_column("S%", justify="right", style=p.number)
    table.add_column("C", justify="right", style=p.number)
    table.add_column("CN", justify="right", style=p.number)
    table.add_column("Analisis", justify="right")
    table.add_column("Tr", justify="left", style=p.muted)

    for basin in basins:
        name = basin.name[:25] if len(basin.name) > 25 else basin.name

        # Formatear C y CN
        c_str = f"{basin.c:.2f}" if basin.c else "-"
        cn_str = str(basin.cn) if basin.cn else "-"

        # Obtener periodos de retorno unicos
        if basin.analyses:
            trs = sorted(set(a.storm.return_period for a in basin.analyses))
            tr_str = ",".join(str(t) for t in trs[:4])
            if len(trs) > 4:
                tr_str += "..."
        else:
            tr_str = "-"

        # Contar analisis y colorear segun cantidad
        n_analyses = len(basin.analyses)
        if n_analyses == 0:
            analyses_str = Text("0", style=p.muted)
        elif n_analyses < 5:
            analyses_str = Text(str(n_analyses), style=p.warning)
        else:
            analyses_str = Text(str(n_analyses), style=p.success)

        table.add_row(
            basin.id,
            name,
            f"{basin.area_ha:.1f}",
            f"{basin.slope_pct:.1f}",
            c_str,
            cn_str,
            analyses_str,
            tr_str,
        )

    console.print(table)


def print_sessions_table(sessions: list[dict], title: str = "SESIONES LEGACY") -> None:
    """Imprime tabla de sesiones legacy."""
    console = get_console()
    p = get_palette()

    if not sessions:
        console.print("  No hay sesiones.", style=p.muted)
        return

    table = create_sessions_table(title)

    for sess in sessions:
        name = sess['name'][:35] if len(sess['name']) > 35 else sess['name']
        table.add_row(
            sess['id'],
            name,
            str(sess.get('n_analyses', 0)),
        )

    console.print(table)
