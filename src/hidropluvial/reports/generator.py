"""
Generador de reportes LaTeX para HidroPluvial.

Genera memorias de cálculo y reportes técnicos en formato LaTeX.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from hidropluvial import __version__


# Directorio de templates
_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _escape_latex(text: str) -> str:
    """Escapa caracteres especiales de LaTeX."""
    if not isinstance(text, str):
        return str(text)

    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


def _create_jinja_env() -> Environment:
    """Crea entorno Jinja2 configurado para LaTeX."""
    env = Environment(
        block_start_string=r'\BLOCK{',
        block_end_string='}',
        variable_start_string=r'\VAR{',
        variable_end_string='}',
        comment_start_string=r'\#{',
        comment_end_string='}',
        line_statement_prefix='%%',
        trim_blocks=True,
        autoescape=False,
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    )
    env.filters['escape_latex'] = _escape_latex
    return env


@dataclass
class ProjectInfo:
    """Información del proyecto para el reporte."""
    name: str = "Estudio Hidrológico"
    location: str = ""
    engineer: str = ""
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    client: str = ""
    description: str = ""


@dataclass
class ReportData:
    """Contenedor de datos para el reporte."""
    project: ProjectInfo
    idf_results: dict[str, Any] | None = None
    hyetograph_results: dict[str, Any] | None = None
    runoff_results: dict[str, Any] | None = None
    hydrograph_results: dict[str, Any] | None = None
    tc_results: dict[str, Any] | None = None
    tikz_figures: list[str] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)


class ReportGenerator:
    """Generador de reportes LaTeX."""

    def __init__(self):
        self.env = _create_jinja_env()

    def generate_idf_table_latex(
        self,
        durations_hr: list[float],
        return_periods_yr: list[int],
        intensities_mmhr: list[list[float]],
        caption: str = "Tabla de Intensidades IDF",
        label: str = "tab:idf",
    ) -> str:
        """
        Genera tabla LaTeX de curvas IDF.

        Args:
            durations_hr: Lista de duraciones en horas
            return_periods_yr: Lista de períodos de retorno
            intensities_mmhr: Matriz de intensidades [periodo][duracion]
            caption: Título de la tabla
            label: Etiqueta LaTeX

        Returns:
            Código LaTeX de la tabla
        """
        # Construir encabezado
        header = "Duración"
        for T in return_periods_yr:
            header += f" & T={T}"
        header += r" \\"

        # Construir filas
        rows = []
        for j, d in enumerate(durations_hr):
            if d < 1:
                dur_str = f"{d*60:.0f} min"
            else:
                dur_str = f"{d:.1f} hr"

            row = dur_str
            for i in range(len(return_periods_yr)):
                row += f" & {intensities_mmhr[i][j]:.1f}"
            row += r" \\"
            rows.append(row)

        rows_str = "\n\t\t".join(rows)
        col_spec = "r" + "r" * len(return_periods_yr)

        tex = f"""\\begin{{table}}[H]
\t\\centering
\t\\caption{{{caption}}}
\t\\label{{{label}}}
\t\\begin{{tabular}}{{{col_spec}}}
\t\t\\toprule
\t\t{header}
\t\t\\midrule
\t\t{rows_str}
\t\t\\bottomrule
\t\\end{{tabular}}
\\end{{table}}
"""
        return tex

    def generate_hyetograph_table_latex(
        self,
        time_min: list[float],
        intensity_mmhr: list[float],
        cumulative_mm: list[float] | None = None,
        caption: str = "Datos del Hietograma",
        label: str = "tab:hyetograph",
    ) -> str:
        """
        Genera tabla LaTeX de datos del hietograma.

        Args:
            time_min: Tiempos en minutos
            intensity_mmhr: Intensidades en mm/hr
            cumulative_mm: Precipitación acumulada (opcional)
            caption: Título de la tabla
            label: Etiqueta LaTeX

        Returns:
            Código LaTeX de la tabla
        """
        include_cumulative = cumulative_mm is not None

        if include_cumulative:
            header = r"Tiempo (min) & Intensidad (mm/hr) & Acumulado (mm) \\"
            col_spec = "rrr"
        else:
            header = r"Tiempo (min) & Intensidad (mm/hr) \\"
            col_spec = "rr"

        rows = []
        for i, (t, inten) in enumerate(zip(time_min, intensity_mmhr)):
            if include_cumulative:
                row = f"{t:.0f} & {inten:.2f} & {cumulative_mm[i]:.2f}"
            else:
                row = f"{t:.0f} & {inten:.2f}"
            row += r" \\"
            rows.append(row)

        rows_str = "\n\t\t".join(rows)

        tex = f"""\\begin{{table}}[H]
