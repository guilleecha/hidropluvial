"""
Sistema de temas para la interfaz CLI de HidroPluvial.

Proporciona una paleta de colores consistente y funciones de formato
para mejorar la legibilidad de la salida en terminal.

El paquete esta organizado en modulos:
- palette: Definicion de paletas y gestion de temas (CLITheme, ColorPalette)
- styled: Funciones que retornan objetos Text estilizados
- printing: Funciones que imprimen directamente a consola
- tables: Funciones para crear e imprimir tablas Rich
"""

# Re-exportar todo para mantener compatibilidad con imports existentes

# Desde palette
from hidropluvial.cli.theme.palette import (
    ThemeName,
    ColorPalette,
    THEME_DEFAULT,
    THEME_MONOKAI,
    THEME_NORD,
    THEME_MINIMAL,
    THEMES,
    CLITheme,
    get_console,
    get_palette,
)

# Desde styled
from hidropluvial.cli.theme.styled import (
    styled_header,
    styled_title,
    styled_subtitle,
    styled_value,
    styled_label,
    styled_success,
    styled_warning,
    styled_error,
    styled_info,
    styled_muted,
    create_summary_panel,
)

# Desde printing
from hidropluvial.cli.theme.printing import (
    format_number,
    print_separator,
    print_header,
    print_step,
    print_field,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_section,
    print_result_row,
    print_summary_box,
    print_analysis_summary,
    print_banner,
    print_completion_banner,
)

# Desde tables
from hidropluvial.cli.theme.tables import (
    create_results_table,
    create_analysis_table,
    create_projects_table,
    create_basins_table,
    create_sessions_table,
    print_projects_table,
    print_basins_table,
    print_basins_detail_table,
    print_sessions_table,
    print_analyses_summary_table,
)

__all__ = [
    # palette
    "ThemeName",
    "ColorPalette",
    "THEME_DEFAULT",
    "THEME_MONOKAI",
    "THEME_NORD",
    "THEME_MINIMAL",
    "THEMES",
    "CLITheme",
    "get_console",
    "get_palette",
    # styled
    "styled_header",
    "styled_title",
    "styled_subtitle",
    "styled_value",
    "styled_label",
    "styled_success",
    "styled_warning",
    "styled_error",
    "styled_info",
    "styled_muted",
    "create_summary_panel",
    # printing
    "format_number",
    "print_separator",
    "print_header",
    "print_step",
    "print_field",
    "print_success",
    "print_warning",
    "print_error",
    "print_info",
    "print_section",
    "print_result_row",
    "print_summary_box",
    "print_analysis_summary",
    "print_banner",
    "print_completion_banner",
    # tables
    "create_results_table",
    "create_analysis_table",
    "create_projects_table",
    "create_basins_table",
    "create_sessions_table",
    "print_projects_table",
    "print_basins_table",
    "print_basins_detail_table",
    "print_sessions_table",
    "print_analyses_summary_table",
]
