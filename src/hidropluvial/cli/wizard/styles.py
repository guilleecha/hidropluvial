"""
Estilos y utilidades compartidas para el wizard.

Integra el sistema de temas de hidropluvial.cli.theme para mantener
consistencia visual en toda la aplicación.
"""

import questionary
from questionary import Style

from hidropluvial.cli.theme import (
    get_console,
    get_palette,
    print_header,
    print_section,
    print_field,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_step,
    print_summary_box,
    print_banner,
    print_completion_banner,
    create_results_table,
    create_analysis_table,
    styled_value,
    styled_label,
)


def get_wizard_style() -> Style:
    """Obtiene el estilo de questionary basado en el tema actual."""
    p = get_palette()
    return Style([
        ('qmark', f'fg:{p.accent} bold'),
        ('question', 'bold'),
        ('answer', f'fg:{p.primary}'),
        ('pointer', f'fg:{p.accent} bold'),
        ('highlighted', f'fg:{p.primary} bold'),
        ('selected', f'fg:{p.success}'),
        ('instruction', f'fg:{p.muted}'),
        ('text', ''),
        ('disabled', f'fg:{p.muted}'),
    ])


# Estilo por defecto (compatible con código existente)
WIZARD_STYLE = get_wizard_style()


def validate_positive_float(value: str) -> bool | str:
    """Valida que sea un numero positivo."""
    try:
        v = float(value)
        if v <= 0:
            return "Debe ser un numero positivo"
        return True
    except ValueError:
        return "Debe ser un numero valido"


def validate_range(value: str, min_val: float, max_val: float) -> bool | str:
    """Valida que este en un rango."""
    try:
        v = float(value)
        if v < min_val or v > max_val:
            return f"Debe estar entre {min_val} y {max_val}"
        return True
    except ValueError:
        return "Debe ser un numero valido"


# Re-exportar funciones de tema para uso conveniente
__all__ = [
    'WIZARD_STYLE',
    'get_wizard_style',
    'get_console',
    'get_palette',
    'print_header',
    'print_section',
    'print_field',
    'print_success',
    'print_warning',
    'print_error',
    'print_info',
    'print_step',
    'print_summary_box',
    'print_banner',
    'print_completion_banner',
    'create_results_table',
    'create_analysis_table',
    'styled_value',
    'styled_label',
    'validate_positive_float',
    'validate_range',
]
