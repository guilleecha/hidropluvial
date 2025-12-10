"""
Visor interactivo tipo formulario para ingreso de datos.

Muestra una tabla con campos editables que el usuario puede navegar
y completar de forma interactiva.
"""

from .models import (
    FieldType,
    FieldStatus,
    FormField,
    FormState,
    FormResult,
)
from .main import interactive_form
from .validators import validate_field_value, format_field_value

__all__ = [
    "FieldType",
    "FieldStatus",
    "FormField",
    "FormState",
    "FormResult",
    "interactive_form",
    "validate_field_value",
    "format_field_value",
]
