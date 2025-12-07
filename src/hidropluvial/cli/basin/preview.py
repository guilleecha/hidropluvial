"""
Funciones de preview para cuencas.

Visualización rápida de análisis en terminal.
"""

from typing import Optional

from hidropluvial.models import Basin


def basin_preview_interactive(
    basin: Basin,
    width: int = 70,
    height: int = 18,
) -> None:
    """
    Muestra visor interactivo de análisis.

    Args:
        basin: Cuenca con análisis
        width: Ancho del gráfico
        height: Alto del gráfico
    """
    from hidropluvial.cli.interactive_viewer import interactive_hydrograph_viewer

    if not basin.analyses:
        print("  No hay análisis en esta cuenca.")
        return

    interactive_hydrograph_viewer(basin.analyses, basin.name, width, height)


def basin_preview_table(
    basin: Basin,
    tr: Optional[str] = None,
    x: Optional[str] = None,
    tc: Optional[str] = None,
    storm: Optional[str] = None,
    runoff: Optional[str] = None,
) -> None:
    """
    Muestra tabla resumen con sparklines.

    Args:
        basin: Cuenca con análisis
        tr: Filtrar por período de retorno
        x: Filtrar por factor X
        tc: Filtrar por método Tc
        storm: Filtrar por tipo de tormenta
        runoff: Filtrar por método de escorrentía
    """
    from hidropluvial.cli.theme import (
        print_analyses_summary_table,
        get_console,
    )

    if not basin.analyses:
        print("  No hay análisis en esta cuenca.")
        return

    # Aplicar filtros
    analyses = _filter_analyses(
        basin.analyses,
        tr=tr,
        x=x,
        tc=tc,
        storm_type=storm,
        runoff_method=runoff,
    )

    if not analyses:
        print("  No hay análisis que coincidan con los filtros.")
        return

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

    console = get_console()
    console.print()
    console.print(f"  Cuenca: [bold]{basin.name}[/bold] ({basin.id}){filter_msg}")
    console.print(f"  Área: {basin.area_ha} ha, S={basin.slope_pct}%")
    if active_filters:
        console.print(f"  Mostrando {len(analyses)} de {len(basin.analyses)} análisis")
    console.print()

    print_analyses_summary_table(
        analyses,
        title=f"Análisis - {basin.name}",
        show_sparkline=True,
    )


def _filter_analyses(
    analyses: list,
    tr: Optional[str] = None,
    x: Optional[str] = None,
    tc: Optional[str] = None,
    storm_type: Optional[str] = None,
    runoff_method: Optional[str] = None,
) -> list:
    """
    Filtra lista de análisis según criterios.

    Args:
        analyses: Lista de AnalysisRun
        tr: Períodos de retorno (ej: "10" o "2,10,25")
        x: Factores X (ej: "1.0" o "1.0,1.25")
        tc: Métodos Tc (ej: "desbordes" o "kirpich,temez")
        storm_type: Tipos de tormenta (ej: "gz" o "blocks,bimodal")
        runoff_method: Métodos de escorrentía (ej: "racional" o "scs-cn")

    Returns:
        Lista filtrada de análisis
    """
    result = analyses

    # Filtrar por período de retorno
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

    # Filtrar por método Tc
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
            analysis_runoff = None
            if a.tc.parameters and "runoff_method" in a.tc.parameters:
                analysis_runoff = a.tc.parameters["runoff_method"]
            elif a.tc.parameters:
                if "cn_adjusted" in a.tc.parameters:
                    analysis_runoff = "scs-cn"
                elif "c" in a.tc.parameters:
                    analysis_runoff = "racional"

            if analysis_runoff and analysis_runoff.lower() in runoff_methods:
                filtered.append(a)
        result = filtered

    return result
