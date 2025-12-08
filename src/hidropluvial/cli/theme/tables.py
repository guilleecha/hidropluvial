"""
Funciones para crear e imprimir tablas Rich.
"""

from typing import TYPE_CHECKING

from rich.table import Table
from rich.text import Text
from rich import box

from hidropluvial.cli.theme.palette import get_console, get_palette

if TYPE_CHECKING:
    from hidropluvial.core.coefficients import (
        CoefficientEntry, ChowCEntry, FHWACEntry, CNEntry
    )


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


def print_analyses_summary_table(
    analyses,
    title: str = "RESUMEN DE ANALISIS",
    show_sparkline: bool = True,
    sparkline_width: int = 15,
) -> None:
    """
    Imprime tabla resumen de analisis con formato Rich.

    Muestra informacion clave de cada analisis:
    - #: Indice para referencia
    - Metodo Tc: Metodo de tiempo de concentracion
    - Tc: Tiempo de concentracion (min)
    - X: Factor morfologico
    - tp: Tiempo pico del hidrograma unitario (min)
    - Abst: Metodo de abstraccion y coeficiente (C o CN)
    - Tormenta: Tipo de tormenta
    - Dur: Duracion de la tormenta (min)
    - Tr: Periodo de retorno (anos)
    - P: Precipitacion total (mm)
    - Pe: Escorrentia efectiva (mm)
    - Qp: Caudal pico (m3/s) - destacado
    - Vol: Volumen (hm3)
    - Hidrograma: Sparkline visual

    Args:
        analyses: Lista de AnalysisRun
        title: Titulo de la tabla
        show_sparkline: Si mostrar sparklines
        sparkline_width: Ancho del sparkline
    """
    from hidropluvial.cli.preview import sparkline
    from hidropluvial.cli.formatters import format_flow

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

    # Columnas agrupadas logicamente
    table.add_column("#", justify="right", style=p.muted, width=3)
    table.add_column("Metodo Tc", justify="left")
    table.add_column("Tc", justify="right", style=p.number)
    table.add_column("X", justify="right", style=p.number)
    table.add_column("tp", justify="right", style=p.muted)
    table.add_column("Abst", justify="left")  # Abstraccion: C=0.5 o CN=75
    table.add_column("Tormenta", justify="left")
    table.add_column("Dur", justify="right", style=p.number)  # Duracion (h)
    table.add_column("Tr", justify="right", style=p.number)
    table.add_column("P", justify="right", style=p.number)
    table.add_column("Pe", justify="right", style=p.number)
    table.add_column("Qp", justify="right")
    table.add_column("Vol", justify="right", style=p.number)
    if show_sparkline:
        table.add_column("Hidrograma", justify="left")

    # Encontrar Qp maximo para destacar
    max_qp = max(a.hydrograph.peak_flow_m3s for a in analyses) if analyses else 0

    for idx, analysis in enumerate(analyses):
        hydro = analysis.hydrograph
        storm = analysis.storm
        tc = analysis.tc

        # Formatear valores basicos
        tc_min = f"{tc.tc_min:.0f}" if tc.tc_min else "-"
        x_str = f"{hydro.x_factor:.2f}" if hydro.x_factor else "-"
        tp_unit = f"{hydro.tp_unit_min:.0f}" if hydro.tp_unit_min else "-"

        # Abstraccion: obtener C o CN de los parametros
        abst_str = "-"
        params = tc.parameters or {}
        if "c" in params:
            c_val = params["c"]
            abst_str = f"C={c_val:.2f}"
        elif "cn_adjusted" in params:
            cn_val = params["cn_adjusted"]
            abst_str = f"CN={cn_val:.0f}"
        elif "cn" in params:
            cn_val = params["cn"]
            abst_str = f"CN={cn_val:.0f}"

        # Tormenta
        storm_type = storm.type.upper()[:6]
        dur_hr = f"{storm.duration_hr:.1f}" if storm.duration_hr else "-"

        # Precipitacion
        p_total = f"{storm.total_depth_mm:.1f}" if storm.total_depth_mm else "-"
        pe = f"{hydro.runoff_mm:.1f}" if hydro.runoff_mm else "-"

        # Qp con formato especial - destacar el maximo
        qp_val = hydro.peak_flow_m3s
        qp_str = format_flow(qp_val)
        if qp_val == max_qp:
            qp_text = Text(qp_str, style=f"bold {p.accent}")
        else:
            qp_text = Text(qp_str, style=p.number)

        # Volumen con 2 decimales
        vol_hm3 = hydro.volume_m3 / 1e6
        vol_str = f"{vol_hm3:.2f}"

        row = [
            str(idx),
            tc.method[:12],
            tc_min,
            x_str,
            tp_unit,
            abst_str,
            storm_type,
            dur_hr,
            str(storm.return_period),
            p_total,
            pe,
            qp_text,
            vol_str,
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
        f"  [dim]Tc, tp: min | Dur: h | Abst: C o CN | P, Pe: mm | Qp: m3/s | Vol: hm3[/dim]"
    )


