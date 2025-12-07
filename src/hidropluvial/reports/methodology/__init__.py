"""
Textos metodológicos para reportes LaTeX.

Este módulo genera contenido LaTeX explicativo sobre las metodologías
hidrológicas empleadas en los cálculos.
"""

from hidropluvial.reports.methodology.tc import get_tc_methodology_latex
from hidropluvial.reports.methodology.runoff import get_runoff_methodology_latex
from hidropluvial.reports.methodology.hydrograph import get_hydrograph_methodology_latex
from hidropluvial.reports.methodology.storms import get_storms_methodology_latex

__all__ = [
    "get_tc_methodology_latex",
    "get_runoff_methodology_latex",
    "get_hydrograph_methodology_latex",
    "get_storms_methodology_latex",
]
