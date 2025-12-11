"""
Vista expandida de detalles de análisis.

Muestra información adicional como:
- Parámetros de tormenta bimodal
- Tabla de ponderación de C/CN
- Parámetros del hidrograma unitario
"""

import shutil

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from hidropluvial.cli.theme import get_palette, get_console
from hidropluvial.cli.viewer.terminal import clear_screen, get_key


def build_bimodal_panel(storm) -> Panel:
    """Construye panel con parámetros de tormenta bimodal."""
    p = get_palette()

    table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Label", style=p.label, width=18)
    table.add_column("Value", style=f"bold {p.number}", width=20)
    table.add_column("Label2", style=p.label, width=18)
    table.add_column("Value2", style=f"bold {p.number}", width=20)

    # Posición de picos
    peak1_pct = f"{storm.bimodal_peak1 * 100:.0f}%" if storm.bimodal_peak1 else "-"
    peak2_pct = f"{storm.bimodal_peak2 * 100:.0f}%" if storm.bimodal_peak2 else "-"
    table.add_row(
        "Pico 1 (posición):", peak1_pct,
        "Pico 2 (posición):", peak2_pct,
    )

    # Volumen y ancho
    vol_pct = f"{storm.bimodal_vol_split * 100:.0f}% / {(1 - storm.bimodal_vol_split) * 100:.0f}%" if storm.bimodal_vol_split else "-"
    width_pct = f"{storm.bimodal_peak_width * 100:.0f}%" if storm.bimodal_peak_width else "-"
    table.add_row(
        "División volumen:", vol_pct,
        "Ancho de picos:", width_pct,
    )

    # Duración
    table.add_row(
        "Duración:", f"{storm.duration_hr:.1f} h",
        "", "",
    )

    return Panel(
        table,
        title=f"[bold {p.primary}] Parámetros Bimodales [/]",
        border_style=p.border,
        padding=(0, 1),
    )


