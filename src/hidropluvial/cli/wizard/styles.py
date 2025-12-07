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


def get_select_kwargs() -> dict:
    """
    Obtiene los kwargs para questionary.select() con iconos personalizados.

    Returns:
        Dict con style, pointer, y otros parámetros de estilo
    """
    icons = get_icons()
    return {
        'style': get_wizard_style(),
        'pointer': f'{icons.pointer} ',
        'instruction': '(↑↓ mover, Enter seleccionar)',
    }


def get_checkbox_kwargs() -> dict:
    """
    Obtiene los kwargs para questionary.checkbox() con iconos personalizados.

    Returns:
        Dict con style, pointer, y otros parámetros de estilo
    """
    icons = get_icons()
    return {
        'style': get_wizard_style(),
        'pointer': f'{icons.pointer} ',
        'instruction': '(↑↓ mover, Espacio marcar, Enter confirmar)',
    }


def get_confirm_kwargs() -> dict:
    """
    Obtiene los kwargs para questionary.confirm() con estilo.

    Returns:
        Dict con style
    """
    return {
        'style': get_wizard_style(),
    }


def get_text_kwargs() -> dict:
    """
    Obtiene los kwargs para questionary.text() con estilo.

    Returns:
        Dict con style
    """
    return {
        'style': get_wizard_style(),
    }


# Estilo por defecto (compatible con código existente)
WIZARD_STYLE = get_wizard_style()


def styled_choice(text: str, checked: bool = False, disabled: bool = False) -> questionary.Choice:
    """
    Crea un Choice con estilo consistente.

    Args:
        text: Texto de la opción
        checked: Si está marcado por defecto (checkbox)
        disabled: Si está deshabilitado

    Returns:
        questionary.Choice configurado
    """
    return questionary.Choice(
        title=text,
        checked=checked,
        disabled=disabled,
    )


def menu_separator(text: str = "") -> questionary.Separator:
    """
    Crea un separador de menú estilizado.

    Args:
        text: Texto opcional del separador

    Returns:
        questionary.Separator
    """
    icons = get_icons()
    if text:
        sep_char = icons.separator
        return questionary.Separator(f"{sep_char * 3} {text} {sep_char * 3}")
    return questionary.Separator()


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
    'get_select_kwargs',
    'get_checkbox_kwargs',
    'get_confirm_kwargs',
    'get_text_kwargs',
    # Helpers de choices
    'styled_choice',
    'menu_separator',
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
    'create_analysis_table',
    'styled_value',
    'styled_label',
    # Validación
    'validate_positive_float',
    'validate_range',
    # Iconos
    'get_icons',
    'supports_unicode',
]
