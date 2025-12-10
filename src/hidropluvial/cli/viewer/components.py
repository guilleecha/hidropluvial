"""
Componentes de UI para el visor interactivo.

Construcción de tablas y paneles con Rich.
"""

from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from hidropluvial.cli.theme import get_palette


def build_analysis_list(analyses: list, current_idx: int, max_visible: int = 6) -> Table:
    """
    Construye la tabla compacta con lista de analisis, destacando el actual.

    Muestra: #, Método Tc, Tormenta, TR, Coef, X, P, Pe, Qp, Vol
    Con scroll automático centrado en el análisis actual.
    """
    from hidropluvial.cli.formatters import format_flow, format_volume_hm3

    p = get_palette()

    table = Table(
        show_header=True,
        header_style=f"bold {p.secondary}",
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
        expand=False,
    )
    table.add_column("#", style=p.muted, width=5, justify="right")
    table.add_column("Método Tc", width=10)
    table.add_column("Storm", width=6)
    table.add_column("TR", width=4, justify="right")
    table.add_column("Coef", width=8)
    table.add_column("X", width=5, justify="right")
    table.add_column("P", width=5, justify="right")
    table.add_column("Pe", width=5, justify="right")
    table.add_column("Qp", width=8, justify="right")
    table.add_column("Vol", width=8, justify="right")

    n = len(analyses)

    # Calcular ventana visible centrada en current_idx
    half = max_visible // 2
    start = max(0, current_idx - half)
    end = min(n, start + max_visible)
    if end - start < max_visible:
        start = max(0, end - max_visible)

    # Indicador de scroll arriba
    if start > 0:
        table.add_row(Text(f"↑{start}", style=p.muted), "", "", "", "", "", "", "", "", "")

    for i in range(start, end):
        a = analyses[i]
        hydro = a.hydrograph
        storm = a.storm
        tc = a.tc

        # Formatear valores compactos
        tc_str = tc.method[:10].title()
        storm_str = storm.type[:6].upper()
        tr_str = str(storm.return_period)

        # Coeficiente (C o CN)
        coef_str = "-"
        if tc.parameters:
            if "c" in tc.parameters:
                coef_str = f"C={tc.parameters['c']:.2f}"
            elif "cn_adjusted" in tc.parameters:
                coef_str = f"CN{tc.parameters['cn_adjusted']:.0f}"
            elif "cn" in tc.parameters:
                coef_str = f"CN{tc.parameters['cn']:.0f}"

        x_str = f"{hydro.x_factor:.1f}" if hydro.x_factor else "-"
        p_str = f"{storm.total_depth_mm:.0f}" if storm.total_depth_mm else "-"
        pe_str = f"{hydro.runoff_mm:.1f}" if hydro.runoff_mm else "-"
        qp_str = format_flow(hydro.peak_flow_m3s)
        vol_str = format_volume_hm3(hydro.volume_m3)

        # Estilo: destacado si es el actual
        if i == current_idx:
            style = f"bold {p.accent}"
            idx_text = Text(f"▶{i+1}", style=style)
        else:
            style = p.muted
            idx_text = Text(f" {i+1}", style=style)

        table.add_row(
            idx_text,
            Text(tc_str, style=style),
            Text(storm_str, style=style),
            Text(tr_str, style=style),
            Text(coef_str, style=style),
            Text(x_str, style=style),
            Text(p_str, style=style),
            Text(pe_str, style=style),
            Text(qp_str, style=style),
            Text(vol_str, style=style),
        )

    # Indicador de scroll abajo
    remaining = n - end
    if remaining > 0:
        table.add_row(Text(f"↓{remaining}", style=p.muted), "", "", "", "", "", "", "", "", "")

    return table


