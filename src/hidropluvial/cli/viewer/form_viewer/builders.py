"""
Funciones para construir componentes visuales del formulario.
"""

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box

from hidropluvial.cli.theme import get_palette, get_icons

from .models import FormState, FormField, FieldType, FieldStatus
from .validators import format_field_value


def build_form_table(state: FormState) -> Table:
    """Construye la tabla del formulario."""
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

    table.add_column("#", justify="right", width=3)
    table.add_column("Campo", justify="left", width=25)
    table.add_column("Valor", justify="left", width=30)
    table.add_column("Estado", justify="center", width=12)

    for idx, fld in enumerate(state.fields):
        is_selected = idx == state.selected_idx

        # Campo deshabilitado (dependencia no cumplida)
        if fld.disabled:
            idx_text = Text(str(idx + 1), style=f"dim {p.muted}")
            label_text = Text(fld.label, style=f"dim {p.muted} strike")
            # Mostrar disabled_hint en amarillo si existe, sino "bloqueado" en gris
            if fld.disabled_hint:
                value_text = Text(fld.disabled_hint, style=f"{p.warning}")
                status_full = Text(f"{icons.warning}", style=f"{p.warning}")
            else:
                value_text = Text("-", style=f"dim {p.muted}")
                status_full = Text(f"{icons.info} bloqueado", style=f"dim {p.muted}")
            table.add_row(idx_text, label_text, value_text, status_full)
            continue

        # Determinar estado visual
        if fld.status == FieldStatus.FILLED:
            status_icon = icons.check
            status_style = p.success
            status_text = "completo"
        elif fld.status == FieldStatus.INVALID:
            status_icon = icons.cross
            status_style = p.error
            status_text = "inválido"
        elif not fld.required:
            status_icon = icons.info
            status_style = p.muted
            status_text = "opcional"
        else:
            status_icon = icons.warning
            status_style = p.warning
            status_text = "pendiente"

        # Formatear valor
        value_str = format_field_value(fld)

        # Construir label con unidad si aplica
        label = fld.label
        if fld.unit and fld.value is None:
            label += f" ({fld.unit})"

        # Estilos según selección
        if is_selected:
            row_style = f"bold reverse {p.primary}"
            idx_text = Text(f">{idx + 1}", style=row_style)
            label_text = Text(label, style=row_style)
            value_text = Text(value_str, style=row_style)
            status_full = Text(f"{status_icon} {status_text}", style=row_style)
        else:
            idx_text = Text(str(idx + 1), style=p.muted)
            label_text = Text(label, style="bold" if fld.required else p.muted)
            if fld.status == FieldStatus.FILLED:
                value_text = Text(value_str, style=f"bold {p.accent}")
            else:
                value_text = Text(value_str, style=p.muted)
            status_full = Text(f"{status_icon} {status_text}", style=status_style)

        table.add_row(idx_text, label_text, value_text, status_full)

    return table


def build_hint_text(state: FormState) -> Text:
    """Construye el texto de ayuda para el campo actual."""
    p = get_palette()
    fld = state.fields[state.selected_idx]

    hint = Text()
    if fld.hint:
        hint.append(f"  {fld.hint}", style=p.info)

    # Agregar info de rango si existe
    if fld.min_value is not None or fld.max_value is not None:
        range_info = []
        if fld.min_value is not None:
            range_info.append(f"mín: {fld.min_value}")
        if fld.max_value is not None:
            range_info.append(f"máx: {fld.max_value}")
        if hint:
            hint.append("  ", style=p.muted)
        hint.append(f"({', '.join(range_info)})", style=p.muted)

    return hint


def build_progress_panel(state: FormState) -> Panel:
    """Construye el panel de progreso."""
    p = get_palette()
    filled, required = state.count_filled()

    text = Text()
    text.append("  Progreso: ", style=p.muted)
    text.append(f"{filled}/{required}", style=f"bold {p.accent}")
    text.append(" campos requeridos", style=p.muted)

    if state.is_complete():
        text.append("  │  ", style=p.muted)
        text.append("✓ Listo para continuar", style=f"bold {p.success}")

    return Panel(text, border_style=p.border, padding=(0, 1))


