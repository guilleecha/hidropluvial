"""
Editor de parametros de cuenca usando formulario interactivo.

Separa edición de metadatos (nombre, notas) que NO invalidan análisis,
de parámetros físicos (área, pendiente, etc.) que SÍ los invalidan.
"""

from typing import Optional

from hidropluvial.cli.theme import (
    print_info, print_warning, print_success,
    get_console, get_palette,
)
from hidropluvial.cli.viewer.panel_input import panel_confirm
from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem
from hidropluvial.cli.viewer.form_viewer import (
    interactive_form,
    FormField,
    FieldType,
    FormResult,
)
from hidropluvial.cli.viewer.terminal import clear_screen
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import box


class CuencaEditor:
    """Editor para modificar parametros de una cuenca usando formulario interactivo."""

    # Campos que invalidan análisis si cambian
    PARAMS_THAT_INVALIDATE = {"area_ha", "slope_pct", "p3_10", "length_m", "c", "cn"}

    def __init__(self, basin, project_manager=None):
        """
        Inicializa el editor.

        Args:
            basin: Cuenca a editar
            project_manager: ProjectManager (opcional, para compatibilidad)
        """
        self.basin = basin
        self.project_manager = project_manager

    def edit(self) -> str:
        """
        Muestra menú para elegir qué editar.

        Returns:
            "modified" si se modificó la cuenca
            "cancelled" si se canceló
        """
        n_analyses = len(self.basin.analyses) if self.basin.analyses else 0

        items = [
            MenuItem(
                key="m",
                label="Editar metadatos",
                value="metadata",
                hint="Nombre, notas (no afecta análisis)",
            ),
            MenuItem(
                key="p",
                label="Editar parámetros físicos",
                value="params",
                hint=f"Área, pendiente, etc. (elimina {n_analyses} análisis)" if n_analyses else "Área, pendiente, P3,10...",
            ),
        ]

        choice = menu_panel(
            title=f"Editar Cuenca: {self.basin.name}",
            items=items,
            subtitle=f"{n_analyses} análisis" if n_analyses else "Sin análisis",
            allow_back=True,
        )

        if choice is None:
            return "cancelled"

        if choice == "metadata":
            return self._edit_metadata()
        elif choice == "params":
            return self._edit_params()

        return "cancelled"

    def _edit_metadata(self) -> str:
        """Edita metadatos sin afectar análisis."""
        clear_screen()

        fields = [
            FormField(
                key="name",
                label="Nombre de la cuenca",
                field_type=FieldType.TEXT,
                required=True,
                default=self.basin.name,
                hint="Identificador de la cuenca",
            ),
            FormField(
                key="notes",
                label="Notas",
                field_type=FieldType.TEXT,
                required=False,
                default=self.basin.notes or "",
                hint="Observaciones adicionales",
            ),
        ]

        result = interactive_form(
            title=f"Metadatos: {self.basin.name}",
            fields=fields,
            allow_back=True,
        )

        if result is None or result.get("_result") == FormResult.BACK:
            return "cancelled"

        # Aplicar cambios
        changed = False
        if result.get("name") and result["name"] != self.basin.name:
            self.basin.name = result["name"]
            changed = True

        new_notes = result.get("notes") or None
        if new_notes != self.basin.notes:
            self.basin.notes = new_notes
            changed = True

        if changed:
            print_success("Metadatos actualizados.")
            return "modified"
        else:
            print_info("No se realizaron cambios.")
            return "cancelled"

    def _edit_params(self) -> str:
        """Edita parámetros físicos (puede invalidar análisis)."""
        clear_screen()

        self._show_current_values()
        self._show_warnings()

        # Preguntar si quiere continuar
        if not self._confirm_edit():
            return "cancelled"

        # Mostrar formulario con datos precargados
        new_values = self._show_edit_form()
        if new_values is None:
            return "cancelled"

        # Verificar si hay cambios
        changes = self._get_changes(new_values)
        if not changes:
            print_info("No se realizaron cambios.")
            return "cancelled"

        # Mostrar resumen de cambios
        self._show_changes(changes)

        # Confirmar cambios
        if not panel_confirm(title="¿Aplicar estos cambios?", default=True):
            return "cancelled"

        # Aplicar cambios
        return self._apply_changes(new_values, changes)

    def _show_current_values(self) -> None:
        """Muestra los valores actuales de la cuenca en un panel."""
        console = get_console()
        p = get_palette()

        table = Table(
            show_header=False,
            box=None,
            padding=(0, 2),
            expand=True,
        )
        table.add_column("Label", style=p.label, width=20)
        table.add_column("Value")

        # Nombre
        table.add_row("Nombre", Text(self.basin.name, style=f"bold {p.primary}"))

        # Área
        area_text = Text()
        area_text.append(f"{self.basin.area_ha:.2f}", style=f"bold {p.number}")
        area_text.append(" ha", style=p.unit)
        table.add_row("Área", area_text)

        # Pendiente
        slope_text = Text()
        slope_text.append(f"{self.basin.slope_pct:.2f}", style=f"bold {p.number}")
        slope_text.append(" %", style=p.unit)
        table.add_row("Pendiente", slope_text)

        # P3,10
        p310_text = Text()
        p310_text.append(f"{self.basin.p3_10:.1f}", style=f"bold {p.number}")
        p310_text.append(" mm", style=p.unit)
        table.add_row("P(3h, Tr=10)", p310_text)

        # Longitud (opcional)
        if self.basin.length_m:
            len_text = Text()
            len_text.append(f"{self.basin.length_m:.0f}", style=f"bold {p.number}")
            len_text.append(" m", style=p.unit)
            table.add_row("Longitud cauce", len_text)
        else:
            table.add_row("Longitud cauce", Text("No definida", style=p.muted))

        # C y CN
        if self.basin.c:
            table.add_row("Coef. C", Text(f"{self.basin.c:.2f}", style=f"bold {p.number}"))
        if self.basin.cn:
            table.add_row("CN", Text(str(self.basin.cn), style=f"bold {p.number}"))

        title = Text(f"Editar cuenca: {self.basin.name}", style=f"bold {p.primary}")

        console.print()
        panel = Panel(
            table,
            title=title,
            title_align="left",
            border_style=p.primary,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        console.print(panel)

    def _show_warnings(self) -> None:
        """Muestra advertencias si hay analisis existentes."""
        n_analyses = len(self.basin.analyses) if self.basin.analyses else 0

        if n_analyses > 0:
            print_warning(f"Esta cuenca tiene {n_analyses} análisis que serán ELIMINADOS al modificar los datos.")

    def _confirm_edit(self) -> bool:
        """Confirma que el usuario quiere editar."""
        n_analyses = len(self.basin.analyses) if self.basin.analyses else 0

        if n_analyses > 0:
            return panel_confirm(
                title="¿Continuar con la edición?",
                message="Los análisis existentes serán eliminados",
                default=False,
            )
        return True

    def _show_edit_form(self) -> Optional[dict]:
        """Muestra el formulario de edición con datos precargados."""
        fields = [
            FormField(
                key="name",
                label="Nombre de la cuenca",
                field_type=FieldType.TEXT,
                required=True,
                default=self.basin.name,
                hint="Identificador único para esta cuenca",
            ),
            FormField(
                key="area_ha",
                label="Área",
                field_type=FieldType.FLOAT,
                required=True,
                unit="ha",
                default=self.basin.area_ha,
                min_value=0.01,
                max_value=10000,
                hint="Típico: 1-50 ha (urbano), 50-500 ha (subcuenca)",
            ),
            FormField(
                key="slope_pct",
                label="Pendiente media",
                field_type=FieldType.FLOAT,
                required=True,
                unit="%",
                default=self.basin.slope_pct,
                min_value=0.01,
                max_value=100,
                hint="Típico: 0.5-2% (llano), 2-5% (ondulado), >5% (pronunciado)",
            ),
            FormField(
                key="p3_10",
                label="Precipitación P(3h, Tr=10)",
                field_type=FieldType.FLOAT,
                required=True,
                unit="mm",
                default=self.basin.p3_10,
                min_value=1,
                max_value=500,
                hint="Consulta tabla IDF de DINAGUA. Montevideo: ~55mm",
            ),
            FormField(
                key="length_m",
                label="Longitud del cauce",
                field_type=FieldType.FLOAT,
                required=False,
                unit="m",
                default=self.basin.length_m if self.basin.length_m else None,
                min_value=1,
                max_value=100000,
                hint="Típico: 200-2000m (urbano), 1-10km (rural)",
            ),
            FormField(
                key="c",
                label="Coeficiente C (Racional)",
                field_type=FieldType.FLOAT,
                required=False,
                default=self.basin.c if self.basin.c else None,
                min_value=0.1,
                max_value=0.95,
                hint="Típico: 0.7-0.9 (urbano), 0.4-0.7 (residencial), 0.2-0.4 (rural)",
            ),
            FormField(
                key="cn",
                label="Número de Curva CN (SCS)",
                field_type=FieldType.INT,
                required=False,
                default=self.basin.cn if self.basin.cn else None,
                min_value=30,
                max_value=98,
                hint="Típico: 85-95 (urbano), 70-85 (residencial), 55-70 (bosque)",
            ),
        ]

        result = interactive_form(
            title=f"Editar: {self.basin.name}",
            fields=fields,
            allow_back=True,
        )

        if result is None:
            return None

        if result.get("_result") == FormResult.BACK:
            return None

        return result

    def _get_changes(self, new_values: dict) -> dict:
        """Compara valores nuevos con actuales y retorna solo los cambios."""
        changes = {}

        # Comparar cada campo
        if new_values.get("name") != self.basin.name:
            changes["name"] = (self.basin.name, new_values.get("name"))

        if new_values.get("area_ha") != self.basin.area_ha:
            changes["area_ha"] = (self.basin.area_ha, new_values.get("area_ha"))

        if new_values.get("slope_pct") != self.basin.slope_pct:
            changes["slope_pct"] = (self.basin.slope_pct, new_values.get("slope_pct"))

        if new_values.get("p3_10") != self.basin.p3_10:
            changes["p3_10"] = (self.basin.p3_10, new_values.get("p3_10"))

        # Campos opcionales
        new_length = new_values.get("length_m")
        if new_length != self.basin.length_m:
            changes["length_m"] = (self.basin.length_m, new_length)

        new_c = new_values.get("c")
        if new_c != self.basin.c:
            changes["c"] = (self.basin.c, new_c)

        new_cn = new_values.get("cn")
        if new_cn != self.basin.cn:
            changes["cn"] = (self.basin.cn, new_cn)

        return changes

    def _show_changes(self, changes: dict) -> None:
        """Muestra resumen de cambios a aplicar."""
        console = get_console()
        p = get_palette()

        table = Table(
            show_header=True,
            box=box.SIMPLE,
            padding=(0, 1),
        )
        table.add_column("Campo", style=p.label)
        table.add_column("Anterior", style=p.muted)
        table.add_column("→", style=p.muted, width=2)
        table.add_column("Nuevo", style=f"bold {p.number}")

        field_labels = {
            "name": "Nombre",
            "area_ha": "Área (ha)",
            "slope_pct": "Pendiente (%)",
            "p3_10": "P3,10 (mm)",
            "length_m": "Longitud (m)",
            "c": "Coef. C",
            "cn": "CN",
        }

        for key, (old, new) in changes.items():
            label = field_labels.get(key, key)
            old_str = self._format_value(old)
            new_str = self._format_value(new)
            table.add_row(label, old_str, "→", new_str)

        console.print()
        panel = Panel(
            table,
            title=Text("Cambios a aplicar", style=f"bold {p.secondary}"),
            title_align="left",
            border_style=p.secondary,
            box=box.ROUNDED,
            padding=(0, 1),
        )
        console.print(panel)

    def _format_value(self, value) -> str:
        """Formatea un valor para mostrar."""
        if value is None:
            return "-"
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    def _apply_changes(self, new_values: dict, changes: dict) -> str:
        """Aplica los cambios a la cuenca."""
        # Aplicar todos los valores nuevos
        if "area_ha" in new_values:
            self.basin.area_ha = new_values["area_ha"]
        if "slope_pct" in new_values:
            self.basin.slope_pct = new_values["slope_pct"]
        if "p3_10" in new_values:
            self.basin.p3_10 = new_values["p3_10"]

        # Campos opcionales
        self.basin.length_m = new_values.get("length_m")
        self.basin.c = new_values.get("c")
        self.basin.cn = new_values.get("cn")

        # Eliminar análisis si hay cambios en parámetros que los afectan
        if any(key in changes for key in self.PARAMS_THAT_INVALIDATE):
            n_deleted = len(self.basin.analyses) if self.basin.analyses else 0
            self.basin.analyses = []
            if n_deleted > 0:
                print_warning(f"Se eliminaron {n_deleted} análisis (parámetros cambiaron).")

        print_success("Cuenca actualizada correctamente.")
        return "modified"
