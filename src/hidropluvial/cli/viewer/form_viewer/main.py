"""
Función principal del formulario interactivo.
"""

import shutil
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

    # Guardar tamaño inicial del terminal para detectar cambios
    last_terminal_size = shutil.get_terminal_size()

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
                if result.get("_no_update"):
                    # Tecla no reconocida, no actualizar display
                    continue

            # Detectar si cambió el tamaño del terminal
            current_size = shutil.get_terminal_size()
            if current_size != last_terminal_size:
                # Reiniciar Live para evitar acumulación de contenido
                live.stop()
                clear_screen()
                last_terminal_size = current_size
                live.start()

            # Actualizar display (solo si hubo cambio de estado)
            display = build_display(state, allow_back)
            live.update(display, refresh=True)

    return None
