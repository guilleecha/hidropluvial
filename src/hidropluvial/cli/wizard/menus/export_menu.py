"""
Menu para exportar sesiones a Excel o LaTeX con filtrado de analisis.
"""

from datetime import datetime
from typing import Optional
from pathlib import Path

import questionary

from hidropluvial.cli.wizard.menus.base import BaseMenu, SessionMenu
from hidropluvial.session import Session


def get_output_dir(session_name: str, base_dir: str = "outputs") -> Path:
    """
    Genera el directorio de salida para una sesión.

    Estructura: outputs/<nombre_sesion>_<fecha>/
    """
    safe_name = session_name.lower().replace(" ", "_").replace("/", "_")
    date_str = datetime.now().strftime("%Y%m%d")
    dir_name = f"{safe_name}_{date_str}"

    output_dir = Path(base_dir) / dir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


class ExportMenu(SessionMenu):
    """Menu para exportar una sesion con opciones de filtrado."""

    def show(self) -> None:
        """Muestra el menu de exportacion."""
        if not self.session.analyses:
            self.echo("\n  La sesion no tiene analisis para exportar.\n")
            return

        self.header("EXPORTAR SESION")
        self._show_session_info()

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

        # Preguntar si filtrar
        use_filter = False
        if len(self.session.analyses) > 1:
            use_filter = self.confirm(
                f"Filtrar analisis? (hay {len(self.session.analyses)} disponibles)",
                default=False,
            )

        # Obtener indices de analisis a incluir
        selected_indices = None
        if use_filter:
            selected_indices = self._select_analyses()
            if selected_indices is None:
                return
            if not selected_indices:
                self.echo("\n  No se seleccionaron analisis.\n")
                return

        # Directorio de salida organizado
        output_dir = get_output_dir(self.session.name)
        self.echo(f"\n  Directorio de salida: {output_dir.absolute()}")

        # Nombre base para archivos
        default_name = self.session.name.lower().replace(" ", "_")

        # Exportar segun formato
        if "Excel" in format_choice or "Ambos" in format_choice:
            self._export_excel(output_dir, default_name, selected_indices)

        if "LaTeX" in format_choice or "Ambos" in format_choice:
            self._export_latex(output_dir, default_name, selected_indices)

    def _show_session_info(self) -> None:
        """Muestra informacion de la sesion."""
        self.echo(f"\n  Sesion: {self.session.name}")
        self.echo(f"  Cuenca: {self.session.cuenca.nombre}")
        self.echo(f"  Analisis: {len(self.session.analyses)}")

        # Mostrar resumen de analisis
        tr_values = sorted(set(a.storm.return_period for a in self.session.analyses))
        tc_methods = sorted(set(a.hydrograph.tc_method for a in self.session.analyses))

        self.echo(f"  Periodos de retorno: {tr_values}")
        self.echo(f"  Metodos Tc: {tc_methods}")
        self.echo("")

    def _select_analyses(self) -> Optional[list[int]]:
        """Permite seleccionar que analisis incluir."""
        self.echo("\n  Selecciona los analisis a incluir:\n")

        # Crear opciones con checkbox
        choices = []
        for i, a in enumerate(self.session.analyses):
            hydro = a.hydrograph
            storm = a.storm
            x_str = f" X={hydro.x_factor:.2f}" if hydro.x_factor else ""
            label = (
                f"{a.id}: {hydro.tc_method} + {storm.type} "
                f"Tr{storm.return_period}{x_str} -> Qp={hydro.peak_flow_m3s:.2f} m3/s"
            )
            choices.append(questionary.Choice(label, checked=True))

        selected = self.checkbox("Analisis:", choices)

        if selected is None:
            return None

        # Extraer indices de los seleccionados
        indices = []
        for sel in selected:
            analysis_id = sel.split(":")[0]
            for i, a in enumerate(self.session.analyses):
                if a.id == analysis_id:
                    indices.append(i)
                    break

        return indices

    def _export_excel(self, output_dir: Path, base_name: str, selected_indices: Optional[list[int]]) -> None:
        """Exporta a Excel con filtrado opcional."""
        from hidropluvial.cli.session.export import (
            _get_cuenca_dataframe,
            _get_tc_dataframe,
            _get_notes_dataframe,
        )
        import pandas as pd

        output_path = output_dir / f"{base_name}.xlsx"

        # Filtrar analisis si es necesario
        if selected_indices is not None:
            analyses_to_export = [self.session.analyses[i] for i in selected_indices]
        else:
            analyses_to_export = self.session.analyses

        try:
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                # Hoja 1: Datos de la cuenca
                cuenca_data = _get_cuenca_dataframe(self.session)
                cuenca_data.to_excel(writer, sheet_name="Cuenca", index=False)

                # Hoja 2: Resultados de Tc
                if self.session.tc_results:
                    tc_data = _get_tc_dataframe(self.session)
                    tc_data.to_excel(writer, sheet_name="Tiempo Concentracion", index=False)

                # Hoja 3: Resumen de analisis (filtrado)
                summary_data = self._get_filtered_summary(analyses_to_export)
                summary_data.to_excel(writer, sheet_name="Resumen Analisis", index=False)

                # Hoja 4: Tabla pivote
                pivot_data = self._get_filtered_pivot(analyses_to_export)
                if pivot_data is not None:
                    pivot_data.to_excel(writer, sheet_name="Por Periodo Retorno", index=True)

                # Hoja 5: Notas
                notes_data = _get_notes_dataframe(self.session)
                if notes_data is not None:
                    notes_data.to_excel(writer, sheet_name="Notas", index=False)

            self.echo(f"\n  Excel exportado: {output_path.name}")

        except Exception as e:
            self.error(f"Error al exportar Excel: {e}")

    def _export_latex(self, output_dir: Path, base_name: str, selected_indices: Optional[list[int]]) -> None:
        """Exporta a LaTeX con filtrado opcional."""
        import os

        # Cambiar al directorio de salida para que los archivos se generen ahí
        original_dir = os.getcwd()

        try:
            os.chdir(output_dir)

            from hidropluvial.cli.session.report import session_report
            session_report(self.session.id, base_name, author=None, template_dir=None)
            self.echo(f"\n  Reporte LaTeX generado en: {output_dir}")
            if selected_indices is not None:
                self.echo("  (Nota: El filtrado de analisis aun no aplica al reporte LaTeX)")
        except SystemExit:
            pass  # Capturar typer.Exit
        except Exception as e:
            self.error(f"Error al generar reporte: {e}")
        finally:
            os.chdir(original_dir)

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
                "Metodo Tc": a.tc.method.capitalize(),
                "Tc (min)": round(a.tc.tc_min, 1),
                "tp (min)": round(a.hydrograph.tp_unit_min, 1) if a.hydrograph.tp_unit_min else None,
                "tb (min)": round(a.hydrograph.tb_min, 1) if a.hydrograph.tb_min else None,
                "Metodo Pe": runoff_method,
                "Tormenta": a.storm.type.upper(),
                "Tr (anos)": a.storm.return_period,
                "Duracion (hr)": round(a.storm.duration_hr, 2),
                "P total (mm)": round(a.storm.total_depth_mm, 1),
                "i pico (mm/hr)": round(a.storm.peak_intensity_mmhr, 1),
                "Pe (mm)": round(a.hydrograph.runoff_mm, 1),
                "Qp (m3/s)": round(a.hydrograph.peak_flow_m3s, 2),
                "Tp (min)": round(a.hydrograph.time_to_peak_min, 1),
                "Vol (hm3)": round(a.hydrograph.volume_m3 / 1_000_000, 4),
            }

            # Agregar C si el metodo de Tc depende de C
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
                "Q pico (m3/s)": round(a.hydrograph.peak_flow_m3s, 3),
            })

        df = pd.DataFrame(rows)

        if len(df["Tr"].unique()) > 1 or len(df["Metodo"].unique()) > 1:
            pivot = df.pivot_table(
                index="Metodo",
                columns="Tr",
                values="Q pico (m3/s)",
                aggfunc="first",
            )
            pivot.columns = [f"Tr={tr}" for tr in pivot.columns]
            return pivot

        return None


class ExportBasinSelector(BaseMenu):
    """Menu para seleccionar cuenca y exportar desde gestion de proyectos."""

    def show(self) -> None:
        """Muestra selector de sesion para exportar."""
        sessions = self.manager.list_sessions()

        if not sessions:
            self.echo("\n  No hay sesiones disponibles.\n")
            return

        # Filtrar sesiones con analisis
        sessions_with_analyses = [s for s in sessions if s['n_analyses'] > 0]

        if not sessions_with_analyses:
            self.echo("\n  No hay sesiones con analisis para exportar.\n")
            return

        self.header("EXPORTAR SESION")

        # Seleccionar sesion
        choices = [
            f"{s['id']} - {s['name']} ({s['n_analyses']} analisis)"
            for s in sessions_with_analyses
        ]
        choices.append("← Cancelar")

        choice = self.select("Selecciona sesion a exportar:", choices)

        if choice is None or "Cancelar" in choice:
            return

        session_id = choice.split(" - ")[0]
        session = self.manager.get_session(session_id)

        if session:
            export_menu = ExportMenu(session)
            export_menu.show()


# Alias para compatibilidad
ExportSessionSelector = ExportBasinSelector