def build_info_panel(analysis, session_name: str, current_idx: int, n_total: int) -> Panel:
    """Construye panel con informacion del analisis."""
    from hidropluvial.cli.formatters import format_flow, format_volume_hm3
    p = get_palette()

    hydro = analysis.hydrograph
    storm = analysis.storm
    tc = analysis.tc
    params = tc.parameters or {}

    # Titulo del panel
    title = Text()
    title.append(f" FICHA DE ANALISIS ", style=f"bold {p.primary}")
    title.append(f"[{current_idx+1}/{n_total}]", style=p.muted)

    # Contenido: tabla compacta con datos
    info_table = Table(
        show_header=False,
        box=None,
        padding=(0, 1),
        expand=False,
    )
    info_table.add_column("Label", style=p.label, width=10)
    info_table.add_column("Value", style=f"bold {p.number}", width=14)
    info_table.add_column("Label2", style=p.label, width=10)
    info_table.add_column("Value2", style=f"bold {p.number}", width=14)

    # Fila 1: Cuenca y Tormenta
    info_table.add_row(
        "Cuenca:", Text(session_name[:14], style=p.secondary),
        "Tormenta:", Text(f"{storm.type.upper()} Tr{storm.return_period}", style=p.secondary),
    )

    # Fila 2: Tc (metodo) y tp
    tp_str = f"{hydro.tp_unit_min:.0f} min" if hydro.tp_unit_min else "-"
    tc_text = Text()
    tc_text.append(f"{tc.tc_min:.1f} min ", style=f"bold {p.number}")
    tc_text.append(f"({tc.method[:6]})", style=p.muted)
    info_table.add_row(
        "Tc:", tc_text,
        "tp (HU):", Text(tp_str, style=f"bold {p.number}"),
    )

    # Fila 3: Factor X y tb
    x_val = f"{hydro.x_factor:.2f}" if hydro.x_factor else "-"
    tb_str = f"{hydro.tb_min:.0f} min" if hydro.tb_min else "-"
    info_table.add_row(
        "Factor X:", Text(x_val, style=f"bold {p.number}"),
        "tb:", Text(tb_str, style=f"bold {p.number}"),
    )

    # Fila 4: P y Pe
    info_table.add_row(
        "P total:", Text(f"{storm.total_depth_mm:.1f} mm", style=f"bold {p.number}"),
        "Pe:", Text(f"{hydro.runoff_mm:.1f} mm", style=f"bold {p.number}"),
    )

    # Fila 5: i_max y coeficiente (con detalles según método)
    runoff_method = params.get("runoff_method", "")
    if runoff_method == "racional":
        c_val = params.get("c", "-")
        coef_str = f"C={c_val:.2f}" if isinstance(c_val, (int, float)) else f"C={c_val}"
    elif runoff_method == "scs-cn":
        cn_adj = params.get("cn_adjusted", "-")
        coef_str = f"CN={cn_adj:.0f}" if isinstance(cn_adj, (int, float)) else f"CN={cn_adj}"
    elif "c" in params:
        coef_str = f"C={params['c']:.2f}"
    elif "cn_adjusted" in params:
        coef_str = f"CN={params['cn_adjusted']}"
    else:
        coef_str = "-"

    info_table.add_row(
        "i max:", Text(f"{storm.peak_intensity_mmhr:.1f} mm/h", style=f"bold {p.number}"),
        "Coef.:", Text(coef_str, style=f"bold {p.number}"),
    )

    # Fila 6: Parámetros adicionales de escorrentía (AMC y λ para SCS-CN)
    if runoff_method == "scs-cn":
        amc = params.get("amc", "-")
        lambda_val = params.get("lambda", 0.2)
        lambda_str = f"{lambda_val:.2f}" if isinstance(lambda_val, (int, float)) else str(lambda_val)
        info_table.add_row(
            "AMC:", Text(str(amc), style=f"bold {p.number}"),
            "λ (Ia/S):", Text(lambda_str, style=f"bold {p.number}"),
        )

    # Fila 7: Parámetros bimodales (si aplica)
    if storm.type.lower() == "bimodal" and storm.bimodal_peak1 is not None:
        peak1_pct = f"{storm.bimodal_peak1 * 100:.0f}%"
        peak2_pct = f"{storm.bimodal_peak2 * 100:.0f}%" if storm.bimodal_peak2 else "-"
        info_table.add_row(
            "Pico 1:", Text(peak1_pct, style=f"bold {p.number}"),
            "Pico 2:", Text(peak2_pct, style=f"bold {p.number}"),
        )
        vol_split = f"{storm.bimodal_vol_split * 100:.0f}%" if storm.bimodal_vol_split else "-"
        width_pct = f"{storm.bimodal_peak_width * 100:.0f}%" if storm.bimodal_peak_width else "-"
        info_table.add_row(
            "Vol P1:", Text(vol_split, style=f"bold {p.number}"),
            "Ancho:", Text(width_pct, style=f"bold {p.number}"),
        )

    # Separador
    info_table.add_row("", "", "", "")

    # Fila: Resultados principales (destacados)
    qp_text = Text()
    qp_text.append(f"{format_flow(hydro.peak_flow_m3s)} ", style=f"bold {p.accent}")
    qp_text.append("m3/s", style=p.unit)

    tp_peak_text = Text()
    tp_peak_text.append(f"{hydro.time_to_peak_min:.0f} ", style=f"bold {p.accent}")
    tp_peak_text.append("min", style=p.unit)

    info_table.add_row(
        "Qp:", qp_text,
        "Tp:", tp_peak_text,
    )

    # Fila: Volumen y tr (tiempo de recesión)
    vol_text = Text()
    vol_text.append(f"{format_volume_hm3(hydro.volume_m3)} ", style=f"bold {p.accent}")
    vol_text.append("hm3", style=p.unit)

    # Calcular tr = tb - tp
    tr_str = "-"
    if hydro.tb_min and hydro.tp_unit_min:
        tr_min = hydro.tb_min - hydro.tp_unit_min
        tr_str = f"{tr_min:.0f} min"

    info_table.add_row(
        "Volumen:", vol_text,
        "tr:", Text(tr_str, style=f"bold {p.number}"),
    )

    return Panel(
        info_table,
        title=title,
        title_align="left",
        border_style=p.primary,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def format_analysis_label(analysis, index: int, max_len: int = 35) -> str:
    """Formatea etiqueta corta de un analisis."""
    hydro = analysis.hydrograph
    storm = analysis.storm
    tc = analysis.tc

    x_str = f"X{hydro.x_factor:.1f}" if hydro.x_factor else ""
    label = f"{tc.method[:8]} {storm.type[:3]}Tr{storm.return_period}"
    if x_str:
        label += f" {x_str}"
    label += f" Qp={hydro.peak_flow_m3s:.1f}"

    if len(label) > max_len:
        label = label[:max_len-2] + ".."
    return label
