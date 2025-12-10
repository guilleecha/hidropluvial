"""
Función principal del formulario interactivo.
"""

from typing import List, Optional

from rich.live import Live

from hidropluvial.cli.theme import get_console
from hidropluvial.cli.viewer.terminal import get_key, clear_screen

from .models import FormField, FormState, FieldStatus, FormResult
from .builders import build_display
from .handlers import handle_key


def interactive_form(
    title: str,
    fields: List[FormField],
    allow_back: bool = True,
) -> Optional[dict]:
    """
    Muestra un formulario interactivo.

    Args:
        title: Título del formulario
        fields: Lista de FormField definiendo los campos
        allow_back: Si permite volver al paso anterior con 'b'

    Returns:
        Diccionario con los valores o None si cancela
        El diccionario incluye "_result" con FormResult.COMPLETED o FormResult.BACK
    """
    console = get_console()

    # Inicializar estado de campos
    for fld in fields:
        if fld.default is not None:
            fld.value = fld.default
            fld.status = FieldStatus.FILLED
        elif not fld.required:
            fld.status = FieldStatus.OPTIONAL
        else:
            fld.status = FieldStatus.EMPTY

    state = FormState(
        title=title,
        fields=fields,
    )

    # Actualizar dependencias iniciales y asegurar selección válida
    state.update_dependencies()
    state.ensure_valid_selection()

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_display(state, allow_back)
        live.update(display, refresh=True)

        while True:
            key = get_key()

            # Manejar tecla
            result = handle_key(key, state, allow_back, live)

            # Verificar resultado
            if result is not None:
                if result.get("_cancel"):
                    return None
                if "_result" in result:
                    if result["_result"] == FormResult.RELOAD:
                        return {"_result": FormResult.RELOAD}
                    return result
                if result.get("_continue"):
                    # Solo refrescar display y continuar
                    display = build_display(state, allow_back)
                    live.update(display, refresh=True)
                    continue

            # Actualizar display
            display = build_display(state, allow_back)
            live.update(display, refresh=True)

    return None
