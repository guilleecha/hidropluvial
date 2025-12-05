"""
Comando de generación de reportes LaTeX desde sesión.
"""

import shutil
from pathlib import Path
from typing import Annotated, Optional

import typer

from hidropluvial.reports import ReportGenerator
from hidropluvial.cli.session.base import get_session_manager


def session_report(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Nombre del directorio de salida (default: nombre de sesión)")] = None,
    author: Annotated[str, typer.Option("--author", help="Autor del reporte")] = "",
    template_dir: Annotated[Optional[str], typer.Option("--template", "-t", help="Directorio con template Pablo Pizarro")] = None,
):
    """
    Genera reporte LaTeX con gráficos TikZ para cada análisis.

    Crea estructura en output/<nombre_sesion>/:
    - Archivo principal (.tex)
    - hietogramas/*.tex
    - hidrogramas/*.tex

    Con --template: Genera documento compatible con template Pablo Pizarro
    y copia los archivos del template al directorio de salida.

    Ejemplo:
        hidropluvial session report abc123 --author "Ing. Pérez"
        hidropluvial session report abc123 -o mi_reporte --template examples/
    """
    from hidropluvial.reports.charts import (
        HydrographSeries,
        generate_hydrograph_tikz,
        generate_hyetograph_tikz,
    )

    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    if not session.analyses:
        typer.echo(f"Error: No hay análisis en la sesión.", err=True)
        raise typer.Exit(1)

    # Determinar nombre del directorio de salida
    if output is None:
        # Usar nombre de sesión sanitizado
        safe_name = session.name.lower().replace(" ", "_").replace("/", "_")
        output_name = safe_name
    else:
        output_name = output

    # Crear estructura: output/<nombre_sesion>/
    base_output = Path("output")
    output_dir = base_output / output_name
    output_dir.mkdir(parents=True, exist_ok=True)

    hidrogramas_dir = output_dir / "hidrogramas"
    hietogramas_dir = output_dir / "hietogramas"
    hidrogramas_dir.mkdir(exist_ok=True)
    hietogramas_dir.mkdir(exist_ok=True)

    generator = ReportGenerator()
    rows = manager.get_summary_table(session)

    typer.echo(f"\n{'='*60}")
    typer.echo(f"  GENERANDO REPORTE - {session.name}")
    typer.echo(f"{'='*60}")
    typer.echo(f"  Directorio: {output_dir.absolute()}")

    # =========================================================================
    # GENERAR GRÁFICOS TIKZ
    # =========================================================================
    generated_files = {"hyetographs": [], "hydrographs": []}

    typer.echo(f"\n  Generando gráficos TikZ...")

    for i, analysis in enumerate(session.analyses):
        # Verificar si hay datos de series temporales
        has_storm_data = len(analysis.storm.time_min) > 0 and len(analysis.storm.intensity_mmhr) > 0
        has_hydro_data = len(analysis.hydrograph.time_hr) > 0 and len(analysis.hydrograph.flow_m3s) > 0

        # Identificador único para el análisis
        x_str = f"_X{analysis.hydrograph.x_factor:.2f}".replace(".", "") if analysis.hydrograph.x_factor else ""
        file_id = f"{analysis.tc.method}_{analysis.storm.type}_Tr{analysis.storm.return_period}{x_str}"

        # -----------------------------------------------------------------
        # Generar hietograma
        # -----------------------------------------------------------------
        if has_storm_data:
            hyeto_filename = f"hietograma_{file_id}.tex"
            hyeto_path = hietogramas_dir / hyeto_filename

            hyeto_caption = (
                f"Hietograma - {analysis.storm.type.upper()} "
                f"$T_r$={analysis.storm.return_period} años "
                f"(P={analysis.storm.total_depth_mm:.1f} mm)"
            )

            hyeto_tikz = generate_hyetograph_tikz(
                time_min=analysis.storm.time_min,
                intensity_mmhr=analysis.storm.intensity_mmhr,
                caption=hyeto_caption,
                label=f"fig:hyeto_{file_id}",
                width=r"0.9\textwidth",
                height="6cm",
                include_figure=False,  # Se incluirá dentro de minipage en fichas
            )

            hyeto_path.write_text(hyeto_tikz, encoding="utf-8")
            generated_files["hyetographs"].append(hyeto_filename)
            typer.echo(f"    + hietogramas/{hyeto_filename}")

        # -----------------------------------------------------------------
        # Generar hidrograma
        # -----------------------------------------------------------------
        if has_hydro_data:
            hydro_filename = f"hidrograma_{file_id}.tex"
            hydro_path = hidrogramas_dir / hydro_filename

            # Convertir tiempo de horas a minutos para el gráfico
            time_min_hydro = [t * 60 for t in analysis.hydrograph.time_hr]

            hydro_caption = (
                f"Hidrograma - {analysis.tc.method.title()} + {analysis.storm.type.upper()} "
                f"$T_r$={analysis.storm.return_period} años "
                r"($Q_p$=" + f"{analysis.hydrograph.peak_flow_m3s:.3f}" + r" m$^3$/s)"
            )

            x_label = f" X={analysis.hydrograph.x_factor:.2f}" if analysis.hydrograph.x_factor else ""
            series_label = f"{analysis.tc.method.title()}{x_label}"

            series = [
                HydrographSeries(
                    time_min=time_min_hydro,
                    flow_m3s=analysis.hydrograph.flow_m3s,
                    label=series_label,
                    color="blue",
                    style="solid",
                )
            ]

            hydro_tikz = generate_hydrograph_tikz(
                series=series,
                caption=hydro_caption,
                label=f"fig:hydro_{file_id}",
                width=r"0.9\textwidth",
                height="6cm",
                include_figure=False,  # Se incluirá dentro de minipage en fichas
            )

            hydro_path.write_text(hydro_tikz, encoding="utf-8")
            generated_files["hydrographs"].append(hydro_filename)
            typer.echo(f"    + hidrogramas/{hydro_filename}")

    # =========================================================================
    # GENERAR ARCHIVOS DE SECCIONES SEPARADOS
    # =========================================================================
    sections = _generate_sections(session, rows, generated_files)

    # =========================================================================
    # GENERAR DOCUMENTO PRINCIPAL
    # =========================================================================
    main_filename = f"{session.name.replace(' ', '_').lower()}_memoria.tex"
    main_path = output_dir / main_filename

    if template_dir:
        doc = _generate_template_document(
            session, author, template_dir, output_dir, sections, typer
        )
    else:
        # Generar documento standalone completo
        content = "\n".join(sections.values())
        doc = generator.generate_standalone_document(
            content=content,
            title=f"Memoria de Cálculo: {session.name}",
            author=author,
            include_tikz=True,
        )

    main_path.write_text(doc, encoding="utf-8")

    # =========================================================================
    # RESUMEN
    # =========================================================================
    typer.echo(f"\n  {'='*50}")
    typer.echo(f"  ARCHIVOS GENERADOS:")
    typer.echo(f"  {'='*50}")
    typer.echo(f"  Documento principal: {main_filename}")
    if template_dir:
        typer.echo(f"  Template:            template.tex + template_config.tex")
        typer.echo(f"  Contenido:           document.tex")
        typer.echo(f"  Secciones:           {len(sections)} archivos (sec_*.tex)")
    typer.echo(f"  hietogramas/         {len(generated_files['hyetographs'])} archivos")
    typer.echo(f"  hidrogramas/         {len(generated_files['hydrographs'])} archivos")
    typer.echo(f"  {'='*50}")
    typer.echo(f"\n  Para compilar:")
    typer.echo(f"    cd {output_dir.absolute()}")
    typer.echo(f"    pdflatex {main_filename}")
    typer.echo(f"{'='*60}\n")


