"""
Handlers para el modo popup (on_edit).
"""

from typing import Any, Optional

from ..models import FormState, FieldType, FieldStatus, FormResult


def handle_popup(key: str, state: FormState, allow_back: bool, live: Any) -> Optional[dict]:
    """Maneja el modo popup (on_edit)."""
    n_opts = len(state.popup_options)

    if key == 'esc':
        state.mode = "navigate"
        state.popup_field = None
        state.popup_options = []
        state.message = ""

    elif key == 'up':
        # Navegar hacia arriba saltando separadores y disabled
        for _ in range(n_opts):
            state.popup_idx = (state.popup_idx - 1) % n_opts
            opt = state.popup_options[state.popup_idx]
            if not opt.get("separator") and not opt.get("disabled"):
                break

    elif key == 'down':
        # Navegar hacia abajo saltando separadores y disabled
        for _ in range(n_opts):
            state.popup_idx = (state.popup_idx + 1) % n_opts
            opt = state.popup_options[state.popup_idx]
            if not opt.get("separator") and not opt.get("disabled"):
                break

    elif key == 'space':
        return _handle_popup_space(state, allow_back, live)

    elif key == 'enter':
        return _handle_popup_enter(state, allow_back, live)

    else:
        # Buscar por shortcut
        return _handle_popup_shortcut(key, state)

    return None


def _handle_popup_space(state: FormState, allow_back: bool, live: Any) -> Optional[dict]:
    """Maneja la tecla espacio en el popup."""
    opt = state.popup_options[state.popup_idx]
    if opt.get("separator") or opt.get("disabled"):
        return None

    if opt.get("checkable"):
        opt_value = opt.get("value")
        if opt_value:
            # Obtener valor normalizado
            check_val = opt_value.lower() if isinstance(opt_value, str) else opt_value
            # Obtener lista actual de valores
            current_values = []
            if state.popup_field.value and isinstance(state.popup_field.value, list):
                current_values = list(state.popup_field.value)
            # Toggle - Buscar si existe (comparando en lowercase)
            found_idx = None
            for i, v in enumerate(current_values):
                v_lower = v.lower() if isinstance(v, str) else v
                if v_lower == check_val:
                    found_idx = i
                    break
            if found_idx is not None:
                # Desmarcar
                current_values.pop(found_idx)
            else:
                # Marcar - verificar si necesita confirmación
                if opt.get("confirm_message") and callable(opt.get("on_check")):
                    # Mostrar popup de confirmación inline
                    state.mode = "popup_confirm"
                    state.pending_check_opt = opt
                    state.confirm_default = True
                    return {"_continue": True}
                # Si tiene on_check pero sin confirmación, ejecutar directo
                on_check = opt.get("on_check")
                if callable(on_check):
                    result = on_check()
                    if result == "__reload__":
                        return {"_result": FormResult.RELOAD}
                    if result is None:
                        # Callback canceló, no marcar
                        return None
                current_values.append(opt_value)
            # Actualizar el campo
            state.popup_field.value = current_values
            if current_values:
                state.popup_field.status = FieldStatus.FILLED
            else:
                state.popup_field.status = FieldStatus.EMPTY
    elif callable(opt.get("action")):
        # Para opciones con acción, ejecutarla
        result = opt["action"]()
        if result == "__reload__":
            return {"_result": FormResult.RELOAD}
        # Soporte para abrir calculadora NRCS
        if isinstance(result, dict) and result.get("__open_nrcs_calculator__"):
            state.nrcs_segments = list(result.get("segments", []))
            state.nrcs_p2_mm = result.get("p2_mm", 50.0)
            state.nrcs_basin = result.get("basin")
            state.nrcs_callback = result.get("callback")
            state.nrcs_selected_idx = 0
            state.nrcs_message = ""
            state.mode = "popup_nrcs_calculator"
            return None
        # Soporte para abrir calculadora bimodal
        if isinstance(result, dict) and result.get("__open_bimodal_calculator__"):
            state.bimodal_callback = result.get("callback")
            state.bimodal_selected_idx = 0
            state.mode = "popup_bimodal_calculator"
            return None
        if result is not None:
            state.popup_field.value = result
            state.popup_field.status = FieldStatus.FILLED
            state.message = f"{state.popup_field.label}: {result}"
            state.update_dependencies()
        state.mode = "navigate"
        state.popup_field = None
        state.popup_options = []

    return None


