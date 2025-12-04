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
    print_summary_table_with_sparklines,
)


def session_preview(
    session_id: Annotated[str, typer.Argument(help="ID de la sesion (primeros 8 caracteres)")],
    analysis_idx: Annotated[Optional[int], typer.Option("--idx", "-i", help="Indice del analisis a mostrar")] = None,
    compare: Annotated[bool, typer.Option("--compare", "-c", help="Comparar todos los hidrogramas")] = False,
    hyetograph: Annotated[bool, typer.Option("--hyeto", "-y", help="Mostrar hietograma")] = False,
    tr: Annotated[Optional[str], typer.Option("--tr", help="Filtrar por periodo de retorno (ej: 10 o 2,10,25)")] = None,
    x: Annotated[Optional[str], typer.Option("--x", help="Filtrar por factor X (ej: 1.0 o 1.0,1.25)")] = None,
    tc: Annotated[Optional[str], typer.Option("--tc", help="Filtrar por metodo Tc (ej: desbordes o kirpich,temez)")] = None,
    storm: Annotated[Optional[str], typer.Option("--storm", "-s", help="Filtrar por tipo de tormenta (ej: gz o blocks,bimodal)")] = None,
    width: Annotated[int, typer.Option("--width", "-w", help="Ancho del grafico")] = 70,
    height: Annotated[int, typer.Option("--height", "-h", help="Alto del grafico")] = 18,
):
    """
    Muestra graficos de hidrogramas/hietogramas en la terminal.

    Ejemplos:
        hp session preview abc123              # Tabla con sparklines
        hp session preview abc123 --compare    # Comparar hidrogramas
        hp session preview abc123 -i 0         # Ver primer analisis
        hp session preview abc123 -i 0 --hyeto # Ver hietograma
        hp session preview abc123 --tr 10      # Solo Tr=10
        hp session preview abc123 --x 1.25     # Solo X=1.25
        hp session preview abc123 --tc desbordes --tr 10  # Combinado
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
    analyses = _filter_analyses(session.analyses, tr=tr, x=x, tc=tc, storm_type=storm)

    if not analyses:
        typer.echo("  No hay analisis que coincidan con los filtros.")
        typer.echo(f"  Filtros aplicados: tr={tr}, x={x}, tc={tc}, storm={storm}")
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

    filter_msg = f" [Filtros: {', '.join(active_filters)}]" if active_filters else ""

    # Modo comparacion: todos los hidrogramas superpuestos
    if compare:
        analyses_data = []
        for analysis in analyses:
            hydro = analysis.hydrograph
            storm_data = analysis.storm
            if hydro.time_hr and hydro.flow_m3s:
                x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
                label = f"{hydro.tc_method} {storm_data.type} Tr{storm_data.return_period}{x_str}"
                analyses_data.append({
                    "time_hr": hydro.time_hr,
                    "flow_m3s": hydro.flow_m3s,
                    "label": label,
                })

        if analyses_data:
            typer.echo(f"\n  Sesion: {session.name} ({session.id}){filter_msg}")
            typer.echo(f"  Comparando {len(analyses_data)} hidrogramas\n")
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
                typer.echo(f"\n  {title_base}")
                typer.echo(f"  Qp: {hydro.peak_flow_m3s:.3f} m3/s")
                typer.echo(f"  Tp: {hydro.time_to_peak_hr:.2f} h")
                typer.echo(f"  Vol: {hydro.volume_m3:.1f} m3\n")

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
    typer.echo(f"\n  Sesion: {session.name} ({session.id}){filter_msg}")
    typer.echo(f"  Cuenca: {session.cuenca.area_ha} ha, S={session.cuenca.slope_pct}%")
    if active_filters:
        typer.echo(f"  Mostrando {len(analyses)} de {len(session.analyses)} analisis")

    rows = []
    for i, analysis in enumerate(analyses):
        hydro = analysis.hydrograph
        storm_data = analysis.storm
        rows.append({
            'idx': i,
            'tc_method': hydro.tc_method,
            'storm': storm_data.type,
            'tr': storm_data.return_period,
            'x': hydro.x_factor,
            'qpeak_m3s': hydro.peak_flow_m3s,
            'tp_hr': hydro.time_to_peak_hr,
            'hydrograph_flow': hydro.flow_m3s or [],
        })

    print_summary_table_with_sparklines(rows, show_sparkline=True)

    typer.echo("  Comandos:")
    typer.echo(f"    hp session preview {session_id} -i 0         Ver hidrograma #0")
    typer.echo(f"    hp session preview {session_id} -i 0 --hyeto Ver hietograma #0")
    typer.echo(f"    hp session preview {session_id} --compare    Comparar todos")
    typer.echo(f"    hp session preview {session_id} --tr 10      Filtrar por Tr")
    typer.echo("")


def _filter_analyses(
    analyses: list,
    tr: Optional[str] = None,
    x: Optional[str] = None,
    tc: Optional[str] = None,
    storm_type: Optional[str] = None,
) -> list:
    """
    Filtra lista de analisis segun criterios.

    Args:
        analyses: Lista de AnalysisRun
        tr: Periodos de retorno (ej: "10" o "2,10,25")
        x: Factores X (ej: "1.0" o "1.0,1.25")
        tc: Metodos Tc (ej: "desbordes" o "kirpich,temez")
        storm_type: Tipos de tormenta (ej: "gz" o "blocks,bimodal")

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

    return result
