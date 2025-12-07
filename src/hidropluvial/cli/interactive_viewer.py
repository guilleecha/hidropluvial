"""
Visor interactivo de fichas de análisis con navegación por teclado.

Este módulo re-exporta las funciones del paquete viewer para
mantener compatibilidad con código existente.

Ver hidropluvial.cli.viewer para la implementación.
"""

# Re-exportar desde el nuevo módulo
from hidropluvial.cli.viewer.main import interactive_hydrograph_viewer
from hidropluvial.cli.viewer.terminal import clear_screen, get_key
from hidropluvial.cli.viewer.plots import plot_combined, plot_hydrograph
from hidropluvial.cli.viewer.components import (
    build_analysis_list,
    build_info_panel,
    format_analysis_label,
)
from hidropluvial.cli.viewer.filters import (
    get_unique_values,
    filter_analyses,
    show_filter_menu,
)

# Aliases para compatibilidad con código legacy
plot_combined_styled = plot_combined
_build_analysis_list = build_analysis_list
_build_info_panel = build_info_panel
_format_analysis_label = format_analysis_label
_get_unique_values = get_unique_values
_filter_analyses = filter_analyses
_filter_analyses_multi = filter_analyses
_show_filter_menu = show_filter_menu
_build_filter_summary_table = None  # Interno, no se exporta


__all__ = [
    "interactive_hydrograph_viewer",
    "clear_screen",
    "get_key",
    "plot_combined",
    "plot_combined_styled",
    "plot_hydrograph",
    "build_analysis_list",
    "build_info_panel",
    "format_analysis_label",
    "get_unique_values",
    "filter_analyses",
    "show_filter_menu",
]
