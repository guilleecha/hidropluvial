"""
Handlers para los modos de confirmación.
"""

from typing import Any, Optional

from ..models import FormState, FieldStatus, FormResult


def handle_confirm_cancel(key: str, state: FormState) -> Optional[dict]:
    """Maneja el modo de confirmación de cancelación."""
    if key in ('s', 'y'):
        # Confirmar cancelación
        return {"_cancel": True}
    elif key in ('n', 'esc'):
        # Cancelar y volver a navegación
        state.mode = "navigate"
        state.message = ""
    # Ignorar otras teclas
    return None


def handle_popup_confirm(key: str, state: FormState, allow_back: bool, live: Any) -> Optional[dict]:
    """Maneja el modo de confirmación inline para popup."""
    if key in ('s', 'y', 'enter') and state.pending_check_opt:
        # Confirmar - ejecutar on_check
        opt = state.pending_check_opt
        on_check = opt.get("on_check")
        if callable(on_check):
            result = on_check()
            if result == "__reload__":
                return {"_result": FormResult.RELOAD}
            if result is not None:
                # Éxito - marcar la opción
                opt_value = opt.get("value")
                if opt_value and state.popup_field:
                    current_values = []
                    if state.popup_field.value and isinstance(state.popup_field.value, list):
                        current_values = list(state.popup_field.value)
                    current_values.append(opt_value)
                    state.popup_field.value = current_values
                    state.popup_field.status = FieldStatus.FILLED
        # Volver al popup
        state.mode = "popup"
        state.pending_check_opt = None
    elif key in ('n', 'esc'):
        # Cancelar - volver al popup sin marcar
        state.mode = "popup"
        state.pending_check_opt = None
        state.message = ""
    # Ignorar otras teclas
    return None
