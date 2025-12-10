"""
Handler para el modo de navegación del formulario.
"""

from typing import Any, Optional

from ..models import FormState, FormField, FieldType, FieldStatus, FormResult


def handle_navigate(
    key: str,
    state: FormState,
    current_field: FormField,
    allow_back: bool,
    live: Any,
) -> Optional[dict]:
    """Maneja el modo de navegación."""
    if key == 'q':
        # Finalizar si está completo
        if state.is_complete():
            values = state.get_values()
            values["_result"] = FormResult.COMPLETED
            return values
        else:
            state.message = "Completa los campos requeridos para continuar"

    elif key == 'b' and allow_back:
        # Volver al paso anterior
        values = state.get_values()
        values["_result"] = FormResult.BACK
        return values

    elif key == 'esc':
        # Mostrar confirmación de cancelación
        state.mode = "confirm_cancel"

    elif key == 'up':
        state.selected_idx = state.prev_enabled_field(state.selected_idx)
        state.message = ""

    elif key == 'down':
        state.selected_idx = state.next_enabled_field(state.selected_idx)
        state.message = ""

    elif key == 'enter':
        state.message = ""

        # Si el campo está deshabilitado, no hacer nada
        if current_field.disabled:
            state.message = "Campo bloqueado"
            return {"_continue": True}

        # Si tiene callback on_edit, obtener opciones y entrar en modo popup
        if current_field.on_edit is not None:
            # on_edit retorna lista de opciones para el popup
            popup_opts = current_field.on_edit(current_field, state)
            if popup_opts:
                state.mode = "popup"
                state.popup_field = current_field
                state.popup_options = popup_opts
                state.popup_idx = 0
                # Saltar separadores y opciones deshabilitadas iniciales
                while state.popup_idx < len(popup_opts) and (
                    popup_opts[state.popup_idx].get("separator") or
                    popup_opts[state.popup_idx].get("disabled")
                ):
                    state.popup_idx += 1
                return {"_continue": True}
            # Si on_edit retorna None, continuar al modo edit_select normal

        if current_field.field_type in (FieldType.SELECT, FieldType.CHECKBOX):
            state.mode = "edit_select"
            state.select_idx = 0
            # Para SELECT, posicionar en valor actual si existe
            if current_field.field_type == FieldType.SELECT and current_field.value:
                for idx, opt in enumerate(current_field.options):
                    if opt.get("value") == current_field.value:
                        state.select_idx = idx
                        break
            # Para CHECKBOX, inicializar lista si no existe
            elif current_field.field_type == FieldType.CHECKBOX:
                if current_field.value is None:
                    current_field.value = []
        else:
            state.mode = "edit_text"
            # Pre-cargar valor actual
            if current_field.value is not None:
                if current_field.field_type == FieldType.FLOAT:
                    state.input_buffer = f"{current_field.value:.2f}"
                else:
                    state.input_buffer = str(current_field.value)
            else:
                state.input_buffer = ""

    return None
