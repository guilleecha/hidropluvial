"""
Modelos de datos para el formulario interactivo.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, List, Any, Union
from enum import Enum


class FieldType(Enum):
    """Tipos de campo disponibles."""
    TEXT = "text"
    FLOAT = "float"
    INT = "int"
    SELECT = "select"
    CHECKBOX = "checkbox"


class FieldStatus(Enum):
    """Estado de un campo."""
    EMPTY = "empty"
    FILLED = "filled"
    INVALID = "invalid"
    OPTIONAL = "optional"


class FormResult:
    """Resultado de un formulario interactivo."""
    COMPLETED = "completed"  # Formulario completado
    BACK = "back"  # Usuario quiere volver al paso anterior
    CANCEL = "cancel"  # Usuario canceló
    RELOAD = "reload"  # Recargar el formulario (después de cambios externos)


@dataclass
class FormField:
    """Definición de un campo del formulario."""
    key: str
    label: str
    field_type: FieldType = FieldType.TEXT
    required: bool = True
    default: Any = None
    options: List[dict] = field(default_factory=list)  # Para SELECT/CHECKBOX
    unit: str = ""  # Unidad (ej: "ha", "m", "%")
    hint: str = ""  # Ayuda/sugerencia
    validator: Optional[Callable[[Any], Union[bool, str]]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    # Campo condicional: se habilita solo si depends_on tiene cierto valor
    depends_on: Optional[str] = None  # Key del campo padre
    depends_value: Any = None  # Valor que debe tener el padre para habilitarse
    disabled_hint: str = ""  # Mensaje a mostrar cuando está deshabilitado
    # Callback para edición especial (ej: mostrar submenú)
    on_edit: Optional[Callable[["FormField", "FormState"], Any]] = None
    # Estado actual
    value: Any = None
    status: FieldStatus = FieldStatus.EMPTY
    disabled: bool = False  # Se calcula dinámicamente


@dataclass
class FormState:
    """Estado del formulario."""
    title: str
    fields: List[FormField]
    selected_idx: int = 0
    mode: str = "navigate"  # "navigate", "edit_text", "edit_select", "popup", "confirm_cancel", "popup_confirm", "popup_submenu", "popup_inline_input", "popup_nrcs_calculator"
    input_buffer: str = ""
    message: str = ""
    select_idx: int = 0  # Para modo select
    popup_field: Optional[FormField] = None  # Campo actual en modo popup
    popup_options: List[dict] = field(default_factory=list)  # Opciones del popup
    popup_idx: int = 0  # Índice seleccionado en popup
    # Para confirmación inline dentro del popup
    pending_check_opt: Optional[dict] = None  # Opción pendiente de confirmar
    confirm_default: bool = True  # Default para confirmación
    # Para submenú dentro del popup (popup_submenu)
    submenu_options: List[dict] = field(default_factory=list)  # Opciones del submenú
    submenu_idx: int = 0  # Índice en submenú
    submenu_title: str = ""  # Título del submenú
    submenu_parent_idx: int = 0  # Índice padre para volver
    submenu_callback: Optional[Callable[[dict], Any]] = None  # Callback al seleccionar
    # Para entrada inline dentro del popup (popup_inline_input)
    inline_input_label: str = ""  # Label del campo
    inline_input_type: str = "float"  # "float", "int", "text"
    inline_input_hint: str = ""  # Ayuda/sugerencia
    inline_input_callback: Optional[Callable[[Any], Any]] = None  # Callback al confirmar
    inline_input_fields: List[dict] = field(default_factory=list)  # Campos del formulario inline
    inline_input_idx: int = 0  # Campo actual del formulario inline
    # Para calculadora NRCS (popup_nrcs_calculator)
    nrcs_segments: List[Any] = field(default_factory=list)  # Segmentos de flujo
    nrcs_p2_mm: float = 50.0  # Precipitación P2
    nrcs_selected_idx: int = 0  # Índice de segmento seleccionado
    nrcs_basin: Any = None  # Referencia a la cuenca
    nrcs_callback: Optional[Callable[[dict], Any]] = None  # Callback al confirmar
    nrcs_message: str = ""  # Mensaje de estado
    # Para calculadora bimodal (popup_bimodal_calculator)
    bimodal_selected_idx: int = 0  # Índice de opción seleccionada
    bimodal_callback: Optional[Callable[[dict], Any]] = None  # Callback al confirmar

    def get_field(self, key: str) -> Optional[FormField]:
        """Obtiene un campo por su key."""
        for f in self.fields:
            if f.key == key:
                return f
        return None

    def get_values(self) -> dict:
        """Retorna diccionario con todos los valores."""
        return {f.key: f.value for f in self.fields}

    def is_complete(self) -> bool:
        """Verifica si todos los campos requeridos están completos."""
        for f in self.fields:
            # Skip disabled fields (they're not required when disabled)
            if f.disabled:
                continue
            if f.required and f.status != FieldStatus.FILLED:
                return False
        return True

    def next_enabled_field(self, current_idx: int) -> int:
        """Encuentra el siguiente campo habilitado."""
        n = len(self.fields)
        for i in range(1, n + 1):
            next_idx = (current_idx + i) % n
            if not self.fields[next_idx].disabled:
                return next_idx
        return current_idx  # Fallback

    def prev_enabled_field(self, current_idx: int) -> int:
        """Encuentra el campo habilitado anterior."""
        n = len(self.fields)
        for i in range(1, n + 1):
            prev_idx = (current_idx - i) % n
            if not self.fields[prev_idx].disabled:
                return prev_idx
        return current_idx  # Fallback

    def ensure_valid_selection(self) -> None:
        """Asegura que el campo seleccionado esté habilitado."""
        if self.fields[self.selected_idx].disabled:
            self.selected_idx = self.next_enabled_field(self.selected_idx)

    def count_filled(self) -> tuple[int, int]:
        """Retorna (campos_llenos, campos_requeridos)."""
        filled = sum(1 for f in self.fields if f.status == FieldStatus.FILLED and not f.disabled)
        required = sum(1 for f in self.fields if f.required and not f.disabled)
        return filled, required

    def update_dependencies(self) -> None:
        """Actualiza el estado disabled de campos según sus dependencias."""
        for fld in self.fields:
            if fld.depends_on:
                parent = self.get_field(fld.depends_on)
                if parent:
                    # depends_value puede ser un valor único o una lista de valores
                    depends_values = fld.depends_value if isinstance(fld.depends_value, list) else [fld.depends_value]

                    # Para checkbox, verificar si algún valor requerido está en la lista
                    if parent.field_type == FieldType.CHECKBOX:
                        parent_values = parent.value if isinstance(parent.value, list) else []
                        # Habilitado si ANY de depends_values está en parent_values
                        fld.disabled = not any(dv in parent_values for dv in depends_values)
                    else:
                        # Para otros tipos, verificar si parent.value está en depends_values
                        fld.disabled = parent.value not in depends_values

                    # Si está disabled, limpiar valor y status
                    if fld.disabled:
                        # No limpiar, solo marcar como opcional si estaba requerido
                        if fld.status == FieldStatus.EMPTY and not fld.required:
                            fld.status = FieldStatus.OPTIONAL