def _handle_popup_enter(state: FormState, allow_back: bool, live: Any) -> Optional[dict]:
    """Maneja la tecla enter en el popup."""
    opt = state.popup_options[state.popup_idx]

    if not opt.get("separator") and not opt.get("disabled"):
        # Si es checkable, hacer toggle como con espacio
        if opt.get("checkable"):
            opt_value = opt.get("value")
            if opt_value:
                check_val = opt_value.lower() if isinstance(opt_value, str) else opt_value
                current_values = []
                if state.popup_field.value and isinstance(state.popup_field.value, list):
                    current_values = list(state.popup_field.value)
                found_idx = None
                for i, v in enumerate(current_values):
                    v_lower = v.lower() if isinstance(v, str) else v
                    if v_lower == check_val:
                        found_idx = i
                        break
                if found_idx is not None:
                    # Desmarcar
                    current_values.pop(found_idx)
                else:
                    # Marcar - verificar si necesita confirmación
                    if opt.get("confirm_message") and callable(opt.get("on_check")):
                        # Mostrar popup de confirmación inline
                        state.mode = "popup_confirm"
                        state.pending_check_opt = opt
                        state.confirm_default = True
                        return {"_continue": True}
                    # Si tiene on_check pero sin confirmación, ejecutar directo
                    on_check = opt.get("on_check")
                    if callable(on_check):
                        result = on_check()
                        if result == "__reload__":
                            return {"_result": FormResult.RELOAD}
                        if result is None:
                            # Callback canceló, no marcar
                            return None
                    current_values.append(opt_value)
                state.popup_field.value = current_values
                if current_values:
                    state.popup_field.status = FieldStatus.FILLED
                else:
                    state.popup_field.status = FieldStatus.EMPTY
            # No cerrar popup, permitir seguir seleccionando
            return None

        value = opt.get("value")
        # Si hay un callback especial (action), ejecutarlo primero
        if callable(opt.get("action")):
            result = opt["action"]()
            # __reload__ indica que hay que recargar el formulario
            if result == "__reload__":
                return {"_result": FormResult.RELOAD}
            # Soporte para abrir calculadora NRCS
            if isinstance(result, dict) and result.get("__open_nrcs_calculator__"):
                state.nrcs_segments = list(result.get("segments", []))
                state.nrcs_p2_mm = result.get("p2_mm", 50.0)
                state.nrcs_basin = result.get("basin")
                state.nrcs_callback = result.get("callback")
                state.nrcs_selected_idx = 0
                state.nrcs_message = ""
                state.mode = "popup_nrcs_calculator"
                return None
            # Soporte para abrir calculadora bimodal
            if isinstance(result, dict) and result.get("__open_bimodal_calculator__"):
                state.bimodal_callback = result.get("callback")
                state.bimodal_selected_idx = 0
                state.mode = "popup_bimodal_calculator"
                return None
            if result is not None:
                state.popup_field.value = result
                state.popup_field.status = FieldStatus.FILLED
                state.message = f"{state.popup_field.label}: {result}"
                state.update_dependencies()
            state.mode = "navigate"
            state.popup_field = None
            state.popup_options = []
        # Si el valor es "__input__", cambiar a modo texto
        elif value == "__input__":
            state.mode = "edit_text"
            state.input_buffer = ""
            if state.popup_field.value is not None:
                if state.popup_field.field_type == FieldType.FLOAT:
                    state.input_buffer = f"{state.popup_field.value:.2f}"
                else:
                    state.input_buffer = str(state.popup_field.value)
            state.popup_field = None
            state.popup_options = []
        else:
            # Asignar valor directamente
            state.popup_field.value = value
            state.popup_field.status = FieldStatus.FILLED
            state.message = f"{state.popup_field.label} actualizado"
            state.update_dependencies()
            state.mode = "navigate"
            state.popup_field = None
            state.popup_options = []
    else:
        # En separador o popup con solo checkables, cerrar popup
        has_checkable = any(o.get("checkable") for o in state.popup_options if not o.get("separator"))
        if has_checkable:
            state.update_dependencies()
            state.mode = "navigate"
            state.popup_field = None
            state.popup_options = []

    return None


def _handle_popup_shortcut(key: str, state: FormState) -> Optional[dict]:
    """Maneja shortcuts en el popup."""
    for idx, opt in enumerate(state.popup_options):
        opt_key = opt.get("key", "")
        if opt_key and opt_key.lower() == key.lower() and not opt.get("separator"):
            value = opt.get("value")
            if value == "__input__":
                state.mode = "edit_text"
                state.input_buffer = ""
                if state.popup_field.value is not None:
                    if state.popup_field.field_type == FieldType.FLOAT:
                        state.input_buffer = f"{state.popup_field.value:.2f}"
                    else:
                        state.input_buffer = str(state.popup_field.value)
                state.popup_field = None
                state.popup_options = []
            elif callable(opt.get("action")):
                result = opt["action"]()
                # __reload__ indica que hay que recargar el formulario
                if result == "__reload__":
                    return {"_result": FormResult.RELOAD}
                # Soporte para abrir calculadora NRCS
                if isinstance(result, dict) and result.get("__open_nrcs_calculator__"):
                    state.nrcs_segments = list(result.get("segments", []))
                    state.nrcs_p2_mm = result.get("p2_mm", 50.0)
                    state.nrcs_basin = result.get("basin")
                    state.nrcs_callback = result.get("callback")
                    state.nrcs_selected_idx = 0
                    state.nrcs_message = ""
                    state.mode = "popup_nrcs_calculator"
                    return None
                # Soporte para abrir calculadora bimodal
                if isinstance(result, dict) and result.get("__open_bimodal_calculator__"):
                    state.bimodal_callback = result.get("callback")
                    state.bimodal_selected_idx = 0
                    state.mode = "popup_bimodal_calculator"
                    return None
                if result is not None:
                    state.popup_field.value = result
                    state.popup_field.status = FieldStatus.FILLED
                    state.message = f"{state.popup_field.label}: {result}"
                    state.update_dependencies()
                state.mode = "navigate"
                state.popup_field = None
                state.popup_options = []
            else:
                state.popup_field.value = value
                state.popup_field.status = FieldStatus.FILLED
                state.message = f"{state.popup_field.label} actualizado"
                state.update_dependencies()
                state.mode = "navigate"
                state.popup_field = None
                state.popup_options = []
            break

    return None
