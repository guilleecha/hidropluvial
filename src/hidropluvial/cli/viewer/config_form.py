"""
Visor interactivo para configuración de análisis.

Extiende el form_viewer con soporte especial para:
- Campos CHECKBOX con múltiples selecciones
- Dependencias entre campos (ej: coef_c depende de metodo_escorrentia)
- Campos deshabilitados que no se pueden seleccionar
- Vista compacta estilo configuración
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, List, Any, Union

from rich.console import Console, Group
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box

from hidropluvial.cli.theme import get_palette, get_icons
from hidropluvial.cli.viewer.terminal import clear_screen, get_key
from hidropluvial.cli.viewer.form_viewer import (
    FormField,
    FieldType,
    FieldStatus,
)


# Agregar atributos adicionales a FormField mediante monkey-patching
# para no modificar form_viewer.py
def _get_enabled(fld: FormField) -> bool:
    return getattr(fld, '_enabled', True)

def _set_enabled(fld: FormField, value: bool):
    fld._enabled = value

def _get_depends_on(fld: FormField) -> Optional[tuple]:
    """Retorna (field_key, required_values) o None."""
    return getattr(fld, '_depends_on', None)

def _set_depends_on(fld: FormField, dep: Optional[tuple]):
    fld._depends_on = dep


@dataclass
class ConfigFormState:
    """Estado del formulario de configuración."""
    title: str
    fields: List[FormField]
    wizard_state: Optional[Any] = None  # Estado del wizard para dependencias
    selected_idx: int = 0
    mode: str = "navigate"  # "navigate", "edit_checkbox", "edit_select", "edit_text"
    message: str = ""
    checkbox_idx: int = 0  # Para modo checkbox
    select_idx: int = 0  # Para modo select
    input_buffer: str = ""  # Para modo text


def is_field_enabled(fld: FormField, all_fields: List[FormField]) -> bool:
    """Verifica si un campo está habilitado basándose en sus dependencias."""
    depends = _get_depends_on(fld)
    if depends is None:
        return True

    dep_key, required_values = depends

    # Buscar el campo del que depende
    for f in all_fields:
        if f.key == dep_key:
            if f.value is None:
                return False
            if isinstance(f.value, list):
                # Para checkbox, verificar si alguno de los valores requeridos está
                return any(v in f.value for v in required_values)
            else:
                return f.value in required_values

    return True


def is_option_enabled(
    opt: dict,
    all_fields: List[FormField],
    state: Optional[Any] = None,
) -> bool:
    """
    Verifica si una opción dentro de un checkbox/select está habilitada.

    Soporta dependencias en el formato:
        opt["depends_on"] = ("field_key", ["value1", "value2"])

    Y también dependencias especiales:
        opt["depends_on"] = ("_state.attr", [True])  # Verifica atributo del state
        opt["depends_on"] = ("_or", [("field1", ["v1"]), ("_state.c", [True])])  # OR lógico
    """
    depends = opt.get("depends_on")
    if depends is None:
        return True

    dep_key, required_values = depends

    # OR lógico: cualquiera de las condiciones
    if dep_key == "_or":
        for sub_dep in required_values:
            sub_key, sub_values = sub_dep
            if _check_dependency(sub_key, sub_values, all_fields, state):
                return True
        return False

    return _check_dependency(dep_key, required_values, all_fields, state)


def _check_dependency(
    dep_key: str,
    required_values: list,
    all_fields: List[FormField],
    state: Optional[Any] = None,
) -> bool:
    """Verifica una dependencia individual."""
    # Dependencia de atributo del state
    if dep_key.startswith("_state."):
        if state is None:
            return False
        attr_name = dep_key[7:]  # Quitar "_state."
        attr_value = getattr(state, attr_name, None)
        if True in required_values:
            # Simplemente verificar que el atributo tenga valor
            return attr_value is not None
        return attr_value in required_values

    # Dependencia de otro campo
    for f in all_fields:
        if f.key == dep_key:
            if f.value is None:
                return False
            if isinstance(f.value, list):
                return any(v in f.value for v in required_values)
            else:
                return f.value in required_values

    return True


def get_next_enabled_idx(fields: List[FormField], current: int, direction: int = 1) -> int:
    """Obtiene el siguiente índice de campo habilitado."""
    n = len(fields)
    idx = current

    for _ in range(n):
        idx = (idx + direction) % n
        if is_field_enabled(fields[idx], fields):
            return idx

    return current  # Si ninguno está habilitado, quedarse donde está


def get_next_enabled_option_idx(
    options: List[dict],
    current: int,
    direction: int,
    all_fields: List[FormField],
    state: Optional[Any] = None,
) -> int:
    """Obtiene el siguiente índice de opción habilitada en un checkbox/select."""
    n = len(options)
    idx = current

    for _ in range(n):
        idx = (idx + direction) % n
        if is_option_enabled(options[idx], all_fields, state):
            return idx

    return current  # Si ninguna está habilitada, quedarse donde está


def format_checkbox_value(fld: FormField) -> str:
    """Formatea el valor de un campo CHECKBOX."""
    if not fld.value or not isinstance(fld.value, list):
        return "Ninguno"

    names = []
    for v in fld.value:
        for opt in fld.options:
            if opt.get("value") == v:
                name = opt.get("name", str(v))
                if len(name) > 15:
                    name = name[:12] + "..."
                names.append(name)
                break

    if len(names) == 0:
        return "Ninguno"
    elif len(names) <= 2:
        return ", ".join(names)
    else:
        return f"{names[0]}, +{len(names)-1} más"


def format_select_value(fld: FormField) -> str:
    """Formatea el valor de un campo SELECT."""
    if fld.value is None:
        return "-"

    for opt in fld.options:
        if opt.get("value") == fld.value:
            name = opt.get("name", str(fld.value))
            if len(name) > 25:
                return name[:22] + "..."
            return name

    return str(fld.value)


def build_config_table(state: ConfigFormState) -> Table:
    """Construye la tabla de configuración."""
    p = get_palette()
    icons = get_icons()

    table = Table(
        title=state.title,
        title_style=f"bold {p.primary}",
        border_style=p.border,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
        expand=False,
    )

    table.add_column("", justify="right", width=3)
    table.add_column("Parámetro", justify="left", width=28)
    table.add_column("Valor", justify="left", width=35)
    table.add_column("", justify="center", width=3)

    for idx, fld in enumerate(state.fields):
        is_selected = idx == state.selected_idx
        is_enabled = is_field_enabled(fld, state.fields)

        # Formatear valor según tipo
        if fld.field_type == FieldType.CHECKBOX:
            value_str = format_checkbox_value(fld)
        elif fld.field_type == FieldType.SELECT:
            value_str = format_select_value(fld)
        elif fld.field_type == FieldType.FLOAT:
            value_str = f"{fld.value}" if fld.value else "-"
            if fld.unit and fld.value:
                value_str += f" {fld.unit}"
        else:
            value_str = str(fld.value) if fld.value else "-"

        # Estado
        if not is_enabled:
            status_icon = "-"
            status_style = p.muted
        elif fld.status == FieldStatus.FILLED:
            status_icon = icons.check
            status_style = p.success
        elif not fld.required:
            status_icon = icons.info
            status_style = p.muted
        else:
            status_icon = icons.warning
            status_style = p.warning

        # Estilos según selección y habilitación
        if not is_enabled:
            # Campo deshabilitado - siempre en gris
            marker = Text(" ", style=p.muted)
            label_text = Text(fld.label, style=f"dim {p.muted}")
            value_text = Text(value_str, style=f"dim {p.muted}")
            status_text = Text(status_icon, style=f"dim {p.muted}")
        elif is_selected:
            row_style = f"bold reverse {p.primary}"
            marker = Text(">", style=row_style)
            label_text = Text(fld.label, style=row_style)
            value_text = Text(value_str, style=row_style)
            status_text = Text(status_icon, style=row_style)
        else:
            marker = Text(" ", style=p.muted)
            label_text = Text(fld.label, style="bold" if fld.required else p.muted)
            if fld.status == FieldStatus.FILLED:
                value_text = Text(value_str, style=f"bold {p.accent}")
            else:
                value_text = Text(value_str, style=p.muted)
            status_text = Text(status_icon, style=status_style)

        table.add_row(marker, label_text, value_text, status_text)

    return table


def build_checkbox_panel(state: ConfigFormState) -> Panel:
    """Construye panel de selección múltiple para CHECKBOX."""
    p = get_palette()
    icons = get_icons()
    fld = state.fields[state.selected_idx]
    ws = state.wizard_state

    selected_values = fld.value if isinstance(fld.value, list) else []

    table = Table(
        show_header=False,
        box=box.SIMPLE,
        padding=(0, 1),
        expand=True,
    )

    table.add_column("", width=3)
    table.add_column("", width=3)
    table.add_column("", width=3)
    table.add_column("", width=50)

    for idx, opt in enumerate(fld.options):
        is_cursor = idx == state.checkbox_idx
        is_checked = opt.get("value") in selected_values
        is_enabled = is_option_enabled(opt, state.fields, ws)
        opt_name = opt.get("name", str(opt.get("value", "")))
        shortcut = chr(ord('a') + idx) if idx < 26 else ""

        # Estilo para opciones deshabilitadas
        if not is_enabled:
            shortcut_text = Text(f"[{shortcut}]", style=f"dim {p.muted}")
            marker = Text(" ", style=p.muted)
            check_box = Text("[-]", style=f"dim {p.muted}")
            name_text = Text(f"{opt_name} (no disponible)", style=f"dim {p.muted}")
        else:
            # Shortcut
            shortcut_text = Text(f"[{shortcut}]", style=f"bold {p.accent}" if shortcut else p.muted)

            if is_cursor:
                marker = Text(">", style=f"bold {p.primary}")
            else:
                marker = Text(" ", style=p.muted)

            if is_checked:
                check_box = Text(f"[{icons.check}]", style=f"bold {p.success}")
            else:
                check_box = Text("[ ]", style=p.muted)

            if is_cursor:
                name_text = Text(opt_name, style=f"bold {p.primary}")
            else:
                name_text = Text(opt_name, style="bold" if is_checked else "")

        table.add_row(shortcut_text, marker, check_box, name_text)

    return Panel(
        table,
        title=f"[bold {p.accent}]{fld.label}[/]",
        border_style=p.accent,
        padding=(0, 1),
    )


def build_select_panel(state: ConfigFormState) -> Panel:
    """Construye panel de selección única para SELECT."""
    p = get_palette()
    icons = get_icons()
    fld = state.fields[state.selected_idx]

    table = Table(
        show_header=False,
        box=box.SIMPLE,
        padding=(0, 1),
        expand=True,
    )

    table.add_column("", width=3)
    table.add_column("", width=3)
    table.add_column("", width=3)
    table.add_column("", width=50)

    for idx, opt in enumerate(fld.options):
        is_cursor = idx == state.select_idx
        is_selected = fld.value == opt.get("value")
        opt_name = opt.get("name", str(opt.get("value", "")))
        shortcut = chr(ord('a') + idx) if idx < 26 else ""

        # Shortcut
        shortcut_text = Text(f"[{shortcut}]", style=f"bold {p.accent}" if shortcut else p.muted)

        if is_cursor:
            marker = Text(">", style=f"bold {p.primary}")
        else:
            marker = Text(" ", style=p.muted)

        if is_selected:
            radio = Text(f"({icons.check})", style=f"bold {p.success}")
        else:
            radio = Text("( )", style=p.muted)

        if is_cursor:
            name_text = Text(opt_name, style=f"bold {p.primary}")
        else:
            name_text = Text(opt_name, style="bold" if is_selected else "")

        table.add_row(shortcut_text, marker, radio, name_text)

    return Panel(
        table,
        title=f"[bold {p.accent}]{fld.label}[/]",
        border_style=p.accent,
        padding=(0, 1),
    )


def build_text_panel(state: ConfigFormState) -> Panel:
    """Construye panel de entrada de texto."""
    p = get_palette()
    fld = state.fields[state.selected_idx]

    content = Text()

    if fld.hint:
        content.append(f"  {fld.hint}\n\n", style=p.info)

    content.append("  > ", style=f"bold {p.accent}")
    content.append(state.input_buffer, style="bold white")
    content.append("_", style="blink bold white")

    if fld.unit:
        content.append(f" {fld.unit}", style=p.muted)

    return Panel(
        content,
        title=f"[bold {p.accent}]{fld.label}[/]",
        border_style=p.accent,
        padding=(0, 1),
    )


def build_config_hint(state: ConfigFormState) -> Text:
    """Construye texto de ayuda."""
    p = get_palette()
    fld = state.fields[state.selected_idx]

    is_enabled = is_field_enabled(fld, state.fields)

    hint = Text()

    if not is_enabled:
        # Mostrar por qué está deshabilitado
        depends = _get_depends_on(fld)
        if depends:
            dep_key, _ = depends
            hint.append(f"  (Requiere seleccionar {dep_key})", style=f"dim {p.muted}")
    elif fld.hint:
        hint.append(f"  {fld.hint}", style=p.info)

    return hint


def build_config_nav(state: ConfigFormState) -> Text:
    """Construye texto de navegación."""
    p = get_palette()
    nav = Text()

    if state.mode == "navigate":
        nav.append("  [", style=p.muted)
        nav.append("↑↓", style=f"bold {p.primary}")
        nav.append("] Navegar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Enter", style=f"bold {p.primary}")
        nav.append("] Editar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("q", style="bold green")
        nav.append("] Continuar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Esc", style="bold red")
        nav.append("] Volver", style=p.muted)

    elif state.mode == "edit_checkbox":
        nav.append("  [", style=p.muted)
        nav.append("a-z", style=f"bold {p.accent}")
        nav.append("] Marcar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Space", style=f"bold {p.primary}")
        nav.append("] Toggle  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("↑↓", style=f"bold {p.primary}")
        nav.append("] Navegar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Enter", style="bold green")
        nav.append("] Confirmar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Esc", style="bold red")
        nav.append("] Cancelar", style=p.muted)

    elif state.mode == "edit_select":
        nav.append("  [", style=p.muted)
        nav.append("a-z", style=f"bold {p.accent}")
        nav.append("] Seleccionar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("↑↓", style=f"bold {p.primary}")
        nav.append("] Navegar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Enter", style="bold green")
        nav.append("] Confirmar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Esc", style="bold red")
        nav.append("] Cancelar", style=p.muted)

    elif state.mode == "edit_text":
        nav.append("  [", style=p.muted)
        nav.append("Enter", style="bold green")
        nav.append("] Confirmar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Esc", style="bold red")
        nav.append("] Cancelar", style=p.muted)

    return nav


def build_config_progress(state: ConfigFormState) -> Panel:
    """Construye panel de progreso."""
    p = get_palette()
    icons = get_icons()

    # Solo contar campos habilitados y requeridos
    filled = sum(
        1 for f in state.fields
        if f.status == FieldStatus.FILLED and is_field_enabled(f, state.fields)
    )
    required = sum(
        1 for f in state.fields
        if f.required and is_field_enabled(f, state.fields)
    )

    text = Text()
    text.append(f"  {icons.check} ", style=p.success)
    text.append(f"{filled}/{required}", style=f"bold {p.accent}")
    text.append(" parámetros configurados", style=p.muted)

    if filled >= required:
        text.append("  │  ", style=p.muted)
        text.append("Listo para continuar [q]", style=f"bold {p.success}")

    return Panel(text, border_style=p.border, padding=(0, 1))


def build_config_message(state: ConfigFormState) -> Text:
    """Construye texto de mensaje."""
    p = get_palette()
    if not state.message:
        return Text("")

    if "error" in state.message.lower():
        return Text(f"  {state.message}", style=f"bold {p.error}")

    return Text(f"  {state.message}", style=p.info)


def build_config_display(state: ConfigFormState) -> Group:
    """Construye el display completo."""
    elements = [
        Text(""),
        build_config_table(state),
        build_config_hint(state),
    ]

    # Mostrar panel de edición si corresponde
    if state.mode == "edit_checkbox":
        elements.append(Text(""))
        elements.append(build_checkbox_panel(state))
    elif state.mode == "edit_select":
        elements.append(Text(""))
        elements.append(build_select_panel(state))
    elif state.mode == "edit_text":
        elements.append(Text(""))
        elements.append(build_text_panel(state))

    elements.extend([
        Text(""),
        build_config_progress(state),
        build_config_message(state),
        build_config_nav(state),
    ])

    return Group(*elements)


def interactive_config_form(
    title: str,
    fields: List[FormField],
    state: Any = None,  # WizardState para contexto
    dependencies: dict = None,  # {"field_key": ("depends_on_key", ["value1", "value2"])}
) -> Optional[dict]:
    """
    Muestra un formulario de configuración interactivo.

    Args:
        title: Título del formulario
        fields: Lista de FormField definiendo los campos
        state: Estado del wizard para contexto (opcional)
        dependencies: Diccionario de dependencias entre campos

    Returns:
        Diccionario con los valores, None si cancela, o False si quiere volver atrás
    """
    console = Console()
    from rich.live import Live

    # Configurar dependencias
    if dependencies:
        for fld in fields:
            if fld.key in dependencies:
                _set_depends_on(fld, dependencies[fld.key])

    # Inicializar estado de campos
    for fld in fields:
        if fld.field_type == FieldType.CHECKBOX:
            if fld.value is None:
                fld.value = [
                    opt.get("value")
                    for opt in fld.options
                    if opt.get("checked", False)
                ]
            if fld.value:
                fld.status = FieldStatus.FILLED
            elif not fld.required:
                fld.status = FieldStatus.OPTIONAL
        elif fld.field_type == FieldType.SELECT:
            if fld.value is None and fld.default is not None:
                fld.value = fld.default
            if fld.value is not None:
                fld.status = FieldStatus.FILLED
            elif not fld.required:
                fld.status = FieldStatus.OPTIONAL
        elif fld.default is not None:
            fld.value = fld.default
            fld.status = FieldStatus.FILLED
        elif not fld.required:
            fld.status = FieldStatus.OPTIONAL

    form_state = ConfigFormState(
        title=title,
        fields=fields,
        wizard_state=state,
    )

    # Asegurar que empezamos en un campo habilitado
    if not is_field_enabled(fields[0], fields):
        form_state.selected_idx = get_next_enabled_idx(fields, 0, 1)

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_config_display(form_state)
        live.update(display, refresh=True)

        while True:
            key = get_key()
            n_fields = len(form_state.fields)
            current_field = form_state.fields[form_state.selected_idx]

            # Modo edición CHECKBOX
            if form_state.mode == "edit_checkbox":
                n_options = len(current_field.options)
                selected_values = current_field.value if isinstance(current_field.value, list) else []
                ws = form_state.wizard_state

                if key == 'up':
                    form_state.checkbox_idx = get_next_enabled_option_idx(
                        current_field.options, form_state.checkbox_idx, -1,
                        form_state.fields, ws
                    )
                elif key == 'down':
                    form_state.checkbox_idx = get_next_enabled_option_idx(
                        current_field.options, form_state.checkbox_idx, 1,
                        form_state.fields, ws
                    )
                elif key == 'space':
                    opt = current_field.options[form_state.checkbox_idx]
                    # Solo permitir toggle si la opción está habilitada
                    if is_option_enabled(opt, form_state.fields, ws):
                        opt_value = opt.get("value")
                        if opt_value in selected_values:
                            selected_values.remove(opt_value)
                        else:
                            selected_values.append(opt_value)
                        current_field.value = selected_values
                elif key == 'enter':
                    # Al confirmar, eliminar valores de opciones deshabilitadas
                    valid_values = [
                        v for v in selected_values
                        if any(
                            opt.get("value") == v and is_option_enabled(opt, form_state.fields, ws)
                            for opt in current_field.options
                        )
                    ]
                    current_field.value = valid_values
                    if valid_values or not current_field.required:
                        current_field.status = FieldStatus.FILLED if valid_values else FieldStatus.OPTIONAL
                        form_state.message = f"{current_field.label} actualizado"
                        form_state.mode = "navigate"
                        # Avanzar al siguiente campo habilitado
                        next_idx = get_next_enabled_idx(form_state.fields, form_state.selected_idx, 1)
                        if next_idx != form_state.selected_idx:
                            form_state.selected_idx = next_idx
                    else:
                        form_state.message = "Debe seleccionar al menos una opción"
                elif key == 'esc':
                    form_state.mode = "navigate"
                    form_state.message = ""
                else:
                    # Shortcut con letras
                    if len(key) == 1 and key.isalpha():
                        idx = ord(key.lower()) - ord('a')
                        if 0 <= idx < n_options:
                            opt = current_field.options[idx]
                            # Solo permitir toggle si la opción está habilitada
                            if is_option_enabled(opt, form_state.fields, ws):
                                opt_value = opt.get("value")
                                if opt_value in selected_values:
                                    selected_values.remove(opt_value)
                                else:
                                    selected_values.append(opt_value)
                                current_field.value = selected_values
                                form_state.checkbox_idx = idx

            # Modo edición SELECT
            elif form_state.mode == "edit_select":
                n_options = len(current_field.options)

                if key == 'up':
                    form_state.select_idx = (form_state.select_idx - 1) % n_options
                elif key == 'down':
                    form_state.select_idx = (form_state.select_idx + 1) % n_options
                elif key == 'enter':
                    selected_opt = current_field.options[form_state.select_idx]
                    current_field.value = selected_opt.get("value")
                    current_field.status = FieldStatus.FILLED
                    form_state.message = f"{current_field.label} actualizado"
                    form_state.mode = "navigate"
                    # Avanzar al siguiente campo habilitado
                    next_idx = get_next_enabled_idx(form_state.fields, form_state.selected_idx, 1)
                    if next_idx != form_state.selected_idx:
                        form_state.selected_idx = next_idx
                elif key == 'esc':
                    form_state.mode = "navigate"
                    form_state.message = ""
                else:
                    # Shortcut con letras
                    if len(key) == 1 and key.isalpha():
                        idx = ord(key.lower()) - ord('a')
                        if 0 <= idx < n_options:
                            selected_opt = current_field.options[idx]
                            current_field.value = selected_opt.get("value")
                            current_field.status = FieldStatus.FILLED
                            form_state.message = f"{current_field.label} actualizado"
                            form_state.mode = "navigate"
                            next_idx = get_next_enabled_idx(form_state.fields, form_state.selected_idx, 1)
                            if next_idx != form_state.selected_idx:
                                form_state.selected_idx = next_idx

            # Modo edición TEXT
            elif form_state.mode == "edit_text":
                if key == 'enter':
                    value = form_state.input_buffer.strip()

                    # Validar según tipo
                    if current_field.field_type == FieldType.FLOAT:
                        try:
                            value = float(value) if value else None
                            if value is not None:
                                if current_field.min_value is not None and value < current_field.min_value:
                                    form_state.message = f"Error: mínimo {current_field.min_value}"
                                    display = build_config_display(form_state)
                                    live.update(display, refresh=True)
                                    continue
                                if current_field.max_value is not None and value > current_field.max_value:
                                    form_state.message = f"Error: máximo {current_field.max_value}"
                                    display = build_config_display(form_state)
                                    live.update(display, refresh=True)
                                    continue
                        except ValueError:
                            form_state.message = "Error: debe ser un número"
                            display = build_config_display(form_state)
                            live.update(display, refresh=True)
                            continue

                    current_field.value = value
                    current_field.status = FieldStatus.FILLED if value else FieldStatus.OPTIONAL
                    form_state.message = f"{current_field.label} actualizado"
                    form_state.mode = "navigate"
                    form_state.input_buffer = ""
                    next_idx = get_next_enabled_idx(form_state.fields, form_state.selected_idx, 1)
                    if next_idx != form_state.selected_idx:
                        form_state.selected_idx = next_idx

                elif key == 'esc':
                    form_state.mode = "navigate"
                    form_state.input_buffer = ""
                    form_state.message = ""
                elif key == 'backspace':
                    form_state.input_buffer = form_state.input_buffer[:-1]
                elif isinstance(key, str) and len(key) == 1 and (key.isprintable() or key in '.-'):
                    form_state.input_buffer += key

            # Modo navegación
            elif form_state.mode == "navigate":
                if key == 'q':
                    # Continuar - retornar valores
                    clear_screen()
                    return {f.key: f.value for f in form_state.fields}

                elif key == 'esc':
                    # Volver atrás
                    clear_screen()
                    return False  # Indicador de "volver"

                elif key == 'up':
                    form_state.selected_idx = get_next_enabled_idx(
                        form_state.fields, form_state.selected_idx, -1
                    )
                    form_state.message = ""

                elif key == 'down':
                    form_state.selected_idx = get_next_enabled_idx(
                        form_state.fields, form_state.selected_idx, 1
                    )
                    form_state.message = ""

                elif key == 'enter':
                    if not is_field_enabled(current_field, form_state.fields):
                        form_state.message = "Este campo está deshabilitado"
                    else:
                        form_state.message = ""
                        if current_field.field_type == FieldType.CHECKBOX:
                            form_state.mode = "edit_checkbox"
                            form_state.checkbox_idx = 0
                        elif current_field.field_type == FieldType.SELECT:
                            form_state.mode = "edit_select"
                            form_state.select_idx = 0
                            if current_field.value is not None:
                                for idx, opt in enumerate(current_field.options):
                                    if opt.get("value") == current_field.value:
                                        form_state.select_idx = idx
                                        break
                        elif current_field.field_type in (FieldType.TEXT, FieldType.FLOAT, FieldType.INT):
                            form_state.mode = "edit_text"
                            form_state.input_buffer = str(current_field.value) if current_field.value else ""

            # Actualizar display
            display = build_config_display(form_state)
            live.update(display, refresh=True)

    clear_screen()
    return None
