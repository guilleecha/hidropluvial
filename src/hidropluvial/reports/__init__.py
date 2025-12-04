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
]
