"""
Handlers para los modos de edición (texto y selección).
"""

from typing import Any, Optional

from ..models import FormState, FormField, FieldType, FieldStatus
from ..validators import validate_field_value


def handle_edit_text(
    key: str,
    state: FormState,
    current_field: FormField,
    allow_back: bool,
    live: Any,
) -> Optional[dict]:
    """Maneja el modo de edición de texto."""
    if key == 'enter':
        value = state.input_buffer.strip()

        # Convertir según tipo
        if current_field.field_type == FieldType.FLOAT and value:
            try:
                value = float(value)
            except ValueError:
                state.message = "Error: Debe ser un número"
                state.input_buffer = ""
                return {"_continue": True}
        elif current_field.field_type == FieldType.INT and value:
            try:
                value = int(float(value))
            except ValueError:
                state.message = "Error: Debe ser un número entero"
                state.input_buffer = ""
                return {"_continue": True}

        # Validar
        valid, error_msg = validate_field_value(current_field, value)
        if not valid:
            state.message = f"Error: {error_msg}"
            state.input_buffer = ""
        else:
            current_field.value = value if value else None
            current_field.status = FieldStatus.FILLED if value else (
                FieldStatus.OPTIONAL if not current_field.required else FieldStatus.EMPTY
            )
            state.message = f"{current_field.label} actualizado"
            state.input_buffer = ""
            state.mode = "navigate"
            # Avanzar al siguiente campo habilitado
            state.selected_idx = state.next_enabled_field(state.selected_idx)

    elif key == 'esc':
        state.mode = "navigate"
        state.input_buffer = ""
        state.message = ""

    elif key == 'backspace':
        state.input_buffer = state.input_buffer[:-1]

    elif isinstance(key, str) and len(key) == 1 and (key.isprintable() or key in '.-'):
        state.input_buffer += key

    return None


def handle_edit_select(
    key: str,
    state: FormState,
    current_field: FormField,
    allow_back: bool,
    live: Any,
) -> Optional[dict]:
    """Maneja el modo de selección (SELECT o CHECKBOX)."""
    n_options = len(current_field.options)
    is_checkbox = current_field.field_type == FieldType.CHECKBOX

    if key == 'up':
        state.select_idx = (state.select_idx - 1) % n_options
    elif key == 'down':
        state.select_idx = (state.select_idx + 1) % n_options

    elif key == 'space' and is_checkbox:
        # Toggle opción actual en checkbox
        opt_value = current_field.options[state.select_idx].get("value")
        if current_field.value is None:
            current_field.value = []
        if opt_value in current_field.value:
            current_field.value.remove(opt_value)
        else:
            current_field.value.append(opt_value)
        # Actualizar dependencias inmediatamente para reflejar cambios
        state.update_dependencies()

    elif key == 'enter':
        if is_checkbox:
            # Confirmar selección múltiple
            if current_field.value and len(current_field.value) > 0:
                current_field.status = FieldStatus.FILLED
                n_selected = len(current_field.value)
                state.message = f"{current_field.label}: {n_selected} seleccionados"
            else:
                if current_field.required:
                    state.message = "Selecciona al menos una opción"
                    return {"_continue": True}
                current_field.status = FieldStatus.OPTIONAL
                state.message = f"{current_field.label}: ninguno seleccionado"
            state.mode = "navigate"
            # Actualizar dependencias (checkbox puede afectar otros campos)
            state.update_dependencies()
            # Avanzar al siguiente campo habilitado
            state.selected_idx = state.next_enabled_field(state.selected_idx)
        else:
            # SELECT simple: seleccionar opción actual
            selected_opt = current_field.options[state.select_idx]
            current_field.value = selected_opt.get("value")
            current_field.status = FieldStatus.FILLED
            state.message = f"{current_field.label} actualizado"
            state.mode = "navigate"
            # Actualizar dependencias
            state.update_dependencies()
            # Avanzar al siguiente campo habilitado
            state.selected_idx = state.next_enabled_field(state.selected_idx)

    elif key == 'esc':
        state.mode = "navigate"
        state.message = ""
        # Asegurar que la selección sea válida después de posibles cambios
        state.ensure_valid_selection()

    return None
