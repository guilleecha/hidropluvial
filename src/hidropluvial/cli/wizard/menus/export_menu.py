"""
Menú para exportar sesiones a Excel o LaTeX con filtrado de análisis.
"""

from typing import Optional
from pathlib import Path

from hidropluvial.cli.wizard.menus.base import BaseMenu, SessionMenu
from hidropluvial.cli.output_manager import (
    get_latex_output_dir,
    get_excel_output_dir,
    get_basin_output_dir,
    _sanitize_name,
)
from hidropluvial.models import Basin
from hidropluvial.project import Project


class ExportMenu(SessionMenu):
    """Menú para exportar una cuenca con opciones de filtrado."""

    def __init__(
        self,
        basin: Basin,
        project: Optional[Project] = None,
        preselected_analyses: Optional[list] = None,
    ):
        """
        Inicializa el menú de exportación.

        Args:
            basin: Cuenca a exportar
            project: Proyecto al que pertenece (opcional)
            preselected_analyses: Lista de análisis pre-seleccionados para exportar.
                                  Si se proporciona, no se pregunta por filtrado.
        """
        super().__init__(basin)
        self.project = project
        self.preselected_analyses = preselected_analyses

    def show(self) -> None:
        """Muestra el menú de exportacion."""
        # Determinar qué análisis exportar
        if self.preselected_analyses is not None:
            analyses_to_export = self.preselected_analyses
            if not analyses_to_export:
                self.info("No hay análisis seleccionados para exportar.")
                return
        else:
            analyses_to_export = self.basin.analyses

        if not analyses_to_export:
            self.info("La cuenca no tiene analisis para exportar.")
            return

        self.header("EXPORTAR CUENCA")
        self._show_basin_info(analyses_to_export)

        # Preguntar formato
        format_choice = self.select(
            "Formato de exportacion:",
            choices=[
                "Excel (.xlsx) - Tabla con todos los datos",
                "Reporte LaTeX (.tex) - Documento tecnico",
                "Ambos formatos",
                "← Cancelar",
            ],
        )

        if format_choice is None or "Cancelar" in format_choice:
            return

        # Si ya hay análisis pre-seleccionados, no preguntar por filtrado adicional
        selected_indices = None
        if self.preselected_analyses is not None:
            # Convertir análisis pre-seleccionados a índices
            selected_indices = []
            for a in self.preselected_analyses:
                for i, ba in enumerate(self.basin.analyses):
                    if ba.id == a.id:
                        selected_indices.append(i)
                        break
        else:
            # Preguntar si filtrar (comportamiento original)
            use_filter = False
            if len(self.basin.analyses) > 1:
                use_filter = self.confirm(
                    f"¿Filtrar análisis? (hay {len(self.basin.analyses)} disponibles)",
                    default=False,
                )

            if use_filter:
                selected_indices = self._select_analyses()
                if selected_indices is None:
                    return
                if not selected_indices:
                    self.info("No se seleccionaron análisis.")
                    return

        # Directorio de salida organizado
        project_id = self.project.id if self.project else None
        project_name = self.project.name if self.project else None

        output_dir = get_basin_output_dir(
            self.basin.id,
            self.basin.name,
            project_id,
            project_name,
        )
        self.info(f"Directorio de salida: {output_dir.absolute()}")

        # Nombre base para archivos
        default_name = self.basin.name.lower().replace(" ", "_")

        # Exportar segun formato
        if "Excel" in format_choice or "Ambos" in format_choice:
            self._export_excel(output_dir, default_name, selected_indices)

        if "LaTeX" in format_choice or "Ambos" in format_choice:
            self._export_latex(output_dir, default_name, selected_indices)

    def _show_basin_info(self, analyses_to_export: list = None) -> None:
        """Muestra información de la cuenca."""
        analyses = analyses_to_export or self.basin.analyses
        total_analyses = len(self.basin.analyses)
        export_count = len(analyses)

        self.info(f"Cuenca: {self.basin.name}")
        if export_count < total_analyses:
            self.info(f"Analisis a exportar: {export_count} de {total_analyses}")
        else:
            self.info(f"Analisis: {export_count}")

        # Mostrar resumen de análisis a exportar
        tr_values = sorted(set(a.storm.return_period for a in analyses))
        tc_methods = sorted(set(a.hydrograph.tc_method for a in analyses))

        self.info(f"Períodos de retorno: {tr_values}")
        self.info(f"Métodos Tc: {tc_methods}")

    def _select_analyses(self) -> Optional[list[int]]:
        """Permite seleccionar que analisis incluir."""
        self.info("Selecciona los analisis a incluir:")

        # Crear opciones con checkbox
        choices = []
        for i, a in enumerate(self.basin.analyses):
            hydro = a.hydrograph
            storm = a.storm
            x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
            label = (
                f"{a.id}: {hydro.tc_method} + {storm.type} "
                f"Tr{storm.return_period}{x_str} -> Qp={hydro.peak_flow_m3s:.2f} m³/s"
            )
            choices.append({"name": label, "value": a.id, "checked": True})

        selected = self.checkbox("Analisis:", choices)

        if selected is None:
            return None

        # Extraer indices de los seleccionados (selected contiene los IDs directamente)
        indices = []
        for analysis_id in selected:
            for i, a in enumerate(self.basin.analyses):
                if a.id == analysis_id:
                    indices.append(i)
                    break

        return indices

    def _export_excel(self, output_dir: Path, base_name: str, selected_indices: Optional[list[int]]) -> None:
        """Exporta a Excel con filtrado opcional."""
        from hidropluvial.cli.basin.export import export_to_excel

        # Usar subdirectorio excel/
        excel_dir = output_dir / "excel"
        excel_dir.mkdir(parents=True, exist_ok=True)
        output_path = excel_dir / f"{base_name}.xlsx"

        # Filtrar analisis si es necesario (sin deepcopy para mejor rendimiento)
        if selected_indices is not None:
            from hidropluvial.models import Basin
            analyses_to_export = [self.basin.analyses[i] for i in selected_indices]
            # Crear cuenca ligera con solo los datos necesarios
            basin_to_export = Basin(
                id=self.basin.id,
                name=self.basin.name,
                area_ha=self.basin.area_ha,
                slope_pct=self.basin.slope_pct,
                p3_10=self.basin.p3_10,
                c=self.basin.c,
                cn=self.basin.cn,
                length_m=self.basin.length_m,
                notes=self.basin.notes,
            )
            basin_to_export.tc_results = self.basin.tc_results
            basin_to_export.analyses = analyses_to_export
        else:
            basin_to_export = self.basin

        try:
            export_to_excel(basin_to_export, output_path)
            self.success(f"Excel exportado: {output_path.name}")

        except Exception as e:
            self.error(f"Error al exportar Excel: {e}")

    def _export_latex(self, output_dir: Path, base_name: str, selected_indices: Optional[list[int]]) -> None:
        """Exporta a LaTeX con filtrado opcional."""
        from hidropluvial.cli.basin.report import generate_basin_report

        # Usar subdirectorio latex/
        latex_dir = output_dir / "latex"

        try:
            # Filtrar analisis si es necesario (sin deepcopy para mejor rendimiento)
            if selected_indices is not None:
                from hidropluvial.models import Basin
                analyses_to_export = [self.basin.analyses[i] for i in selected_indices]
                # Crear cuenca ligera con solo los datos necesarios
                basin_to_export = Basin(
                    id=self.basin.id,
                    name=self.basin.name,
                    area_ha=self.basin.area_ha,
                    slope_pct=self.basin.slope_pct,
                    p3_10=self.basin.p3_10,
                    c=self.basin.c,
                    cn=self.basin.cn,
                    length_m=self.basin.length_m,
                    notes=self.basin.notes,
                )
                basin_to_export.tc_results = self.basin.tc_results
                basin_to_export.analyses = analyses_to_export
                self.note("El filtrado de analisis se aplica al reporte LaTeX")
            else:
                basin_to_export = self.basin

            generate_basin_report(basin_to_export, output_dir=latex_dir)
            self.success(f"Reporte LaTeX generado en: {latex_dir}")
        except SystemExit:
            pass  # Capturar typer.Exit
        except Exception as e:
            self.error(f"Error al generar reporte: {e}")

    def _get_filtered_summary(self, analyses: list) -> "pd.DataFrame":
        """Genera DataFrame con resumen de analisis filtrados."""
        import pandas as pd

        rows = []
        for a in analyses:
            # Determinar método de escorrentía
            runoff_method = "-"
            if a.tc.parameters and "runoff_method" in a.tc.parameters:
                rm = a.tc.parameters["runoff_method"]
                runoff_method = "Racional" if rm == "racional" else "SCS-CN"
            elif a.tc.parameters:
                if "cn_adjusted" in a.tc.parameters:
                    runoff_method = "SCS-CN"
                elif "c" in a.tc.parameters:
                    runoff_method = "Racional"

            row = {
                "ID": a.id,
                "Método Tc": a.tc.method.capitalize(),
                "Tc (min)": round(a.tc.tc_min, 1),
                "tp (min)": round(a.hydrograph.tp_unit_min, 1) if a.hydrograph.tp_unit_min else None,
                "tb (min)": round(a.hydrograph.tb_min, 1) if a.hydrograph.tb_min else None,
                "Método Pe": runoff_method,
                "Tormenta": a.storm.type.upper(),
                "Tr (anos)": a.storm.return_period,
                "Duracion (hr)": round(a.storm.duration_hr, 2),
                "P total (mm)": round(a.storm.total_depth_mm, 1),
                "i pico (mm/hr)": round(a.storm.peak_intensity_mmhr, 1),
                "Pe (mm)": round(a.hydrograph.runoff_mm, 1),
                "Qp (m³/s)": round(a.hydrograph.peak_flow_m3s, 2),
                "Tp (min)": round(a.hydrograph.time_to_peak_min, 1),
                "Vol (hm3)": round(a.hydrograph.volume_m3 / 1_000_000, 4),
            }

            # Agregar C si el método de Tc depende de C
            if a.tc.parameters and "c" in a.tc.parameters:
                row["C"] = round(a.tc.parameters["c"], 3)

            # Agregar t0 si existe (para desbordes)
            if a.tc.parameters and "t0_min" in a.tc.parameters:
                row["t0 (min)"] = a.tc.parameters["t0_min"]

            # Agregar parámetros SCS-CN si existen
            if a.tc.parameters:
                if "cn_adjusted" in a.tc.parameters:
                    row["CN ajustado"] = a.tc.parameters["cn_adjusted"]
                if "amc" in a.tc.parameters:
                    row["AMC"] = a.tc.parameters["amc"]
                if "lambda" in a.tc.parameters:
                    row["λ"] = a.tc.parameters["lambda"]

            if a.hydrograph.x_factor:
                row["Factor X"] = a.hydrograph.x_factor

            if a.note:
                row["Nota"] = a.note

            rows.append(row)

        return pd.DataFrame(rows)

    def _get_filtered_pivot(self, analyses: list) -> Optional["pd.DataFrame"]:
        """Genera tabla pivote de Q pico filtrada."""
        import pandas as pd

        if not analyses:
            return None

        rows = []
        for a in analyses:
            # Construir etiqueta del método
            method_label = a.tc.method

            # Agregar método de escorrentía
            if a.tc.parameters and "runoff_method" in a.tc.parameters:
                rm = a.tc.parameters["runoff_method"]
                esc_label = "C" if rm == "racional" else "CN"
                method_label = f"{method_label}+{esc_label}"
            elif a.tc.parameters:
                if "cn_adjusted" in a.tc.parameters:
                    method_label = f"{method_label}+CN"
                elif "c" in a.tc.parameters:
                    method_label = f"{method_label}+C"

            # Agregar factor X
            if a.hydrograph.x_factor:
                method_label = f"{method_label} X={a.hydrograph.x_factor:.2f}"

            rows.append({
                "Metodo": method_label,
                "Tr": a.storm.return_period,
                "Q pico (m³/s)": round(a.hydrograph.peak_flow_m3s, 3),
            })

        df = pd.DataFrame(rows)

        if len(df["Tr"].unique()) > 1 or len(df["Metodo"].unique()) > 1:
            pivot = df.pivot_table(
                index="Metodo",
                columns="Tr",
                values="Q pico (m³/s)",
                aggfunc="first",
            )
            pivot.columns = [f"Tr={tr}" for tr in pivot.columns]
            return pivot

        return None


