"""
Visor interactivo para asignación de coberturas (C y CN).

Permite navegar entre filas usando:
- Flechas arriba/abajo: cambiar fila seleccionada
- Enter: asignar cobertura a la fila
- e: editar descripción de la última asignación
- d: eliminar última asignación
- Espacio: asignar toda el área restante a la fila
- q/ESC: terminar y calcular
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, List

from rich.console import Group
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich import box

from hidropluvial.cli.theme import get_palette, get_console
from hidropluvial.cli.viewer.terminal import clear_screen, get_key


@dataclass
class CoverageOption:
    """Opción de cobertura disponible en la tabla."""
    index: int
    category: str
    description: str
    value: float  # C o CN (base, grupo B para CN)
    value_label: str  # "C" o "CN"
    # Valores CN por grupo de suelo (solo para CN)
    cn_a: Optional[int] = None
    cn_b: Optional[int] = None
    cn_c: Optional[int] = None
    cn_d: Optional[int] = None
    # Valores C por periodo de retorno (solo para C - tabla Chow)
    c_tr2: Optional[float] = None
    c_tr5: Optional[float] = None
    c_tr10: Optional[float] = None
    c_tr25: Optional[float] = None
    c_tr50: Optional[float] = None
    c_tr100: Optional[float] = None

    @property
    def has_soil_groups(self) -> bool:
        """Indica si tiene valores por grupo de suelo."""
        return self.cn_a is not None

    @property
    def has_tr_values(self) -> bool:
        """Indica si tiene valores C por periodo de retorno."""
        return self.c_tr2 is not None


@dataclass
class CoverageAssignment:
    """Una asignación de cobertura realizada."""
    option_index: int  # Índice en la tabla de opciones
    category: str
    description: str
    value: float  # C o CN efectivo
    area: float
    note: str = ""
    soil_group: str = ""  # Solo para CN


@dataclass
class CoverageFormState:
    """Estado del formulario para agregar cobertura."""
    area: str = ""
    note: str = ""
    soil_group: str = "B"  # Default
    active_field: int = 0  # 0=area, 1=note, 2=soil (solo CN)
    is_cn: bool = False


@dataclass
class CoverageViewerState:
    """Estado del visor de coberturas."""
    options: List[CoverageOption]
    assignments: List[CoverageAssignment]
    total_area: float
    value_label: str  # "C" o "CN"
    table_name: str
    selected_idx: int = 0
    selected_assignment_idx: int = -1  # -1 = tabla opciones, >=0 = tabla asignaciones
    mode: str = "navigate"  # "navigate", "input_area", "input_desc", "select_soil", "form", "edit_note"
    input_buffer: str = ""
    message: str = ""
    soil_groups: List[str] = field(default_factory=lambda: ["A", "B", "C", "D"])
    focus_assignments: bool = False  # True = foco en tabla de asignaciones
    form_state: Optional[CoverageFormState] = None  # Estado del formulario

    @property
    def area_assigned(self) -> float:
        return sum(a.area for a in self.assignments)

    @property
    def area_remaining(self) -> float:
        return self.total_area - self.area_assigned

    def weighted_value(self) -> Optional[float]:
        """Calcula el valor ponderado."""
        if not self.assignments:
            return None
        total_area = sum(a.area for a in self.assignments)
        if total_area == 0:
            return None
        return sum(a.area * a.value for a in self.assignments) / total_area


def build_options_table(
    state: CoverageViewerState,
    max_visible_rows: int = 15,
) -> Table:
    """Construye la tabla de opciones de cobertura."""
    p = get_palette()

    # Calcular ventana visible
    n_rows = len(state.options)
    if n_rows <= max_visible_rows:
        start_idx = 0
        end_idx = n_rows
    else:
        half = max_visible_rows // 2
        start_idx = state.selected_idx - half
        end_idx = start_idx + max_visible_rows

        if start_idx < 0:
            start_idx = 0
            end_idx = max_visible_rows
        elif end_idx > n_rows:
            end_idx = n_rows
            start_idx = end_idx - max_visible_rows

    # Detectar tipo de tabla
    is_cn_with_soil = (
        state.value_label == "CN" and
        state.options and
        state.options[0].has_soil_groups
    )
    is_c_with_tr = (
        state.value_label == "C" and
        state.options and
        state.options[0].has_tr_values
    )

    table = Table(
        title=state.table_name,
        title_style=f"bold {p.primary}",
        border_style=p.border if not state.focus_assignments else p.muted,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    # Columnas base
    table.add_column("#", justify="right", width=3)
    table.add_column("Categoría", justify="left", max_width=15)
    table.add_column("Descripción", justify="left", max_width=22)

    if is_cn_with_soil:
        # Mostrar columnas A, B, C, D para CN
        table.add_column("A", justify="right", width=4)
        table.add_column("B", justify="right", width=4)
        table.add_column("C", justify="right", width=4)
        table.add_column("D", justify="right", width=4)
    elif is_c_with_tr:
        # Mostrar columnas por Tr para C (Chow)
        table.add_column("Tr2", justify="right", width=5, header_style=f"bold {p.accent}")
        table.add_column("Tr5", justify="right", width=5, header_style=p.muted)
        table.add_column("Tr10", justify="right", width=5, header_style=p.muted)
        table.add_column("Tr25", justify="right", width=5, header_style=p.muted)
        table.add_column("Tr50", justify="right", width=5, header_style=p.muted)
        table.add_column("Tr100", justify="right", width=5, header_style=p.muted)
    else:
        table.add_column(state.value_label, justify="right", width=6)

    for idx in range(start_idx, end_idx):
        opt = state.options[idx]
        is_selected = idx == state.selected_idx and not state.focus_assignments

        # Estilos según estado
        if is_selected:
            row_style = f"bold reverse {p.primary}"
            idx_text = Text(f">{opt.index + 1}", style=row_style)
            cat_text = Text(opt.category[:15], style=row_style)
            desc_text = Text(opt.description[:22], style=row_style)

            if is_cn_with_soil:
                cn_a = Text(str(opt.cn_a), style=row_style)
                cn_b = Text(str(opt.cn_b), style=row_style)
                cn_c = Text(str(opt.cn_c), style=row_style)
                cn_d = Text(str(opt.cn_d), style=row_style)
            elif is_c_with_tr:
                # Tr2 resaltado (elegible), otros en gris
                c_tr2 = Text(f"{opt.c_tr2:.2f}", style=row_style)
                c_tr5 = Text(f"{opt.c_tr5:.2f}", style=row_style)
                c_tr10 = Text(f"{opt.c_tr10:.2f}", style=row_style)
                c_tr25 = Text(f"{opt.c_tr25:.2f}", style=row_style)
                c_tr50 = Text(f"{opt.c_tr50:.2f}", style=row_style)
                c_tr100 = Text(f"{opt.c_tr100:.2f}", style=row_style)
            else:
                val_text = Text(
                    f"{opt.value:.2f}" if state.value_label == "C" else str(int(opt.value)),
                    style=row_style
                )
        else:
            idx_text = Text(str(opt.index + 1), style=p.muted)
            cat_text = Text(opt.category[:15])
            desc_text = Text(opt.description[:22])

            if is_cn_with_soil:
                cn_a = Text(str(opt.cn_a), style=p.number)
                cn_b = Text(str(opt.cn_b), style=p.number)
                cn_c = Text(str(opt.cn_c), style=p.number)
                cn_d = Text(str(opt.cn_d), style=p.number)
            elif is_c_with_tr:
                # Tr2 con color de número (elegible), otros en gris
                c_tr2 = Text(f"{opt.c_tr2:.2f}", style=f"bold {p.accent}")
                c_tr5 = Text(f"{opt.c_tr5:.2f}", style=p.muted)
                c_tr10 = Text(f"{opt.c_tr10:.2f}", style=p.muted)
                c_tr25 = Text(f"{opt.c_tr25:.2f}", style=p.muted)
                c_tr50 = Text(f"{opt.c_tr50:.2f}", style=p.muted)
                c_tr100 = Text(f"{opt.c_tr100:.2f}", style=p.muted)
            else:
                val_text = Text(
                    f"{opt.value:.2f}" if state.value_label == "C" else str(int(opt.value)),
                    style=p.number
                )

        if is_cn_with_soil:
            table.add_row(idx_text, cat_text, desc_text, cn_a, cn_b, cn_c, cn_d)
        elif is_c_with_tr:
            table.add_row(idx_text, cat_text, desc_text, c_tr2, c_tr5, c_tr10, c_tr25, c_tr50, c_tr100)
        else:
            table.add_row(idx_text, cat_text, desc_text, val_text)

    return table


def build_assignments_table(state: CoverageViewerState) -> Optional[Table]:
    """Construye la tabla de asignaciones realizadas."""
    if not state.assignments:
        return None

    p = get_palette()

    table = Table(
        title="Asignaciones",
        title_style=f"bold {p.success}",
        border_style=p.border if state.focus_assignments else p.muted,
        header_style=f"bold {p.secondary}",
        box=box.ROUNDED,
        show_header=True,
        padding=(0, 1),
    )

    table.add_column("#", justify="right", width=3)
    table.add_column("Cobertura", justify="left", max_width=25)
    table.add_column(state.value_label, justify="right", width=6)
    table.add_column("Área (ha)", justify="right", width=10)
    table.add_column("Nota", justify="left", max_width=30)

    for idx, assign in enumerate(state.assignments):
        is_selected = state.focus_assignments and idx == state.selected_assignment_idx

        # Construir descripción de cobertura
        cov_desc = f"{assign.category}: {assign.description[:15]}"
        if assign.soil_group:
            cov_desc += f" [{assign.soil_group}]"

        if is_selected:
            row_style = f"bold reverse {p.primary}"
            idx_text = Text(f">{idx + 1}", style=row_style)
            cov_text = Text(cov_desc[:25], style=row_style)
            val_text = Text(
                f"{assign.value:.2f}" if state.value_label == "C" else str(int(assign.value)),
                style=row_style
            )
            area_text = Text(f"{assign.area:.2f}", style=row_style)
            note_text = Text(assign.note[:30] if assign.note else "-", style=row_style)
        else:
            idx_text = Text(str(idx + 1), style=p.muted)
            cov_text = Text(cov_desc[:25], style=p.success)
            val_text = Text(
                f"{assign.value:.2f}" if state.value_label == "C" else str(int(assign.value)),
                style=f"bold {p.number}"
            )
            area_text = Text(f"{assign.area:.2f}", style=f"bold {p.accent}")
            note_text = Text(assign.note[:30] if assign.note else "-", style=p.muted)

        table.add_row(idx_text, cov_text, val_text, area_text, note_text)

    return table


def build_status_panel(state: CoverageViewerState) -> Panel:
    """Construye el panel de estado."""
    p = get_palette()

    text = Text()
    text.append("  Área total: ", style=p.muted)
    text.append(f"{state.total_area:.2f} ha", style=f"bold {p.primary}")
    text.append("  │  Asignada: ", style=p.muted)
    text.append(
        f"{state.area_assigned:.2f} ha",
        style=f"bold {p.success}" if state.area_assigned > 0 else p.muted
    )
    text.append("  │  Restante: ", style=p.muted)

    remaining = state.area_remaining
    if remaining < 0.001:
        text.append("0.00 ha", style=f"bold {p.success}")
    else:
        text.append(f"{remaining:.2f} ha", style=f"bold {p.accent}")

    # Mostrar valor ponderado si hay asignaciones
    weighted = state.weighted_value()
    if weighted is not None:
        text.append("  │  ", style=p.muted)
        text.append(f"{state.value_label} ponderado: ", style=p.muted)
        if state.value_label == "C":
            text.append(f"{weighted:.3f}", style=f"bold {p.accent}")
        else:
            text.append(f"{int(round(weighted))}", style=f"bold {p.accent}")

    return Panel(text, border_style=p.border, padding=(0, 1))


def build_coverage_form(state: CoverageViewerState, opt: CoverageOption) -> Panel:
    """Construye el formulario popup para agregar cobertura."""
    p = get_palette()
    form = state.form_state
    is_cn = state.value_label == "CN" and opt.has_soil_groups

    content = Text()

    # Header con cobertura seleccionada
    content.append("\n  Cobertura: ", style=f"bold {p.secondary}")
    content.append(f"{opt.category}", style=f"bold {p.primary}")
    content.append(" - ", style=p.muted)
    content.append(f"{opt.description}\n", style=p.input_text)

    # Mostrar CN para el grupo seleccionado si es CN
    if is_cn:
        cn_val = getattr(opt, f"cn_{form.soil_group.lower()}", opt.value)
        content.append(f"  {state.value_label} ", style=f"bold {p.secondary}")
        content.append(f"(Suelo {form.soil_group})", style=p.muted)
        content.append(": ", style=p.muted)
        content.append(f"{cn_val}\n", style=f"bold {p.accent}")

    content.append("\n")

    # Campo: Área
    is_area_active = form.active_field == 0
    if is_area_active:
        content.append("  > ", style=f"bold {p.accent}")
    else:
        content.append("    ", style="")
    content.append("Área ", style=f"bold {p.primary}" if is_area_active else p.muted)
    content.append("(ha)", style=f"{p.muted}")
    content.append(": ", style=p.muted)
    content.append(form.area if form.area else "", style=f"bold {p.accent}" if is_area_active else p.input_text)
    if is_area_active:
        content.append("_", style=f"blink bold {p.accent}")
    content.append(f"  (máx: ", style=p.muted)
    content.append(f"{state.area_remaining:.2f}", style=f"{p.number}")
    content.append(")", style=p.muted)
    content.append("\n")

    # Campo: Nota (opcional)
    is_note_active = form.active_field == 1
    if is_note_active:
        content.append("  > ", style=f"bold {p.accent}")
    else:
        content.append("    ", style="")
    content.append("Nota", style=f"bold {p.primary}" if is_note_active else p.muted)
    content.append(": ", style=p.muted)
    if form.note:
        content.append(form.note, style=f"bold {p.accent}" if is_note_active else p.input_text)
    else:
        content.append("(opcional)", style=p.muted)
    if is_note_active:
        content.append("_", style=f"blink bold {p.accent}")
    content.append("\n")

    # Campo: Tipo de suelo (solo CN)
    if is_cn:
        is_soil_active = form.active_field == 2
        if is_soil_active:
            content.append("  > ", style=f"bold {p.accent}")
        else:
            content.append("    ", style="")
        content.append("Tipo de suelo", style=f"bold {p.primary}" if is_soil_active else p.muted)
        content.append(":  ", style=p.muted)

        for sg in ["A", "B", "C", "D"]:
            if sg == form.soil_group:
                content.append(f" {sg} ", style=f"bold reverse {p.success}")
            else:
                content.append(f" {sg} ", style=f"{p.muted}" if not is_soil_active else "dim white")
            content.append(" ", style="")

        # Mostrar valores CN de referencia con colores
        content.append(" (", style=p.muted)
        for i, sg in enumerate(["A", "B", "C", "D"]):
            if i > 0:
                content.append(" ", style="")
            cn = getattr(opt, f"cn_{sg.lower()}")
            if sg == form.soil_group:
                content.append(f"{sg}=", style=f"bold {p.secondary}")
                content.append(f"{cn}", style=f"bold {p.accent}")
            else:
                content.append(f"{sg}={cn}", style=p.muted)
        content.append(")", style=p.muted)
        content.append("\n")

    content.append("\n")

    # Ayuda de navegación
    content.append("  [", style=p.muted)
    content.append("↑↓", style=f"bold {p.primary}")
    content.append("] Campo  ", style=p.muted)
    if is_cn and form.active_field == 2:
        content.append("[", style=p.muted)
        content.append("←→", style=f"bold {p.primary}")
        content.append("] Suelo  ", style=p.muted)
    content.append("[", style=p.muted)
    content.append("Enter", style=f"bold {p.success}")
    content.append("] Confirmar  ", style=p.muted)
    content.append("[", style=p.muted)
    content.append("Esc", style=f"bold {p.error}")
    content.append("] Cancelar\n", style=p.muted)

    return Panel(
        content,
        title=f"[bold {p.success}] Agregar Cobertura [/]",
        border_style=p.success,
        box=box.DOUBLE,
        padding=(0, 1),
        width=70,
    )


def build_nav_text(state: CoverageViewerState) -> Text:
    """Construye el texto de navegación."""
    p = get_palette()
    nav = Text()

    if state.mode == "navigate":
        nav.append("  [", style=p.muted)
        nav.append("↑↓", style=f"bold {p.primary}")
        nav.append("] Navegar  ", style=p.muted)

        if not state.focus_assignments:
            # En tabla de opciones
            nav.append("[", style=p.muted)
            nav.append("Enter", style=f"bold {p.primary}")
            nav.append("] Asignar  ", style=p.muted)
            nav.append("[", style=p.muted)
            nav.append("Espacio", style=f"bold {p.primary}")
            nav.append("] Área restante  ", style=p.muted)
        else:
            # En tabla de asignaciones
            nav.append("[", style=p.muted)
            nav.append("e", style=f"bold {p.primary}")
            nav.append("] Editar nota  ", style=p.muted)
            nav.append("[", style=p.muted)
            nav.append("d", style=f"bold {p.primary}")
            nav.append("] Eliminar  ", style=p.muted)

        if state.assignments:
            nav.append("[", style=p.muted)
            nav.append("Tab", style=f"bold {p.primary}")
            nav.append("] Cambiar tabla  ", style=p.muted)

        nav.append("[", style=p.muted)
        nav.append("q", style=f"bold {p.primary}")
        nav.append("] Terminar", style=p.muted)

    elif state.mode == "input_area":
        nav.append("  Ingresa área (ha): ", style=f"bold {p.accent}")
        nav.append(state.input_buffer, style=f"bold {p.input_text}")
        nav.append("_", style=f"blink bold {p.input_text}")
        nav.append("  [", style=p.muted)
        nav.append("Enter", style=f"bold {p.nav_confirm}")
        nav.append("] Confirmar  [", style=p.muted)
        nav.append("Esc", style=f"bold {p.nav_cancel}")
        nav.append("] Cancelar", style=p.muted)

    elif state.mode == "input_desc":
        nav.append("  Nota (opcional): ", style=f"bold {p.accent}")
        nav.append(state.input_buffer, style=f"bold {p.input_text}")
        nav.append("_", style=f"blink bold {p.input_text}")
        nav.append("  [", style=p.muted)
        nav.append("Enter", style=f"bold {p.nav_confirm}")
        nav.append("] Confirmar  [", style=p.muted)
        nav.append("Esc", style=f"bold {p.nav_cancel}")
        nav.append("] Cancelar", style=p.muted)

    elif state.mode == "select_soil":
        nav.append("  Selecciona grupo de suelo: ", style=f"bold {p.accent}")
        for i, sg in enumerate(state.soil_groups):
            if i > 0:
                nav.append("  ", style=p.muted)
            nav.append(f"[{sg}]", style=f"bold {p.nav_key}")
        nav.append("  [", style=p.muted)
        nav.append("Esc", style=f"bold {p.nav_cancel}")
        nav.append("] Cancelar", style=p.muted)

    elif state.mode == "edit_note":
        nav.append("  Editar nota: ", style=f"bold {p.accent}")
        nav.append(state.input_buffer, style=f"bold {p.input_text}")
        nav.append("_", style=f"blink bold {p.input_text}")
        nav.append("  [", style=p.muted)
        nav.append("Enter", style=f"bold {p.nav_confirm}")
        nav.append("] Confirmar  [", style=p.muted)
        nav.append("Esc", style=f"bold {p.nav_cancel}")
        nav.append("] Cancelar", style=p.muted)

    return nav


def build_message_text(state: CoverageViewerState) -> Text:
    """Construye el texto de mensaje."""
    p = get_palette()
    if not state.message:
        return Text("")

    # Determinar estilo según contenido
    if "Error" in state.message or "inválido" in state.message.lower():
        style = f"bold {p.error}"
    elif "Asignado" in state.message or "agregó" in state.message or "Agregado" in state.message:
        style = f"bold {p.success}"
    else:
        style = p.info

    return Text(f"  {state.message}", style=style)


def build_display(state: CoverageViewerState, max_visible_rows: int = 15) -> Group:
    """Construye el display completo."""
    p = get_palette()

    # Header
    header = Text()
    header.append(f"  Asignación de Coberturas - {state.value_label}", style=f"bold {p.secondary}")
    n_assigned = len(state.assignments)
    if n_assigned > 0:
        header.append(f" ({n_assigned} asignaciones)", style=p.muted)

    options_table = build_options_table(state, max_visible_rows)
    assignments_table = build_assignments_table(state)
    status = build_status_panel(state)
    nav = build_nav_text(state)
    msg = build_message_text(state)

    elements = [
        Text(""),
        header,
        Text(""),
        options_table,
    ]

    if assignments_table:
        elements.append(Text(""))
        elements.append(assignments_table)

    elements.extend([
        Text(""),
        status,
        msg,
    ])

    # Mostrar formulario si está en modo form
    if state.mode == "form" and state.form_state:
        opt = state.options[state.selected_idx]
        elements.append(Text(""))
        elements.append(build_coverage_form(state, opt))
    else:
        elements.append(nav)

    return Group(*elements)


# Alias para compatibilidad
@dataclass
class CoverageRow(CoverageOption):
    """Alias de CoverageOption para compatibilidad."""
    pass


def interactive_coverage_viewer(
    rows: List[CoverageOption],
    total_area: float,
    value_label: str,
    table_name: str,
    on_get_cn_for_soil: Optional[Callable[[int, str], int]] = None,
    max_visible_rows: int = 15,
) -> Optional[List[dict]]:
    """
    Visor interactivo para asignación de coberturas.

    Args:
        rows: Lista de CoverageOption con las opciones de cobertura
        total_area: Área total a asignar (ha)
        value_label: "C" o "CN"
        table_name: Nombre de la tabla de referencia
        on_get_cn_for_soil: Callback para obtener CN según grupo de suelo (solo CN)
        max_visible_rows: Máximo de filas visibles

    Returns:
        Lista de diccionarios con las asignaciones, o None si cancela
    """
    console = get_console()
    from rich.live import Live

    state = CoverageViewerState(
        options=rows,
        assignments=[],
        total_area=total_area,
        value_label=value_label,
        table_name=table_name,
    )

    # Para CN, necesitamos seleccionar grupo de suelo primero
    is_cn = value_label == "CN"
    pending_area: Optional[float] = None

    clear_screen()

    with Live(console=console, auto_refresh=False, screen=False) as live:
        display = build_display(state, max_visible_rows)
        live.update(display, refresh=True)

        while True:
            key = get_key()
            n_options = len(state.options)
            n_assignments = len(state.assignments)

            # Modo selección de grupo de suelo (solo CN)
            if state.mode == "select_soil":
                soil_selected = None
                if key in ('a', 'A'):
                    soil_selected = "A"
                elif key in ('b', 'B'):
                    soil_selected = "B"
                elif key in ('c', 'C'):
                    soil_selected = "C"
                elif key in ('d', 'D'):
                    soil_selected = "D"
                elif key == 'esc':
                    state.mode = "input_desc"  # Volver a pedir nota
                    state.message = ""
                    pending_area = None

                if soil_selected:
                    opt = state.options[state.selected_idx]
                    cn_value = on_get_cn_for_soil(opt.index, soil_selected) if on_get_cn_for_soil else opt.value

                    # Crear asignación
                    assignment = CoverageAssignment(
                        option_index=opt.index,
                        category=opt.category,
                        description=opt.description,
                        value=cn_value,
                        area=pending_area,
                        note=state.input_buffer,
                        soil_group=soil_selected,
                    )
                    state.assignments.append(assignment)
                    state.message = f"Agregado: {pending_area:.2f} ha de {opt.category} (Suelo {soil_selected}, CN={int(cn_value)})"
                    state.mode = "navigate"
                    state.input_buffer = ""
                    pending_area = None

            # Modo formulario para agregar cobertura
            elif state.mode == "form" and state.form_state:
                form = state.form_state
                opt = state.options[state.selected_idx]
                is_cn_form = form.is_cn
                max_field = 2 if is_cn_form else 1

                if key == 'esc':
                    state.mode = "navigate"
                    state.form_state = None
                    state.message = "Cancelado"

                elif key == 'up':
                    form.active_field = (form.active_field - 1) % (max_field + 1)

                elif key == 'down':
                    form.active_field = (form.active_field + 1) % (max_field + 1)

                elif key == 'left' and is_cn_form and form.active_field == 2:
                    # Cambiar grupo de suelo
                    soil_list = ["A", "B", "C", "D"]
                    idx = soil_list.index(form.soil_group)
                    form.soil_group = soil_list[(idx - 1) % 4]

                elif key == 'right' and is_cn_form and form.active_field == 2:
                    # Cambiar grupo de suelo
                    soil_list = ["A", "B", "C", "D"]
                    idx = soil_list.index(form.soil_group)
                    form.soil_group = soil_list[(idx + 1) % 4]

                elif key == 'enter':
                    # Validar y crear asignación
                    try:
                        area = float(form.area) if form.area else 0
                        if area <= 0:
                            state.message = "Error: El área debe ser mayor a 0"
                        elif area > state.area_remaining + 0.001:
                            state.message = f"Error: Máximo disponible {state.area_remaining:.2f} ha"
                        else:
                            # Crear asignación
                            if is_cn_form:
                                cn_value = on_get_cn_for_soil(opt.index, form.soil_group) if on_get_cn_for_soil else opt.value
                                assignment = CoverageAssignment(
                                    option_index=opt.index,
                                    category=opt.category,
                                    description=opt.description,
                                    value=cn_value,
                                    area=min(area, state.area_remaining),
                                    note=form.note,
                                    soil_group=form.soil_group,
                                )
                                state.message = f"Agregado: {area:.2f} ha de {opt.category} (Suelo {form.soil_group}, CN={int(cn_value)})"
                            else:
                                assignment = CoverageAssignment(
                                    option_index=opt.index,
                                    category=opt.category,
                                    description=opt.description,
                                    value=opt.value,
                                    area=min(area, state.area_remaining),
                                    note=form.note,
                                )
                                state.message = f"Agregado: {area:.2f} ha de {opt.category}"

                            state.assignments.append(assignment)
                            state.mode = "navigate"
                            state.form_state = None
                    except ValueError:
                        state.message = "Error: Valor de área inválido"

                elif key == 'backspace':
                    if form.active_field == 0:
                        form.area = form.area[:-1]
                    elif form.active_field == 1:
                        form.note = form.note[:-1]

                elif isinstance(key, str) and len(key) == 1:
                    if form.active_field == 0 and (key.isdigit() or key == '.'):
                        form.area += key
                    elif form.active_field == 1 and key.isprintable():
                        form.note += key
                    elif form.active_field == 2 and key.upper() in "ABCD":
                        form.soil_group = key.upper()

            # Modo input de área (legacy)
            elif state.mode == "input_area":
                if key == 'enter':
                    try:
                        area = float(state.input_buffer)
                        if area <= 0:
                            state.message = "Error: El área debe ser mayor a 0"
                            state.input_buffer = ""
                        elif area > state.area_remaining + 0.001:
                            state.message = f"Error: Máximo disponible {state.area_remaining:.2f} ha"
                            state.input_buffer = ""
                        else:
                            pending_area = min(area, state.area_remaining)
                            state.mode = "input_desc"
                            state.input_buffer = ""
                            state.message = ""
                    except ValueError:
                        state.message = "Error: Valor inválido"
                        state.input_buffer = ""
                elif key == 'esc':
                    state.mode = "navigate"
                    state.input_buffer = ""
                    state.message = "Cancelado"
                elif key == 'backspace':
                    state.input_buffer = state.input_buffer[:-1]
                elif isinstance(key, str) and (key.isdigit() or key == '.'):
                    state.input_buffer += key

            # Modo input de descripción/nota
            elif state.mode == "input_desc":
                if key == 'enter':
                    if is_cn:
                        # Para CN, ir a selección de suelo
                        state.mode = "select_soil"
                        state.message = ""
                    else:
                        # Para C, crear asignación directamente
                        opt = state.options[state.selected_idx]
                        assignment = CoverageAssignment(
                            option_index=opt.index,
                            category=opt.category,
                            description=opt.description,
                            value=opt.value,
                            area=pending_area,
                            note=state.input_buffer,
                        )
                        state.assignments.append(assignment)
                        state.message = f"Agregado: {pending_area:.2f} ha de {opt.category}"
                        state.mode = "navigate"
                        state.input_buffer = ""
                        pending_area = None
                elif key == 'esc':
                    state.mode = "navigate"
                    state.input_buffer = ""
                    state.message = "Cancelado"
                    pending_area = None
                elif key == 'backspace':
                    state.input_buffer = state.input_buffer[:-1]
                elif isinstance(key, str) and len(key) == 1 and key.isprintable():
                    state.input_buffer += key

            # Modo input de edición de nota existente
            elif state.mode == "edit_note":
                if key == 'enter':
                    if state.focus_assignments and 0 <= state.selected_assignment_idx < n_assignments:
                        state.assignments[state.selected_assignment_idx].note = state.input_buffer
                        state.message = "Nota actualizada"
                    state.mode = "navigate"
                    state.input_buffer = ""
                elif key == 'esc':
                    state.mode = "navigate"
                    state.input_buffer = ""
                    state.message = "Cancelado"
                elif key == 'backspace':
                    state.input_buffer = state.input_buffer[:-1]
                elif isinstance(key, str) and len(key) == 1 and key.isprintable():
                    state.input_buffer += key

            # Modo navegación normal
            elif state.mode == "navigate":
                if key == 'q' or key == 'esc':
                    break

                elif key == 'up':
                    state.message = ""
                    if state.focus_assignments:
                        if n_assignments > 0:
                            state.selected_assignment_idx = (state.selected_assignment_idx - 1) % n_assignments
                    else:
                        state.selected_idx = (state.selected_idx - 1) % n_options

                elif key == 'down':
                    state.message = ""
                    if state.focus_assignments:
                        if n_assignments > 0:
                            state.selected_assignment_idx = (state.selected_assignment_idx + 1) % n_assignments
                    else:
                        state.selected_idx = (state.selected_idx + 1) % n_options

                elif key == 'tab' or key == '\t':
                    # Cambiar entre tablas
                    if state.assignments:
                        state.focus_assignments = not state.focus_assignments
                        if state.focus_assignments and state.selected_assignment_idx < 0:
                            state.selected_assignment_idx = 0
                        state.message = ""

                elif key == 'enter' and not state.focus_assignments:
                    if state.area_remaining < 0.001:
                        state.message = "No hay área restante para asignar"
                    else:
                        # Abrir formulario de cobertura
                        opt = state.options[state.selected_idx]
                        state.form_state = CoverageFormState(
                            is_cn=state.value_label == "CN" and opt.has_soil_groups
                        )
                        state.mode = "form"
                        state.message = ""

                elif key == 'space' and not state.focus_assignments:
                    if state.area_remaining < 0.001:
                        state.message = "No hay área restante para asignar"
                    else:
                        # Abrir formulario con área pre-llenada
                        opt = state.options[state.selected_idx]
                        state.form_state = CoverageFormState(
                            area=f"{state.area_remaining:.2f}",
                            is_cn=state.value_label == "CN" and opt.has_soil_groups
                        )
                        state.mode = "form"
                        state.message = ""

                elif key == 'e' and state.focus_assignments:
                    if 0 <= state.selected_assignment_idx < n_assignments:
                        state.mode = "edit_note"
                        state.input_buffer = state.assignments[state.selected_assignment_idx].note
                        state.message = ""

                elif key == 'd' and state.focus_assignments:
                    if 0 <= state.selected_assignment_idx < n_assignments:
                        removed = state.assignments.pop(state.selected_assignment_idx)
                        state.message = f"Eliminada asignación de {removed.area:.2f} ha"
                        # Ajustar índice
                        if state.selected_assignment_idx >= len(state.assignments):
                            state.selected_assignment_idx = max(0, len(state.assignments) - 1)
                        if not state.assignments:
                            state.focus_assignments = False
                            state.selected_assignment_idx = -1

            # Actualizar display
            display = build_display(state, max_visible_rows)
            live.update(display, refresh=True)

    clear_screen()

    # Retornar resultados
    if not state.assignments:
        return None

    results = []
    for assign in state.assignments:
        result = {
            "area": assign.area,
            "table_index": assign.option_index,
            "description": _build_description(assign),
            "c_val": assign.value,  # Usado para C y CN
        }
        if state.value_label == "CN":
            result["soil_group"] = assign.soil_group
        results.append(result)

    return results


def _build_description(assign: CoverageAssignment) -> str:
    """Construye la descripción completa de una asignación."""
    base = f"{assign.category}: {assign.description}"
    if assign.note:
        base += f" [{assign.note}]"
    if assign.soil_group:
        base += f" (Suelo {assign.soil_group})"
    return base
