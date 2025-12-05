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


def print_analyses_summary_table(
    analyses,
    title: str = "RESUMEN DE ANALISIS",
    show_sparkline: bool = True,
    sparkline_width: int = 15,
) -> None:
    """
    Imprime tabla resumen de analisis con formato Rich.

    Muestra informacion clave de cada analisis:
    - Idx: Indice para referencia
    - Metodo Tc: Metodo de tiempo de concentracion
    - Tormenta: Tipo de tormenta
    - Tr: Periodo de retorno (anos)
    - Tc: Tiempo de concentracion (min)
    - P: Precipitacion total (mm)
    - Pe: Escorrentia efectiva (mm)
    - Qp: Caudal pico (m3/s) - destacado
    - Tp: Tiempo al pico (min)
    - Vol: Volumen (hm3)
    - Hidrograma: Sparkline visual

    Args:
        analyses: Lista de AnalysisRun
        title: Titulo de la tabla
        show_sparkline: Si mostrar sparklines
        sparkline_width: Ancho del sparkline
    """
    from hidropluvial.cli.preview import sparkline
    from hidropluvial.cli.formatters import format_flow, format_volume_hm3

    console = get_console()
    p = get_palette()

    if not analyses:
        console.print("  No hay analisis.", style=p.muted)
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

    # Columnas
    table.add_column("#", justify="right", style=p.muted, width=3)
    table.add_column("Metodo Tc", justify="left")
    table.add_column("Tormenta", justify="left")
    table.add_column("Tr", justify="right", style=p.number)
    table.add_column("Tc", justify="right", style=p.number)
    table.add_column("P", justify="right", style=p.number)
    table.add_column("Pe", justify="right", style=p.number)
    table.add_column("Qp", justify="right")  # Estilo especial
    table.add_column("Tp", justify="right", style=p.number)
    table.add_column("Vol", justify="right", style=p.number)
    if show_sparkline:
        table.add_column("Hidrograma", justify="left")

    # Encontrar Qp maximo para destacar
    max_qp = max(a.hydrograph.peak_flow_m3s for a in analyses) if analyses else 0

    for idx, analysis in enumerate(analyses):
        hydro = analysis.hydrograph
        storm = analysis.storm
        tc = analysis.tc

        # Formatear valores
        tc_min = f"{tc.tc_min:.0f}" if tc.tc_min else "-"
        p_total = f"{storm.total_depth_mm:.1f}" if storm.total_depth_mm else "-"
        pe = f"{hydro.runoff_mm:.1f}" if hydro.runoff_mm else "-"
        tp = f"{hydro.time_to_peak_min:.0f}" if hydro.time_to_peak_min else "-"
        vol = format_volume_hm3(hydro.volume_m3)

        # Qp con formato especial - destacar el maximo
        qp_val = hydro.peak_flow_m3s
        qp_str = format_flow(qp_val)
        if qp_val == max_qp:
            qp_text = Text(qp_str, style=f"bold {p.accent}")
        else:
            qp_text = Text(qp_str, style=p.number)

        # Tipo de tormenta abreviado
        storm_type = storm.type.upper()[:6]

        # X factor si existe
        method_str = tc.method
        if hydro.x_factor:
            method_str = f"{tc.method} X={hydro.x_factor:.2f}"

        row = [
            str(idx),
            method_str[:18],
            storm_type,
            str(storm.return_period),
            tc_min,
            p_total,
            pe,
            qp_text,
            tp,
            vol,
        ]

        if show_sparkline:
            if hydro.flow_m3s:
                spark = sparkline(hydro.flow_m3s, width=sparkline_width)
                row.append(Text(spark, style=p.info))
            else:
                row.append("-")

        table.add_row(*row)

    console.print(table)

    # Leyenda de unidades
    console.print(
        f"  [dim]Tc: min | P: mm | Pe: mm | Qp: m³/s | Tp: min | Vol: hm³[/dim]"
    )


