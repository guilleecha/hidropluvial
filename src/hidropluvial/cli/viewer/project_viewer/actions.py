"""
Acciones para el visor de proyectos.

Contiene todas las funciones que manejan acciones del usuario
(editar, crear, eliminar, importar, etc.)
"""

from typing import Optional

from hidropluvial.cli.theme import print_info, print_success, print_error
from hidropluvial.cli.viewer.terminal import clear_screen
from hidropluvial.project import ProjectManager, Project, Basin


def edit_project(project_manager: ProjectManager, project_id: str) -> None:
    """Edita metadatos de un proyecto usando formulario interactivo."""
    from hidropluvial.cli.wizard.menus.project_editor import ProjectEditor

    clear_screen()
    project = project_manager.get_project(project_id)
    if not project:
        print_error("Proyecto no encontrado")
        return

    editor = ProjectEditor(project, project_manager)
    editor.edit()


def create_new_project(project_manager: ProjectManager) -> Optional[Project]:
    """Crea un nuevo proyecto usando formulario interactivo."""
    from hidropluvial.cli.viewer.form_viewer import (
        interactive_form,
        FormField,
        FieldType,
        FormResult,
    )
    from hidropluvial.cli.theme import print_success

    clear_screen()

    fields = [
        FormField(
            key="name",
            label="Nombre del proyecto",
            field_type=FieldType.TEXT,
            required=True,
            hint="Identificador del proyecto",
        ),
        FormField(
            key="description",
            label="Descripción",
            field_type=FieldType.TEXT,
            required=False,
            hint="Descripción del estudio",
        ),
        FormField(
            key="author",
            label="Autor",
            field_type=FieldType.TEXT,
            required=False,
            hint="Responsable del estudio",
        ),
        FormField(
            key="location",
            label="Ubicación",
            field_type=FieldType.TEXT,
            required=False,
            hint="Ubicación geográfica",
        ),
    ]

    result = interactive_form(
        title="Nuevo Proyecto",
        fields=fields,
        allow_back=True,
    )

    if result is None:
        return None

    if result.get("_result") == FormResult.BACK:
        return None

    name = result.get("name")
    if not name:
        return None

    project = project_manager.create_project(
        name=name,
        description=result.get("description") or "",
        author=result.get("author") or "",
        location=result.get("location") or "",
    )

    print_success(f"Proyecto creado: {project.name} [{project.id}]")
    return project


def edit_basin(project_manager: ProjectManager, project: Project, basin: Basin) -> None:
    """Edita una cuenca usando CuencaEditor (versión con menú)."""
    from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor

    clear_screen()
    editor = CuencaEditor(basin, project_manager)
    editor.edit()


def edit_basin_metadata(project_manager: ProjectManager, basin: Basin) -> None:
    """Edita solo los metadatos de una cuenca (nombre, notas)."""
    from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor

    clear_screen()
    editor = CuencaEditor(basin, project_manager)
    editor._edit_metadata()


def edit_basin_params(project_manager: ProjectManager, basin: Basin) -> None:
    """Edita los parámetros físicos de una cuenca (puede invalidar análisis)."""
    from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor

    clear_screen()
    editor = CuencaEditor(basin, project_manager)
    editor._edit_params()


def create_new_basin(project_manager: ProjectManager, project: Project) -> None:
    """Crea una nueva cuenca."""
    from hidropluvial.cli.wizard.config import WizardConfig
    from hidropluvial.cli.wizard.runner import AnalysisRunner
    from hidropluvial.cli.wizard.menus.post_execution import PostExecutionMenu
    from hidropluvial.cli.theme import print_section, print_header
    from hidropluvial.cli.viewer.panel_input import panel_confirm

    clear_screen()
    print_section(f"Configurar cuenca en: {project.name}")

    config = WizardConfig.from_wizard()
    if config is None:
        return

    config.print_summary()

    if not panel_confirm(title="Ejecutar análisis?", default=True):
        return

    print_header("EJECUTANDO ANÁLISIS")

    runner = AnalysisRunner(config, project_id=project.id)
    updated_project, basin = runner.run()

    print_success(f"Cuenca '{basin.name}' agregada al proyecto")

    menu = PostExecutionMenu(updated_project, basin, config.c, config.cn, config.length_m)
    menu.show()


def do_import_basin(
    project_manager: ProjectManager,
    target_project: Project,
    source_basin: Basin,
) -> None:
    """
    Importa una cuenca directamente (sin menús).

    Usado por el popup multinivel del visor.
    """
    # Crear copia de la cuenca en el proyecto destino
    project_manager.create_basin(
        project=target_project,
        name=source_basin.name,
        area_ha=source_basin.area_ha,
        slope_pct=source_basin.slope_pct,
        p3_10=source_basin.p3_10,
        c=source_basin.c,
        cn=source_basin.cn,
        length_m=source_basin.length_m,
    )


