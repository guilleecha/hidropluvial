"""
Módulo de visor interactivo de análisis.

Submodulos:
- terminal: Utilidades de terminal (clear_screen, get_key)
- components: Componentes de UI (tablas, paneles)
- filters: Lógica de filtrado de análisis
- plots: Gráficos con plotext
- coverage_viewer: Visor interactivo para asignación de coberturas
- form_viewer: Visor interactivo tipo formulario
- config_form: Formulario de configuración de análisis
"""

from hidropluvial.cli.viewer.main import interactive_hydrograph_viewer
from hidropluvial.cli.viewer.coverage_viewer import (
    interactive_coverage_viewer,
    CoverageOption,
    CoverageRow,  # Alias para compatibilidad
)
from hidropluvial.cli.viewer.form_viewer import (
    interactive_form,
    FormField,
    FormState,
    FieldType,
    FieldStatus,
    FormResult,
)
from hidropluvial.cli.viewer.config_form import interactive_config_form
from hidropluvial.cli.viewer.panel_input import (
    panel_select,
    panel_checkbox,
    panel_text,
    panel_confirm,
    PanelOption,
    quick_select,
    quick_checkbox,
)
from hidropluvial.cli.viewer.menu_panel import (
    menu_panel,
    quick_menu,
    confirm_menu,
    add_basin_menu,
    MenuItem,
)

__all__ = [
    "interactive_hydrograph_viewer",
    "interactive_coverage_viewer",
    "CoverageOption",
    "CoverageRow",
    "interactive_form",
    "interactive_config_form",
    "FormField",
    "FormState",
    "FieldType",
    "FieldStatus",
    "FormResult",
    # Panel input
    "panel_select",
    "panel_checkbox",
    "panel_text",
    "panel_confirm",
    "PanelOption",
    "quick_select",
    "quick_checkbox",
    # Menu panel
    "menu_panel",
    "quick_menu",
    "confirm_menu",
    "add_basin_menu",
    "MenuItem",
]
