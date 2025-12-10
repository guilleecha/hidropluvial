"""
Handlers para submenús y entrada inline dentro del popup.
"""

from typing import Any, Optional

from ..models import FormState, FormResult


def handle_popup_submenu(key: str, state: FormState) -> Optional[dict]:
    """Maneja el modo de submenú dentro del popup."""
    n_submenu = len(state.submenu_options)

    if key == 'esc':
        # Volver al popup principal
        state.mode = "popup"
        state.submenu_options = []
        state.submenu_idx = 0
        state.submenu_title = ""
        state.submenu_callback = None

    elif key == 'up':
        state.submenu_idx = (state.submenu_idx - 1) % n_submenu

    elif key == 'down':
        state.submenu_idx = (state.submenu_idx + 1) % n_submenu

    elif key == 'enter':
        selected_opt = state.submenu_options[state.submenu_idx]
        callback = state.submenu_callback

        # Limpiar estado del submenú
        state.submenu_options = []
        state.submenu_idx = 0
        state.submenu_title = ""
        state.submenu_callback = None

        # Ejecutar callback con la opción seleccionada
        if callable(callback):
            result = callback(selected_opt)
            if result == "__reload__":
                return {"_result": FormResult.RELOAD}
            # El callback puede cambiar el modo (ej: a popup_inline_input)

    return None


def handle_popup_inline_input(key: str, state: FormState, allow_back: bool, live: Any) -> Optional[dict]:
    """Maneja el modo de entrada inline dentro del popup."""
    n_inline_fields = len(state.inline_input_fields)
    current_inline_field = state.inline_input_fields[state.inline_input_idx] if state.inline_input_fields else {}

    if key == 'esc':
        # Cancelar y volver al popup principal
        state.mode = "popup"
        state.inline_input_fields = []
        state.inline_input_idx = 0
        state.inline_input_label = ""
        state.inline_input_hint = ""
        state.inline_input_callback = None
        state.input_buffer = ""

    elif key == 'tab':
        # Guardar valor actual y pasar al siguiente campo
        value = state.input_buffer.strip()
        fld_type = current_inline_field.get("type", "float")

        if value:
            try:
                if fld_type == "float":
                    value = float(value)
                elif fld_type == "int":
                    value = int(float(value))
            except ValueError:
                state.message = "Error: Valor inválido"
                return {"_continue": True}

            current_inline_field["value"] = value

        # Avanzar al siguiente campo
        state.inline_input_idx = (state.inline_input_idx + 1) % n_inline_fields
        next_field = state.inline_input_fields[state.inline_input_idx]
        # Pre-cargar valor si existe
        if next_field.get("value"):
            state.input_buffer = str(next_field["value"])
        else:
            state.input_buffer = ""

    elif key == 'enter':
        # Guardar valor actual
        value = state.input_buffer.strip()
        fld_type = current_inline_field.get("type", "float")

        if value:
            try:
                if fld_type == "float":
                    value = float(value)
                elif fld_type == "int":
                    value = int(float(value))
            except ValueError:
                state.message = "Error: Valor inválido"
                return {"_continue": True}

            current_inline_field["value"] = value

        # Verificar si todos los campos requeridos tienen valor
        all_filled = all(
            fld.get("value") is not None or not fld.get("required", True)
            for fld in state.inline_input_fields
        )

        if all_filled:
            # Ejecutar callback con los valores
            callback = state.inline_input_callback
            fields_data = list(state.inline_input_fields)

            # Limpiar estado
            state.inline_input_fields = []
            state.inline_input_idx = 0
            state.inline_input_label = ""
            state.inline_input_hint = ""
            state.inline_input_callback = None
            state.input_buffer = ""

            if callable(callback):
                result = callback(fields_data)
                if result == "__reload__":
                    return {"_result": FormResult.RELOAD}
                # El callback determina el siguiente modo
        else:
            state.message = "Completa todos los campos requeridos"

    elif key == 'backspace':
        state.input_buffer = state.input_buffer[:-1]

    elif isinstance(key, str) and len(key) == 1 and (key.isprintable() or key in '.-'):
        state.input_buffer += key

    return None
