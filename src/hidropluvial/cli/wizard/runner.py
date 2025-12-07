"""
AnalysisRunner - Ejecuta analisis hidrologicos.
"""

from typing import Optional, Tuple

import numpy as np
import typer

from hidropluvial.cli.session.base import get_session_manager
from hidropluvial.cli.wizard.config import WizardConfig
from hidropluvial.cli.theme import (
    get_console,
    get_palette,
    print_success,
    print_info,
    print_section,
    print_completion_banner,
    print_result_row,
    create_analysis_table,
)
from rich.text import Text
from hidropluvial.config import AntecedentMoistureCondition
from hidropluvial.core import (
    kirpich,
    desbordes,
    temez,
    alternating_blocks_dinagua,
    bimodal_dinagua,
    rainfall_excess_series,
    scs_triangular_uh,
    triangular_uh_x,
    convolve_uh,
    adjust_c_for_tr,
    adjust_cn_for_amc,
    recalculate_weighted_c_for_tr,
)
from hidropluvial.core.temporal import huff_distribution, scs_distribution
from hidropluvial.core.idf import dinagua_depth
from hidropluvial.config import StormMethod
from hidropluvial.core.coefficients import get_c_for_tr_from_table
from hidropluvial.session import Session, CoverageItem
from hidropluvial.project import Project, Basin, get_project_manager


def _get_amc_enum(amc_str: str) -> AntecedentMoistureCondition:
    """Convierte string AMC a enum."""
    if amc_str == "I":
        return AntecedentMoistureCondition.DRY
    elif amc_str == "III":
        return AntecedentMoistureCondition.WET
    return AntecedentMoistureCondition.AVERAGE


def _get_c_for_tr(config: WizardConfig, tr: int) -> float:
    """
    Obtiene el coeficiente C ajustado para un período de retorno específico.

    Si hay datos de ponderación (tabla Ven Te Chow), recalcula usando
    los valores exactos de la tabla. Si no, usa el factor de ajuste promedio.
    """
    if config.c_weighted_data and config.c_weighted_data.get("table_key") == "chow":
        # Recalcular usando los datos de la tabla original
        table_key = config.c_weighted_data["table_key"]
        items_data = config.c_weighted_data["items"]

        # Convertir a objetos CoverageItem para la función
        items = [
            CoverageItem(
                description=d["description"],
                area_ha=d["area"],
                value=d["c_val"],
                table_index=d["table_index"],
            )
            for d in items_data
        ]

        return recalculate_weighted_c_for_tr(items, tr, table_key)
    else:
        # Sin datos de ponderación o tabla que no varía por Tr
        # Usar factor de ajuste promedio (menos preciso)
        return adjust_c_for_tr(config.c, tr, base_tr=2)


def _get_c_for_tr_from_session(session: Session, c_base: float, tr: int) -> float:
    """
    Obtiene el coeficiente C ajustado para un Tr desde datos de sesión.

    Si la sesión tiene datos de ponderación (c_weighted), recalcula exacto.
    Si no, usa el factor de ajuste promedio.
    """
    c_weighted = session.cuenca.c_weighted

    if c_weighted and c_weighted.table_used == "chow" and c_weighted.items:
        # Verificar que los items tengan table_index
        has_indices = all(item.table_index is not None for item in c_weighted.items)
        if has_indices:
            return recalculate_weighted_c_for_tr(
                c_weighted.items, tr, c_weighted.table_used
            )

    # Sin datos de ponderación o sin índices - usar factor promedio
    return adjust_c_for_tr(c_base, tr, base_tr=2)