class ExportBasinSelector(BaseMenu):
    """Menú para seleccionar cuenca y exportar desde gestión de proyectos."""

    def show(self) -> None:
        """Muestra selector de proyecto/cuenca para exportar."""
        from hidropluvial.project import ProjectManager

        project_manager = ProjectManager()
        projects = project_manager.list_projects()

        if not projects:
            self.info("No hay proyectos disponibles.")
            return

        self.header("EXPORTAR CUENCA")

        # Seleccionar proyecto
        project_choices = [
            f"{p['id']} - {p['name']} ({p['n_basins']} cuencas)"
            for p in projects
        ]
        project_choices.append("← Cancelar")

        project_choice = self.select("Selecciona proyecto:", project_choices)

        if project_choice is None or "Cancelar" in project_choice:
            return

        project_id = project_choice.split(" - ")[0]
        project = project_manager.get_project(project_id)

        if not project or not project.basins:
            self.info("Este proyecto no tiene cuencas.")
            return

        # Filtrar cuencas con análisis
        basins_with_analyses = [b for b in project.basins if b.analyses]

        if not basins_with_analyses:
            self.info("No hay cuencas con analisis para exportar.")
            return

        # Seleccionar cuenca
        basin_choices = [
            f"{b.id} - {b.name} ({len(b.analyses)} análisis)"
            for b in basins_with_analyses
        ]
        basin_choices.append("← Cancelar")

        basin_choice = self.select("Selecciona cuenca a exportar:", basin_choices)

        if basin_choice is None or "Cancelar" in basin_choice:
            return

        basin_id = basin_choice.split(" - ")[0]
        basin = project.get_basin(basin_id)

        if basin:
            export_menu = ExportMenu(basin, project)
            export_menu.show()
