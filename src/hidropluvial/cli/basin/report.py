"""
Generación de reportes LaTeX para cuencas.
"""

import shutil
from pathlib import Path
from typing import Optional

from hidropluvial.models import Basin


def _escape_latex(text: str) -> str:
    """Escapa caracteres especiales de LaTeX en texto plano."""
    if '\\' in text or '$' in text:
        return text
    return text.replace('_', r'\_')


def generate_basin_report(
    basin: Basin,
    output_dir: Optional[Path] = None,
    author: str = "",
    template_dir: Optional[Path] = None,
    pdf: bool = False,
    clean: bool = True,
    fig_width: str = r"0.9\textwidth",
    fig_height: str = "6cm",
    palette: str = "default",
    methodology: bool = False,
) -> Path:
    """
    Genera reporte LaTeX con gráficos TikZ para cada análisis.

    Args:
        basin: Cuenca con análisis
        output_dir: Directorio de salida (default: output/<nombre_cuenca>)
        author: Autor del reporte
        template_dir: Directorio con template Pablo Pizarro
        pdf: Compilar automáticamente a PDF
        clean: Limpiar archivos auxiliares después de compilar
        fig_width: Ancho de figuras
        fig_height: Alto de figuras
        palette: Paleta de colores
        methodology: Incluir textos explicativos sobre metodologías

    Returns:
        Path del directorio de salida
    """
    from hidropluvial.reports.charts import (
        HydrographSeries,
        generate_hydrograph_tikz,
        generate_hyetograph_tikz,
    )
    from hidropluvial.reports.palettes import set_active_palette

    if not basin.analyses:
        raise ValueError("No hay análisis en la cuenca.")

    # Configurar paleta de colores
    set_active_palette(palette)

    # Determinar directorio de salida
    if output_dir is None:
        safe_name = basin.name.lower().replace(" ", "_").replace("/", "_")
        output_dir = Path("output") / safe_name

    output_dir.mkdir(parents=True, exist_ok=True)

    # Crear subdirectorios
    hidrogramas_dir = output_dir / "hidrogramas"
    hietogramas_dir = output_dir / "hietogramas"
    hidrogramas_dir.mkdir(exist_ok=True)
    hietogramas_dir.mkdir(exist_ok=True)

    # Generar gráficos TikZ
    for i, analysis in enumerate(basin.analyses):
        hydro = analysis.hydrograph
        storm = analysis.storm

        # Nombre base del archivo
        x_str = f"_X{hydro.x_factor:.2f}".replace(".", "") if hydro.x_factor else ""
        base_name = f"{hydro.tc_method}_Tr{storm.return_period}{x_str}"

        # Hidrograma
        if hydro.time_hr and hydro.flow_m3s:
            series = HydrographSeries(
                time_hr=hydro.time_hr,
                flow_m3s=hydro.flow_m3s,
                label=f"{hydro.tc_method} Tr{storm.return_period}",
            )
            tikz_hydro = generate_hydrograph_tikz(
                series=[series],
                title=f"Hidrograma - {base_name}",
                width=fig_width,
                height=fig_height,
            )
            hydro_path = hidrogramas_dir / f"{base_name}.tex"
            with open(hydro_path, "w", encoding="utf-8") as f:
                f.write(tikz_hydro)

        # Hietograma
        if storm.time_min and storm.intensity_mmhr:
            tikz_hyeto = generate_hyetograph_tikz(
                time_min=storm.time_min,
                intensity_mmhr=storm.intensity_mmhr,
                title=f"Hietograma - {base_name}",
                width=fig_width,
                height=fig_height,
            )
            hyeto_path = hietogramas_dir / f"{base_name}.tex"
            with open(hyeto_path, "w", encoding="utf-8") as f:
                f.write(tikz_hyeto)

    # Generar documento principal
    main_tex = _generate_main_document(
        basin,
        author=author,
        methodology=methodology,
    )
    main_path = output_dir / f"{basin.name.lower().replace(' ', '_')}.tex"
    with open(main_path, "w", encoding="utf-8") as f:
        f.write(main_tex)

    # Copiar template si se especifica
    if template_dir:
        template_path = Path(template_dir)
        if template_path.exists():
            for item in template_path.iterdir():
                if item.is_file() and item.suffix in ['.sty', '.cls', '.bib']:
                    shutil.copy2(item, output_dir)

    # Compilar a PDF si se solicita
    if pdf:
        from hidropluvial.reports.compiler import compile_latex
        try:
            compile_latex(main_path, clean=clean)
            print(f"PDF generado: {main_path.with_suffix('.pdf')}")
        except Exception as e:
            print(f"Error compilando PDF: {e}")

    return output_dir