def build_weighted_table(weighted_data: dict, coef_type: str) -> Panel:
    """Construye panel con tabla de ponderación de C o CN."""
    p = get_palette()

    table = Table(
        show_header=True,
        header_style=f"bold {p.secondary}",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("#", width=3, justify="right", style=p.muted)
    table.add_column("Descripción", width=30)
    table.add_column("Área (ha)", width=10, justify="right")
    table.add_column("%", width=6, justify="right")
    table.add_column("Valor", width=8, justify="right")
    table.add_column("Aporte", width=10, justify="right")

    items = weighted_data.get("items", [])
    weighted_value = weighted_data.get("weighted_value", 0)

    for i, item in enumerate(items):
        desc = item.get("description", "")[:28]
        area = item.get("area_ha", 0)
        pct = item.get("percentage", 0)
        val = item.get("value", 0)
        aporte = pct / 100 * val

        table.add_row(
            str(i + 1),
            desc,
            f"{area:.2f}",
            f"{pct:.1f}",
            f"{val:.2f}" if coef_type == "c" else f"{val:.0f}",
            f"{aporte:.3f}" if coef_type == "c" else f"{aporte:.1f}",
        )

    # Fila total
    table.add_row(
        "",
        Text("TOTAL PONDERADO", style=f"bold {p.accent}"),
        "",
        "100.0",
        "",
        Text(f"{weighted_value:.2f}" if coef_type == "c" else f"{weighted_value:.0f}",
             style=f"bold {p.accent}"),
    )

    # Título con tabla usada
    table_name = weighted_data.get("table_used", "").upper() or "MANUAL"
    title_text = f" Ponderación de {'C' if coef_type == 'c' else 'CN'} ({table_name}) "

    return Panel(
        table,
        title=f"[bold {p.primary}]{title_text}[/]",
        border_style=p.border,
        padding=(0, 1),
    )


def build_hu_params_panel(hydro) -> Panel:
    """Construye panel con parámetros del hidrograma unitario."""
    p = get_palette()

    table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Label", style=p.label, width=20)
    table.add_column("Value", style=f"bold {p.number}", width=15)
    table.add_column("Label2", style=p.label, width=20)
    table.add_column("Value2", style=f"bold {p.number}", width=15)

    # Tiempos del HU
    tp_str = f"{hydro.tp_unit_min:.1f} min" if hydro.tp_unit_min else "-"
    tb_str = f"{hydro.tb_min:.1f} min" if hydro.tb_min else "-"
    table.add_row(
        "tp (pico HU):", tp_str,
        "tb (base HU):", tb_str,
    )

    # Factor X y tiempos derivados
    x_str = f"{hydro.x_factor:.2f}" if hydro.x_factor else "-"
    # Tiempo de recesión: tr = tb - tp = X * tp
    tr_min = None
    if hydro.tb_min and hydro.tp_unit_min:
        tr_min = hydro.tb_min - hydro.tp_unit_min
    tr_str = f"{tr_min:.1f} min" if tr_min else "-"
    table.add_row(
        "Factor X:", x_str,
        "tr (recesión):", tr_str,
    )

    # Tiempo al pico del hidrograma resultante
    tp_peak_str = f"{hydro.time_to_peak_min:.1f} min" if hydro.time_to_peak_min else "-"
    table.add_row(
        "Tp (pico resultante):", tp_peak_str,
        "", "",
    )

    return Panel(
        table,
        title=f"[bold {p.primary}] Parámetros del Hidrograma Unitario [/]",
        border_style=p.border,
        padding=(0, 1),
    )


def build_runoff_params_panel(tc) -> Panel:
    """Construye panel con parámetros de escorrentía."""
    p = get_palette()

    params = tc.parameters or {}

    table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("Label", style=p.label, width=20)
    table.add_column("Value", style=f"bold {p.number}", width=15)
    table.add_column("Label2", style=p.label, width=20)
    table.add_column("Value2", style=f"bold {p.number}", width=15)

    runoff_method = params.get("runoff_method", "-")
    table.add_row(
        "Método:", runoff_method.upper() if runoff_method else "-",
        "", "",
    )

    if runoff_method == "racional":
        c_val = params.get("c", "-")
        table.add_row(
            "C:", f"{c_val:.3f}" if isinstance(c_val, (int, float)) else str(c_val),
            "", "",
        )
    elif runoff_method == "scs-cn":
        cn_adj = params.get("cn_adjusted", "-")
        amc = params.get("amc", "-")
        lambda_val = params.get("lambda", 0.2)
        table.add_row(
            "CN ajustado:", f"{cn_adj:.0f}" if isinstance(cn_adj, (int, float)) else str(cn_adj),
            "AMC:", str(amc),
        )
        table.add_row(
            "λ (Ia/S):", f"{lambda_val:.2f}" if isinstance(lambda_val, (int, float)) else str(lambda_val),
            "", "",
        )

    return Panel(
        table,
        title=f"[bold {p.primary}] Parámetros de Escorrentía [/]",
        border_style=p.border,
        padding=(0, 1),
    )


def show_detail_view(
    analysis,
    basin_id: str,
    session_name: str,
    db=None,
) -> None:
    """
    Muestra vista expandida con detalles del análisis.

    Args:
        analysis: AnalysisRun con datos del análisis
        basin_id: ID de la cuenca (para obtener datos de ponderación)
        session_name: Nombre de la cuenca
        db: DatabaseConnection (opcional, para obtener ponderación)
    """
    console = get_console()
    p = get_palette()

    # Guardar tamaño inicial del terminal para detectar cambios
    last_terminal_size = shutil.get_terminal_size()

    clear_screen()

    while True:
        # Detectar si cambió el tamaño del terminal
        current_size = shutil.get_terminal_size()
        if current_size != last_terminal_size:
            clear_screen()
            last_terminal_size = current_size

        components = []

        # Título
        title = Text()
        title.append("\n  DETALLES DEL ANÁLISIS ", style=f"bold {p.primary}")
        title.append(f"- {session_name}\n", style=p.secondary)
        components.append(title)

        # Panel de parámetros del HU
        hu_panel = build_hu_params_panel(analysis.hydrograph)
        components.append(hu_panel)

        # Panel de escorrentía
        runoff_panel = build_runoff_params_panel(analysis.tc)
        components.append(runoff_panel)

        # Panel bimodal (solo si aplica)
        storm = analysis.storm
        if storm.type.lower() == "bimodal" and storm.bimodal_peak1 is not None:
            bimodal_panel = build_bimodal_panel(storm)
            components.append(bimodal_panel)

        # Tabla de ponderación (si existe)
        if db:
            tc_params = analysis.tc.parameters or {}
            runoff_method = tc_params.get("runoff_method", "")

            if runoff_method == "racional":
                weighted_c = db.get_weighted_coefficient(basin_id, "c")
                if weighted_c and weighted_c.get("items"):
                    weighted_panel = build_weighted_table(weighted_c, "c")
                    components.append(weighted_panel)
            elif runoff_method == "scs-cn":
                weighted_cn = db.get_weighted_coefficient(basin_id, "cn")
                if weighted_cn and weighted_cn.get("items"):
                    weighted_panel = build_weighted_table(weighted_cn, "cn")
                    components.append(weighted_panel)

        # Navegación
        nav = Text()
        nav.append("\n  [", style=p.muted)
        nav.append("Esc", style=f"bold {p.primary}")
        nav.append("/", style=p.muted)
        nav.append("q", style=f"bold {p.primary}")
        nav.append("] Volver", style=p.muted)
        components.append(nav)

        # Mostrar
        console.print(Group(*components))

        # Esperar input
        key = get_key()
        if key in ('q', 'esc', 'enter'):
            break

        clear_screen()

    clear_screen()


def show_weighted_view(
    analysis,
    basin_id: str,
    session_name: str,
    db=None,
) -> None:
    """
    Muestra vista de la tabla de ponderación de C o CN.

    Args:
        analysis: AnalysisRun con datos del análisis
        basin_id: ID de la cuenca (para obtener datos de ponderación)
        session_name: Nombre de la cuenca
        db: DatabaseConnection (para obtener ponderación)
    """
    console = get_console()
    p = get_palette()

    if not db:
        console.print("\n  [yellow]No hay conexión a base de datos.[/]\n")
        get_key()
        return

    # Determinar qué tipo de coeficiente mostrar según el método de escorrentía
    tc_params = analysis.tc.parameters or {}
    runoff_method = tc_params.get("runoff_method", "")

    weighted_data = None
    coef_type = None

    if runoff_method == "racional" or "c" in tc_params:
        weighted_data = db.get_weighted_coefficient(basin_id, "c")
        coef_type = "c"
    elif runoff_method == "scs-cn" or "cn_adjusted" in tc_params:
        weighted_data = db.get_weighted_coefficient(basin_id, "cn")
        coef_type = "cn"

    # Guardar tamaño inicial del terminal para detectar cambios
    last_terminal_size = shutil.get_terminal_size()

    clear_screen()

    while True:
        # Detectar si cambió el tamaño del terminal
        current_size = shutil.get_terminal_size()
        if current_size != last_terminal_size:
            clear_screen()
            last_terminal_size = current_size

        components = []

        # Título
        title = Text()
        title.append("\n  TABLA DE PONDERACIÓN ", style=f"bold {p.primary}")
        title.append(f"- {session_name}\n", style=p.secondary)
        components.append(title)

        if weighted_data and weighted_data.get("items"):
            # Mostrar tabla de ponderación
            weighted_panel = build_weighted_table(weighted_data, coef_type)
            components.append(weighted_panel)

            # Info adicional
            info = Text()
            info.append("\n  Tabla usada: ", style=p.label)
            table_used = weighted_data.get("table_used", "").upper() or "MANUAL"
            info.append(table_used, style=f"bold {p.secondary}")

            if weighted_data.get("base_tr"):
                info.append("  |  TR base: ", style=p.label)
                info.append(str(weighted_data.get("base_tr")), style=f"bold {p.number}")

            info.append("  |  Valor ponderado: ", style=p.label)
            wv = weighted_data.get("weighted_value", 0)
            if coef_type == "c":
                info.append(f"{wv:.3f}", style=f"bold {p.accent}")
            else:
                info.append(f"{wv:.0f}", style=f"bold {p.accent}")
            components.append(info)
        else:
            # No hay datos de ponderación
            no_data = Text()
            no_data.append("\n  No hay datos de ponderación para ", style=p.muted)
            if coef_type == "c":
                no_data.append("C (Coeficiente de escorrentía)", style=p.secondary)
            elif coef_type == "cn":
                no_data.append("CN (Curve Number)", style=p.secondary)
            else:
                no_data.append("este análisis", style=p.secondary)
            no_data.append(".\n", style=p.muted)
            components.append(no_data)

            hint = Text()
            hint.append("  El coeficiente fue ingresado directamente sin usar ponderación por áreas.\n", style=p.muted)
            components.append(hint)

        # Navegación
        nav = Text()
        nav.append("\n  [", style=p.muted)
        nav.append("Esc", style=f"bold {p.primary}")
        nav.append("/", style=p.muted)
        nav.append("q", style=f"bold {p.primary}")
        nav.append("/", style=p.muted)
        nav.append("Enter", style=f"bold {p.primary}")
        nav.append("] Volver", style=p.muted)
        components.append(nav)

        # Mostrar
        console.print(Group(*components))

        # Esperar input
        key = get_key()
        if key in ('q', 'esc', 'enter'):
            break

        clear_screen()

    clear_screen()