def view_basin_analyses(project_manager: ProjectManager, project: Project, basin: Basin) -> None:
    """Muestra la tabla de análisis directamente con opciones integradas."""
    from hidropluvial.cli.viewer.table_viewer import interactive_table_viewer
    from hidropluvial.cli.interactive_viewer import interactive_hydrograph_viewer
    from hidropluvial.cli.viewer.terminal import clear_screen
    from hidropluvial.database import get_database

    db = get_database()

    while True:
        # Recargar basin desde DB para tener datos actualizados
        reloaded_basin = db.get_basin_model(basin.id)
        if not reloaded_basin:
            break
        basin = reloaded_basin

        # Callback para editar nota
        def on_edit_note(analysis_id: str, current_note: str) -> Optional[str]:
            from hidropluvial.cli.viewer.panel_input import panel_text
            new_note = panel_text(
                title=f"Nota para análisis {analysis_id[:8]}:",
                default=current_note or "",
                as_popup=True,
            )
            if new_note is not None:
                db.update_analysis_note(analysis_id, new_note if new_note else None)
            return new_note

        # Callback para eliminar (sin confirmación - cada visor la maneja)
        def on_delete(analysis_id: str) -> bool:
            return db.delete_analysis(analysis_id)

        # Callback para ver ficha detallada
        def on_view_detail(index: int, filtered_analyses: list, active_filters: dict) -> None:
            if index < len(filtered_analyses):
                interactive_hydrograph_viewer(
                    filtered_analyses,  # Usar lista ya filtrada
                    basin.name,
                    on_edit_note=on_edit_note,
                    on_delete=on_delete,
                    on_export=on_export,
                    start_index=index,
                    basin_id=basin.id,
                    db=db,
                    inherited_filters=active_filters,
                )

        # Callback para agregar análisis
        def on_add_analysis() -> None:
            add_analysis_to_basin(basin)

        # Callback para exportar (recibe lista de análisis a exportar)
        def on_export(analyses_to_export: list) -> None:
            export_basin(basin, project, analyses_to_export)

        # Callback para comparar (recibe lista de análisis marcados o todos)
        def on_compare(analyses_to_compare: list) -> None:
            compare_hydrographs(analyses_to_compare, basin.name, basin.analyses)

        # Callback para editar cuenca
        def on_edit_basin() -> None:
            edit_basin_submenu(project_manager, basin)

        # Si no hay análisis, ir directo al formulario de agregar
        if not basin.analyses:
            clear_screen()
            print_info(f"Cuenca '{basin.name}' sin análisis - creando nuevo...")
            on_add_analysis()
            # Recargar y verificar si ahora tiene análisis
            reloaded_basin = db.get_basin_model(basin.id)
            if reloaded_basin and reloaded_basin.analyses:
                basin = reloaded_basin
                continue  # Ahora mostrar la tabla
            else:
                break  # Si canceló o sigue sin análisis, volver

        # Construir info de cuenca para mostrar arriba de la tabla
        basin_info = {
            'name': basin.name,
            'area_ha': basin.area_ha,
            'slope_pct': basin.slope_pct,
            'c': basin.c,
            'cn': basin.cn,
            'length_m': basin.length_m,
            'tc_min': basin.tc_results[0].tc_min if basin.tc_results else None,
        }

        # Mostrar tabla interactiva con todas las opciones
        result = interactive_table_viewer(
            basin.analyses,
            basin.name,
            on_edit_note=on_edit_note,
            on_delete=on_delete,
            on_view_detail=on_view_detail,
            on_add_analysis=on_add_analysis,
            on_export=on_export,
            on_compare=on_compare,
            on_edit_basin=on_edit_basin,
            basin_info=basin_info,
        )

        # Desempaquetar resultado
        if isinstance(result, tuple):
            updated_analyses, needs_reload = result
        else:
            updated_analyses = result
            needs_reload = False

        # Si no necesita recargar, salir del loop
        if not needs_reload:
            break


def add_analysis_to_basin(basin: Basin) -> None:
    """Agrega análisis a una cuenca usando AddAnalysisMenu."""
    from hidropluvial.cli.wizard.menus.add_analysis import AddAnalysisMenu

    menu = AddAnalysisMenu(basin, basin.c, basin.cn, basin.length_m)
    menu.show()
    clear_screen()