def _generate_main_document(
    basin: Basin,
    author: str = "",
    methodology: bool = False,
) -> str:
    """Genera el contenido del documento LaTeX principal."""
    safe_name = _escape_latex(basin.name)

    lines = [
        r"\documentclass[a4paper,11pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[spanish]{babel}",
        r"\usepackage{amsmath,amssymb}",
        r"\usepackage{graphicx}",
        r"\usepackage{tikz}",
        r"\usepackage{pgfplots}",
        r"\pgfplotsset{compat=1.18}",
        r"\usepackage{booktabs}",
        r"\usepackage{siunitx}",
        r"\usepackage{geometry}",
        r"\geometry{margin=2.5cm}",
        "",
        f"\\title{{Estudio Hidrológico - {safe_name}}}",
        f"\\author{{{_escape_latex(author)}}}" if author else r"\author{}",
        r"\date{\today}",
        "",
        r"\begin{document}",
        r"\maketitle",
        "",
    ]

    # Sección: Datos de la Cuenca
    lines.extend([
        r"\section{Datos de la Cuenca}",
        "",
        r"\begin{table}[h]",
        r"\centering",
        r"\begin{tabular}{ll}",
        r"\toprule",
        r"Parámetro & Valor \\",
        r"\midrule",
        f"Nombre & {safe_name} \\\\",
        f"Área & {basin.area_ha:.2f} ha \\\\",
        f"Pendiente & {basin.slope_pct:.2f}\\% \\\\",
        f"$P_{{3,10}}$ & {basin.p3_10:.1f} mm \\\\",
    ])

    if basin.c:
        lines.append(f"Coeficiente C & {basin.c:.3f} \\\\")
    if basin.cn:
        lines.append(f"Curve Number & {basin.cn} \\\\")
    if basin.length_m:
        lines.append(f"Longitud cauce & {basin.length_m:.0f} m \\\\")

    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        f"\\caption{{Parámetros de la cuenca {safe_name}}}",
        r"\end{table}",
        "",
    ])

    # Sección: Tiempos de Concentración
    if basin.tc_results:
        lines.extend([
            r"\section{Tiempos de Concentración}",
            "",
            r"\begin{table}[h]",
            r"\centering",
            r"\begin{tabular}{lrr}",
            r"\toprule",
            r"Método & Tc (min) & Tc (hr) \\",
            r"\midrule",
        ])

        for tc in basin.tc_results:
            method_name = _escape_latex(tc.method.capitalize())
            lines.append(f"{method_name} & {tc.tc_min:.1f} & {tc.tc_hr:.3f} \\\\")

        lines.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Tiempos de concentración calculados}",
            r"\end{table}",
            "",
        ])

    # Sección: Resumen de Análisis
    if basin.analyses:
        lines.extend([
            r"\section{Resumen de Análisis}",
            "",
            r"\begin{table}[h]",
            r"\centering",
            r"\footnotesize",
            r"\begin{tabular}{llrrrrr}",
            r"\toprule",
            r"Método Tc & Tormenta & Tr & P (mm) & Qp (m³/s) & Tp (min) & Vol (hm³) \\",
            r"\midrule",
        ])

        for a in basin.analyses:
            method = _escape_latex(a.tc.method)
            storm = a.storm.type.upper()
            tr = a.storm.return_period
            p_mm = a.storm.total_depth_mm
            qp = a.hydrograph.peak_flow_m3s
            tp = a.hydrograph.time_to_peak_min
            vol = a.hydrograph.volume_m3 / 1_000_000

            lines.append(
                f"{method} & {storm} & {tr} & {p_mm:.1f} & {qp:.3f} & {tp:.1f} & {vol:.4f} \\\\"
            )

        lines.extend([
            r"\bottomrule",
            r"\end{tabular}",
            r"\caption{Resumen de análisis hidrológicos}",
            r"\end{table}",
            "",
        ])

    # Incluir gráficos
    lines.extend([
        r"\section{Gráficos}",
        "",
        r"\subsection{Hidrogramas}",
        "",
    ])

    for a in basin.analyses:
        hydro = a.hydrograph
        storm = a.storm
        x_str = f"_X{hydro.x_factor:.2f}".replace(".", "") if hydro.x_factor else ""
        base_name = f"{hydro.tc_method}_Tr{storm.return_period}{x_str}"

        lines.extend([
            r"\begin{figure}[h]",
            r"\centering",
            f"\\input{{hidrogramas/{base_name}}}",
            f"\\caption{{Hidrograma - {_escape_latex(base_name)}}}",
            r"\end{figure}",
            "",
        ])

    lines.extend([
        r"\subsection{Hietogramas}",
        "",
    ])

    for a in basin.analyses:
        hydro = a.hydrograph
        storm = a.storm
        x_str = f"_X{hydro.x_factor:.2f}".replace(".", "") if hydro.x_factor else ""
        base_name = f"{hydro.tc_method}_Tr{storm.return_period}{x_str}"

        lines.extend([
            r"\begin{figure}[h]",
            r"\centering",
            f"\\input{{hietogramas/{base_name}}}",
            f"\\caption{{Hietograma - {_escape_latex(base_name)}}}",
            r"\end{figure}",
            "",
        ])

    # Metodología si se solicita
    if methodology:
        lines.extend(_generate_methodology_section())

    lines.extend([
        r"\end{document}",
    ])

    return "\n".join(lines)