class AnalysisRunner:
    """Ejecuta analisis hidrologicos basados en WizardConfig."""

    def __init__(self, config: WizardConfig, project_id: Optional[str] = None):
        """
        Inicializa el runner.

        Args:
            config: Configuración del wizard
            project_id: ID del proyecto existente (opcional).
                       Si no se especifica, se crea un proyecto por defecto.
        """
        self.config = config
        self.manager = get_session_manager()
        self.project_manager = get_project_manager()
        self.session: Optional[Session] = None
        self.project: Optional[Project] = None
        self.basin: Optional[Basin] = None
        self.project_id = project_id

    def run(self) -> Tuple[Project, Basin]:
        """
        Ejecuta el analisis completo y retorna (project, basin).

        Siempre crea o usa un proyecto y guarda la cuenca tanto como
        Session (compatibilidad) como Basin en el proyecto.
        """
        self._create_session()
        self._calculate_tc()
        self._run_analyses()

        if self.config.output_name:
            self._generate_report()

        self._print_summary()

        # Crear/obtener proyecto y convertir session a basin
        self._create_project_and_basin()

        return self.project, self.basin

    def _create_project_and_basin(self) -> None:
        """Crea o obtiene el proyecto y convierte la session a basin."""
        # Si hay project_id, usar ese proyecto
        if self.project_id:
            self.project = self.project_manager.get_project(self.project_id)

        # Si no hay proyecto o no se encontró, crear uno por defecto
        if not self.project:
            self.project = self.project_manager.create_project(
                name=f"Proyecto - {self.config.nombre}",
                description=f"Proyecto creado automaticamente para la cuenca {self.config.nombre}",
            )
            print_success(f"Proyecto creado: {self.project.id}")

        # Convertir session a basin y agregar al proyecto
        self.basin = Basin.from_session(self.session)
        self.project.add_basin(self.basin)
        self.project_manager.save_project(self.project)

    def _create_session(self) -> None:
        """Crea la sesion."""
        from hidropluvial.session import WeightedCoefficient

        self.session = self.manager.create(
            name=self.config.nombre,
            area_ha=self.config.area_ha,
            slope_pct=self.config.slope_pct,
            p3_10=self.config.p3_10,
            c=self.config.c,
            cn=self.config.cn,
            length_m=self.config.length_m,
            cuenca_nombre=self.config.nombre,
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
            weighted_coef = WeightedCoefficient(
                type="c",
                table_used=self.config.c_weighted_data["table_key"],
                weighted_value=self.config.c,
                items=items,
                base_tr=self.config.c_weighted_data["base_tr"],
            )
            self.manager.set_weighted_coefficient(self.session, weighted_coef)

        print_success(f"Sesion creada: {self.session.id}")

    def _calculate_tc(self) -> None:
        """Calcula tiempo de concentracion con los metodos seleccionados."""
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
                result = self.manager.add_tc_result(self.session, method, tc_hr, **tc_params)
                print_result_row(f"Tc ({method})", f"{result.tc_min:.1f}", "min")

    def _run_analyses(self) -> None:
        """Ejecuta todos los analisis."""
        n_analyses = 0

        # Determinar métodos de escorrentía disponibles
        runoff_methods = []
        if self.config.c:
            runoff_methods.append("racional")
        if self.config.cn:
            runoff_methods.append("scs-cn")

        for tc_result in self.session.tc_results:
            for storm_code in self.config.storm_codes:
                for tr in self.config.return_periods:
                    for runoff_method in runoff_methods:
                        if storm_code == "gz":
                            # Multiples valores de X para GZ
                            for x in self.config.x_factors:
                                self._run_single_analysis(tc_result, tr, x, storm_code, runoff_method)
                                n_analyses += 1
                        else:
                            # Solo X=1.0 para tormentas no-GZ
                            self._run_single_analysis(tc_result, tr, 1.0, storm_code, runoff_method)
                            n_analyses += 1

        print_success(f"{n_analyses} analisis completados")

    def _run_single_analysis(self, tc_result, tr: int, x: float, storm_code: str, runoff_method: str = "racional") -> None:
        """Ejecuta un analisis individual.

        Args:
            tc_result: Resultado de tiempo de concentración
            tr: Período de retorno (años)
            x: Factor X morfológico
            storm_code: Código de tormenta (gz, blocks, blocks24)
            runoff_method: Método de escorrentía ('racional' o 'scs-cn')
        """
        p3_10 = self.config.p3_10
        area = self.config.area_ha

        # Obtener C ajustado para el Tr del análisis (si aplica y usa método racional)
        c_adjusted = None
        if runoff_method == "racional" and self.config.c:
            c_adjusted = _get_c_for_tr(self.config, tr)

        # Recalcular Tc si es método Desbordes (depende de C y t0)
        if tc_result.method == "desbordes" and c_adjusted:
            tc_hr = desbordes(area, self.config.slope_pct, c_adjusted, self.config.t0_min)
        else:
            tc_hr = tc_result.tc_hr

        # Determinar duracion y dt
        # Usar dt configurado por el usuario (default 5 min)
        dt = self.config.dt_min
        if storm_code == "gz":
            duration_hr = 6.0
        elif storm_code == "blocks24" or storm_code == "scs_ii":
            duration_hr = 24.0
            # Para tormentas de 24h, dt mínimo de 10 min si el usuario puso menos
            if dt < 10.0:
                dt = 10.0
        elif storm_code.startswith("huff"):
            duration_hr = max(tc_hr * 2, 2.0)  # Duración 2x Tc o mínimo 2 horas
        else:
            duration_hr = max(tc_hr, 1.0)

        # Generar tormenta
        if storm_code == "gz":
            peak_position = 1.0 / 6.0
            hyetograph = alternating_blocks_dinagua(
                p3_10, tr, duration_hr, dt, None, peak_position
            )
        elif storm_code == "bimodal":
            hyetograph = bimodal_dinagua(p3_10, tr, duration_hr, dt)
        elif storm_code.startswith("huff"):
            # Extraer cuartil (ej: huff_q2 -> 2)
            quartile = int(storm_code.split("_q")[1]) if "_q" in storm_code else 2
            total_depth = dinagua_depth(p3_10, tr, duration_hr, None)
            hyetograph = huff_distribution(total_depth, duration_hr, dt, quartile=quartile)
        elif storm_code == "scs_ii":
            total_depth = dinagua_depth(p3_10, tr, duration_hr, None)
            hyetograph = scs_distribution(total_depth, duration_hr, dt, StormMethod.SCS_TYPE_II)
        else:
            hyetograph = alternating_blocks_dinagua(
                p3_10, tr, duration_hr, dt, None
            )

        depths = np.array(hyetograph.depth_mm)

        # Escorrentía según método seleccionado
        cn_adjusted = None
        if runoff_method == "racional" and c_adjusted:
            # Método Racional: Q = C × P
            excess_mm = c_adjusted * depths
            runoff_mm = float(np.sum(excess_mm))
        elif runoff_method == "scs-cn" and self.config.cn:
            # Método SCS-CN
            amc_enum = _get_amc_enum(self.config.amc)
            cn_adjusted = adjust_cn_for_amc(self.config.cn, amc_enum)

            cumulative = np.array(hyetograph.cumulative_mm)
            excess_mm = rainfall_excess_series(
                cumulative, cn_adjusted, self.config.lambda_coef
            )
            runoff_mm = float(np.sum(excess_mm))
        else:
            # No hay coeficiente para el método solicitado
            return

        # Hidrograma unitario
        dt_hr = dt / 60
        x_val = x if storm_code == "gz" else 1.0

        # Calcular tp del hidrograma unitario SCS: Tp = ΔD/2 + 0.6×Tc
        from hidropluvial.core import scs_time_to_peak
        tp_unit_hr = scs_time_to_peak(tc_hr, dt_hr)

        if runoff_method == "racional" or storm_code == "gz":
            # Hidrograma triangular con factor X para método racional o tormenta GZ
            uh_time, uh_flow = triangular_uh_x(area, tc_hr, dt_hr, x_val)
        else:
            # Hidrograma SCS para método CN
            uh_time, uh_flow = scs_triangular_uh(area / 100, tc_hr, dt_hr)
            x_val = 1.67

        # Convolucion
        hydrograph_flow = convolve_uh(excess_mm, uh_flow)
        n_total = len(hydrograph_flow)
        hydrograph_time = np.arange(n_total) * dt_hr

        peak_idx = np.argmax(hydrograph_flow)
        peak_flow = float(hydrograph_flow[peak_idx])
        time_to_peak = float(hydrograph_time[peak_idx])
        volume_m3 = float(np.trapezoid(hydrograph_flow, hydrograph_time * 3600))

        # Preparar parametros de Tc para guardar
        tc_params = {}
        if tc_result.method == "desbordes" and c_adjusted:
            tc_params = {
                "c": c_adjusted,
                "area_ha": area,
                "t0_min": self.config.t0_min,
            }
        elif tc_result.parameters:
            tc_params = dict(tc_result.parameters)

        # Agregar método de escorrentía usado
        tc_params["runoff_method"] = runoff_method

        # Agregar parámetros según el método de escorrentía
        if runoff_method == "racional" and c_adjusted:
            tc_params["c"] = round(c_adjusted, 3)
        elif runoff_method == "scs-cn" and cn_adjusted is not None:
            tc_params["cn_adjusted"] = round(cn_adjusted, 1)
            tc_params["amc"] = self.config.amc
            tc_params["lambda"] = self.config.lambda_coef

        # Guardar analisis
        self.manager.add_analysis(
            session=self.session,
            tc_method=tc_result.method,
            tc_hr=tc_hr,
            storm_type=storm_code,
            return_period=tr,
            duration_hr=duration_hr,
            total_depth_mm=hyetograph.total_depth_mm,
            peak_intensity_mmhr=hyetograph.peak_intensity_mmhr,
            n_intervals=len(hyetograph.time_min),
            peak_flow_m3s=peak_flow,
            time_to_peak_hr=time_to_peak,
            volume_m3=volume_m3,
            runoff_mm=runoff_mm,
            x_factor=x if storm_code == "gz" else None,
            tp_unit_hr=tp_unit_hr,
            storm_time_min=list(hyetograph.time_min),
            storm_intensity_mmhr=list(hyetograph.intensity_mmhr),
            hydrograph_time_hr=[float(t) for t in hydrograph_time],
            hydrograph_flow_m3s=[float(q) for q in hydrograph_flow],
            **tc_params,
        )

    def _generate_report(self) -> None:
        """Genera reporte LaTeX."""
        from hidropluvial.cli.session.report import session_report

        print_info("Generando reporte...")
        session_report(self.session.id, self.config.output_name, author=None, template_dir=None)

    def _print_summary(self) -> None:
        """Imprime resumen final."""
        console = get_console()
        p = get_palette()

        rows = self.manager.get_summary_table(self.session)
        n_analyses = len(rows) if rows else 0

        print_completion_banner(n_analyses, self.session.id)

        if rows:
            max_q = max(rows, key=lambda r: r['qpeak_m3s'])

            # Mostrar caudal máximo destacado
            text = Text()
            text.append("  Caudal maximo: ", style=p.label)
            text.append(f"{max_q['qpeak_m3s']:.2f}", style=f"bold {p.accent}")
            text.append(" m3/s", style=p.unit)
            console.print(text)

            text = Text()
            text.append(f"  ({max_q['tc_method']} + {max_q['storm']} Tr{max_q['tr']})", style=p.muted)
            console.print(text)
            console.print()


class AdditionalAnalysisRunner:
    """Ejecuta analisis adicionales sobre una sesion existente."""

    def __init__(
        self,
        session: Session,
        c: float = None,
        cn: float = None,
        amc: str = "II",
        lambda_coef: float = 0.2,
        t0_min: float = 5.0,
        dt_min: float = 5.0,
    ):
        self.session = session
        self.manager = get_session_manager()
        self.c = c
        self.cn = cn
        self.amc = amc
        self.lambda_coef = lambda_coef
        self.t0_min = t0_min
        self.dt_min = dt_min

    def run(
        self,
        tc_methods: list[str],
        storm_code: str,
        return_periods: list[int],
        x_factors: list[float],
        runoff_method: str = None,
    ) -> int:
        """Ejecuta analisis adicionales. Retorna cantidad de analisis agregados.

        Args:
            tc_methods: Lista de métodos de Tc a usar
            storm_code: Código de tormenta
            return_periods: Lista de períodos de retorno
            x_factors: Lista de factores X
            runoff_method: Método de escorrentía ('racional', 'scs-cn' o None para ambos)
        """
        p3_10 = self.session.cuenca.p3_10
        area = self.session.cuenca.area_ha
        n_analyses = 0

        # Determinar métodos de escorrentía a usar
        if runoff_method:
            runoff_methods = [runoff_method]
        else:
            runoff_methods = []
            if self.c:
                runoff_methods.append("racional")
            if self.cn:
                runoff_methods.append("scs-cn")

        for tc_result in self.session.tc_results:
            if tc_result.method not in tc_methods:
                continue

            for tr in return_periods:
                for x in x_factors:
                    for r_method in runoff_methods:
                        # Obtener C ajustado para el Tr del análisis (si usa método racional)
                        c_adjusted = None
                        if r_method == "racional" and self.c:
                            c_adjusted = _get_c_for_tr_from_session(self.session, self.c, tr)

                        # Recalcular Tc si es método Desbordes (depende de C y t0)
                        if tc_result.method == "desbordes" and c_adjusted:
                            tc_hr = desbordes(area, self.session.cuenca.slope_pct, c_adjusted, self.t0_min)
                        else:
                            tc_hr = tc_result.tc_hr

                        # Determinar duracion y dt
                        dt = self.dt_min
                        if storm_code == "gz":
                            duration_hr = 6.0
                        elif storm_code == "blocks24" or storm_code == "scs_ii":
                            duration_hr = 24.0
                            # Para tormentas de 24h, dt mínimo de 10 min
                            if dt < 10.0:
                                dt = 10.0
                        elif storm_code.startswith("huff"):
                            duration_hr = max(tc_hr * 2, 2.0)
                        else:
                            duration_hr = max(tc_hr, 1.0)

                        # Generar tormenta
                        if storm_code == "gz":
                            peak_position = 1.0 / 6.0
                            hyetograph = alternating_blocks_dinagua(
                                p3_10, tr, duration_hr, dt, None, peak_position
                            )
                        elif storm_code == "bimodal":
                            hyetograph = bimodal_dinagua(p3_10, tr, duration_hr, dt)
                        elif storm_code.startswith("huff"):
                            quartile = int(storm_code.split("_q")[1]) if "_q" in storm_code else 2
                            total_depth = dinagua_depth(p3_10, tr, duration_hr, None)
                            hyetograph = huff_distribution(total_depth, duration_hr, dt, quartile=quartile)
                        elif storm_code == "scs_ii":
                            total_depth = dinagua_depth(p3_10, tr, duration_hr, None)
                            hyetograph = scs_distribution(total_depth, duration_hr, dt, StormMethod.SCS_TYPE_II)
                        else:
                            hyetograph = alternating_blocks_dinagua(
                                p3_10, tr, duration_hr, dt, None
                            )

                        depths = np.array(hyetograph.depth_mm)

                        # Escorrentía según método seleccionado
                        cn_adjusted = None
                        if r_method == "racional" and c_adjusted:
                            excess_mm = c_adjusted * depths
                            runoff_mm = float(np.sum(excess_mm))
                        elif r_method == "scs-cn" and self.cn:
                            amc_enum = _get_amc_enum(self.amc)
                            cn_adjusted = adjust_cn_for_amc(self.cn, amc_enum)

                            cumulative = np.array(hyetograph.cumulative_mm)
                            excess_mm = rainfall_excess_series(
                                cumulative, cn_adjusted, self.lambda_coef
                            )
                            runoff_mm = float(np.sum(excess_mm))
                        else:
                            continue

                        # Hidrograma unitario
                        dt_hr = dt / 60
                        x_val = x if storm_code == "gz" else 1.0

                        # Calcular tp del hidrograma unitario SCS: Tp = ΔD/2 + 0.6×Tc
                        from hidropluvial.core import scs_time_to_peak
                        tp_unit_hr = scs_time_to_peak(tc_hr, dt_hr)

                        if r_method == "racional" or storm_code == "gz":
                            uh_time, uh_flow = triangular_uh_x(area, tc_hr, dt_hr, x_val)
                        else:
                            uh_time, uh_flow = scs_triangular_uh(area / 100, tc_hr, dt_hr)
                            x_val = 1.67

                        # Convolucion
                        hydrograph_flow = convolve_uh(excess_mm, uh_flow)
                        n_total = len(hydrograph_flow)
                        hydrograph_time = np.arange(n_total) * dt_hr

                        peak_idx = np.argmax(hydrograph_flow)
                        peak_flow = float(hydrograph_flow[peak_idx])
                        time_to_peak = float(hydrograph_time[peak_idx])
                        volume_m3 = float(np.trapezoid(hydrograph_flow, hydrograph_time * 3600))

                        # Preparar parametros de Tc para guardar
                        tc_params = {}
                        if tc_result.method == "desbordes" and c_adjusted:
                            tc_params = {
                                "c": c_adjusted,
                                "area_ha": area,
                                "t0_min": self.t0_min,
                            }
                        elif tc_result.parameters:
                            tc_params = dict(tc_result.parameters)

                        # Agregar método de escorrentía usado
                        tc_params["runoff_method"] = r_method

                        # Agregar parámetros según el método
                        if r_method == "racional" and c_adjusted:
                            tc_params["c"] = round(c_adjusted, 3)
                        elif r_method == "scs-cn" and cn_adjusted is not None:
                            tc_params["cn_adjusted"] = round(cn_adjusted, 1)
                            tc_params["amc"] = self.amc
                            tc_params["lambda"] = self.lambda_coef

                        # Guardar analisis
                        self.manager.add_analysis(
                            session=self.session,
                            tc_method=tc_result.method,
                            tc_hr=tc_hr,
                            storm_type=storm_code,
                            return_period=tr,
                            duration_hr=duration_hr,
                            total_depth_mm=hyetograph.total_depth_mm,
                            peak_intensity_mmhr=hyetograph.peak_intensity_mmhr,
                            n_intervals=len(hyetograph.time_min),
                            peak_flow_m3s=peak_flow,
                            time_to_peak_hr=time_to_peak,
                            volume_m3=volume_m3,
                            runoff_mm=runoff_mm,
                            x_factor=x if storm_code == "gz" else None,
                            tp_unit_hr=tp_unit_hr,
                            storm_time_min=list(hyetograph.time_min),
                            storm_intensity_mmhr=list(hyetograph.intensity_mmhr),
                            hydrograph_time_hr=[float(t) for t in hydrograph_time],
                            hydrograph_flow_m3s=[float(q) for q in hydrograph_flow],
                            **tc_params,
                        )

                        n_analyses += 1

                    # Solo un X para tormentas no-GZ
                    if storm_code != "gz":
                        break

        print_success(f"{n_analyses} analisis agregados")
        print_info(f"Total en sesion: {len(self.session.analyses) + n_analyses} analisis")

        return n_analyses