def _generate_sections(session, rows, generated_files):
    """Genera el contenido de las secciones del reporte."""
    # --- sec_cuenca.tex: Datos de la cuenca ---
    cuenca_content = f"""% Sección: Datos de la Cuenca
% Generado automáticamente por HidroPluvial

\\section{{Datos de la Cuenca}}

\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{lr}}
\\toprule
Parámetro & Valor \\\\
\\midrule
Nombre & {session.cuenca.nombre or session.name} \\\\
Área & {session.cuenca.area_ha:.2f} ha \\\\
Pendiente & {session.cuenca.slope_pct:.2f} \\% \\\\
$P_{{3,10}}$ & {session.cuenca.p3_10:.1f} mm \\\\
"""
    if session.cuenca.c:
        cuenca_content += f"Coef. escorrentía C & {session.cuenca.c:.2f} \\\\\n"
    if session.cuenca.cn:
        cuenca_content += f"Curve Number CN & {session.cuenca.cn} \\\\\n"
    if session.cuenca.length_m:
        cuenca_content += f"Longitud cauce & {session.cuenca.length_m:.0f} m \\\\\n"

    cuenca_content += """\\bottomrule
\\end{tabular}
\\caption{Características de la cuenca}
\\label{tab:cuenca}
\\end{table}
"""

    # Agregar tabla de ponderación de C si existe
    if session.cuenca.c_weighted and session.cuenca.c_weighted.items:
        cw = session.cuenca.c_weighted
        cuenca_content += f"""
\\subsection{{Determinación del Coeficiente C}}

El coeficiente de escorrentía C se determinó mediante ponderación por área
usando la tabla \\textbf{{{cw.table_used.upper() if cw.table_used else "N/A"}}}.

\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{lrrr}}
\\toprule
Cobertura & Área (ha) & \\% Área & C \\\\
\\midrule
"""
        for item in cw.items:
            pct = (item.area_ha / session.cuenca.area_ha) * 100 if session.cuenca.area_ha > 0 else 0
            cuenca_content += f"{item.description} & {item.area_ha:.2f} & {pct:.1f}\\% & {item.value:.2f} \\\\\n"

        cuenca_content += f"""\\midrule
\\textbf{{Total}} & \\textbf{{{session.cuenca.area_ha:.2f}}} & \\textbf{{100\\%}} & \\textbf{{{cw.weighted_value:.2f}}} \\\\
\\bottomrule
\\end{{tabular}}
\\caption{{Ponderación del coeficiente de escorrentía C}}
\\label{{tab:c_ponderado}}
\\end{{table}}
"""

    # Agregar tabla de ponderación de CN si existe
    if session.cuenca.cn_weighted and session.cuenca.cn_weighted.items:
        cnw = session.cuenca.cn_weighted
        cuenca_content += f"""
\\subsection{{Determinación del Curve Number CN}}

El Curve Number se determinó mediante ponderación por área
usando la tabla \\textbf{{{cnw.table_used.upper() if cnw.table_used else "NRCS"}}}.

\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{lrrr}}
\\toprule
Cobertura/Uso de suelo & Área (ha) & \\% Área & CN \\\\
\\midrule
"""
        for item in cnw.items:
            pct = (item.area_ha / session.cuenca.area_ha) * 100 if session.cuenca.area_ha > 0 else 0
            cuenca_content += f"{item.description} & {item.area_ha:.2f} & {pct:.1f}\\% & {item.value:.0f} \\\\\n"

        cuenca_content += f"""\\midrule
\\textbf{{Total}} & \\textbf{{{session.cuenca.area_ha:.2f}}} & \\textbf{{100\\%}} & \\textbf{{{cnw.weighted_value:.0f}}} \\\\
\\bottomrule
\\end{{tabular}}
\\caption{{Ponderación del Curve Number CN}}
\\label{{tab:cn_ponderado}}
\\end{{table}}
"""

    # --- sec_tc.tex: Tiempos de concentración ---
    tc_content = """% Sección: Tiempos de Concentración
% Generado automáticamente por HidroPluvial

\\section{Tiempos de Concentración}

\\begin{table}[H]
\\centering
\\begin{tabular}{lrr}
\\toprule
Método & $T_c$ (hr) & $T_c$ (min) \\\\
\\midrule
"""
    for tc in session.tc_results:
        tc_content += f"{tc.method.title()} & {tc.tc_hr:.3f} & {tc.tc_min:.1f} \\\\\n"

    tc_content += """\\bottomrule
\\end{tabular}
\\caption{Tiempos de concentración calculados}
\\label{tab:tc}
\\end{table}
"""

    # --- sec_resultados.tex: Tabla de resultados ---
    # Determinar si hay múltiples métodos de escorrentía
    has_multiple_runoff = _has_multiple_runoff_methods(session)

    results_content = f"""% Sección: Resultados de Análisis
% Generado automáticamente por HidroPluvial

\\section{{Resultados de Análisis}}

Se realizaron {len(rows)} combinaciones de análisis variando:
\\begin{{itemize}}
    \\item Métodos de tiempo de concentración
    \\item Tipos de tormenta de diseño
    \\item Períodos de retorno
"""
    if has_multiple_runoff:
        results_content += "    \\item Métodos de precipitación efectiva ($P_e$): Racional (C) y SCS-CN\n"
    results_content += """    \\item Factor morfológico X (para tormentas GZ)
\\end{{itemize}}

\\begin{{table}}[H]
\\centering
\\footnotesize
"""
    if has_multiple_runoff:
        results_content += """\\begin{tabular}{lclcccccccc}
\\toprule
Método $T_c$ & $P_e$ & Tormenta & $T_r$ & $t_p$ (min) & X & $t_b$ (min) & P (mm) & $P_e$ (mm) & $Q_p$ (m$^3$/s) \\\\
\\midrule
"""
    else:
        results_content += """\\begin{tabular}{lcccccccccc}
\\toprule
Método $T_c$ & Tormenta & $T_r$ & $t_p$ (min) & X & $t_b$ (min) & P (mm) & $P_e$ (mm) & $Q_p$ (m$^3$/s) & $T_p$ (min) & Vol (hm$^3$) \\\\
\\midrule
"""
    for i, r in enumerate(rows):
        x_str = f"{r['x']:.2f}" if r['x'] else "-"
        tp_str = f"{r['tp_min']:.1f}" if r['tp_min'] else "-"
        tb_str = f"{r['tb_min']:.1f}" if r['tb_min'] else "-"
        Tp_str = f"{r['Tp_min']:.1f}" if r['Tp_min'] else "-"
        vol_hm3 = r['vol_m3'] / 1_000_000
        # Obtener método de escorrentía del análisis
        analysis = session.analyses[i] if i < len(session.analyses) else None
        runoff_label = _get_runoff_label(analysis) if analysis else "-"

        if has_multiple_runoff:
            results_content += (
                f"{r['tc_method']} & {runoff_label} & {r['storm']} & {r['tr']} & {tp_str} & {x_str} & {tb_str} & "
                f"{r['depth_mm']:.1f} & {r['runoff_mm']:.1f} & {r['qpeak_m3s']:.2f} \\\\\n"
            )
        else:
            results_content += (
                f"{r['tc_method']} & {r['storm']} & {r['tr']} & {tp_str} & {x_str} & {tb_str} & "
                f"{r['depth_mm']:.1f} & {r['runoff_mm']:.1f} & {r['qpeak_m3s']:.2f} & {Tp_str} & {vol_hm3:.4f} \\\\\n"
            )

    results_content += """\\bottomrule
\\end{tabular}
\\caption{Tabla comparativa de análisis}
\\label{tab:results}
\\end{table}
"""

    # --- sec_estadisticas.tex: Resumen estadístico ---
    stats_content = ""
    if len(rows) > 1:
        max_q = max(rows, key=lambda x: x['qpeak_m3s'])
        min_q = min(rows, key=lambda x: x['qpeak_m3s'])
        avg_q = sum(r['qpeak_m3s'] for r in rows) / len(rows)
        variation = (max_q['qpeak_m3s'] - min_q['qpeak_m3s']) / min_q['qpeak_m3s'] * 100

        stats_content = f"""% Sección: Resumen Estadístico
% Generado automáticamente por HidroPluvial

\\section{{Resumen Estadístico}}

\\begin{{table}}[H]
\\centering
\\begin{{tabular}}{{lr}}
\\toprule
Estadístico & Valor \\\\
\\midrule
Número de análisis & {len(rows)} \\\\
Caudal pico máximo & {max_q['qpeak_m3s']:.2f} m$^3$/s ({max_q['tc_method']} + {max_q['storm']} $T_r$={max_q['tr']}) \\\\
Caudal pico mínimo & {min_q['qpeak_m3s']:.2f} m$^3$/s ({min_q['tc_method']} + {min_q['storm']} $T_r$={min_q['tr']}) \\\\
Caudal pico promedio & {avg_q:.2f} m$^3$/s \\\\
Variación máx/mín & {variation:.1f}\\% \\\\
\\bottomrule
\\end{{tabular}}
\\caption{{Resumen estadístico de caudales pico}}
\\label{{tab:summary}}
\\end{{table}}
"""

    # --- Generar fichas técnicas por análisis ---
    # Cada análisis tiene su propia ficha con: datos, hietograma, hidrograma
    fichas_content = ""
    if generated_files["hyetographs"] or generated_files["hydrographs"]:
        fichas_content = """% Sección: Fichas Técnicas por Análisis
% Generado automáticamente por HidroPluvial

\\section{Fichas Técnicas por Análisis}

"""
        # Crear ficha para cada análisis
        for i, analysis in enumerate(session.analyses):
            x_str = f"_X{analysis.hydrograph.x_factor:.2f}".replace(".", "") if analysis.hydrograph.x_factor else ""
            file_id = f"{analysis.tc.method}_{analysis.storm.type}_Tr{analysis.storm.return_period}{x_str}"

            # Título de la ficha
            x_display = f"X={analysis.hydrograph.x_factor:.2f}" if analysis.hydrograph.x_factor else ""
            ficha_titulo = f"{analysis.tc.method.title()} + {analysis.storm.type.upper()} $T_r$={analysis.storm.return_period} años {x_display}"

            # Calcular parámetros del Hidrograma Unitario
            tc_hr = analysis.tc.tc_hr
            # Asumir dt = Tc/10 para el HU (intervalo típico)
            dt_hr = tc_hr / 10
            x = analysis.hydrograph.x_factor if analysis.hydrograph.x_factor else 1.0

            # Tp = Du/2 + 0.6*Tc (tiempo al pico del HU)
            tp_hu_hr = dt_hr / 2 + 0.6 * tc_hr
            tp_hu_min = tp_hu_hr * 60

            # Tb = (1 + X) * Tp (tiempo base del HU)
            tb_hu_hr = (1 + x) * tp_hu_hr
            tb_hu_min = tb_hu_hr * 60

            # qp_unit = 0.278 * A[km²] / Tp * 2 / (1 + X) para 1 mm de escorrentía
            area_km2 = session.cuenca.area_ha / 100
            qp_unit = 0.278 * area_km2 / tp_hu_hr * 2 / (1 + x)

            # Determinar método de precipitación efectiva
            pe_method = "-"
            if analysis.tc.parameters and "runoff_method" in analysis.tc.parameters:
                rm = analysis.tc.parameters["runoff_method"]
                pe_method = "Racional (C)" if rm == "racional" else "SCS-CN"
            elif analysis.tc.parameters:
                if "cn_adjusted" in analysis.tc.parameters:
                    pe_method = "SCS-CN"
                elif "c" in analysis.tc.parameters:
                    pe_method = "Racional (C)"

            # Usar valores del modelo si existen, sino calcular
            tp_hu_min = analysis.hydrograph.tp_unit_min if analysis.hydrograph.tp_unit_min else tp_hu_hr * 60
            tb_hu_min = analysis.hydrograph.tb_min if analysis.hydrograph.tb_min else tb_hu_hr * 60
            vol_hm3 = analysis.hydrograph.volume_m3 / 1_000_000
            Tp_min = analysis.hydrograph.time_to_peak_min

            fichas_content += f"""\\subsection{{{ficha_titulo}}}

% Tabla de parámetros del análisis
\\begin{{table}}[H]
\\centering
\\small
\\begin{{tabular}}{{lr|lr|lr}}
\\toprule
\\multicolumn{{2}}{{c|}}{{\\textbf{{Tormenta}}}} & \\multicolumn{{2}}{{c|}}{{\\textbf{{Hidrograma Unitario}}}} & \\multicolumn{{2}}{{c}}{{\\textbf{{Resultados}}}} \\\\
\\midrule
$T_c$ ({analysis.tc.method.title()}) & {analysis.tc.tc_min:.1f} min & $t_p$ & {tp_hu_min:.1f} min & $P$ (total) & {analysis.storm.total_depth_mm:.1f} mm \\\\
Tipo & {analysis.storm.type.upper()} & X & {x:.2f} & $P_e$ ({pe_method}) & {analysis.hydrograph.runoff_mm:.1f} mm \\\\
$T_r$ & {analysis.storm.return_period} años & $t_b$ & {tb_hu_min:.1f} min & $Q_p$ & \\textbf{{{analysis.hydrograph.peak_flow_m3s:.2f} m$^3$/s}} \\\\
Duración & {analysis.storm.duration_hr:.1f} hr & $q_p$ (HU) & {qp_unit:.2f} m$^3$/s/mm & $T_p$ & {Tp_min:.1f} min \\\\
& & & & Volumen & {vol_hm3:.4f} hm$^3$ \\\\
\\bottomrule
\\end{{tabular}}
\\caption{{Ficha técnica: {ficha_titulo}}}
\\end{{table}}

"""
            # Incluir hietograma (ancho completo)
            hyeto_file = f"hietograma_{file_id}.tex"
            if hyeto_file in generated_files["hyetographs"]:
                fichas_content += f"""% Hietograma
\\begin{{figure}}[H]
\\centering
\\resizebox{{0.95\\textwidth}}{{!}}{{\\input{{hietogramas/{hyeto_file}}}}}
\\caption{{Hietograma - {ficha_titulo}}}
\\end{{figure}}

"""

            # Incluir hidrograma (ancho completo)
            hydro_file = f"hidrograma_{file_id}.tex"
            if hydro_file in generated_files["hydrographs"]:
                fichas_content += f"""% Hidrograma
\\begin{{figure}}[H]
\\centering
\\resizebox{{0.95\\textwidth}}{{!}}{{\\input{{hidrogramas/{hydro_file}}}}}
\\caption{{Hidrograma - {ficha_titulo}}}
\\end{{figure}}

"""

    # --- sec_comparacion.tex: Comparación de metodologías (si hay ambos métodos) ---
    comparison_content = ""
    if _has_multiple_runoff_methods(session):
        comparison_content = _generate_comparison_section(session)

    # Diccionario de secciones
    sections = {
        "sec_cuenca.tex": cuenca_content,
        "sec_tc.tex": tc_content,
        "sec_resultados.tex": results_content,
    }
    if stats_content:
        sections["sec_estadisticas.tex"] = stats_content
    if comparison_content:
        sections["sec_comparacion.tex"] = comparison_content
    if fichas_content:
        sections["sec_fichas.tex"] = fichas_content

    return sections


