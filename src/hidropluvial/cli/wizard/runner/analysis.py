"""
AnalysisRunner - Ejecuta análisis hidrológicos basados en WizardConfig.
"""

from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from rich.text import Text

from hidropluvial.cli.wizard.config import WizardConfig
from hidropluvial.cli.theme import (
    get_console,
    get_palette,
    print_success,
    print_info,
    print_completion_banner,
    print_result_row,
)
from hidropluvial.core import (
    kirpich,
    desbordes,
    temez,
    scs_triangular_uh,
    triangular_uh_x,
    convolve_uh,
    scs_time_to_peak,
)
from hidropluvial.models import (
    Basin,
    CoverageItem,
    WeightedCoefficient,
    TcResult,
    Project,
)
from hidropluvial.database import get_database

from .helpers import get_c_for_tr
from .generators import (
    get_storm_duration_and_dt,
    generate_hyetograph,
    calculate_runoff,
    create_analysis_results,
)


class AnalysisRunner:
    """Ejecuta análisis hidrológicos basados en WizardConfig."""

    def __init__(self, config: WizardConfig, project_id: Optional[str] = None):
        """
        Inicializa el runner.

        Args:
            config: Configuración del wizard
            project_id: ID del proyecto existente (opcional).
                       Si no se especifica, se crea un proyecto por defecto.
        """
        self.config = config
        self.db = get_database()
        self.project: Optional[Project] = None
        self.basin: Optional[Basin] = None
        self.project_id = project_id

    def run(self) -> Tuple[Project, Basin]:
        """
        Ejecuta el análisis completo y retorna (project, basin).

        Crea o usa un proyecto y guarda la cuenca con todos sus análisis.
        """
        self._create_project_and_basin()
        self._calculate_tc()
        self._run_analyses()

        if self.config.output_name:
            self._generate_report()

        self._print_summary()

        # Guardar proyecto con la cuenca actualizada
        self.db.save_project_model(self.project)

        return self.project, self.basin

    def _create_project_and_basin(self) -> None:
        """Crea o obtiene el proyecto y crea la cuenca."""
        if self.project_id:
            self.project = self.db.get_project_model(self.project_id)

        if not self.project:
            self.project = self.db.create_project_model(
                name=f"Proyecto - {self.config.nombre}",
                description=f"Proyecto creado automaticamente para la cuenca {self.config.nombre}",
            )
            print_success(f"Proyecto creado: {self.project.id}")

        self.basin = self.db.create_basin_model(
            project_id=self.project.id,
            name=self.config.nombre,
            area_ha=self.config.area_ha,
            slope_pct=self.config.slope_pct,
            p3_10=self.config.p3_10,
            c=self.config.c,
            cn=self.config.cn,
            length_m=self.config.length_m,
        )

        # Guardar datos de ponderación de C si existen
        if self.config.c_weighted_data:
            items = [
                CoverageItem(
                    description=d["description"],
                    area_ha=d["area"],
                    value=d["c_val"],
                    table_index=d["table_index"],
                    percentage=d["area"] / self.config.area_ha * 100,
                )
                for d in self.config.c_weighted_data["items"]
            ]
            c_weighted = WeightedCoefficient(
                type="c",
                table_used=self.config.c_weighted_data["table_key"],
                weighted_value=self.config.c,
                items=items,
                base_tr=self.config.c_weighted_data["base_tr"],
            )
            self.basin.c_weighted = c_weighted
            self.db.set_weighted_coefficient(
                basin_id=self.basin.id,
                coef_type="c",
                weighted_value=self.config.c,
                items=items,
                table_used=self.config.c_weighted_data["table_key"],
                base_tr=self.config.c_weighted_data["base_tr"],
            )

        self.project.add_basin(self.basin)
        print_success(f"Cuenca creada: {self.basin.id}")

    def _calculate_tc(self) -> None:
        """Calcula tiempo de concentración con los métodos seleccionados."""
        for method_str in self.config.tc_methods:
            method = method_str.split()[0].lower()
            tc_hr = None
            tc_params = {}

            if method == "kirpich" and self.config.length_m:
                tc_hr = kirpich(self.config.length_m, self.config.slope_pct / 100)
                tc_params = {"length_m": self.config.length_m}
            elif method == "temez" and self.config.length_m:
                tc_hr = temez(self.config.length_m / 1000, self.config.slope_pct / 100)
                tc_params = {"length_m": self.config.length_m}
            elif method == "desbordes" and self.config.c:
                tc_hr = desbordes(
                    self.config.area_ha,
                    self.config.slope_pct,
                    self.config.c,
                    self.config.t0_min,
                )
                tc_params = {
                    "c": self.config.c,
                    "area_ha": self.config.area_ha,
                    "t0_min": self.config.t0_min,
                }

            if tc_hr:
                tc_min = tc_hr * 60
                result = TcResult(
                    method=method,
                    tc_hr=tc_hr,
                    tc_min=tc_min,
                    parameters=tc_params,
                )
                self.db.add_tc_result(self.basin.id, method, tc_hr, tc_params)
                self.basin.add_tc_result(result)
                print_result_row(f"Tc ({method})", f"{tc_min:.1f}", "min")

    def _run_analyses(self) -> None:
        """Ejecuta todos los análisis."""
        n_analyses = 0

        runoff_methods = []
        if self.config.c:
            runoff_methods.append("racional")
        if self.config.cn:
            runoff_methods.append("scs-cn")

        for tc_result in self.basin.tc_results:
            for storm_code in self.config.storm_codes:
                for tr in self.config.return_periods:
                    for runoff_method in runoff_methods:
                        if storm_code == "gz":
                            for x in self.config.x_factors:
                                self._run_single_analysis(tc_result, tr, x, storm_code, runoff_method)
                                n_analyses += 1
                        else:
                            self._run_single_analysis(tc_result, tr, 1.0, storm_code, runoff_method)
                            n_analyses += 1

        print_success(f"{n_analyses} analisis completados")

    def _run_single_analysis(
        self,
        tc_result,
        tr: int,
        x: float,
        storm_code: str,
        runoff_method: str = "racional"
    ) -> None:
        """Ejecuta un análisis individual."""
        p3_10 = self.config.p3_10
        area = self.config.area_ha

        # Obtener C ajustado
        c_adjusted = None
        if runoff_method == "racional" and self.config.c:
            c_adjusted = get_c_for_tr(self.config, tr)

        # Recalcular Tc si es método Desbordes
        if tc_result.method == "desbordes" and c_adjusted:
            tc_hr = desbordes(area, self.config.slope_pct, c_adjusted, self.config.t0_min)
        else:
            tc_hr = tc_result.tc_hr

        # Duración y dt
        duration_hr, dt = get_storm_duration_and_dt(
            storm_code, tc_hr, self.config.dt_min,
            self.config.bimodal_duration_hr,
            self.config.custom_duration_hr,
        )

        # Generar tormenta
        hyetograph = generate_hyetograph(
            storm_code, p3_10, tr, duration_hr, dt,
            bimodal_peak1=self.config.bimodal_peak1,
            bimodal_peak2=self.config.bimodal_peak2,
            bimodal_vol_split=self.config.bimodal_vol_split,
            bimodal_peak_width=self.config.bimodal_peak_width,
            custom_depth_mm=self.config.custom_depth_mm,
            custom_distribution=self.config.custom_distribution,
            custom_hyetograph_time=self.config.custom_hyetograph_time,
            custom_hyetograph_depth=self.config.custom_hyetograph_depth,
        )

        depths = np.array(hyetograph.depth_mm)
        cumulative = np.array(hyetograph.cumulative_mm)

        # Escorrentía
        excess_mm, runoff_mm, cn_adjusted = calculate_runoff(
            depths, cumulative, runoff_method,
            c_adjusted=c_adjusted,
            cn=self.config.cn,
            amc=self.config.amc,
            lambda_coef=self.config.lambda_coef,
        )

        if excess_mm is None:
            return

        # Hidrograma unitario
        dt_hr = dt / 60
        x_val = x if storm_code == "gz" else 1.0
        tp_unit_hr = scs_time_to_peak(tc_hr, dt_hr)

        if runoff_method == "racional" or storm_code == "gz":
            uh_time, uh_flow = triangular_uh_x(area, tc_hr, dt_hr, x_val)
        else:
            uh_time, uh_flow = scs_triangular_uh(area / 100, tc_hr, dt_hr)
            x_val = 1.67

        # Convolución
        hydrograph_flow = convolve_uh(excess_mm, uh_flow)
        hydrograph_time = np.arange(len(hydrograph_flow)) * dt_hr

        peak_idx = np.argmax(hydrograph_flow)
        peak_flow = float(hydrograph_flow[peak_idx])
        time_to_peak = float(hydrograph_time[peak_idx])
        volume_m3 = float(np.trapezoid(hydrograph_flow, hydrograph_time * 3600))

        # Parámetros de Tc
        tc_params = {}
        if tc_result.method == "desbordes" and c_adjusted:
            tc_params = {"c": c_adjusted, "area_ha": area, "t0_min": self.config.t0_min}
        elif tc_result.parameters:
            tc_params = dict(tc_result.parameters)

        tc_params["runoff_method"] = runoff_method
        if runoff_method == "racional" and c_adjusted:
            tc_params["c"] = round(c_adjusted, 3)
        elif runoff_method == "scs-cn" and cn_adjusted is not None:
            tc_params["cn_adjusted"] = round(cn_adjusted, 1)
            tc_params["amc"] = self.config.amc
            tc_params["lambda"] = self.config.lambda_coef

        # Crear resultados
        bimodal_params = None
        if storm_code == "bimodal":
            bimodal_params = {
                "peak1": self.config.bimodal_peak1,
                "peak2": self.config.bimodal_peak2,
                "vol_split": self.config.bimodal_vol_split,
                "peak_width": self.config.bimodal_peak_width,
            }
        tc_result_obj, storm_result, hydrograph_result = create_analysis_results(
            tc_result.method, tc_hr, tc_params,
            storm_code, tr, duration_hr, hyetograph,
            x, peak_flow, time_to_peak, tp_unit_hr, volume_m3, runoff_mm,
            hydrograph_time, hydrograph_flow,
            bimodal_params=bimodal_params,
        )

        # Guardar análisis
        analysis = self.db.add_analysis_model(
            basin_id=self.basin.id,
            tc=tc_result_obj,
            storm=storm_result,
            hydrograph=hydrograph_result,
        )
        self.basin.add_analysis(analysis)

    def _generate_report(self) -> None:
        """Genera reporte LaTeX."""
        from hidropluvial.cli.basin.report import generate_basin_report

        print_info("Generando reporte...")
        output_dir = Path("output") / self.config.output_name
        generate_basin_report(
            basin=self.basin,
            output_dir=output_dir,
            author="",
            template_dir=None,
            pdf=False,
            clean=True,
        )

    def _print_summary(self) -> None:
        """Imprime resumen final."""
        console = get_console()
        p = get_palette()

        n_analyses = len(self.basin.analyses)
        print_completion_banner(n_analyses, self.basin.id)

        if self.basin.analyses:
            max_analysis = max(self.basin.analyses, key=lambda a: a.hydrograph.peak_flow_m3s)

            text = Text()
            text.append("  Caudal maximo: ", style=p.label)
            text.append(f"{max_analysis.hydrograph.peak_flow_m3s:.2f}", style=f"bold {p.accent}")
            text.append(" m3/s", style=p.unit)
            console.print(text)

            text = Text()
            text.append(
                f"  ({max_analysis.tc.method} + {max_analysis.storm.type} Tr{max_analysis.storm.return_period})",
                style=p.muted
            )
            console.print(text)
            console.print()
