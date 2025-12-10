"""
Validación y formateo de valores de campos.
"""

from typing import Any, Union

from .models import FormField, FieldType


def format_field_value(field: FormField) -> str:
    """Formatea el valor de un campo para mostrar."""
    if field.value is None:
        return "-"

    if field.field_type == FieldType.FLOAT:
        val = f"{field.value:.2f}"
    elif field.field_type == FieldType.INT:
        val = str(int(field.value))
    elif field.field_type == FieldType.SELECT:
        # Buscar label de la opción seleccionada
        for opt in field.options:
            if opt.get("value") == field.value:
                return opt.get("name", str(field.value))
        val = str(field.value)
    elif field.field_type == FieldType.CHECKBOX:
        if isinstance(field.value, list):
            names = []
            for v in field.value:
                for opt in field.options:
                    if opt.get("value") == v:
                        names.append(opt.get("name", str(v))[:10])
                        break
            return ", ".join(names) if names else "-"
        val = str(field.value)
    else:
        val = str(field.value)

    if field.unit:
        val += f" {field.unit}"

    return val


def validate_field_value(field: FormField, value: Any) -> tuple[bool, str]:
    """Valida el valor de un campo."""
    if value is None or value == "":
        if field.required:
            return False, "Campo requerido"
        return True, ""

    # Validar tipo
    if field.field_type == FieldType.FLOAT:
        try:
            val = float(value)
            if field.min_value is not None and val < field.min_value:
                return False, f"Mínimo: {field.min_value}"
            if field.max_value is not None and val > field.max_value:
                return False, f"Máximo: {field.max_value}"
        except ValueError:
            return False, "Debe ser un número"

    elif field.field_type == FieldType.INT:
        try:
            val = int(float(value))
            if field.min_value is not None and val < field.min_value:
                return False, f"Mínimo: {field.min_value}"
            if field.max_value is not None and val > field.max_value:
                return False, f"Máximo: {field.max_value}"
        except ValueError:
            return False, "Debe ser un número entero"

    # Validador personalizado
    if field.validator:
        result = field.validator(value)
        if result is True:
            return True, ""
        elif isinstance(result, str):
            return False, result
        else:
            return False, "Valor inválido"

    return True, ""
