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
    styled_value,
    styled_label,
)
from hidropluvial.cli.theme.icons import get_icons, supports_unicode


def get_wizard_style() -> Style:
    """
    Obtiene el estilo de questionary basado en el tema actual.

    Colores mejorados para mejor visibilidad y consistencia con el tema.
    """
    p = get_palette()
    return Style([
        # Marcador de pregunta (?)
        ('qmark', f'fg:{p.accent} bold'),
        # Texto de la pregunta
        ('question', 'bold'),
        # Respuesta seleccionada/ingresada
        ('answer', f'fg:{p.success} bold'),
        # Puntero de selección (❯)
        ('pointer', f'fg:{p.accent} bold'),
        # Opción resaltada (donde está el cursor)
        ('highlighted', f'fg:{p.primary} bold'),
        # Items seleccionados en checkbox (◉)
        ('selected', f'fg:{p.success} bold'),
        # Instrucciones (ej: "Use arrows to move")
        ('instruction', f'fg:{p.muted} italic'),
        # Texto normal
        ('text', ''),
        # Opciones deshabilitadas
        ('disabled', f'fg:{p.muted} italic'),
        # Separadores en listas
        ('separator', f'fg:{p.border}'),
    ])


# Estilo por defecto (compatible con código existente)
WIZARD_STYLE = get_wizard_style()


def back_choice(text: str = "Volver") -> str:
    """
    Genera el texto para una opción de volver atrás.

    Args:
        text: Texto base

    Returns:
        Texto formateado con icono
    """
    icons = get_icons()
    return f"{icons.back} {text}"


def cancel_choice(text: str = "Cancelar") -> str:
    """
    Genera el texto para una opción de cancelar.

    Args:
        text: Texto base

    Returns:
        Texto formateado con icono
    """
    icons = get_icons()
    return f"{icons.cross} {text}"


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
    # Estilos
    'WIZARD_STYLE',
    'get_wizard_style',
    # Helpers de choices
    'back_choice',
    'cancel_choice',
    # Tema
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
    'styled_value',
    'styled_label',
    # Validación
    'validate_positive_float',
    'validate_range',
    # Iconos
    'get_icons',
    'supports_unicode',
]
