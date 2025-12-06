"""Módulos de generación de reportes LaTeX."""

from hidropluvial.reports.charts import (
    HydrographSeries,
    HyetographData,
    generate_hydrograph_tikz,
    generate_hydrograph_comparison_tikz,
    generate_hyetograph_tikz,
    generate_hyetograph_filled_tikz,
    hydrograph_result_to_tikz,
    hyetograph_result_to_tikz,
)

from hidropluvial.reports.generator import (
    ReportGenerator,
    ProjectInfo,
    ReportData,
    export_to_json,
    export_to_csv,
    idf_to_csv,
    hyetograph_to_csv,
    hydrograph_to_csv,
)

from hidropluvial.reports.compiler import (
    LaTeXEngine,
    CompilationResult,
    compile_latex,
    find_latex_engine,
    check_latex_installation,
)

from hidropluvial.reports.palettes import (
    ColorPalette,
    PaletteType,
    get_palette,
    list_palettes,
    set_active_palette,
    get_active_palette,
    get_series_colors,
    get_series_styles,
)

__all__ = [
    # Charts
    "HydrographSeries",
    "HyetographData",
    "generate_hydrograph_tikz",
    "generate_hydrograph_comparison_tikz",
    "generate_hyetograph_tikz",
    "generate_hyetograph_filled_tikz",
    "hydrograph_result_to_tikz",
    "hyetograph_result_to_tikz",
    # Generator
    "ReportGenerator",
    "ProjectInfo",
    "ReportData",
    "export_to_json",
    "export_to_csv",
    "idf_to_csv",
    "hyetograph_to_csv",
    "hydrograph_to_csv",
    # Compiler
    "LaTeXEngine",
    "CompilationResult",
    "compile_latex",
    "find_latex_engine",
    "check_latex_installation",
    # Palettes
    "ColorPalette",
    "PaletteType",
    "get_palette",
    "list_palettes",
    "set_active_palette",
    "get_active_palette",
    "get_series_colors",
    "get_series_styles",
]