\t\\centering
\t\\caption{{{caption}}}
\t\\label{{{label}}}
\t\\begin{{tabular}}{{{col_spec}}}
\t\t\\toprule
\t\t{header}
\t\t\\midrule
\t\t{rows_str}
\t\t\\bottomrule
\t\\end{{tabular}}
\\end{{table}}
"""
        return tex

    def generate_results_summary_latex(
        self,
        results: dict[str, Any],
        caption: str = "Resumen de Resultados",
        label: str = "tab:results",
    ) -> str:
        """
        Genera tabla de resumen de resultados.

        Args:
            results: Diccionario con parámetros y valores
            caption: Título de la tabla
            label: Etiqueta LaTeX

        Returns:
            Código LaTeX de la tabla
        """
        rows = []
        for param, value in results.items():
            if isinstance(value, float):
                value_str = f"{value:.4f}"
            else:
                value_str = str(value)
            rows.append(f"{_escape_latex(param)} & {value_str} " + r"\\")

        rows_str = "\n\t\t".join(rows)

        tex = f"""\\begin{{table}}[H]
\t\\centering
\t\\caption{{{caption}}}
\t\\label{{{label}}}
\t\\begin{{tabular}}{{lr}}
\t\t\\toprule
\t\tParámetro & Valor \\\\
\t\t\\midrule
\t\t{rows_str}
\t\t\\bottomrule
\t\\end{{tabular}}
\\end{{table}}
"""
        return tex

    def generate_standalone_document(
        self,
        content: str,
        title: str = "Memoria de Cálculo Hidrológico",
        author: str = "",
        include_tikz: bool = True,
    ) -> str:
        """
        Genera documento LaTeX completo standalone.

        Args:
            content: Contenido del documento
            title: Título del documento
            author: Autor del documento
            include_tikz: Si incluir paquetes TikZ/PGFPlots

        Returns:
            Documento LaTeX completo
        """
        tikz_packages = ""
        if include_tikz:
            tikz_packages = """\\usepackage{tikz}
\\usepackage{pgfplots}
\\pgfplotsset{compat=1.18}
"""

        author_line = f"\\author{{{_escape_latex(author)}}}" if author else ""
        date_line = f"\\date{{{datetime.now().strftime('%d de %B de %Y')}}}"

        tex = f"""\\documentclass[11pt, a4paper]{{article}}

% Paquetes básicos
\\usepackage[utf8]{{inputenc}}
\\usepackage[spanish]{{babel}}
\\usepackage[margin=2.5cm]{{geometry}}
\\usepackage{{booktabs}}
\\usepackage{{siunitx}}
\\usepackage{{amsmath}}
\\usepackage{{float}}
\\usepackage{{graphicx}}
\\usepackage{{hyperref}}

% TikZ/PGFPlots
{tikz_packages}

% Metadatos
\\title{{{_escape_latex(title)}}}
{author_line}
{date_line}

% Generado por HidroPluvial v{__version__}

\\begin{{document}}

\\maketitle

{content}

\\end{{document}}
"""
        return tex


# ============================================================================
# Funciones de conveniencia para exportación
# ============================================================================

def export_to_json(data: dict[str, Any], filepath: str | Path) -> None:
    """Exporta datos a JSON."""
    filepath = Path(filepath)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def export_to_csv(
    headers: list[str],
    rows: list[list[Any]],
    filepath: str | Path,
    delimiter: str = ",",
) -> None:
    """
    Exporta datos a CSV.

    Args:
        headers: Lista de encabezados
        rows: Lista de filas (cada fila es una lista de valores)
        filepath: Ruta del archivo
        delimiter: Delimitador (default: coma)
    """
    filepath = Path(filepath)

    with open(filepath, 'w', encoding='utf-8') as f:
        # Encabezados
        f.write(delimiter.join(str(h) for h in headers) + "\n")
        # Filas
        for row in rows:
            f.write(delimiter.join(str(v) for v in row) + "\n")


def idf_to_csv(
    durations_hr: list[float],
    return_periods_yr: list[int],
    intensities_mmhr: list[list[float]],
    filepath: str | Path,
) -> None:
    """
    Exporta tabla IDF a CSV.

    Args:
        durations_hr: Duraciones en horas
        return_periods_yr: Períodos de retorno
        intensities_mmhr: Matriz de intensidades
        filepath: Ruta del archivo
    """
    headers = ["Duracion_hr"] + [f"T{T}_yr" for T in return_periods_yr]

    rows = []
    for j, d in enumerate(durations_hr):
        row = [d] + [intensities_mmhr[i][j] for i in range(len(return_periods_yr))]
        rows.append(row)

    export_to_csv(headers, rows, filepath)


def hyetograph_to_csv(
    time_min: list[float],
    intensity_mmhr: list[float],
    filepath: str | Path,
) -> None:
    """
    Exporta hietograma a CSV.

    Args:
        time_min: Tiempos en minutos
        intensity_mmhr: Intensidades en mm/hr
        filepath: Ruta del archivo
    """
    headers = ["Tiempo_min", "Intensidad_mmhr"]
    rows = [[t, i] for t, i in zip(time_min, intensity_mmhr)]
    export_to_csv(headers, rows, filepath)


def hydrograph_to_csv(
    time_hr: list[float],
    flow_m3s: list[float],
    filepath: str | Path,
) -> None:
    """
    Exporta hidrograma a CSV.

    Args:
        time_hr: Tiempos en horas
        flow_m3s: Caudales en m³/s
        filepath: Ruta del archivo
    """
    headers = ["Tiempo_hr", "Caudal_m3s"]
    rows = [[t, q] for t, q in zip(time_hr, flow_m3s)]
    export_to_csv(headers, rows, filepath)