def print_comparison_table(
    analyses_to_show: list,
    all_analyses: list = None,
    title: str = "COMPARACION DE ANALISIS",
) -> None:
    """
    Imprime tabla de parametros caracteristicos para comparacion de hidrogramas.

    Usa el mismo formato que print_analyses_summary_table para consistencia.

    Args:
        analyses_to_show: Lista de analisis a mostrar en la tabla
        all_analyses: Lista completa de analisis (para obtener indice original)
        title: Titulo de la tabla
    """
    from hidropluvial.cli.formatters import format_flow

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

    # Columnas - mismas que print_analyses_summary_table (sin sparkline)
    table.add_column("#", justify="right", style=p.muted, width=3)
    table.add_column("Metodo Tc", justify="left")
    table.add_column("Tc", justify="right", style=p.number)
    table.add_column("X", justify="right", style=p.number)
    table.add_column("tp", justify="right", style=p.muted)
    table.add_column("Abst", justify="left")  # Abstraccion: C=0.5 o CN=75
    table.add_column("Tormenta", justify="left")
    table.add_column("Dur", justify="right", style=p.number)  # Duracion (h)
    table.add_column("Tr", justify="right", style=p.number)
    table.add_column("P", justify="right", style=p.number)
    table.add_column("Pe", justify="right", style=p.number)
    table.add_column("Qp", justify="right")  # Estilo especial para destacar max
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

        # Formatear valores basicos
        tc_min = f"{tc.tc_min:.0f}" if tc.tc_min else "-"
        x_str = f"{hydro.x_factor:.2f}" if hydro.x_factor else "-"
        tp_unit = f"{hydro.tp_unit_min:.0f}" if hydro.tp_unit_min else "-"

        # Abstraccion: obtener C o CN de los parametros
        abst_str = "-"
        params = tc.parameters or {}
        if "c" in params:
            c_val = params["c"]
            abst_str = f"C={c_val:.2f}"
        elif "cn_adjusted" in params:
            cn_val = params["cn_adjusted"]
            abst_str = f"CN={cn_val:.0f}"
        elif "cn" in params:
            cn_val = params["cn"]
            abst_str = f"CN={cn_val:.0f}"

        # Tormenta
        storm_type = storm.type.upper()[:6]
        dur_hr = f"{storm.duration_hr:.1f}" if storm.duration_hr else "-"

        # Precipitacion
        p_total = f"{storm.total_depth_mm:.1f}" if storm.total_depth_mm else "-"
        pe = f"{hydro.runoff_mm:.1f}" if hydro.runoff_mm else "-"

        # Qp con formato especial - destacar el maximo
        qp_val = hydro.peak_flow_m3s
        qp_str = format_flow(qp_val)
        if qp_val == max_qp:
            qp_text = Text(qp_str, style=f"bold {p.accent}")
        else:
            qp_text = Text(qp_str, style=p.number)

        # Volumen con 2 decimales
        vol_hm3 = hydro.volume_m3 / 1e6
        vol_str = f"{vol_hm3:.2f}"

        table.add_row(
            str(orig_idx),
            tc.method[:12],
            tc_min,
            x_str,
            tp_unit,
            abst_str,
            storm_type,
            dur_hr,
            str(storm.return_period),
            p_total,
            pe,
            qp_text,
            vol_str,
        )

    console.print(table)

    # Leyenda de unidades (misma que print_analyses_summary_table)
    console.print(
        f"  [dim]Tc, tp: min | Dur: h | Abst: C o CN | P, Pe: mm | Qp: m3/s | Vol: hm3[/dim]"
    )


# =============================================================================
# TABLAS DE COEFICIENTES C y CN
# =============================================================================

