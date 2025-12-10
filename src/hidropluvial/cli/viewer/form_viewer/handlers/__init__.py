"""
Handlers de teclas para el formulario interactivo.

Cada módulo maneja un modo específico del formulario.
"""

from typing import Any, Optional

from ..models import FormState, FormResult
from ..builders import build_display

from .navigate import handle_navigate
from .edit import handle_edit_text, handle_edit_select
from .popup import handle_popup
from .confirm import handle_confirm_cancel, handle_popup_confirm
from .submenu import handle_popup_submenu, handle_popup_inline_input
from .nrcs import handle_nrcs_calculator
from .bimodal import handle_bimodal_calculator


def handle_key(
    key: str,
    state: FormState,
    allow_back: bool,
    live: Any,
) -> Optional[dict]:
    """
    Maneja una tecla presionada.

    Returns:
        None si debe continuar el loop
        dict con resultado si debe salir
    """
    current_field = state.fields[state.selected_idx]

    # Modo confirmación de cancelación
    if state.mode == "confirm_cancel":
        return handle_confirm_cancel(key, state)

    # Modo confirmación inline para popup
    elif state.mode == "popup_confirm":
        return handle_popup_confirm(key, state, allow_back, live)

    # Modo submenú dentro del popup
    elif state.mode == "popup_submenu":
        return handle_popup_submenu(key, state)

    # Modo entrada inline dentro del popup
    elif state.mode == "popup_inline_input":
        return handle_popup_inline_input(key, state, allow_back, live)

    # Modo calculadora NRCS
    elif state.mode == "popup_nrcs_calculator":
        return handle_nrcs_calculator(key, state)

    # Modo calculadora bimodal
    elif state.mode == "popup_bimodal_calculator":
        return handle_bimodal_calculator(key, state)

    # Modo edición de texto
    elif state.mode == "edit_text":
        return handle_edit_text(key, state, current_field, allow_back, live)

    # Modo selección (SELECT o CHECKBOX)
    elif state.mode == "edit_select":
        return handle_edit_select(key, state, current_field, allow_back, live)

    # Modo popup (on_edit)
    elif state.mode == "popup":
        return handle_popup(key, state, allow_back, live)

    # Modo navegación
    elif state.mode == "navigate":
        return handle_navigate(key, state, current_field, allow_back, live)

    return None


__all__ = ["handle_key"]
