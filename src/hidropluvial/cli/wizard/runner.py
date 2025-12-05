"""
AnalysisRunner - Ejecuta analisis hidrologicos.
"""

from typing import Optional

import numpy as np
import typer

from hidropluvial.cli.session.base import get_session_manager
from hidropluvial.cli.wizard.config import WizardConfig
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
from hidropluvial.core.coefficients import get_c_for_tr_from_table
from hidropluvial.session import Session, CoverageItem


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

    def __init__(self, config: WizardConfig):
        self.config = config
        self.manager = get_session_manager()
        self.session: Optional[Session] = None

    def run(self) -> Session:
        """Ejecuta el analisis completo y retorna la sesion."""
        self._create_session()
        self._calculate_tc()
        self._run_analyses()

        if self.config.output_name:
            self._generate_report()

        self._print_summary()
        return self.session

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

        typer.echo(f"  + Sesion creada: {self.session.id}")

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
                typer.echo(f"  + Tc ({method}): {result.tc_min:.1f} min")

    def _run_analyses(self) -> None:
        """Ejecuta todos los analisis."""
        n_analyses = 0

        for tc_result in self.session.tc_results:
            for storm_code in self.config.storm_codes:
                for tr in self.config.return_periods:
                    if storm_code == "gz":
                        # Multiples valores de X para GZ
                        for x in self.config.x_factors:
                            self._run_single_analysis(tc_result, tr, x, storm_code)
                            n_analyses += 1
                    else:
                        # Solo X=1.0 para tormentas no-GZ
                        self._run_single_analysis(tc_result, tr, 1.0, storm_code)
                        n_analyses += 1

        typer.echo(f"  + {n_analyses} analisis completados")

    def _run_single_analysis(self, tc_result, tr: int, x: float, storm_code: str) -> None:
        """Ejecuta un analisis individual."""
        p3_10 = self.config.p3_10
        area = self.config.area_ha

        # Obtener C ajustado para el Tr del análisis (si aplica)
        c_adjusted = None
        if self.config.c:
            c_adjusted = _get_c_for_tr(self.config, tr)

        # Recalcular Tc si es método Desbordes (depende de C y t0)
        if tc_result.method == "desbordes" and c_adjusted:
            tc_hr = desbordes(area, self.config.slope_pct, c_adjusted, self.config.t0_min)
        else:
            tc_hr = tc_result.tc_hr

        # Determinar duracion y dt
        if storm_code == "gz":
            duration_hr = 6.0
            dt = 5.0
        elif storm_code == "blocks24":
            duration_hr = 24.0
            dt = 10.0
        else:
            duration_hr = max(tc_hr, 1.0)
            dt = 5.0

        # Generar tormenta
        if storm_code == "gz":
            peak_position = 1.0 / 6.0
            hyetograph = alternating_blocks_dinagua(
                p3_10, tr, duration_hr, dt, None, peak_position
            )
        elif storm_code == "bimodal":
            hyetograph = bimodal_dinagua(p3_10, tr, duration_hr, dt)
        else:
            hyetograph = alternating_blocks_dinagua(
                p3_10, tr, duration_hr, dt, None
            )

        depths = np.array(hyetograph.depth_mm)

        # Escorrentia
        cn_adjusted = None
        if c_adjusted:
            excess_mm = c_adjusted * depths
            runoff_mm = float(np.sum(excess_mm))
        elif self.config.cn:
            # Ajustar CN por condición de humedad antecedente (AMC)
            amc_enum = _get_amc_enum(self.config.amc)
            cn_adjusted = adjust_cn_for_amc(self.config.cn, amc_enum)

            cumulative = np.array(hyetograph.cumulative_mm)
            excess_mm = rainfall_excess_series(
                cumulative, cn_adjusted, self.config.lambda_coef
            )
            runoff_mm = float(np.sum(excess_mm))
        else:
            return

        # Hidrograma unitario
        dt_hr = dt / 60
        x_val = x if storm_code == "gz" else 1.0

        if storm_code == "gz" or self.config.c:
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
                "t0_min": self.config.t0_min,
            }
        elif tc_result.parameters:
            tc_params = dict(tc_result.parameters)

        # Agregar parámetros de escorrentía SCS si aplica
        if cn_adjusted is not None:
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
            storm_time_min=list(hyetograph.time_min),
            storm_intensity_mmhr=list(hyetograph.intensity_mmhr),
            hydrograph_time_hr=[float(t) for t in hydrograph_time],
            hydrograph_flow_m3s=[float(q) for q in hydrograph_flow],
            **tc_params,
        )

    def _generate_report(self) -> None:
        """Genera reporte LaTeX."""
        from hidropluvial.cli.session.report import session_report

        typer.echo(f"\n  Generando reporte...")
        session_report(self.session.id, self.config.output_name, author=None, template_dir=None)

    def _print_summary(self) -> None:
        """Imprime resumen final."""
        typer.echo("\n" + "=" * 60)
        typer.echo("  ANALISIS COMPLETADO")
        typer.echo("=" * 60)

        rows = self.manager.get_summary_table(self.session)
        if rows:
            max_q = max(rows, key=lambda r: r['qpeak_m3s'])
            typer.echo(f"\n  Caudal maximo: {max_q['qpeak_m3s']:.3f} m3/s")
            typer.echo(f"  ({max_q['tc_method']} + {max_q['storm']} Tr{max_q['tr']})")

        typer.echo(f"\n  Sesion guardada: {self.session.id}")


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
    ):
        self.session = session
        self.manager = get_session_manager()
        self.c = c
        self.cn = cn
        self.amc = amc
        self.lambda_coef = lambda_coef
        self.t0_min = t0_min

    def run(
        self,
        tc_methods: list[str],
        storm_code: str,
        return_periods: list[int],
        x_factors: list[float],
    ) -> int:
        """Ejecuta analisis adicionales. Retorna cantidad de analisis agregados."""
        p3_10 = self.session.cuenca.p3_10
        area = self.session.cuenca.area_ha
        n_analyses = 0

        for tc_result in self.session.tc_results:
            if tc_result.method not in tc_methods:
                continue

            for tr in return_periods:
                for x in x_factors:
                    # Obtener C ajustado para el Tr del análisis (si aplica)
                    c_adjusted = None
                    if self.c:
                        c_adjusted = _get_c_for_tr_from_session(self.session, self.c, tr)

                    # Recalcular Tc si es método Desbordes (depende de C y t0)
                    if tc_result.method == "desbordes" and c_adjusted:
                        tc_hr = desbordes(area, self.session.cuenca.slope_pct, c_adjusted, self.t0_min)
                    else:
                        tc_hr = tc_result.tc_hr

                    # Determinar duracion
                    if storm_code == "gz":
                        duration_hr = 6.0
                        dt = 5.0
                    elif storm_code == "blocks24":
                        duration_hr = 24.0
                        dt = 10.0
                    else:
                        duration_hr = max(tc_hr, 1.0)
                        dt = 5.0

                    # Generar tormenta
                    if storm_code == "gz":
                        peak_position = 1.0 / 6.0
                        hyetograph = alternating_blocks_dinagua(
                            p3_10, tr, duration_hr, dt, None, peak_position
                        )
                    elif storm_code == "bimodal":
                        hyetograph = bimodal_dinagua(p3_10, tr, duration_hr, dt)
                    else:
                        hyetograph = alternating_blocks_dinagua(
                            p3_10, tr, duration_hr, dt, None
                        )

                    depths = np.array(hyetograph.depth_mm)

                    # Escorrentia
                    cn_adjusted = None
                    if c_adjusted:
                        excess_mm = c_adjusted * depths
                        runoff_mm = float(np.sum(excess_mm))
                    elif self.cn:
                        # Ajustar CN por condición de humedad antecedente (AMC)
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

                    if storm_code == "gz" or self.c:
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

                    # Agregar parámetros de escorrentía SCS si aplica
                    if cn_adjusted is not None:
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

        typer.echo(f"  + {n_analyses} analisis agregados")
        typer.echo(f"  Total en sesion: {len(self.session.analyses) + n_analyses} analisis")

        return n_analyses