def build_select_options(state: FormState) -> Table:
    """Construye tabla de opciones para modo SELECT."""
    p = get_palette()
    icons = get_icons()
    fld = state.fields[state.selected_idx]

    is_checkbox = fld.field_type == FieldType.CHECKBOX

    table = Table(
        title=f"{'Seleccionar múltiple' if is_checkbox else 'Seleccionar'}: {fld.label}",
        title_style=f"bold {p.accent}",
        border_style=p.accent,
        box=box.ROUNDED,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column("", width=3)
    if is_checkbox:
        table.add_column("", width=3)
    table.add_column("Opción", width=50)

    # Para checkbox, obtener lista de valores seleccionados
    selected_values = []
    if is_checkbox and isinstance(fld.value, list):
        selected_values = fld.value

    for idx, opt in enumerate(fld.options):
        is_cursor = idx == state.select_idx
        opt_value = opt.get("value")
        name = opt.get("name", str(opt_value or ""))

        # Checkbox: mostrar si está marcado (usando mismos iconos que popup)
        if is_checkbox:
            is_checked = opt_value in selected_values
            check_icon = icons.selected if is_checked else icons.unselected
            check_mark = Text(check_icon,
                            style=f"bold {p.success}" if is_checked else p.muted)

        if is_cursor:
            row_style = f"bold reverse {p.primary}"
            marker = Text(">", style=row_style)
            opt_text = Text(name, style=row_style)
            if is_checkbox:
                check_icon = icons.selected if opt_value in selected_values else icons.unselected
                check_mark = Text(check_icon, style=row_style)
        else:
            marker = Text(" ", style=p.muted)
            opt_text = Text(name, style=f"bold {p.accent}" if (is_checkbox and opt_value in selected_values) else "")

        if is_checkbox:
            table.add_row(marker, check_mark, opt_text)
        else:
            table.add_row(marker, opt_text)

    return table


def build_nav_text(state: FormState, allow_back: bool = True) -> Text:
    """Construye el texto de navegación."""
    p = get_palette()
    nav = Text()

    if state.mode == "navigate":
        nav.append("  [", style=p.muted)
        nav.append("↑↓", style=f"bold {p.primary}")
        nav.append("] Navegar  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Enter", style=f"bold {p.primary}")
        nav.append("] Editar  ", style=p.muted)
        if state.is_complete():
            nav.append("[", style=p.muted)
            nav.append("q", style=f"bold {p.nav_confirm}")
            nav.append("] Finalizar  ", style=p.muted)
        if allow_back:
            nav.append("[", style=p.muted)
            nav.append("b", style=f"bold {p.primary}")
            nav.append("] Volver  ", style=p.muted)
        nav.append("[", style=p.muted)
        nav.append("Esc", style=f"bold {p.nav_cancel}")
        nav.append("] Cancelar", style=p.muted)

    elif state.mode == "edit_text":
        fld = state.fields[state.selected_idx]
        nav.append(f"  {fld.label}: ", style=f"bold {p.accent}")
        nav.append(state.input_buffer, style=f"bold {p.input_text}")
        nav.append("_", style=f"blink bold {p.input_text}")
        nav.append("  [Enter] Confirmar  [Esc] Cancelar", style=p.muted)

    elif state.mode == "edit_select":
        fld = state.fields[state.selected_idx]
        is_checkbox = fld.field_type == FieldType.CHECKBOX

        nav.append("  [", style=p.muted)
        nav.append("↑↓", style=f"bold {p.primary}")
        nav.append("] Navegar  ", style=p.muted)

        if is_checkbox:
            nav.append("[", style=p.muted)
            nav.append("Espacio", style=f"bold {p.primary}")
            nav.append("] Marcar  ", style=p.muted)
            nav.append("[", style=p.muted)
            nav.append("Enter", style=f"bold {p.primary}")
            nav.append("] Confirmar  ", style=p.muted)
        else:
            nav.append("[", style=p.muted)
            nav.append("Enter", style=f"bold {p.primary}")
            nav.append("] Seleccionar  ", style=p.muted)

        nav.append("[", style=p.muted)
        nav.append("Esc", style=f"bold {p.primary}")
        nav.append("] Cancelar", style=p.muted)

    return nav


def build_message_text(state: FormState) -> Text:
    """Construye el texto de mensaje."""
    p = get_palette()
    if not state.message:
        return Text("")

    if "Error" in state.message or "inválido" in state.message.lower():
        style = f"bold {p.error}"
    elif "guardado" in state.message.lower() or "actualizado" in state.message.lower():
        style = f"bold {p.success}"
    else:
        style = p.info

    return Text(f"  {state.message}", style=style)


def build_popup_overlay(state: FormState) -> Table:
    """Construye el popup overlay para on_edit como una tabla."""
    p = get_palette()
    icons = get_icons()
    fld = state.popup_field

    # Determinar si hay opciones checkable
    has_checkable = any(opt.get("checkable") for opt in state.popup_options if not opt.get("separator"))

    table = Table(
        title=f"{fld.label}",
        title_style=f"bold {p.accent}",
        border_style=p.accent,
        box=box.DOUBLE,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column("", width=3)  # Marcador de selección
    table.add_column("", width=5)  # Checkbox o shortcut
    table.add_column("", width=5)  # Shortcut (si hay checkbox)
    table.add_column("Opción", width=30)  # Label
    table.add_column("", width=20)  # Hint

    # Obtener valores actuales del campo para checkables
    current_values = []
    if fld.value and isinstance(fld.value, list):
        current_values = [v.lower() if isinstance(v, str) else v for v in fld.value]

    for idx, opt in enumerate(state.popup_options):
        is_selected = idx == state.popup_idx
        is_separator = opt.get("separator", False)
        section_title = opt.get("title")

        if is_separator:
            # Si tiene título, mostrar como encabezado de sección
            if section_title:
                table.add_row(
                    Text("", style=p.muted),
                    Text("─" * 5, style=p.muted),
                    Text("", style=p.muted),
                    Text(f" {section_title} ", style=f"bold {p.secondary}"),
                    Text("─" * 10, style=p.muted),
                )
            else:
                table.add_row(
                    Text("", style=p.muted),
                    Text("─" * 5, style=p.muted),
                    Text("", style=p.muted),
                    Text("─" * 30, style=p.muted),
                    Text("", style=p.muted),
                )
            continue

        key = opt.get("key", "")
        label = opt.get("label", "")
        hint = opt.get("hint", "")
        is_checkable = opt.get("checkable", False)
        has_action = callable(opt.get("action"))
        opt_value = opt.get("value")
        is_disabled = opt.get("disabled", False)

        # Detectar si es una opción de "agregar" (key es + o icons.add)
        is_add_action = has_action and key in ("+", icons.add)

        # Para checkables, verificar si está marcado
        is_checked = False
        if is_checkable and opt_value:
            check_val = opt_value.lower() if isinstance(opt_value, str) else opt_value
            is_checked = check_val in current_values

        # Opciones deshabilitadas siempre en estilo muted
        if is_disabled:
            marker = Text(" ", style=p.muted)
            checkbox = Text("", style=p.muted)
            key_text = Text(f"[{key}]" if key else "", style=p.muted)
            label_text = Text(label, style=f"dim {p.muted}")
            hint_text = Text(hint, style=f"dim {p.muted}")
        elif is_selected:
            row_style = f"bold reverse {p.primary}"
            marker = Text(">", style=row_style)
            if is_checkable:
                check_icon = icons.selected if is_checked else icons.unselected
                checkbox = Text(f"{check_icon}", style=row_style)
            else:
                checkbox = Text("", style=row_style)
            key_text = Text(f"[{key}]" if key else "", style=row_style)
            label_text = Text(label, style=row_style)
            hint_text = Text(hint, style=row_style)
        else:
            marker = Text(" ", style=p.muted)
            if is_checkable:
                check_icon = icons.selected if is_checked else icons.unselected
                check_style = f"bold {p.success}" if is_checked else p.muted
                checkbox = Text(f"{check_icon}", style=check_style)
            else:
                checkbox = Text("", style=p.muted)
            # Usar verde para opciones de "agregar", accent para el resto
            key_style = f"bold {p.success}" if is_add_action else f"bold {p.accent}"
            key_text = Text(f"[{key}]" if key else "", style=key_style)
            label_text = Text(label, style="")
            hint_text = Text(hint, style=p.muted)

        table.add_row(marker, checkbox, key_text, label_text, hint_text)

    # Agregar fila de navegación
    nav_hint = "[↑↓] Navegar  [Enter] OK  [Esc] Cancelar"
    if has_checkable:
        nav_hint = "[↑↓] Navegar  [Espacio/Enter] Marcar  [Esc] Listo"
    table.add_row(
        Text("", style=p.muted),
        Text("", style=p.muted),
        Text("", style=p.muted),
        Text(nav_hint, style=p.muted),
        Text("", style=p.muted),
    )

    return table


def build_cancel_confirm_panel() -> Panel:
    """Construye el panel de confirmación de cancelación (estilo alerta amarilla)."""
    p = get_palette()
    icons = get_icons()

    content = Text()
    content.append(f"\n  {icons.warning} ", style=f"bold {p.warning}")
    content.append("Se perderán los datos ingresados\n\n", style=f"bold {p.warning}")
    content.append("  ¿Cancelar?\n\n", style=f"bold {p.input_text}")
    content.append("  [", style=p.muted)
    content.append("s", style=f"bold {p.warning}")
    content.append("] Sí, cancelar    ", style=p.muted)
    content.append("[", style=p.muted)
    content.append("n", style=f"bold {p.nav_confirm}")
    content.append("] No, continuar\n", style=p.muted)

    return Panel(
        content,
        border_style=p.warning,
        box=box.DOUBLE,
        padding=(0, 2),
        width=50,
    )


def build_popup_confirm_panel(title: str, message: str, default: bool = True) -> Panel:
    """Construye un panel de confirmación inline para el popup (estilo alerta)."""
    p = get_palette()
    icons = get_icons()

    content = Text()
    content.append(f"\n    [{icons.warning}] ", style=f"bold {p.warning}")
    content.append(f"{message}\n\n", style=f"{p.warning}")
    content.append("    [", style=p.muted)
    content.append("s", style=f"bold {p.success}")
    content.append("] Sí    ", style=p.muted)
    content.append("[", style=p.muted)
    content.append("n", style=f"bold {p.error}")
    content.append("] No", style=p.muted)
    if default:
        content.append("  (Enter = Sí)", style=p.muted)
    else:
        content.append("  (Enter = No)", style=p.muted)
    content.append("\n", style=p.muted)

    return Panel(
        content,
        title=f"[bold {p.warning}] {title} [/]",
        border_style=p.warning,
        box=box.DOUBLE,
        padding=(0, 2),
    )


def build_popup_submenu_panel(state: FormState) -> Panel:
    """Construye el panel de submenú dentro del popup."""
    p = get_palette()

    table = Table(
        title=state.submenu_title,
        title_style=f"bold {p.accent}",
        border_style=p.accent,
        box=box.ROUNDED,
        show_header=False,
        padding=(0, 1),
    )

    table.add_column("", width=3)  # Marcador
    table.add_column("Opción", width=35)
    table.add_column("", width=25)  # Descripción

    for idx, opt in enumerate(state.submenu_options):
        is_selected = idx == state.submenu_idx
        label = opt.get("label", "")
        desc = opt.get("description", "")

        if is_selected:
            row_style = f"bold reverse {p.primary}"
            marker = Text(">", style=row_style)
            label_text = Text(label, style=row_style)
            desc_text = Text(desc, style=row_style)
        else:
            marker = Text(" ", style=p.muted)
            label_text = Text(label, style="")
            desc_text = Text(desc, style=p.muted)

        table.add_row(marker, label_text, desc_text)

    # Navegación
    nav = Text()
    nav.append("\n  [↑↓] Navegar  [Enter] Seleccionar  [Esc] Volver", style=p.muted)

    return Panel(
        Group(table, nav),
        border_style=p.accent,
        box=box.DOUBLE,
        padding=(0, 1),
    )


def build_popup_inline_input_panel(state: FormState) -> Panel:
    """Construye el panel de entrada inline dentro del popup."""
    p = get_palette()

    content_parts = []

    # Título/label principal
    title_text = Text()
    title_text.append(f"\n  {state.inline_input_label}\n", style=f"bold {p.accent}")
    content_parts.append(title_text)

    # Mostrar cada campo del formulario inline
    for idx, fld in enumerate(state.inline_input_fields):
        is_current = idx == state.inline_input_idx
        label = fld.get("label", "")
        value = fld.get("value", "")
        unit = fld.get("unit", "")
        fld_type = fld.get("type", "float")

        line = Text()
        if is_current:
            line.append("  > ", style=f"bold {p.primary}")
            line.append(f"{label}: ", style=f"bold {p.primary}")
            # Mostrar input buffer con cursor
            line.append(state.input_buffer, style=f"bold {p.input_text}")
            line.append("_", style=f"blink bold {p.input_text}")
            if unit:
                line.append(f" {unit}", style=p.muted)
        else:
            line.append("    ", style=p.muted)
            line.append(f"{label}: ", style=p.muted)
            if value:
                line.append(str(value), style=f"bold {p.accent}")
            else:
                line.append("-", style=p.muted)
            if unit:
                line.append(f" {unit}", style=p.muted)

        line.append("\n")
        content_parts.append(line)

    # Hint si existe
    if state.inline_input_hint:
        hint_text = Text()
        hint_text.append(f"\n  {state.inline_input_hint}\n", style=p.info)
        content_parts.append(hint_text)

    # Navegación
    nav_text = Text()
    nav_text.append("\n  [Tab] Siguiente  [Enter] Confirmar  [Esc] Cancelar\n", style=p.muted)
    content_parts.append(nav_text)

    return Panel(
        Group(*content_parts),
        border_style=p.accent,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def build_display(state: FormState, allow_back: bool = True) -> Group:
    """Construye el display completo."""
    from .nrcs import build_nrcs_calculator_panel
    from .bimodal import build_bimodal_calculator_panel

    form_table = build_form_table(state)
    hint = build_hint_text(state)
    progress = build_progress_panel(state)
    nav = build_nav_text(state, allow_back)
    msg = build_message_text(state)

    elements = [
        Text(""),
        form_table,
    ]

    if hint:
        elements.append(hint)

    # Mostrar opciones si está en modo select
    if state.mode == "edit_select":
        elements.append(Text(""))
        elements.append(build_select_options(state))

    # Mostrar popup si está en modo popup
    elif state.mode == "popup" and state.popup_field:
        elements.append(Text(""))
        popup = build_popup_overlay(state)
        elements.append(popup)

    # Mostrar confirmación de cancelación
    elif state.mode == "confirm_cancel":
        elements.append(Text(""))
        elements.append(build_cancel_confirm_panel())

    # Mostrar confirmación inline para opción de popup
    elif state.mode == "popup_confirm" and state.pending_check_opt:
        elements.append(Text(""))
        opt = state.pending_check_opt
        confirm_title = opt.get("confirm_title", "Confirmar")
        confirm_message = opt.get("confirm_message", "¿Continuar?")
        elements.append(build_popup_confirm_panel(confirm_title, confirm_message, state.confirm_default))

    # Mostrar submenú dentro del popup
    elif state.mode == "popup_submenu" and state.submenu_options:
        elements.append(Text(""))
        elements.append(build_popup_submenu_panel(state))

    # Mostrar entrada inline dentro del popup
    elif state.mode == "popup_inline_input" and state.inline_input_fields:
        elements.append(Text(""))
        elements.append(build_popup_inline_input_panel(state))

    # Mostrar calculadora NRCS
    elif state.mode == "popup_nrcs_calculator":
        elements.append(Text(""))
        elements.append(build_nrcs_calculator_panel(state))

    # Mostrar calculadora bimodal
    elif state.mode == "popup_bimodal_calculator":
        elements.append(Text(""))
        elements.append(build_bimodal_calculator_panel(state))

    elements.extend([
        Text(""),
        progress,
        msg,
        nav,
    ])

    return Group(*elements)
