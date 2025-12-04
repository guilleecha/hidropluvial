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

__all__ = [
    "HydrographSeries",
    "HyetographData",
    "generate_hydrograph_tikz",
    "generate_hydrograph_comparison_tikz",
    "generate_hyetograph_tikz",
    "generate_hyetograph_filled_tikz",
    "hydrograph_result_to_tikz",
    "hyetograph_result_to_tikz",
]
