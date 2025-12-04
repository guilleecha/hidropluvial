"""
Estilos y utilidades compartidas para el wizard.
"""

import questionary
from questionary import Style

# Estilo personalizado para questionary
WIZARD_STYLE = Style([
    ('qmark', 'fg:cyan bold'),
    ('question', 'bold'),
    ('answer', 'fg:cyan'),
    ('pointer', 'fg:cyan bold'),
    ('highlighted', 'fg:cyan bold'),
    ('selected', 'fg:green'),
])


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
