"""
Módulo de visor interactivo de análisis.

Submodulos:
- terminal: Utilidades de terminal (clear_screen, get_key)
- components: Componentes de UI (tablas, paneles)
- filters: Lógica de filtrado de análisis
- plots: Gráficos con plotext
"""

from hidropluvial.cli.viewer.main import interactive_hydrograph_viewer

__all__ = ["interactive_hydrograph_viewer"]