def export_basin(
    basin: Basin,
    project: Project,
    preselected_analyses: list = None,
) -> None:
    """
    Exporta resultados de una cuenca usando popup compacto.

    Args:
        basin: Cuenca a exportar
        project: Proyecto al que pertenece
        preselected_analyses: Lista de análisis pre-seleccionados para exportar.
                              Si es None, se exportan todos.
    """
    from hidropluvial.cli.viewer.panel_input import export_popup
    from hidropluvial.cli.output_manager import get_basin_output_dir
    from hidropluvial.cli.theme import print_success, print_error

    analyses_to_export = preselected_analyses if preselected_analyses else basin.analyses

    if not analyses_to_export:
        print_info("No hay análisis para exportar.")
        return

    # Mostrar popup de formato
    format_choice = export_popup(len(analyses_to_export))

    if format_choice is None:
        return

    # Directorio de salida
    project_id = project.id if project else None
    project_name = project.name if project else None

    output_dir = get_basin_output_dir(
        basin.id,
        basin.name,
        project_id,
        project_name,
    )

    # Crear basin filtrada si es necesario (sin deepcopy para mejor rendimiento)
    if preselected_analyses:
        # Crear una cuenca ligera con solo los datos necesarios
        basin_to_export = Basin(
            id=basin.id,
            name=basin.name,
            area_ha=basin.area_ha,
            slope_pct=basin.slope_pct,
            p3_10=basin.p3_10,
            c=basin.c,
            cn=basin.cn,
            length_m=basin.length_m,
            notes=basin.notes,
        )
        basin_to_export.tc_results = basin.tc_results
        basin_to_export.analyses = analyses_to_export
    else:
        basin_to_export = basin

    base_name = basin.name.lower().replace(" ", "_")

    try:
        if format_choice in ("excel", "both"):
            from hidropluvial.cli.basin.export import export_to_excel
            excel_dir = output_dir / "excel"
            excel_dir.mkdir(parents=True, exist_ok=True)
            output_path = excel_dir / f"{base_name}.xlsx"
            export_to_excel(basin_to_export, output_path)
            print_success(f"Excel: {output_path}")

        if format_choice in ("latex", "both"):
            from hidropluvial.cli.basin.report import generate_basin_report
            latex_dir = output_dir / "latex"
            generate_basin_report(basin_to_export, output_dir=latex_dir)
            print_success(f"LaTeX: {latex_dir}")

    except Exception as e:
        print_error(f"Error al exportar: {e}")


def compare_hydrographs(analyses: list, basin_name: str, all_analyses: list = None) -> None:
    """Compara hidrogramas seleccionados."""
    from hidropluvial.cli.basin.preview import basin_preview_compare
    from hidropluvial.cli.viewer.terminal import clear_screen

    if not analyses:
        print_info("No hay análisis disponibles para comparar.")
        return

    clear_screen()
    try:
        basin_preview_compare(analyses, basin_name, all_analyses=all_analyses)
    except SystemExit:
        pass


def compare_basin_hydrographs(basin: Basin) -> None:
    """Compara todos los hidrogramas de una cuenca."""
    compare_hydrographs(basin.analyses, basin.name)


def edit_basin_submenu(project_manager: ProjectManager, basin: Basin) -> None:
    """Submenú para editar cuenca."""
    from hidropluvial.cli.viewer.menu_panel import menu_panel, MenuItem
    from hidropluvial.cli.viewer.panel_input import panel_text, panel_confirm
    from hidropluvial.cli.wizard.menus.cuenca_editor import CuencaEditor
    from hidropluvial.cli.theme import print_success
    from hidropluvial.database import get_database

    clear_screen()

    items = [
        MenuItem(key="e", label="Editar datos", value="edit", hint="área, pendiente, C, CN"),
        MenuItem(key="n", label="Editar notas", value="notes"),
        MenuItem(key="d", label="Eliminar cuenca", value="delete"),
    ]

    choice = menu_panel(
        title=f"Editar cuenca: {basin.name}",
        items=items,
        allow_back=True,
    )

    if choice is None:
        return

    db = get_database()

    if choice == "edit":
        clear_screen()
        editor = CuencaEditor(basin, project_manager)
        editor.edit()

    elif choice == "notes":
        clear_screen()
        current = basin.notes or ""
        print_info(f"Notas actuales: {current if current else '(sin notas)'}")

        new_notes = panel_text(
            title="Nuevas notas (vacío para eliminar):",
            default=current,
        )

        if new_notes is not None:
            basin.notes = new_notes
            db.update_basin(basin.id, notes=new_notes if new_notes else None)
            print_success("Notas guardadas" if new_notes else "Notas eliminadas")

    elif choice == "delete":
        clear_screen()
        if panel_confirm(
            title=f"¿Eliminar cuenca '{basin.name}' y todos sus análisis?",
            default=False,
        ):
            if db.delete_basin(basin.id):
                print_success(f"Cuenca '{basin.name}' eliminada")
