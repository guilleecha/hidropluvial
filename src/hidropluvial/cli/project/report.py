"""
Comando de generación de reportes LaTeX para proyectos.

Genera un reporte consolidado con todas las cuencas del proyecto.
"""

from copy import deepcopy
from pathlib import Path
from typing import Annotated, Optional

import typer

from hidropluvial.cli.project.base import get_project_manager
from hidropluvial.cli.theme import (
    print_header, print_subheader, print_separator,
    print_success, print_error, print_warning,
)


# =============================================================================
# Helper functions para project_report
# =============================================================================


def _validate_palette(palette: str) -> None:
    """Configura y valida la paleta de colores."""
    from hidropluvial.reports.palettes import set_active_palette
    try:
        set_active_palette(palette)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)


def _get_and_validate_project(project_id: str):
    """Obtiene el proyecto y valida que exista y tenga cuencas."""
    manager = get_project_manager()
    project = manager.get_project(project_id)

    if project is None:
        print_error(f"Proyecto '{project_id}' no encontrado.")
        raise typer.Exit(1)

    if not project.basins:
        print_error("El proyecto no tiene cuencas.")
        raise typer.Exit(1)

    return project


def _filter_basins_by_name(project, basin_filter: Optional[list[str]]) -> list:
    """Filtra cuencas por nombre o ID."""
    if not basin_filter:
        return project.basins

    basin_names_lower = [b.lower() for b in basin_filter]
    filtered = [
        b for b in project.basins
        if b.name.lower() in basin_names_lower
        or b.id.lower().startswith(tuple(basin_names_lower))
    ]

    if not filtered:
        print_error(f"No se encontraron cuencas que coincidan con: {basin_filter}")
        raise typer.Exit(1)

    typer.echo(f"  Filtro de cuencas: {len(filtered)} de {len(project.basins)}")
    return filtered


def _filter_analyses(basins: list, tr_filter: Optional[list[int]], tc_method_filter: Optional[list[str]]) -> list:
    """Filtra análisis por Tr y método Tc."""
    if not tr_filter and not tc_method_filter:
        return basins

    filtered_basins = []
    for b in basins:
        filtered_analyses = b.analyses

        if tr_filter:
            filtered_analyses = [
                a for a in filtered_analyses
                if a.storm.return_period in tr_filter
            ]

        if tc_method_filter:
            tc_methods_lower = [m.lower() for m in tc_method_filter]
            filtered_analyses = [
                a for a in filtered_analyses
                if a.tc.method.lower() in tc_methods_lower
            ]

        if filtered_analyses:
            filtered_basin = deepcopy(b)
            filtered_basin.analyses = filtered_analyses
            filtered_basins.append(filtered_basin)

    if not filtered_basins:
        print_error("No hay análisis que coincidan con los filtros aplicados.")
        raise typer.Exit(1)

    # Mostrar resumen de filtros
    filter_info = []
    if tr_filter:
        filter_info.append(f"Tr={tr_filter}")
    if tc_method_filter:
        filter_info.append(f"Tc={tc_method_filter}")
    typer.echo(f"  Filtros aplicados: {', '.join(filter_info)}")

    return filtered_basins


