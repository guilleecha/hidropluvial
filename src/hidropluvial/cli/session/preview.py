"""
Comando preview - Visualizacion rapida de analisis en terminal.
"""

from typing import Annotated, Optional

import typer

from hidropluvial.cli.session.base import get_session_manager
from hidropluvial.cli.preview import (
    sparkline,
    plot_hydrograph_terminal,
    plot_hyetograph_terminal,
    plot_hydrograph_comparison_terminal,
    print_hyetograph_bars,
)
from hidropluvial.cli.theme import print_analyses_summary_table, get_console


def session_preview(
    session_id: Annotated[str, typer.Argument(help="ID de la sesion (primeros 8 caracteres)")],
    analysis_idx: Annotated[Optional[int], typer.Option("--idx", "-i", help="Indice del analisis a mostrar")] = None,
    compare: Annotated[bool, typer.Option("--compare", "-c", help="Comparar todos los hidrogramas")] = False,
    interactive: Annotated[bool, typer.Option("--interactive", help="Modo interactivo con flechas")] = False,
    select: Annotated[Optional[str], typer.Option("--select", help="Indices a comparar (ej: 0,2,5 o 0-3)")] = None,
    hyetograph: Annotated[bool, typer.Option("--hyeto", "-y", help="Mostrar hietograma")] = False,
    tr: Annotated[Optional[str], typer.Option("--tr", help="Filtrar por periodo de retorno (ej: 10 o 2,10,25)")] = None,
    x: Annotated[Optional[str], typer.Option("--x", help="Filtrar por factor X (ej: 1.0 o 1.0,1.25)")] = None,
    tc: Annotated[Optional[str], typer.Option("--tc", help="Filtrar por metodo Tc (ej: desbordes o kirpich,temez)")] = None,
    storm: Annotated[Optional[str], typer.Option("--storm", "-s", help="Filtrar por tipo de tormenta (ej: gz o blocks,bimodal)")] = None,
    runoff: Annotated[Optional[str], typer.Option("--runoff", "-r", help="Filtrar por metodo escorrentia (ej: racional o scs-cn)")] = None,
    width: Annotated[int, typer.Option("--width", "-w", help="Ancho del grafico")] = 70,
    height: Annotated[int, typer.Option("--height", "-h", help="Alto del grafico")] = 18,
):
    """
    Muestra graficos de hidrogramas/hietogramas en la terminal.

    Ejemplos:
        hp session preview abc123              # Tabla con sparklines
        hp session preview abc123 --compare    # Comparar todos los hidrogramas
        hp session preview abc123 --compare --select 0,2,5  # Comparar indices especificos
        hp session preview abc123 --compare --select 0-3    # Comparar rango de indices
        hp session preview abc123 --interactive  # Navegacion con flechas
        hp session preview abc123 -i 0         # Ver primer analisis
        hp session preview abc123 -i 0 --hyeto # Ver hietograma
        hp session preview abc123 --tr 10      # Solo Tr=10
        hp session preview abc123 --x 1.25     # Solo X=1.25
        hp session preview abc123 --tc desbordes --tr 10  # Combinado
        hp session preview abc123 --runoff racional  # Solo metodo Racional
        hp session preview abc123 --runoff scs-cn    # Solo metodo SCS-CN
    """
    manager = get_session_manager()
    session = manager.get_session(session_id)

    if session is None:
        typer.echo(f"Error: Sesion '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    if not session.analyses:
        typer.echo("  No hay analisis en esta sesion.")
        typer.echo("  Usa 'hp session analyze' para agregar analisis.")
        raise typer.Exit(1)

    # Aplicar filtros
    analyses = _filter_analyses(session.analyses, tr=tr, x=x, tc=tc, storm_type=storm, runoff_method=runoff)

    if not analyses:
        typer.echo("  No hay analisis que coincidan con los filtros.")
        typer.echo(f"  Filtros aplicados: tr={tr}, x={x}, tc={tc}, storm={storm}, runoff={runoff}")
        raise typer.Exit(1)

    # Mostrar filtros activos
    active_filters = []
    if tr:
        active_filters.append(f"Tr={tr}")
    if x:
        active_filters.append(f"X={x}")
    if tc:
        active_filters.append(f"Tc={tc}")
    if storm:
        active_filters.append(f"storm={storm}")
    if runoff:
        active_filters.append(f"runoff={runoff}")

    filter_msg = f" [Filtros: {', '.join(active_filters)}]" if active_filters else ""

    # Modo interactivo: navegacion con flechas
    if interactive:
        from hidropluvial.cli.interactive_viewer import interactive_hydrograph_viewer
        interactive_hydrograph_viewer(analyses, session.name, width, height)
        return

    # Modo comparacion: todos los hidrogramas superpuestos
    if compare:
        # Aplicar seleccion por indices si se especifica
        analyses_to_compare = analyses
        if select:
            selected_indices = _parse_select_indices(select, len(analyses))
            if not selected_indices:
                typer.echo(f"Error: Seleccion invalida '{select}'")
                typer.echo(f"  Indices validos: 0-{len(analyses)-1}")
                raise typer.Exit(1)
            analyses_to_compare = [analyses[i] for i in selected_indices if i < len(analyses)]

        analyses_data = []
        for idx, analysis in enumerate(analyses_to_compare):
            hydro = analysis.hydrograph
            storm_data = analysis.storm
            if hydro.time_hr and hydro.flow_m3s:
                x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
                # Incluir indice en label para referencia
                orig_idx = analyses.index(analysis) if select else idx
                label = f"[{orig_idx}] {hydro.tc_method} {storm_data.type} Tr{storm_data.return_period}{x_str}"
                analyses_data.append({
                    "time_hr": hydro.time_hr,
                    "flow_m3s": hydro.flow_m3s,
                    "label": label,
                })

        if analyses_data:
            typer.echo(f"\n  Sesion: {session.name} ({session.id}){filter_msg}")
            select_msg = f" (indices: {select})" if select else ""
            typer.echo(f"  Comparando {len(analyses_data)} hidrogramas{select_msg}\n")

            # Tabla de parametros caracteristicos
            _print_comparison_table(analyses_to_compare, analyses)

            # Grafico de comparacion
            plot_hydrograph_comparison_terminal(analyses_data, width=width, height=height)
        else:
            typer.echo("  No hay datos de hidrogramas disponibles.")
        return

    # Modo analisis individual
    if analysis_idx is not None:
        if analysis_idx < 0 or analysis_idx >= len(analyses):
            typer.echo(f"Error: Indice {analysis_idx} fuera de rango (0-{len(analyses)-1})")
            raise typer.Exit(1)

        analysis = analyses[analysis_idx]
        hydro = analysis.hydrograph
        storm = analysis.storm
        x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
        title_base = f"{hydro.tc_method} + {storm.type} Tr{storm.return_period}{x_str}"

        if hyetograph:
            # Mostrar hietograma
            if storm.time_min and storm.intensity_mmhr:
                typer.echo(f"\n  {title_base}")
                typer.echo(f"  P total: {storm.total_depth_mm:.1f} mm")
                typer.echo(f"  i max: {storm.peak_intensity_mmhr:.1f} mm/h\n")

                # Barras ASCII primero
                dt = storm.time_min[1] - storm.time_min[0] if len(storm.time_min) > 1 else 5.0
                print_hyetograph_bars(
                    storm.time_min,
                    storm.intensity_mmhr,
                    dt_min=dt,
                    max_bar_width=40,
                )

                # Grafico plotext
                plot_hyetograph_terminal(
                    storm.time_min,
                    storm.intensity_mmhr,
                    title=f"Hietograma - {title_base}",
                    width=width,
                    height=height - 4,
                )
            else:
                typer.echo("  No hay datos de hietograma disponibles.")
        else:
            # Mostrar hidrograma
            if hydro.time_hr and hydro.flow_m3s:
                from hidropluvial.cli.formatters import format_flow, format_volume_hm3

                tp_str = f"{hydro.tp_unit_min:.1f}" if hydro.tp_unit_min else "-"
                tb_str = f"{hydro.tb_min:.1f}" if hydro.tb_min else "-"

                typer.echo(f"\n  {title_base}")
                typer.echo(f"  tp: {tp_str} min, tb: {tb_str} min")
                typer.echo(f"  Qp: {format_flow(hydro.peak_flow_m3s)} m3/s")
                typer.echo(f"  Tp: {hydro.time_to_peak_min:.1f} min")
                typer.echo(f"  Vol: {format_volume_hm3(hydro.volume_m3)} hm3\n")

                plot_hydrograph_terminal(
                    hydro.time_hr,
                    hydro.flow_m3s,
                    title=f"Hidrograma - {title_base}",
                    width=width,
                    height=height,
                )
            else:
                typer.echo("  No hay datos de hidrograma disponibles.")
        return

    # Modo por defecto: tabla con sparklines
    console = get_console()
    console.print()
    console.print(f"  Sesion: [bold]{session.name}[/bold] ({session.id}){filter_msg}")
    console.print(f"  Cuenca: {session.cuenca.area_ha} ha, S={session.cuenca.slope_pct}%")
    if active_filters:
        console.print(f"  Mostrando {len(analyses)} de {len(session.analyses)} analisis")
    console.print()

    # Usar la nueva tabla Rich
    print_analyses_summary_table(
        analyses,
        title=f"Analisis - {session.name}",
        show_sparkline=True,
    )

    console.print()
    console.print("  [dim]Comandos:[/dim]")
    console.print(f"    [dim]hp session preview {session_id} -i 0[/dim]         Ver hidrograma #0")
    console.print(f"    [dim]hp session preview {session_id} -i 0 --hyeto[/dim] Ver hietograma #0")
    console.print(f"    [dim]hp session preview {session_id} --compare[/dim]    Comparar todos")
    console.print(f"    [dim]hp session preview {session_id} --tr 10[/dim]      Filtrar por Tr")
    console.print()


def _filter_analyses(
    analyses: list,
    tr: Optional[str] = None,
    x: Optional[str] = None,
    tc: Optional[str] = None,
    storm_type: Optional[str] = None,
    runoff_method: Optional[str] = None,
) -> list:
    """
    Filtra lista de analisis segun criterios.

    Args:
        analyses: Lista de AnalysisRun
        tr: Periodos de retorno (ej: "10" o "2,10,25")
        x: Factores X (ej: "1.0" o "1.0,1.25")
        tc: Metodos Tc (ej: "desbordes" o "kirpich,temez")
        storm_type: Tipos de tormenta (ej: "gz" o "blocks,bimodal")
        runoff_method: Metodos de escorrentia (ej: "racional" o "scs-cn")

    Returns:
        Lista filtrada de analisis
    """
    result = analyses

    # Filtrar por periodo de retorno
    if tr:
        tr_values = [int(v.strip()) for v in tr.split(",")]
        result = [a for a in result if a.storm.return_period in tr_values]

    # Filtrar por factor X
    if x:
        x_values = [float(v.strip()) for v in x.split(",")]
        result = [
            a for a in result
            if a.hydrograph.x_factor is None or a.hydrograph.x_factor in x_values
        ]

    # Filtrar por metodo Tc
    if tc:
        tc_methods = [v.strip().lower() for v in tc.split(",")]
        result = [a for a in result if a.hydrograph.tc_method.lower() in tc_methods]

    # Filtrar por tipo de tormenta
    if storm_type:
        storm_types = [v.strip().lower() for v in storm_type.split(",")]
        result = [a for a in result if a.storm.type.lower() in storm_types]

    # Filtrar por método de escorrentía
    if runoff_method:
        runoff_methods = [v.strip().lower() for v in runoff_method.split(",")]
        filtered = []
        for a in result:
            # Obtener método de escorrentía del análisis
            analysis_runoff = None
            if a.tc.parameters and "runoff_method" in a.tc.parameters:
                analysis_runoff = a.tc.parameters["runoff_method"]
            elif a.tc.parameters:
                # Inferir de parámetros existentes
                if "cn_adjusted" in a.tc.parameters:
                    analysis_runoff = "scs-cn"
                elif "c" in a.tc.parameters:
                    analysis_runoff = "racional"

            if analysis_runoff and analysis_runoff.lower() in runoff_methods:
                filtered.append(a)
        result = filtered

    return result


def _print_comparison_table(analyses_to_show: list, all_analyses: list) -> None:
    """
    Imprime tabla de parametros caracteristicos para comparacion.

    Notacion:
        - tp: tiempo pico del hidrograma unitario (minusculas)
        - Tp: tiempo pico del hidrograma resultante (mayusculas)
        - tb: tiempo base del hidrograma unitario

    Args:
        analyses_to_show: Lista de analisis a mostrar en la tabla
        all_analyses: Lista completa de analisis (para obtener indice original)
    """
    from hidropluvial.cli.formatters import format_flow, format_volume_hm3

    # Encabezado - orden: Tc, tp, X, tb, P, Pe, Qp, Tp, Vol
    typer.echo(f"  {'Idx':<4} {'Metodo Tc':<12} {'Tormenta':<8} {'Tr':>4} "
               f"{'Tc(min)':>8} {'tp(min)':>8} {'X':>5} {'tb(min)':>8} "
               f"{'P(mm)':>7} {'Pe(mm)':>7} {'Qp(m3/s)':>9} {'Tp(min)':>8} {'Vol(hm3)':>9}")
    typer.echo(f"  {'-'*115}")

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
        tc_min = f"{tc.tc_min:.1f}" if tc.tc_min else "-"
        tp_unit = f"{hydro.tp_unit_min:.1f}" if hydro.tp_unit_min else "-"
        x_str = f"{hydro.x_factor:.2f}" if hydro.x_factor else "-"
        tb = f"{hydro.tb_min:.1f}" if hydro.tb_min else "-"
        p_total = f"{storm.total_depth_mm:.1f}" if storm.total_depth_mm else "-"
        pe = f"{hydro.runoff_mm:.1f}" if hydro.runoff_mm else "-"
        qp = format_flow(hydro.peak_flow_m3s)
        tp_result = f"{hydro.time_to_peak_min:.1f}" if hydro.time_to_peak_min else "-"
        vol = format_volume_hm3(hydro.volume_m3)

        typer.echo(
            f"  [{orig_idx:<2}] {tc.method:<12} {storm.type.upper():<8} {storm.return_period:>4} "
            f"{tc_min:>8} {tp_unit:>8} {x_str:>5} {tb:>8} "
            f"{p_total:>7} {pe:>7} {qp:>9} {tp_result:>8} {vol:>9}"
        )

    typer.echo("")


def _parse_select_indices(select_str: str, max_count: int) -> list[int]:
    """
    Parsea string de seleccion de indices.

    Formatos soportados:
        "0,2,5"     -> [0, 2, 5]
        "0-3"       -> [0, 1, 2, 3]
        "0,2-4,7"   -> [0, 2, 3, 4, 7]

    Args:
        select_str: String con indices (ej: "0,2,5" o "0-3")
        max_count: Numero maximo de analisis disponibles

    Returns:
        Lista de indices validos, ordenados y sin duplicados
    """
    indices = set()

    try:
        parts = select_str.split(",")
        for part in parts:
            part = part.strip()
            if "-" in part:
                # Rango: "0-3" -> [0, 1, 2, 3]
                start, end = part.split("-", 1)
                start_idx = int(start.strip())
                end_idx = int(end.strip())
                if start_idx < 0 or end_idx < 0:
                    return []
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx
                for i in range(start_idx, min(end_idx + 1, max_count)):
                    indices.add(i)
            else:
                # Indice individual
                idx = int(part)
                if 0 <= idx < max_count:
                    indices.add(idx)

        return sorted(indices)

    except (ValueError, AttributeError):
        return []