def print_comparison_table(
    analyses_to_show: list,
    all_analyses: list = None,
    title: str = "COMPARACION DE ANALISIS",
) -> None:
    """
    Imprime tabla de parametros caracteristicos para comparacion de hidrogramas.

    Muestra columnas adicionales para comparacion detallada:
    - tp: tiempo pico del hidrograma unitario (minusculas)
    - Tp: tiempo pico del hidrograma resultante (mayusculas)
    - tb: tiempo base del hidrograma unitario

    Args:
        analyses_to_show: Lista de analisis a mostrar en la tabla
        all_analyses: Lista completa de analisis (para obtener indice original)
        title: Titulo de la tabla
    """
    from hidropluvial.cli.formatters import format_flow, format_volume_hm3

    console = get_console()
    p = get_palette()

    if not analyses_to_show:
        console.print("  No hay analisis para comparar.", style=p.muted)
        return

    if all_analyses is None:
        all_analyses = analyses_to_show

    table = Table(
        title=title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    # Columnas - orden similar al original pero mejor organizado
    table.add_column("#", justify="right", style=p.muted, width=3)
    table.add_column("Metodo Tc", justify="left")
    table.add_column("Tormenta", justify="left")
    table.add_column("Tr", justify="right", style=p.number)
    table.add_column("Tc", justify="right", style=p.number)
    table.add_column("tp", justify="right", style=p.muted)  # tiempo pico unitario
    table.add_column("X", justify="right", style=p.number)
    table.add_column("tb", justify="right", style=p.muted)  # tiempo base
    table.add_column("P", justify="right", style=p.number)
    table.add_column("Pe", justify="right", style=p.number)
    table.add_column("Qp", justify="right")  # Estilo especial para destacar max
    table.add_column("Tp", justify="right", style=p.number)
    table.add_column("Vol", justify="right", style=p.number)

    # Encontrar Qp maximo para destacar
    max_qp = max(a.hydrograph.peak_flow_m3s for a in analyses_to_show)

    for analysis in analyses_to_show:
        # Obtener indice original
        try:
            orig_idx = all_analyses.index(analysis)
        except ValueError:
            orig_idx = 0

        hydro = analysis.hydrograph
        storm = analysis.storm
        tc = analysis.tc

        # Formatear valores
        tc_min = f"{tc.tc_min:.0f}" if tc.tc_min else "-"
        tp_unit = f"{hydro.tp_unit_min:.0f}" if hydro.tp_unit_min else "-"
        x_str = f"{hydro.x_factor:.2f}" if hydro.x_factor else "-"
        tb = f"{hydro.tb_min:.0f}" if hydro.tb_min else "-"
        p_total = f"{storm.total_depth_mm:.1f}" if storm.total_depth_mm else "-"
        pe = f"{hydro.runoff_mm:.1f}" if hydro.runoff_mm else "-"
        tp_result = f"{hydro.time_to_peak_min:.0f}" if hydro.time_to_peak_min else "-"
        vol = format_volume_hm3(hydro.volume_m3)

        # Qp con formato especial - destacar el maximo
        qp_val = hydro.peak_flow_m3s
        qp_str = format_flow(qp_val)
        if qp_val == max_qp:
            qp_text = Text(qp_str, style=f"bold {p.accent}")
        else:
            qp_text = Text(qp_str, style=p.number)

        table.add_row(
            str(orig_idx),
            tc.method[:12],
            storm.type.upper()[:6],
            str(storm.return_period),
            tc_min,
            tp_unit,
            x_str,
            tb,
            p_total,
            pe,
            qp_text,
            tp_result,
            vol,
        )

    console.print(table)

    # Leyenda de notacion
    console.print(
        f"  [dim]tp: pico HU | tb: base HU | Tc, Tp: min | P, Pe: mm | Qp: m³/s | Vol: hm³[/dim]"
    )