def _setup_output_dir(project, output: Optional[str]) -> Path:
    """Configura el directorio de salida."""
    if output is None:
        safe_name = project.name.lower().replace(" ", "_").replace("/", "_")
        output_name = safe_name
    else:
        output_name = output

    base_output = Path("output")
    output_dir = base_output / output_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _process_basins(basins: list, output_dir: Path) -> tuple[list[dict], dict]:
    """Procesa todas las cuencas y genera sus archivos."""
    basin_sections = []
    all_generated_files = {"hyetographs": [], "hydrographs": []}

    for basin_obj in basins:
        typer.echo(f"\n  Procesando cuenca: {basin_obj.name}...")

        # Crear subdirectorio para la cuenca
        basin_safe_name = basin_obj.name.lower().replace(" ", "_").replace("/", "_")
        basin_dir = output_dir / f"cuenca_{basin_safe_name}"
        basin_dir.mkdir(exist_ok=True)

        hidrogramas_dir = basin_dir / "hidrogramas"
        hietogramas_dir = basin_dir / "hietogramas"
        hidrogramas_dir.mkdir(exist_ok=True)
        hietogramas_dir.mkdir(exist_ok=True)

        # Generar gráficos TikZ
        basin_files = _generate_basin_tikz(basin_obj, basin_dir, hidrogramas_dir, hietogramas_dir)

        # Generar secciones
        basin_content = _generate_basin_sections(basin_obj, basin_dir, basin_files, basin_safe_name)

        basin_sections.append({
            "name": basin_obj.name,
            "safe_name": basin_safe_name,
            "content": basin_content,
            "n_analyses": len(basin_obj.analyses),
        })

        # Acumular archivos generados
        all_generated_files["hyetographs"].extend(basin_files["hyetographs"])
        all_generated_files["hydrographs"].extend(basin_files["hydrographs"])

        typer.echo(f"    Gráficos: {len(basin_files['hyetographs'])} hietogramas, {len(basin_files['hydrographs'])} hidrogramas")

    return basin_sections, all_generated_files


def _compile_to_pdf(main_path: Path, output_dir: Path, main_filename: str, clean: bool) -> None:
    """Compila el documento LaTeX a PDF."""
    from hidropluvial.reports.compiler import compile_latex, check_latex_installation

    print_subheader("COMPILANDO A PDF")

    latex_info = check_latex_installation()
    if not latex_info["installed"]:
        print_error("No se encontró LaTeX instalado.")
        typer.echo(f"\n  Para compilar manualmente:")
        typer.echo(f"    cd {output_dir.absolute()}")
        typer.echo(f"    pdflatex {main_filename}")
        raise typer.Exit(1)

    typer.echo(f"  Usando: {latex_info['recommended']}")
    typer.echo(f"  Compilando {main_filename}...")

    result = compile_latex(
        tex_file=main_path,
        output_dir=output_dir,
        runs=2,
        quiet=True,
        clean_aux=clean,
    )

    if result.success:
        print_success(f"PDF generado: {result.pdf_path.name}")
        if result.warnings:
            print_warning(f"Advertencias: {len(result.warnings)}")
    else:
        print_error("Error al compilar PDF")
        if result.error_message:
            typer.echo(f"  {result.error_message[:200]}")
        raise typer.Exit(1)

    print_separator()


