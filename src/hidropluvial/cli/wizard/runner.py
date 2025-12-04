"""
AnalysisRunner - Ejecuta analisis hidrologicos.
"""

from typing import Optional

import numpy as np
import typer

from hidropluvial.cli.session.base import get_session_manager
from hidropluvial.cli.wizard.config import WizardConfig
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
)
from hidropluvial.session import Session


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
        typer.echo(f"  + Sesion creada: {self.session.id}")

    def _calculate_tc(self) -> None:
        """Calcula tiempo de concentracion con los metodos seleccionados."""
        for method_str in self.config.tc_methods:
            method = method_str.split()[0].lower()
            tc_hr = None

            if method == "kirpich" and self.config.length_m:
                tc_hr = kirpich(self.config.length_m, self.config.slope_pct / 100)
            elif method == "temez" and self.config.length_m:
                tc_hr = temez(self.config.length_m / 1000, self.config.slope_pct / 100)
            elif method == "desbordes" and self.config.c:
                tc_hr = desbordes(self.config.area_ha, self.config.slope_pct, self.config.c)

            if tc_hr:
                result = self.manager.add_tc_result(self.session, method, tc_hr)
                typer.echo(f"  + Tc ({method}): {result.tc_min:.1f} min")

    def _run_analyses(self) -> None:
        """Ejecuta todos los analisis."""
        n_analyses = 0

        for tc_result in self.session.tc_results:
            for tr in self.config.return_periods:
                for x in self.config.x_factors:
                    self._run_single_analysis(tc_result, tr, x)
                    n_analyses += 1

                    # Solo un X para tormentas no-GZ
                    if self.config.storm_code != "gz":
                        break

        typer.echo(f"  + {n_analyses} analisis completados")

    def _run_single_analysis(self, tc_result, tr: int, x: float) -> None:
        """Ejecuta un analisis individual."""
        tc_hr = tc_result.tc_hr
        storm_code = self.config.storm_code
        p3_10 = self.config.p3_10
        area = self.config.area_ha

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
        if self.config.c:
            excess_mm = self.config.c * depths
            runoff_mm = float(np.sum(excess_mm))
        elif self.config.cn:
            cumulative = np.array(hyetograph.cumulative_mm)
            excess_mm = rainfall_excess_series(cumulative, self.config.cn)
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

    def __init__(self, session: Session, c: float = None, cn: float = None):
        self.session = session
        self.manager = get_session_manager()
        self.c = c
        self.cn = cn

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
                    if self.c:
                        excess_mm = self.c * depths
                        runoff_mm = float(np.sum(excess_mm))
                    elif self.cn:
                        cumulative = np.array(hyetograph.cumulative_mm)
                        excess_mm = rainfall_excess_series(cumulative, self.cn)
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
                    )

                    n_analyses += 1

                    # Solo un X para tormentas no-GZ
                    if storm_code != "gz":
                        break

        typer.echo(f"  + {n_analyses} analisis agregados")
        typer.echo(f"  Total en sesion: {len(self.session.analyses) + n_analyses} analisis")

        return n_analyses