def _generate_methodology_section() -> list[str]:
    """Genera sección de metodología."""
    return [
        r"\section{Marco Metodológico}",
        "",
        r"\subsection{Tiempo de Concentración}",
        r"El tiempo de concentración ($T_c$) es el tiempo que tarda una gota de agua "
        r"en recorrer desde el punto más alejado de la cuenca hasta el punto de salida.",
        "",
        r"\subsubsection{Método de Kirpich}",
        r"\begin{equation}",
        r"T_c = 0.0195 \cdot L^{0.77} \cdot S^{-0.385}",
        r"\end{equation}",
        r"donde $L$ es la longitud del cauce (m) y $S$ es la pendiente (m/m).",
        "",
        r"\subsubsection{Método de Temez}",
        r"\begin{equation}",
        r"T_c = 0.3 \cdot \left(\frac{L}{S^{0.25}}\right)^{0.76}",
        r"\end{equation}",
        r"donde $L$ es la longitud del cauce (km) y $S$ es la pendiente (m/m).",
        "",
        r"\subsection{Escorrentía}",
        r"\subsubsection{Método Racional}",
        r"El coeficiente de escorrentía $C$ relaciona la precipitación efectiva con la total:",
        r"\begin{equation}",
        r"P_e = C \cdot P",
        r"\end{equation}",
        "",
        r"\subsubsection{Método SCS-CN}",
        r"La precipitación efectiva se calcula con:",
        r"\begin{equation}",
        r"P_e = \frac{(P - I_a)^2}{P - I_a + S}",
        r"\end{equation}",
        r"donde $I_a = \lambda \cdot S$ y $S = \frac{25400}{CN} - 254$.",
        "",
    ]