def _generate_template_document(session, author, template_dir, output_dir, sections, typer):
    """Genera documento con template Pablo Pizarro."""
    template_path = Path(template_dir)
    template_file = template_path / "template.tex"
    config_file = template_path / "template_config.tex"

    if template_file.exists():
        shutil.copy(template_file, output_dir / "template.tex")
        typer.echo(f"    + template.tex")
    else:
        typer.echo(f"  Advertencia: No se encontró template.tex en {template_dir}", err=True)

    if config_file.exists():
        shutil.copy(config_file, output_dir / "template_config.tex")
        typer.echo(f"    + template_config.tex")

    # Copiar carpeta departamentos si existe
    dept_dir = template_path / "departamentos"
    if dept_dir.exists() and dept_dir.is_dir():
        dest_dept = output_dir / "departamentos"
        if dest_dept.exists():
            shutil.rmtree(dest_dept)
        shutil.copytree(dept_dir, dest_dept)
        typer.echo(f"    + departamentos/")

    # Guardar archivos de secciones
    typer.echo(f"\n  Generando secciones LaTeX...")
    for sec_filename, sec_content in sections.items():
        sec_path = output_dir / sec_filename
        sec_path.write_text(sec_content, encoding="utf-8")
        typer.echo(f"    + {sec_filename}")

    # Generar document.tex
    document_content = """% Documento de contenido
% Generado automáticamente por HidroPluvial

"""
    section_order = [
        "sec_cuenca.tex",
        "sec_tc.tex",
        "sec_resultados.tex",
        "sec_estadisticas.tex",
        "sec_comparacion.tex",  # Comparación de metodologías C vs CN
        "sec_fichas.tex",  # Fichas técnicas por análisis
    ]
    for sec in section_order:
        if sec in sections:
            document_content += f"\\input{{{sec.replace('.tex', '')}}}\n"

    doc_content_file = output_dir / "document.tex"
    doc_content_file.write_text(document_content, encoding="utf-8")
    typer.echo(f"    + document.tex")

    # Generar main.tex
    safe_title = session.name.replace("_", " ")

    doc = f"""% Memoria de Cálculo Hidrológico
% Generado automáticamente por HidroPluvial
% Template: Informe LaTeX - Pablo Pizarro R.

% CREACIÓN DEL DOCUMENTO
\\documentclass[
    spanish,
    letterpaper, oneside
]{{article}}

% INFORMACIÓN DEL DOCUMENTO
\\def\\documenttitle {{{safe_title}}}
\\def\\documentsubtitle {{Memoria de Cálculo Hidrológico}}
\\def\\documentsubject {{Análisis de escorrentía y caudales de diseño}}

\\def\\documentauthor {{{author or "HidroPluvial"}}}
\\def\\coursename {{}}
\\def\\coursecode {{}}

\\def\\universityname {{}}
\\def\\universityfaculty {{}}
\\def\\universitydepartment {{}}
\\def\\universitydepartmentimage {{}}
\\def\\universitydepartmentimagecfg {{height=3.5cm}}
\\def\\universitylocation {{Uruguay}}

% INTEGRANTES Y FECHAS
\\def\\authortable {{
    \\begin{{tabular}}{{ll}}
        Autor: & {author or "HidroPluvial"} \\\\
        \\\\
        \\multicolumn{{2}}{{l}}{{Fecha: \\today}} \\\\
        \\multicolumn{{2}}{{l}}{{\\universitylocation}}
    \\end{{tabular}}
}}

% IMPORTACIÓN DEL TEMPLATE
\\input{{template}}

% Paquetes adicionales (no incluidos en template)
\\usepackage{{tabularx}}
\\usepackage{{pgfplots}}
\\pgfplotsset{{compat=1.18}}
\\usepackage{{makecell}}

% INICIO DE PÁGINAS
\\begin{{document}}

% Compresión PDF
\\pdfcompresslevel=9
\\pdfobjcompresslevel=3

% PORTADA
\\templatePortrait

% CONFIGURACIÓN DE PÁGINA
\\templatePagecfg

% TABLA DE CONTENIDOS
\\templateIndex

% CONFIGURACIONES FINALES
\\templateFinalcfg

% CONTENIDO
\\input{{document}}

% FIN DEL DOCUMENTO
\\end{{document}}
"""

    return doc


