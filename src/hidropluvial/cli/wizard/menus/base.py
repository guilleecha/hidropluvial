"""
Clase base para menus del wizard.
"""

from abc import ABC, abstractmethod
from typing import Optional

import typer
import questionary

from hidropluvial.cli.wizard.styles import (
    WIZARD_STYLE,
    get_select_kwargs,
    get_checkbox_kwargs,
    get_confirm_kwargs,
    get_text_kwargs,
    back_choice,
    cancel_choice,
    menu_separator,
    get_icons,
)
from hidropluvial.project import get_project_manager, ProjectManager, Project, Basin
from hidropluvial.cli.theme import (
    print_header, print_section, print_success, print_warning,
    print_error, print_info, print_note, print_suggestion, print_basin_info, print_project_info,
)
from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem
from hidropluvial.cli.viewer.panel_input import (
    panel_select, panel_checkbox, panel_text, panel_confirm, PanelOption,
)


class BaseMenu(ABC):
    """Clase base abstracta para menus interactivos."""

    def __init__(self):
        self._manager: Optional[ProjectManager] = None

    @property
    def manager(self) -> ProjectManager:
        """Lazy loading del project manager."""
        if self._manager is None:
            self._manager = get_project_manager()
        return self._manager

    @property
    def style(self):
        """Estilo de questionary."""
        return WIZARD_STYLE

    @property
    def icons(self):
        """Iconos del tema."""
        return get_icons()

    @abstractmethod
    def show(self) -> None:
        """Muestra el menu. Debe ser implementado por subclases."""
        pass

    def echo(self, message: str) -> None:
        """Wrapper para typer.echo."""
        typer.echo(message)

    def header(self, title: str, subtitle: str = None) -> None:
        """Muestra un encabezado formateado con estilo."""
        print_header(title, subtitle)

    def section(self, title: str) -> None:
        """Muestra título de sección."""
        print_section(title)

    def success(self, message: str) -> None:
        """Muestra mensaje de éxito."""
        print_success(message)

    def warning(self, message: str) -> None:
        """Muestra advertencia."""
        print_warning(message)

    def error(self, message: str) -> None:
        """Muestra error."""
        print_error(message)

    def info(self, message: str) -> None:
        """Muestra información."""
        print_info(message)

    def note(self, message: str) -> None:
        """Muestra nota destacada."""
        print_note(message)

    def suggestion(self, message: str) -> None:
        """Muestra sugerencia/recomendación."""
        print_suggestion(message)

    def basin_info(self, basin, project_name: str = None) -> None:
        """Muestra información de cuenca en panel estilizado."""
        trs = None
        if hasattr(basin, 'analyses') and basin.analyses:
            trs = sorted(set(a.storm.return_period for a in basin.analyses))

        print_basin_info(
            basin_name=basin.name,
            basin_id=basin.id,
            project_name=project_name,
            area_ha=basin.area_ha,
            slope_pct=basin.slope_pct,
            n_analyses=len(basin.analyses) if hasattr(basin, 'analyses') else None,
            return_periods=trs,
            c=basin.c if hasattr(basin, 'c') else None,
            cn=basin.cn if hasattr(basin, 'cn') else None,
        )

    def project_info(self, project) -> None:
        """Muestra información de proyecto en panel estilizado."""
        n_analyses = sum(len(b.analyses) for b in project.basins) if project.basins else 0

        print_project_info(
            project_name=project.name,
            project_id=project.id,
            n_basins=len(project.basins) if project.basins else 0,
            n_analyses=n_analyses,
            description=project.description if hasattr(project, 'description') else None,
            author=project.author if hasattr(project, 'author') else None,
            location=project.location if hasattr(project, 'location') else None,
        )

    def select(self, message: str, choices: list[str]) -> Optional[str]:
        """Muestra un panel de selección con shortcuts de letras."""
        # Convertir choices a MenuItem
        items = []
        for idx, choice in enumerate(choices):
            # Detectar si es una opción especial
            if "Volver" in choice or "←" in choice:
                continue  # Se maneja con Esc
            elif "Cancelar" in choice:
                continue  # Se maneja con Esc
            elif choice.startswith("---") or choice.startswith("─"):
                items.append(MenuItem(key=f"sep{idx}", label="", separator=True))
            else:
                key = chr(ord('a') + len([i for i in items if not i.separator]))
                items.append(MenuItem(key=key, label=choice, value=choice))

        if not items:
            return None

        return menu_panel(
            title=message,
            items=items,
            allow_back=True,
        )

    def checkbox(self, message: str, choices: list) -> Optional[list]:
        """Muestra un panel de checkbox con shortcuts de letras."""
        # Convertir choices a PanelOption
        options = []
        for c in choices:
            if isinstance(c, dict):
                options.append(PanelOption(
                    label=c.get("name", str(c.get("value", ""))),
                    value=c.get("value"),
                    checked=c.get("checked", False),
                ))
            elif hasattr(c, 'title'):  # questionary.Choice
                options.append(PanelOption(
                    label=c.title,
                    value=c.title,
                    checked=getattr(c, 'checked', False),
                ))
            else:
                options.append(PanelOption(label=str(c), value=str(c)))

        return panel_checkbox(
            title=message,
            options=options,
        )

    def confirm(self, message: str, default: bool = True) -> bool:
        """Muestra panel de confirmación Sí/No."""
        result = panel_confirm(
            title=message,
            default=default,
        )
        return result if result is not None else False

    def text(self, message: str, default: str = "") -> Optional[str]:
        """Solicita texto con panel interactivo."""
        return panel_text(
            title=message,
            default=default,
        )

    def back_option(self, text: str = "Volver") -> str:
        """Genera texto para opción de volver."""
        return back_choice(text)

    def cancel_option(self, text: str = "Cancelar") -> str:
        """Genera texto para opción de cancelar."""
        return cancel_choice(text)

    def separator(self, text: str = "") -> questionary.Separator:
        """Crea un separador de menú."""
        return menu_separator(text)

    def ask_float(self, prompt: str, current: Optional[float]) -> Optional[float]:
        """Solicita un valor float, retorna None si no cambia."""
        default_str = f"{current:.2f}" if current else ""
        val = self.text(prompt, default=default_str)
        if val is None:
            return None
        val = val.strip()
        if val == "" or val == default_str:
            return None
        try:
            return float(val)
        except ValueError:
            self.echo(f"  Valor invalido, se mantiene {current}")
            return None

    def ask_int(self, prompt: str, current: Optional[int]) -> Optional[int]:
        """Solicita un valor int, retorna None si no cambia."""
        default_str = str(current) if current else ""
        val = self.text(prompt, default=default_str)
        if val is None:
            return None
        val = val.strip()
        if val == "" or val == default_str:
            return None
        try:
            return int(val)
        except ValueError:
            self.echo(f"  Valor invalido, se mantiene {current}")
            return None

    # ========================================================================
    # Métodos compartidos para operaciones de cuenca
    # ========================================================================

    def select_basin_from_project(
        self,
        project: Project,
        prompt: str = "Selecciona una cuenca:",
    ) -> Optional[Basin]:
        """
        Permite seleccionar una cuenca de un proyecto.

        Args:
            project: Proyecto del cual seleccionar
            prompt: Mensaje a mostrar

        Returns:
            Basin seleccionada o None si cancela
        """
        if not project.basins:
            self.echo("  No hay cuencas en este proyecto.")
            return None

        choices = []
        for b in project.basins:
            n_analyses = len(b.analyses) if b.analyses else 0
            choices.append(f"{b.id} - {b.name} ({n_analyses} análisis)")
        choices.append(self.cancel_option())

        choice = self.select(prompt, choices)

        if choice is None or "Cancelar" in choice:
            return None

        basin_id = choice.split(" - ")[0]
        return project.get_basin(basin_id)

    def add_basin_with_wizard(
        self,
        project: Project,
        show_post_menu: bool = True,
    ) -> Optional[tuple[Project, Basin]]:
        """
        Agrega una nueva cuenca a un proyecto.

        Args:
            project: Proyecto al que agregar la cuenca
            show_post_menu: Si mostrar el menú post-ejecución

        Returns:
            Tupla (proyecto_actualizado, nueva_cuenca) o None si cancela
        """
        from hidropluvial.cli.wizard.config import WizardConfig
        from hidropluvial.cli.wizard.runner import AnalysisRunner
        from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu

        self.section(f"Configurar cuenca en: {project.name}")

        config = WizardConfig.from_wizard()
        if config is None:
            return None

        config.print_summary()

        if not self.confirm("\n¿Ejecutar análisis?", default=True):
            return None

        self.header("EJECUTANDO ANÁLISIS")

        runner = AnalysisRunner(config, project_id=project.id)
        updated_project, basin = runner.run()

        self.echo(f"\n  Cuenca '{basin.name}' agregada al proyecto.\n")

        if show_post_menu:
            menu = PostExecutionMenu(
                updated_project, basin,
                config.c, config.cn, config.length_m
            )
            menu.show()

        return updated_project, basin

    def edit_basin_with_editor(
        self,
        basin: Basin,
        project_manager: Optional[ProjectManager] = None,
    ) -> str:
        """
        Edita una cuenca usando CuencaEditor.

        Args:
            basin: Cuenca a editar
            project_manager: ProjectManager a usar (opcional)

        Returns:
            Resultado del editor: "modified", "cancelled", etc.
        """
        from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor

        pm = project_manager or self.manager
        editor = CuencaEditor(basin, pm)
        return editor.edit()

    def delete_basin_from_project(
        self,
        basin: Basin,
        project: Project,
        project_manager: Optional[ProjectManager] = None,
    ) -> bool:
        """
        Elimina una cuenca de un proyecto con confirmación.

        Args:
            basin: Cuenca a eliminar
            project: Proyecto que contiene la cuenca
            project_manager: ProjectManager a usar (opcional)

        Returns:
            True si se eliminó, False si canceló o falló
        """
        msg = f"¿Eliminar cuenca '{basin.name}'"
        if basin.analyses:
            msg += f" y sus {len(basin.analyses)} análisis"
        msg += "?"

        if not self.confirm(msg, default=False):
            return False

        pm = project_manager or self.manager
        if pm.delete_basin(project, basin.id):
            self.echo(f"\n  Cuenca '{basin.name}' eliminada.\n")
            return True

        self.error("No se pudo eliminar la cuenca")
        return False