def print_c_table_chow(
    table: list["ChowCEntry"],
    title: str = "Tabla Ven Te Chow - Applied Hydrology",
    selection_mode: bool = False,
) -> None:
    """
    Imprime tabla de coeficientes C (Ven Te Chow) con formato Rich.

    Args:
        table: Lista de ChowCEntry
        title: Título de la tabla
        selection_mode: Si True, destaca la columna Tr2 como seleccionable
    """
    from hidropluvial.cli.theme.styled import styled_note_box

    console = get_console()
    p = get_palette()

    rich_table = Table(
        title=title,
        title_style=f"bold {p.table_header}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    # Columnas
    rich_table.add_column("#", justify="right", style=p.muted, width=3)
    rich_table.add_column("Categoria", justify="left", style=p.table_category)
    rich_table.add_column("Descripcion", justify="left")

    if selection_mode:
        # Tr2 destacado como seleccionable
        rich_table.add_column("Tr2", justify="right", style=f"bold {p.table_highlight}")
        rich_table.add_column("Tr5", justify="right", style=p.muted)
        rich_table.add_column("Tr10", justify="right", style=p.muted)
        rich_table.add_column("Tr25", justify="right", style=p.muted)
        rich_table.add_column("Tr50", justify="right", style=p.muted)
        rich_table.add_column("Tr100", justify="right", style=p.muted)
    else:
        # Todos los valores con mismo estilo
        for tr in ["Tr2", "Tr5", "Tr10", "Tr25", "Tr50", "Tr100"]:
            rich_table.add_column(tr, justify="right", style=p.number)

    current_category = ""
    for i, entry in enumerate(table):
        # Agregar separador visual entre categorías
        if entry.category != current_category and current_category:
            rich_table.add_row(*[""] * 9)  # Fila vacía como separador
        current_category = entry.category

        rich_table.add_row(
            str(i + 1),
            entry.category,
            entry.description,
            f"{entry.c_tr2:.2f}",
            f"{entry.c_tr5:.2f}",
            f"{entry.c_tr10:.2f}",
            f"{entry.c_tr25:.2f}",
            f"{entry.c_tr50:.2f}",
            f"{entry.c_tr100:.2f}",
        )

    console.print(rich_table)

    # Nota informativa
    if selection_mode:
        console.print(styled_note_box([
            "Selecciona el coeficiente C para Tr=2 años (columna Tr2).",
            "El valor se ajustará automáticamente según el Tr del análisis.",
            "Los valores Tr5-Tr100 son de referencia.",
        ]))
    else:
        console.print(styled_note_box([
            "Para ponderación, se usa C(Tr2) y se ajusta según Tr del análisis."
        ]))


def print_c_table_fhwa(
    table: list["FHWACEntry"],
    title: str = "Tabla FHWA HEC-22",
    tr: int = 10,
) -> None:
    """
    Imprime tabla de coeficientes C (FHWA) con formato Rich.

    Args:
        table: Lista de FHWACEntry
        title: Título de la tabla
        tr: Periodo de retorno para mostrar C ajustado
    """
    from hidropluvial.cli.theme.styled import styled_note_box

    console = get_console()
    p = get_palette()

    rich_table = Table(
        title=title,
        title_style=f"bold {p.table_header}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    rich_table.add_column("#", justify="right", style=p.muted, width=3)
    rich_table.add_column("Categoria", justify="left", style=p.table_category)
    rich_table.add_column("Descripcion", justify="left")
    rich_table.add_column("C base", justify="right", style=p.number)
    rich_table.add_column(f"C (Tr={tr})", justify="right", style=f"bold {p.table_highlight}")

    current_category = ""
    for i, entry in enumerate(table):
        if entry.category != current_category and current_category:
            rich_table.add_row(*[""] * 5)
        current_category = entry.category

        c_adj = entry.get_c(tr)
        rich_table.add_row(
            str(i + 1),
            entry.category,
            entry.description,
            f"{entry.c_base:.2f}",
            f"{c_adj:.2f}",
        )

    console.print(rich_table)

    console.print(styled_note_box([
        "Factores de ajuste FHWA por Tr:",
        "  Tr ≤ 10: 1.00  |  Tr=25: 1.10  |  Tr=50: 1.20  |  Tr=100: 1.25"
    ]))


def print_c_table_simple(
    table: list["CoefficientEntry"],
    title: str = "Tabla de Coeficientes C",
) -> None:
    """
    Imprime tabla de coeficientes C simple (rango min-max) con formato Rich.

    Args:
        table: Lista de CoefficientEntry
        title: Título de la tabla
    """
    console = get_console()
    p = get_palette()

    rich_table = Table(
        title=title,
        title_style=f"bold {p.table_header}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    rich_table.add_column("#", justify="right", style=p.muted, width=3)
    rich_table.add_column("Categoria", justify="left", style=p.table_category)
    rich_table.add_column("Descripcion", justify="left")
    rich_table.add_column("C min", justify="right", style=p.number)
    rich_table.add_column("C max", justify="right", style=p.number)
    rich_table.add_column("C típico", justify="right", style=f"bold {p.table_highlight}")

    current_category = ""
    for i, entry in enumerate(table):
        if entry.category != current_category and current_category:
            rich_table.add_row(*[""] * 6)
        current_category = entry.category

        rich_table.add_row(
            str(i + 1),
            entry.category,
            entry.description,
            f"{entry.c_min:.2f}",
            f"{entry.c_max:.2f}",
            f"{entry.c_recommended:.2f}",
        )

    console.print(rich_table)


def print_cn_table(
    table: list["CNEntry"],
    title: str = "Tabla SCS - Curva Número",
    highlight_group: str = None,
) -> None:
    """
    Imprime tabla de CN con formato Rich.

    Args:
        table: Lista de CNEntry
        title: Título de la tabla
        highlight_group: Grupo de suelo a resaltar (A, B, C, D)
    """
    from hidropluvial.cli.theme.styled import styled_note_box

    console = get_console()
    p = get_palette()

    # Determinar estilos de columnas según grupo resaltado
    style_a = f"bold {p.table_highlight}" if highlight_group == "A" else p.muted
    style_b = f"bold {p.table_highlight}" if highlight_group == "B" else p.muted
    style_c = f"bold {p.table_highlight}" if highlight_group == "C" else p.muted
    style_d = f"bold {p.table_highlight}" if highlight_group == "D" else p.muted

    # Si hay grupo resaltado, mostrar tabla simplificada con solo esa columna
    if highlight_group:
        rich_table = Table(
            title=f"{title} (Suelo {highlight_group})",
            title_style=f"bold {p.table_header}",
            border_style=p.border,
            header_style=f"bold {p.secondary}",
            box=box.ROUNDED,
            show_header=True,
            padding=(0, 1),
        )

        rich_table.add_column("#", justify="right", style=p.muted, width=3)
        rich_table.add_column("Categoría", justify="left", style=p.table_category)
        rich_table.add_column("Descripción", justify="left")
        rich_table.add_column("Cond.", justify="center", style=p.muted)
        rich_table.add_column(f"CN ({highlight_group})", justify="right", style=f"bold {p.number}")

        current_category = ""
        for i, entry in enumerate(table):
            if entry.category != current_category and current_category:
                rich_table.add_row(*[""] * 5)
            current_category = entry.category

            cn_val = entry.get_cn(highlight_group)
            rich_table.add_row(
                str(i + 1),
                entry.category,
                entry.description,
                entry.condition[:3] if entry.condition != "N/A" else "-",
                str(cn_val),
            )
    else:
        # Tabla completa con todos los grupos
        rich_table = Table(
            title=title,
            title_style=f"bold {p.table_header}",
            border_style=p.border,
            header_style=f"bold {p.secondary}",
            box=box.ROUNDED,
            show_header=True,
            padding=(0, 1),
        )

        rich_table.add_column("#", justify="right", style=p.muted, width=3)
        rich_table.add_column("Categoría", justify="left", style=p.table_category)
        rich_table.add_column("Descripción", justify="left")
        rich_table.add_column("Cond.", justify="center", style=p.muted)
        rich_table.add_column("A", justify="right", style=style_a)
        rich_table.add_column("B", justify="right", style=style_b)
        rich_table.add_column("C", justify="right", style=style_c)
        rich_table.add_column("D", justify="right", style=style_d)

        current_category = ""
        for i, entry in enumerate(table):
            if entry.category != current_category and current_category:
                rich_table.add_row(*[""] * 8)
            current_category = entry.category

            rich_table.add_row(
                str(i + 1),
                entry.category,
                entry.description,
                entry.condition[:3] if entry.condition != "N/A" else "-",
                str(entry.cn_a),
                str(entry.cn_b),
                str(entry.cn_c),
                str(entry.cn_d),
            )

    console.print(rich_table)

    # Mostrar nota sobre grupos de suelo solo si no hay grupo resaltado
    if not highlight_group:
        console.print(styled_note_box([
            "Grupos hidrológicos de suelo:",
            "  A: Alta infiltración (arena, grava)",
            "  B: Moderada infiltración (limo arenoso)",
            "  C: Baja infiltración (limo arcilloso)",
            "  D: Muy baja infiltración (arcilla)",
        ], title="GRUPOS DE SUELO"))


def print_summary_table(session_name: str, rows: list[dict]) -> None:
    """
    Imprime tabla resumen comparativa de analisis con formato Rich.

    Args:
        session_name: Nombre de la sesion
        rows: Lista de diccionarios con datos de cada analisis
    """
    from hidropluvial.cli.formatters import format_flow, format_volume_hm3

    console = get_console()
    p = get_palette()

    if not rows:
        console.print("  No hay analisis.", style=p.muted)
        return

    table = Table(
        title=f"RESUMEN COMPARATIVO - {session_name}",
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    # Columnas
    table.add_column("ID", style=p.accent, justify="left")
    table.add_column("Tc", justify="left")
    table.add_column("Tc(min)", justify="right", style=p.number)
    table.add_column("tp(min)", justify="right", style=p.muted)
    table.add_column("X", justify="right", style=p.number)
    table.add_column("tb(min)", justify="right", style=p.muted)
    table.add_column("Tormenta", justify="left")
    table.add_column("Tr", justify="right", style=p.number)
    table.add_column("Qp(m3/s)", justify="right")
    table.add_column("Tp(min)", justify="right", style=p.number)
    table.add_column("Vol(hm3)", justify="right", style=p.number)

    # Encontrar maximo Qp
    max_qp = max(r['qpeak_m3s'] for r in rows) if rows else 0

    for r in rows:
        x_str = f"{r['x']:.2f}" if r.get('x') else "-"
        tp_str = f"{r['tp_min']:.1f}" if r.get('tp_min') else "-"
        tb_str = f"{r['tb_min']:.1f}" if r.get('tb_min') else "-"
        Tp_str = f"{r['Tp_min']:.1f}" if r.get('Tp_min') else "-"

        # Destacar Qp maximo
        qp_val = r['qpeak_m3s']
        qp_str = format_flow(qp_val)
        if qp_val == max_qp:
            qp_text = Text(qp_str, style=f"bold {p.accent}")
        else:
            qp_text = Text(qp_str, style=p.number)

        table.add_row(
            r['id'],
            r['tc_method'],
            f"{r['tc_min']:.1f}",
            tp_str,
            x_str,
            tb_str,
            r['storm'],
            str(r['tr']),
            qp_text,
            Tp_str,
            format_volume_hm3(r['vol_m3']),
        )

    console.print(table)


def print_x_factor_table(
    title: str = "Factor X Morfológico",
) -> None:
    """
    Imprime tabla de factores X con formato Rich.

    Fuente: Adaptado de 'Escoamento Superficial Direto', Rubem La Laina Porto.

    Args:
        title: Título de la tabla
    """
    console = get_console()
    p = get_palette()

    # Datos de la tabla
    x_data = [
        ("1.00", "Método racional", "Respuesta rápida, cuencas pequeñas impermeables"),
        ("1.25", "Urbano alta pendiente", "Áreas urbanas con pendiente pronunciada"),
        ("1.67", "Método NRCS", "Hidrograma unitario SCS estándar"),
        ("2.25", "Uso mixto", "Combinación rural/urbano"),
        ("3.33", "Rural sinuoso", "Cuencas rurales con cauces sinuosos"),
        ("5.50", "Rural pend. baja", "Áreas rurales con pendiente baja"),
        ("12.0", "Rural pend. muy baja", "Áreas rurales con pendiente muy baja"),
    ]

    table = Table(
        title=title,
        title_style=f"bold {p.table_header}",
        caption="Fuente: Porto, R.L.L. 'Escoamento Superficial Direto'",
        caption_style=p.muted,
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("X", justify="right", style=f"bold {p.number}", width=6)
    table.add_column("Tipo", justify="left", style=p.table_category, width=20)
    table.add_column("Aplicación", justify="left", style=p.muted)

    for x_val, tipo, aplicacion in x_data:
        table.add_row(x_val, tipo, aplicacion)

    console.print()
    console.print(table)
    console.print()