def _has_multiple_runoff_methods(session) -> bool:
    """Verifica si la sesión tiene análisis con diferentes métodos de escorrentía."""
    methods = set()
    for a in session.analyses:
        if a.tc.parameters and "runoff_method" in a.tc.parameters:
            methods.add(a.tc.parameters["runoff_method"])
        elif a.tc.parameters:
            if "cn_adjusted" in a.tc.parameters:
                methods.add("scs-cn")
            elif "c" in a.tc.parameters:
                methods.add("racional")
    return len(methods) > 1


def _get_runoff_label(analysis) -> str:
    """Obtiene la etiqueta del método de escorrentía para un análisis."""
    if analysis.tc.parameters and "runoff_method" in analysis.tc.parameters:
        rm = analysis.tc.parameters["runoff_method"]
        return "C" if rm == "racional" else "CN"
    elif analysis.tc.parameters:
        if "cn_adjusted" in analysis.tc.parameters:
            return "CN"
        elif "c" in analysis.tc.parameters:
            return "C"
    return "-"


def _generate_comparison_section(session) -> str:
    """Genera sección de comparación de metodologías C vs CN."""
    # Agrupar análisis por Tr y método de escorrentía
    comparison_data = {}

    for a in session.analyses:
        tr = a.storm.return_period
        runoff_method = None

        if a.tc.parameters and "runoff_method" in a.tc.parameters:
            runoff_method = a.tc.parameters["runoff_method"]
        elif a.tc.parameters:
            if "cn_adjusted" in a.tc.parameters:
                runoff_method = "scs-cn"
            elif "c" in a.tc.parameters:
                runoff_method = "racional"

        if runoff_method is None:
            continue

        key = (tr, a.tc.method, a.hydrograph.x_factor)
        if key not in comparison_data:
            comparison_data[key] = {}
        comparison_data[key][runoff_method] = {
            "qp": a.hydrograph.peak_flow_m3s,
            "runoff_mm": a.hydrograph.runoff_mm,
            "volume_m3": a.hydrograph.volume_m3,
            "p_total_mm": a.storm.total_depth_mm,
            "tc_min": a.tc.tc_min,
        }

    # Solo generar si hay comparaciones válidas (ambos métodos para al menos un caso)
    valid_comparisons = [k for k, v in comparison_data.items() if len(v) == 2]
    if not valid_comparisons:
        return ""

    content = """% Sección: Comparación de Metodologías
% Generado automáticamente por HidroPluvial

\\section{Comparación de Metodologías de Precipitación Efectiva}

Se presenta la comparación entre los métodos de cálculo de precipitación efectiva ($P_e$):
\\begin{itemize}
    \\item \\textbf{Método Racional}: $P_e = C \\times P$ (coeficiente de escorrentía)
    \\item \\textbf{Método SCS-CN}: $P_e = \\frac{(P - I_a)^2}{P - I_a + S}$ (Curve Number)
\\end{itemize}

Ambos métodos transforman la precipitación total ($P$) en precipitación efectiva ($P_e$),
que es la porción de lluvia que se convierte en escorrentía superficial.

\\begin{table}[H]
\\centering
\\small
\\begin{tabular}{llccccccc}
\\toprule
 & & & \\multicolumn{2}{c}{$P_e$ (mm)} & \\multicolumn{2}{c}{$Q_p$ (m$^3$/s)} & \\multicolumn{2}{c}{Diferencia $Q_p$} \\\\
\\cmidrule(lr){4-5} \\cmidrule(lr){6-7} \\cmidrule(lr){8-9}
Método $T_c$ & $T_r$ & $P$ (mm) & C & CN & C & CN & Abs. & \\% \\\\
\\midrule
"""

    for key in sorted(valid_comparisons, key=lambda x: (x[0], x[1])):
        tr, tc_method, x_factor = key
        data = comparison_data[key]

        qp_c = data["racional"]["qp"]
        qp_cn = data["scs-cn"]["qp"]
        pe_c = data["racional"]["runoff_mm"]  # Pe = escorrentía = precipitación efectiva
        pe_cn = data["scs-cn"]["runoff_mm"]
        p_total = data["racional"]["p_total_mm"]  # P total es igual para ambos

        diff_abs = qp_c - qp_cn
        diff_pct = (diff_abs / qp_cn * 100) if qp_cn > 0 else 0

        x_str = f" X={x_factor:.2f}" if x_factor else ""
        content += (
            f"{tc_method.title()}{x_str} & {tr} & {p_total:.1f} & "
            f"{pe_c:.1f} & {pe_cn:.1f} & "
            f"{qp_c:.3f} & {qp_cn:.3f} & "
            f"{diff_abs:+.3f} & {diff_pct:+.1f}\\% \\\\\n"
        )

    content += """\\bottomrule
\\end{tabular}
\\caption{Comparación de métodos de precipitación efectiva: Racional (C) vs SCS-CN}
\\label{tab:comparison}
\\end{table}

\\textbf{Nomenclatura:}
\\begin{itemize}
    \\item $P$ = Precipitación total de la tormenta de diseño
    \\item $P_e$ = Precipitación efectiva (escorrentía en mm)
    \\item $Q_p$ = Caudal pico del hidrograma
    \\item Diferencia positiva indica que el método Racional produce mayor caudal pico
\\end{itemize}

\\textbf{Observaciones:}
\\begin{itemize}
    \\item El método Racional asume una relación lineal entre $P$ y $P_e$ mediante el coeficiente $C$.
    \\item El método SCS-CN considera abstracciones iniciales ($I_a$) y retención potencial ($S$).
    \\item Las diferencias reflejan los distintos modelos de infiltración y abstracción inicial.
\\end{itemize}
"""

    # Agregar gráfico comparativo si hay datos de hidrogramas
    from hidropluvial.reports.charts import generate_c_vs_cn_comparison_tikz

    chart_tex = generate_c_vs_cn_comparison_tikz(
        session.analyses,
        caption="Comparación de hidrogramas: Método Racional vs SCS-CN",
        label="fig:c_vs_cn_comparacion",
    )

    if chart_tex:
        content += """
\\subsection{Comparación Gráfica}

La siguiente figura muestra la superposición de los hidrogramas generados
por cada metodología para el mismo escenario de análisis.

"""
        content += chart_tex

    return content