class SessionMenu(BaseMenu):
    """Menu que opera sobre una cuenca especifica."""

    def __init__(self, basin):
        super().__init__()
        from hidropluvial.models import Basin
        self._basin = basin

    @property
    def basin(self):
        """Basin object."""
        return self._basin

    def reload_session(self) -> None:
        """Recarga la cuenca desde el manager (no-op for now)."""
        # Basin objects are typically managed by project, so this is a no-op
        # Subclasses that need reloading should override this
        pass

    # ========================================================================
    # Callbacks reutilizables para visores interactivos
    # ========================================================================

    def _create_edit_note_callback(self, db=None):
        """
        Crea callback para editar nota de un análisis.

        Args:
            db: Database instance (opcional, se obtiene automáticamente)

        Returns:
            Función callback que recibe (analysis_id, current_note) -> str
        """
        from hidropluvial.database import get_database
        from hidropluvial.cli.viewer.terminal import clear_screen

        if db is None:
            db = get_database()

        def on_edit_note(analysis_id: str, current_note: str) -> str:
            clear_screen()
            print(f"\n  Editando nota del análisis {analysis_id[:8]}...\n")
            new_note = questionary.text(
                "Nueva nota (vacío para eliminar):",
                default=current_note or "",
                **get_text_kwargs(),
            ).ask()
            if new_note is not None:
                db.update_analysis_note(analysis_id, new_note if new_note else None)
                return new_note
            return None

        return on_edit_note

    def _create_delete_callback(self, db=None, confirm_prompt: bool = True):
        """
        Crea callback para eliminar un análisis.

        Args:
            db: Database instance (opcional, se obtiene automáticamente)
            confirm_prompt: Si mostrar confirmación antes de eliminar

        Returns:
            Función callback que recibe (analysis_id) -> bool
        """
        from hidropluvial.database import get_database
        from hidropluvial.cli.viewer.terminal import clear_screen

        if db is None:
            db = get_database()

        def on_delete(analysis_id: str) -> bool:
            if confirm_prompt:
                clear_screen()
                print(f"\n  ¿Eliminar análisis {analysis_id[:8]}?\n")
                if not questionary.confirm(
                    "¿Confirmar eliminación?",
                    default=False,
                    **get_confirm_kwargs(),
                ).ask():
                    return False

            if db.delete_analysis(analysis_id):
                self._basin.analyses = [a for a in self._basin.analyses if a.id != analysis_id]
                return True
            return False

        return on_delete

    # ========================================================================
    # Visores interactivos
    # ========================================================================

    def show_analysis_cards(self, analyses: list = None, name: str = None) -> None:
        """
        Muestra el visor interactivo de fichas de análisis.

        Permite navegar y también editar notas (e) o eliminar (d) análisis.

        Args:
            analyses: Lista de análisis (default: self.basin.analyses)
            name: Nombre a mostrar (default: self.basin.name)
        """
        if analyses is None:
            analyses = self._basin.analyses
        if name is None:
            name = self._basin.name

        if not analyses:
            self.echo("  No hay análisis disponibles.")
            return

        from hidropluvial.cli.interactive_viewer import interactive_hydrograph_viewer

        updated_analyses = interactive_hydrograph_viewer(
            analyses, name,
            on_edit_note=self._create_edit_note_callback(),
            on_delete=self._create_delete_callback(),
        )

        if updated_analyses is not None:
            self._basin.analyses = updated_analyses

    def show_summary_table(self, analyses: list = None, name: str = None) -> None:
        """
        Muestra el visor interactivo de tabla resumen.

        Permite navegar con ↑↓ y también editar notas (e) o eliminar (d) análisis.

        Args:
            analyses: Lista de análisis (default: self.basin.analyses)
            name: Nombre a mostrar (default: self.basin.name)
        """
        if analyses is None:
            analyses = self._basin.analyses
        if name is None:
            name = self._basin.name

        if not analyses:
            self.echo("  No hay análisis disponibles.")
            return

        from hidropluvial.cli.viewer.table_viewer import interactive_table_viewer
        from hidropluvial.cli.interactive_viewer import interactive_hydrograph_viewer

        on_edit_note = self._create_edit_note_callback()
        on_delete = self._create_delete_callback()

        def on_view_detail(index: int) -> None:
            """Callback para ver ficha detallada de un análisis."""
            interactive_hydrograph_viewer(
                [self._basin.analyses[index]],
                name,
                on_edit_note=on_edit_note,
                on_delete=on_delete,
            )

        updated_analyses = interactive_table_viewer(
            analyses, name,
            on_edit_note=on_edit_note,
            on_delete=on_delete,
            on_view_detail=on_view_detail,
        )

        if updated_analyses is not None:
            self._basin.analyses = updated_analyses