def project_report(
    project_id: Annotated[str, typer.Argument(help="ID del proyecto")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Nombre del directorio de salida")] = None,
    author: Annotated[str, typer.Option("--author", help="Autor del reporte")] = "",
    template_dir: Annotated[Optional[str], typer.Option("--template", "-t", help="Directorio con template")] = None,
    pdf: Annotated[bool, typer.Option("--pdf", help="Compilar automáticamente a PDF")] = False,
    clean: Annotated[bool, typer.Option("--clean/--no-clean", help="Limpiar archivos auxiliares")] = True,
    palette: Annotated[str, typer.Option("--palette", "-p", help="Paleta de colores")] = "default",
    methodology: Annotated[bool, typer.Option("--methodology", "-m", help="Incluir textos metodológicos")] = False,
    basin: Annotated[Optional[list[str]], typer.Option("--basin", "-b", help="Incluir solo estas cuencas (puede repetirse)")] = None,
    tr: Annotated[Optional[list[int]], typer.Option("--tr", help="Filtrar por período de retorno (puede repetirse)")] = None,
    tc_method: Annotated[Optional[list[str]], typer.Option("--tc-method", help="Filtrar por método Tc (puede repetirse)")] = None,
) -> None:
    """
    Genera reporte LaTeX consolidado para un proyecto.

    Incluye las cuencas del proyecto en un solo documento,
    con secciones separadas por cuenca.

    Filtros disponibles:
    - --basin/-b: Incluir solo cuencas específicas (por nombre o ID)
    - --tr: Incluir solo análisis con ciertos períodos de retorno
    - --tc-method: Incluir solo análisis con ciertos métodos de Tc

    Estructura de salida:
    - output/<nombre_proyecto>/
      - <proyecto>_memoria.tex (documento principal)
      - sec_proyecto.tex (información del proyecto)
      - sec_metodologia.tex (opcional, con --methodology)
      - cuenca_<id>/
        - sec_cuenca.tex, sec_tc.tex, sec_resultados.tex
        - hietogramas/*.tex, hidrogramas/*.tex

    Ejemplo:
        hidropluvial project report abc123 --pdf
        hidropluvial project report abc123 -m --author "Ing. Pérez"
        hidropluvial project report abc123 --basin "Cuenca A" --basin "Cuenca B"
        hidropluvial project report abc123 --tr 10 --tr 25 --tc-method kirpich
    """
    # Validaciones iniciales
    _validate_palette(palette)
    project = _get_and_validate_project(project_id)

    # Aplicar filtros
    basins_to_include = _filter_basins_by_name(project, basin)
    basins_to_include = _filter_analyses(basins_to_include, tr, tc_method)

    # Validar que hay análisis
    total_analyses = sum(len(b.analyses) for b in basins_to_include)
    if total_analyses == 0:
        print_error("No hay análisis en ninguna cuenca del proyecto.")
        raise typer.Exit(1)

    # Configurar directorio de salida
    output_dir = _setup_output_dir(project, output)
    output_name = output_dir.name

    print_header(f"GENERANDO REPORTE - {project.name}")
    typer.echo(f"  Directorio: {output_dir.absolute()}")
    typer.echo(f"  Cuencas: {len(basins_to_include)}")
    typer.echo(f"  Análisis totales: {total_analyses}")

    # Procesar cuencas
    basin_sections, all_generated_files = _process_basins(basins_to_include, output_dir)

    # Generar sección del proyecto
    project_content = _generate_project_section(project, basins_to_include, len(basin_sections), total_analyses)
    project_section_path = output_dir / "sec_proyecto.tex"
    project_section_path.write_text(project_content, encoding="utf-8")

    # Generar sección de metodología (opcional)
    methodology_content = ""
    if methodology:
        methodology_content = _generate_project_methodology(basins_to_include)
        methodology_path = output_dir / "sec_metodologia.tex"
        methodology_path.write_text(methodology_content, encoding="utf-8")
        typer.echo(f"\n  + sec_metodologia.tex (marco teórico)")

    # Generar documento principal
    main_filename = f"{output_name}_memoria.tex"
    main_path = output_dir / main_filename

    if template_dir:
        doc = _generate_project_template_document(
            project, author, template_dir, output_dir, basin_sections,
            include_methodology=methodology
        )
    else:
        doc = _generate_project_standalone_document(
            project, author, basin_sections,
            include_methodology=methodology
        )

    main_path.write_text(doc, encoding="utf-8")

    # Resumen
    print_subheader("ARCHIVOS GENERADOS")
    typer.echo(f"  Documento principal: {main_filename}")
    typer.echo(f"  Sección proyecto: sec_proyecto.tex")
    if methodology:
        typer.echo(f"  Marco teórico: sec_metodologia.tex")
    for bs in basin_sections:
        typer.echo(f"  Cuenca '{bs['name']}': cuenca_{bs['safe_name']}/")
    typer.echo(f"  Total hietogramas: {len(all_generated_files['hyetographs'])}")
    typer.echo(f"  Total hidrogramas: {len(all_generated_files['hydrographs'])}")
    print_separator()

    # Compilación a PDF
    if pdf:
        _compile_to_pdf(main_path, output_dir, main_filename, clean)
    else:
        typer.echo(f"\n  Para compilar:")
        typer.echo(f"    cd {output_dir.absolute()}")
        typer.echo(f"    pdflatex {main_filename}")
        print_separator()


def _generate_basin_tikz(basin, basin_dir, hidrogramas_dir, hietogramas_dir) -> dict:
    """Genera gráficos TikZ para una cuenca."""
    from hidropluvial.reports.charts import (
        HydrographSeries,
        generate_hydrograph_tikz,
        generate_hyetograph_tikz,
    )

    generated = {"hyetographs": [], "hydrographs": []}
    fig_width = r"0.9\textwidth"
    fig_height = "6cm"

    for analysis in basin.analyses:
        has_storm = len(analysis.storm.time_min) > 0
        has_hydro = len(analysis.hydrograph.time_hr) > 0

        x_str = f"_X{analysis.hydrograph.x_factor:.2f}".replace(".", "") if analysis.hydrograph.x_factor else ""
        file_id = f"{analysis.tc.method}_{analysis.storm.type}_Tr{analysis.storm.return_period}{x_str}"

        # Hietograma
        if has_storm:
            hyeto_filename = f"hietograma_{file_id}.tex"
            hyeto_path = hietogramas_dir / hyeto_filename

            hyeto_tikz = generate_hyetograph_tikz(
                time_min=analysis.storm.time_min,
                intensity_mmhr=analysis.storm.intensity_mmhr,
                caption=f"Hietograma - {analysis.storm.type.upper()} $T_r$={analysis.storm.return_period}",
                label=f"fig:hyeto_{file_id}",
                width=fig_width,
                height=fig_height,
                include_figure=False,
            )
            hyeto_path.write_text(hyeto_tikz, encoding="utf-8")
            generated["hyetographs"].append(hyeto_filename)

        # Hidrograma
        if has_hydro:
            hydro_filename = f"hidrograma_{file_id}.tex"
            hydro_path = hidrogramas_dir / hydro_filename

            time_min_hydro = [t * 60 for t in analysis.hydrograph.time_hr]
            x_label = f" X={analysis.hydrograph.x_factor:.2f}" if analysis.hydrograph.x_factor else ""

            series = [
                HydrographSeries(
                    time_min=time_min_hydro,
                    flow_m3s=analysis.hydrograph.flow_m3s,
                    label=f"{analysis.tc.method.title()}{x_label}",
                    color="blue",
                    style="solid",
                )
            ]

            hydro_tikz = generate_hydrograph_tikz(
                series=series,
                caption=f"Hidrograma - {analysis.tc.method.title()} + {analysis.storm.type.upper()} $T_r$={analysis.storm.return_period}",
                label=f"fig:hydro_{file_id}",
                width=fig_width,
                height=fig_height,
                include_figure=False,
            )
            hydro_path.write_text(hydro_tikz, encoding="utf-8")
            generated["hydrographs"].append(hydro_filename)

    return generated


def _generate_basin_sections(basin, basin_dir, generated_files, basin_safe_name) -> dict:
    """Genera secciones LaTeX para una cuenca individual."""

    # Path prefix para referencias desde el documento principal
    path_prefix = f"cuenca_{basin_safe_name}/"

    sections = {}

    # 1. Sección de información de la cuenca
    sections["sec_cuenca.tex"] = _generate_sec_cuenca(basin)

    # 2. Sección de tiempos de concentración
    sections["sec_tc.tex"] = _generate_sec_tc(basin)

    # 3. Sección de resultados (tabla resumen + fichas individuales)
    sections["sec_resultados.tex"] = _generate_sec_resultados(basin)

    # 4. Sección de fichas individuales (opcional)
    if basin.analyses:
        sections["sec_fichas.tex"] = _generate_sec_fichas(
            basin, generated_files, path_prefix
        )

    # Guardar archivos de sección en el directorio de la cuenca
    for sec_name, sec_content in sections.items():
        sec_path = basin_dir / sec_name
        sec_path.write_text(sec_content, encoding="utf-8")

    return sections


def _generate_sec_cuenca(basin) -> str:
    """Genera sección de información de la cuenca."""
    content = r"""% Sección: Información de la Cuenca
% Generado automáticamente por HidroPluvial

\subsection{Datos de la Cuenca}

\begin{table}[H]
\centering
\begin{tabular}{lr}
\toprule
Parámetro & Valor \\
\midrule
"""
    content += f"Nombre & {basin.name} \\\\\n"
    content += f"Área & {basin.area_ha:.2f} ha \\\\\n"
    content += f"Pendiente & {basin.slope_pct:.2f}\\% \\\\\n"
    content += f"$P_{{3,10}}$ & {basin.p3_10:.1f} mm \\\\\n"

    if basin.length_m:
        content += f"Longitud cauce & {basin.length_m:.0f} m \\\\\n"

    if basin.c is not None:
        content += f"Coeficiente C & {basin.c:.3f} \\\\\n"

    if basin.cn is not None:
        content += f"Curve Number & {basin.cn} \\\\\n"

    content += r"""\bottomrule
\end{tabular}
\caption{Parámetros de la cuenca}
\label{tab:cuenca_params}
\end{table}

"""

    if basin.notes:
        content += f"""\\textbf{{Notas:}} {basin.notes}

"""

    return content


def _generate_sec_tc(basin) -> str:
    """Genera sección de tiempos de concentración."""
    content = r"""% Sección: Tiempos de Concentración
% Generado automáticamente por HidroPluvial

\subsection{Tiempos de Concentración}

"""

    if not basin.tc_results:
        content += "No se han calculado tiempos de concentración para esta cuenca.\n\n"
        return content

    content += r"""\begin{table}[H]
\centering
\begin{tabular}{lrr}
\toprule
Método & Tc (min) & Tc (hr) \\
\midrule
"""

    for tc in basin.tc_results:
        method_name = tc.method.capitalize()
        content += f"{method_name} & {tc.tc_min:.1f} & {tc.tc_hr:.3f} \\\\\n"

    content += r"""\bottomrule
\end{tabular}
\caption{Tiempos de concentración calculados}
\label{tab:tc_results}
\end{table}

"""

    return content


def _generate_sec_resultados(basin) -> str:
    """Genera sección de resultados (tabla resumen)."""
    content = r"""% Sección: Resumen de Resultados
% Generado automáticamente por HidroPluvial

\subsection{Resumen de Análisis}

"""

    if not basin.analyses:
        content += "No se han realizado análisis para esta cuenca.\n\n"
        return content

    content += r"""\begin{table}[H]
\centering
\footnotesize
\begin{tabular}{llrrrrr}
\toprule
Método Tc & Tormenta & Tr & P (mm) & Qp (m³/s) & Tp (min) & Vol (hm³) \\
\midrule
"""

    for analysis in basin.analyses:
        method = analysis.tc.method.capitalize()
        storm = analysis.storm.type.upper()
        tr = analysis.storm.return_period
        p_mm = analysis.storm.total_depth_mm
        qp = analysis.hydrograph.peak_flow_m3s
        tp = analysis.hydrograph.time_to_peak_min
        vol = analysis.hydrograph.volume_m3 / 1_000_000  # Convert to hm³

        content += f"{method} & {storm} & {tr} & {p_mm:.1f} & {qp:.3f} & {tp:.1f} & {vol:.4f} \\\\\n"

    content += r"""\bottomrule
\end{tabular}
\caption{Resumen de análisis hidrológicos}
\label{tab:analisis_resumen}
\end{table}

"""

    return content


def _generate_sec_fichas(basin, generated_files, path_prefix) -> str:
    """Genera sección con fichas individuales de cada análisis."""
    content = r"""% Sección: Fichas Individuales de Análisis
% Generado automáticamente por HidroPluvial

\subsection{Análisis Individuales}

"""

    for i, analysis in enumerate(basin.analyses, 1):
        hydro = analysis.hydrograph
        storm = analysis.storm
        tc = analysis.tc

        # Identificador del análisis
        x_str = f"_X{hydro.x_factor:.2f}".replace(".", "") if hydro.x_factor else ""
        file_id = f"{tc.method}_{storm.type}_Tr{storm.return_period}{x_str}"

        # Título de la ficha
        x_label = f" (X={hydro.x_factor:.2f})" if hydro.x_factor else ""
        content += f"\\subsubsection{{Análisis {i}: {tc.method.capitalize()} + {storm.type.upper()} Tr={storm.return_period}{x_label}}}\n\n"

        # Tabla de parámetros del análisis
        content += r"""\begin{table}[H]
\centering
\small
\begin{tabular}{lr}
\toprule
Parámetro & Valor \\
\midrule
"""

        content += f"Método Tc & {tc.method.capitalize()} \\\\\n"
        content += f"Tc (min) & {tc.tc_min:.1f} \\\\\n"
        content += f"Tc (hr) & {tc.tc_hr:.3f} \\\\\n"
        content += "\\midrule\n"
        content += f"Tipo tormenta & {storm.type.upper()} \\\\\n"
        content += f"Período de retorno & {storm.return_period} años \\\\\n"
        content += f"Precipitación total & {storm.total_depth_mm:.1f} mm \\\\\n"
        content += f"Duración & {storm.duration_min:.0f} min \\\\\n"
        content += "\\midrule\n"
        content += f"Caudal pico & {hydro.peak_flow_m3s:.3f} m³/s \\\\\n"
        content += f"Tiempo al pico & {hydro.time_to_peak_min:.1f} min \\\\\n"
        content += f"Volumen total & {hydro.volume_m3 / 1_000_000:.4f} hm³ \\\\\n"

        if hydro.x_factor:
            content += f"Factor X & {hydro.x_factor:.2f} \\\\\n"

        content += r"""\bottomrule
\end{tabular}
\caption{Parámetros del análisis}
\end{table}

"""

        # Gráficos (hietograma e hidrograma)
        hyeto_filename = f"hietograma_{file_id}.tex"
        hydro_filename = f"hidrograma_{file_id}.tex"

        if hyeto_filename in generated_files.get("hyetographs", []):
            content += r"""\begin{figure}[H]
\centering
"""
            content += f"\\input{{{path_prefix}hietogramas/{hyeto_filename}}}\n"
            content += r"""\end{figure}

"""

        if hydro_filename in generated_files.get("hydrographs", []):
            content += r"""\begin{figure}[H]
\centering
"""
            content += f"\\input{{{path_prefix}hidrogramas/{hydro_filename}}}\n"
            content += r"""\end{figure}

"""

        content += "\\clearpage\n\n"

    return content


def _generate_project_section(project, basins: list, n_basins: int, n_analyses: int) -> str:
    """Genera sección de información del proyecto."""
    content = r"""% Sección: Información del Proyecto
% Generado automáticamente por HidroPluvial

\section{Información del Proyecto}

\begin{table}[H]
\centering
\begin{tabular}{lr}
\toprule
Parámetro & Valor \\
\midrule
"""
    content += f"Nombre & {project.name} \\\\\n"

    if project.description:
        content += f"Descripción & {project.description} \\\\\n"

    if project.author:
        content += f"Autor & {project.author} \\\\\n"

    if project.location:
        content += f"Ubicación & {project.location} \\\\\n"

    content += f"Número de cuencas & {n_basins} \\\\\n"
    content += f"Total de análisis & {n_analyses} \\\\\n"

    content += r"""\bottomrule
\end{tabular}
\caption{Resumen del proyecto}
\label{tab:proyecto}
\end{table}

"""

    if project.notes:
        content += f"""\\textbf{{Notas:}} {project.notes}

"""

    # Tabla resumen de cuencas
    content += r"""\subsection{Cuencas del Proyecto}

\begin{table}[H]
\centering
\begin{tabular}{lccc}
\toprule
Cuenca & Área (ha) & Pendiente (\%) & Análisis \\
\midrule
"""

    for basin_obj in basins:
        content += f"{basin_obj.name} & {basin_obj.area_ha:.2f} & {basin_obj.slope_pct:.2f} & {len(basin_obj.analyses)} \\\\\n"

    content += r"""\bottomrule
\end{tabular}
\caption{Resumen de cuencas del proyecto}
\label{tab:cuencas_proyecto}
\end{table}

"""

    return content


def _generate_project_methodology(basins: list) -> str:
    """Genera sección de metodología consolidada para el proyecto."""
    from hidropluvial.reports.methodology import (
        get_tc_methodology_latex,
        get_runoff_methodology_latex,
        get_hydrograph_methodology_latex,
        get_storms_methodology_latex,
    )

    content = r"""% Sección: Marco Teórico y Metodologías
% Generado automáticamente por HidroPluvial

\section{Marco Teórico y Metodologías}

Este capítulo presenta los fundamentos teóricos de las metodologías hidrológicas
empleadas en el presente estudio. Se incluyen las formulaciones matemáticas,
rangos de aplicación y referencias bibliográficas para cada método.

"""

    # Recolectar todos los métodos usados en todas las cuencas
    tc_methods = set()
    storm_types = set()
    runoff_methods = set()

    for basin_obj in basins:
        for tc in basin_obj.tc_results:
            tc_methods.add(tc.method)

        for a in basin_obj.analyses:
            storm_types.add(a.storm.type)

            if a.tc.parameters:
                if "runoff_method" in a.tc.parameters:
                    rm = a.tc.parameters["runoff_method"]
                    runoff_methods.add("racional" if rm == "racional" else "scs-cn")
                elif "cn_adjusted" in a.tc.parameters:
                    runoff_methods.add("scs-cn")
                elif "c" in a.tc.parameters:
                    runoff_methods.add("racional")

    # Generar contenido
    content += get_tc_methodology_latex(methods_used=list(tc_methods))
    content += get_storms_methodology_latex(storm_types_used=list(storm_types))

    if runoff_methods:
        content += get_runoff_methodology_latex(methods_used=list(runoff_methods))

    content += get_hydrograph_methodology_latex()

    return content


def _generate_project_standalone_document(
    project, author: str, basin_sections: list, include_methodology: bool
) -> str:
    """Genera documento LaTeX standalone para el proyecto."""
    # Usar 'report' para soportar \chapter cuando hay múltiples cuencas
    doc_class = "report" if len(basin_sections) > 1 else "article"
    doc = f"""\\documentclass[11pt,a4paper]{{{doc_class}}}

\\usepackage[spanish]{{babel}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[T1]{{fontenc}}
\\usepackage{{geometry}}
\\geometry{{margin=2.5cm}}
\\usepackage{{booktabs}}
\\usepackage{{siunitx}}
\\usepackage{{float}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}
\\usepackage{{tikz}}
\\usepackage{{pgfplots}}
\\pgfplotsset{{compat=1.18}}
\\usepackage{{amsmath}}

"""

    safe_title = project.name.replace("_", " ")
    doc += f"\\title{{{safe_title} \\\\ \\large Memoria de Cálculo Hidrológico}}\n"
    doc += f"\\author{{{author or 'HidroPluvial'}}}\n"
    doc += "\\date{\\today}\n\n"

    doc += r"""\begin{document}

\maketitle
\tableofcontents
\newpage

"""

    # Incluir sección del proyecto
    doc += "\\input{sec_proyecto}\n\n"

    # Incluir metodología si corresponde
    if include_methodology:
        doc += "\\input{sec_metodologia}\n\n"

    # Incluir cada cuenca
    for bs in basin_sections:
        doc += f"% ==================== CUENCA: {bs['name']} ====================\n"
        doc += f"\\chapter{{{bs['name']}}}\n" if len(basin_sections) > 1 else ""
        doc += f"\\input{{cuenca_{bs['safe_name']}/sec_cuenca}}\n"
        doc += f"\\input{{cuenca_{bs['safe_name']}/sec_tc}}\n"
        doc += f"\\input{{cuenca_{bs['safe_name']}/sec_resultados}}\n"

        # Verificar si existen las secciones opcionales
        doc += f"\\IfFileExists{{cuenca_{bs['safe_name']}/sec_estadisticas.tex}}{{\\input{{cuenca_{bs['safe_name']}/sec_estadisticas}}}}{{}}\n"
        doc += f"\\IfFileExists{{cuenca_{bs['safe_name']}/sec_fichas.tex}}{{\\input{{cuenca_{bs['safe_name']}/sec_fichas}}}}{{}}\n"
        doc += "\n"

    doc += r"""
\end{document}
"""

    return doc


def _generate_project_template_document(
    project, author: str, template_dir: str, output_dir, basin_sections: list,
    include_methodology: bool
) -> str:
    """Genera documento con template Pablo Pizarro para proyecto."""
    import shutil
    from pathlib import Path

    template_path = Path(template_dir)
    template_file = template_path / "template.tex"
    config_file = template_path / "template_config.tex"

    if template_file.exists():
        shutil.copy(template_file, output_dir / "template.tex")

    if config_file.exists():
        shutil.copy(config_file, output_dir / "template_config.tex")

    # Copiar carpeta departamentos si existe
    dept_dir = template_path / "departamentos"
    if dept_dir.exists() and dept_dir.is_dir():
        dest_dept = output_dir / "departamentos"
        if dest_dept.exists():
            shutil.rmtree(dest_dept)
        shutil.copytree(dept_dir, dest_dept)

    # Generar document.tex
    document_content = """% Documento de contenido
% Generado automáticamente por HidroPluvial

\\input{sec_proyecto}

"""

    if include_methodology:
        document_content += "\\input{sec_metodologia}\n\n"

    for bs in basin_sections:
        document_content += f"% Cuenca: {bs['name']}\n"
        document_content += f"\\input{{cuenca_{bs['safe_name']}/sec_cuenca}}\n"
        document_content += f"\\input{{cuenca_{bs['safe_name']}/sec_tc}}\n"
        document_content += f"\\input{{cuenca_{bs['safe_name']}/sec_resultados}}\n"
        document_content += f"\\IfFileExists{{cuenca_{bs['safe_name']}/sec_estadisticas.tex}}{{\\input{{cuenca_{bs['safe_name']}/sec_estadisticas}}}}{{}}\n"
        document_content += f"\\IfFileExists{{cuenca_{bs['safe_name']}/sec_fichas.tex}}{{\\input{{cuenca_{bs['safe_name']}/sec_fichas}}}}{{}}\n\n"

    doc_content_path = output_dir / "document.tex"
    doc_content_path.write_text(document_content, encoding="utf-8")

    # Generar main.tex
    safe_title = project.name.replace("_", " ")

    doc = f"""% Memoria de Cálculo Hidrológico - Proyecto
% Generado automáticamente por HidroPluvial

\\documentclass[
    spanish,
    letterpaper, oneside
]{{article}}

\\def\\documenttitle {{{safe_title}}}
\\def\\documentsubtitle {{Memoria de Cálculo Hidrológico}}
\\def\\documentsubject {{Análisis hidrológico de múltiples cuencas}}

\\def\\documentauthor {{{author or project.author or "HidroPluvial"}}}
\\def\\coursename {{}}
\\def\\coursecode {{}}

\\def\\universityname {{}}
\\def\\universityfaculty {{}}
\\def\\universitydepartment {{}}
\\def\\universitydepartmentimage {{}}
\\def\\universitydepartmentimagecfg {{height=3.5cm}}
\\def\\universitylocation {{{project.location or "Uruguay"}}}

\\def\\authortable {{
    \\begin{{tabular}}{{ll}}
        Autor: & {author or project.author or "HidroPluvial"} \\\\
        \\\\
        \\multicolumn{{2}}{{l}}{{Fecha: \\today}} \\\\
        \\multicolumn{{2}}{{l}}{{\\universitylocation}}
    \\end{{tabular}}
}}

\\input{{template}}

\\usepackage{{tabularx}}
\\usepackage{{pgfplots}}
\\pgfplotsset{{compat=1.18}}
\\usepackage{{makecell}}
\\usepackage{{amsmath}}

\\begin{{document}}

\\pdfcompresslevel=9
\\pdfobjcompresslevel=3

\\templatePortrait
\\templatePagecfg
\\templateIndex
\\templateFinalcfg

\\input{{document}}

\\end{{document}}
"""

    return doc
