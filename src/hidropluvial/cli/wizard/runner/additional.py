"""
AdditionalAnalysisRunner - Ejecuta análisis adicionales sobre cuencas existentes.
"""

from typing import Optional, Tuple

import numpy as np

from hidropluvial.cli.theme import print_success, print_info
from hidropluvial.core import (
    kirpich,
    desbordes,
    temez,
    scs_triangular_uh,
    triangular_uh_x,
    convolve_uh,
    scs_time_to_peak,
)
from hidropluvial.core.tc import nrcs_velocity_method
from hidropluvial.models import Basin
from hidropluvial.database import get_database

from .helpers import get_c_for_tr_from_basin
from .generators import (
    get_storm_duration_and_dt,
    generate_hyetograph,
    calculate_runoff,
    create_analysis_results,
)


class AdditionalAnalysisRunner:
    """Ejecuta análisis adicionales sobre una cuenca existente."""

    def __init__(
        self,
        basin: Basin,
        c: float = None,
        cn: float = None,
        amc: str = "II",
        lambda_coef: float = 0.2,
        t0_min: float = 5.0,
        dt_min: float = 5.0,
        bimodal_duration_hr: float = 6.0,
        bimodal_peak1: float = 0.25,
        bimodal_peak2: float = 0.75,
        bimodal_vol_split: float = 0.5,
        bimodal_peak_width: float = 0.15,
        custom_depth_mm: float = None,
        custom_duration_hr: float = 6.0,
        custom_distribution: str = "alternating_blocks",
        custom_hyetograph_time: list = None,
        custom_hyetograph_depth: list = None,
    ):
        self.db = get_database()
        self.basin = basin
        self.c = c
        self.cn = cn
        self.amc = amc
        self.lambda_coef = lambda_coef
        self.t0_min = t0_min
        self.dt_min = dt_min
        self.bimodal_duration_hr = bimodal_duration_hr
        self.bimodal_peak1 = bimodal_peak1
        self.bimodal_peak2 = bimodal_peak2
        self.bimodal_vol_split = bimodal_vol_split
        self.bimodal_peak_width = bimodal_peak_width
        self.custom_depth_mm = custom_depth_mm
        self.custom_duration_hr = custom_duration_hr
        self.custom_distribution = custom_distribution
        self.custom_hyetograph_time = custom_hyetograph_time
        self.custom_hyetograph_depth = custom_hyetograph_depth

    def _calculate_tc(self, method: str, c_adjusted: float = None) -> Optional[Tuple[float, dict]]:
        """
        Calcula Tc para un método específico.

        El Tc se calcula por análisis (no por cuenca) porque algunos métodos
        dependen de parámetros del análisis (ej: Desbordes depende de C).

        Args:
            method: Nombre del método (desbordes, kirpich, temez, nrcs)
            c_adjusted: Coeficiente C ajustado para el Tr (solo para Desbordes)

        Returns:
            Tupla (tc_hr, tc_params) o None si no se puede calcular
        """
        area = self.basin.area_ha
        slope = self.basin.slope_pct
        length = self.basin.length_m

        if method == "desbordes":
            c_val = c_adjusted or self.c
            if not c_val:
                return None
            tc_hr = desbordes(area, slope, c_val, self.t0_min)
            tc_params = {
                "c": c_val,
                "area_ha": area,
                "t0_min": self.t0_min,
            }
            return tc_hr, tc_params

        elif method == "kirpich":
            if not length:
                return None
            tc_hr = kirpich(length, slope / 100)
            tc_params = {"length_m": length}
            return tc_hr, tc_params

        elif method == "temez":
            if not length:
                return None
            tc_hr = temez(length / 1000, slope / 100)
            tc_params = {"length_m": length}
            return tc_hr, tc_params

        elif method == "nrcs":
            from hidropluvial.cli.wizard.menus.add_analysis.nrcs_inline import (
                get_nrcs_state, get_nrcs_tc_parameters, get_nrcs_tc_value
            )
            nrcs_state = get_nrcs_state()

            if nrcs_state.segments:
                tc_hr = get_nrcs_tc_value()
                tc_params = get_nrcs_tc_parameters() or {}
                return tc_hr, tc_params
            elif self.basin.nrcs_segments:
                p2_mm = self.basin.p2_mm or 50.0
                tc_hr = nrcs_velocity_method(self.basin.nrcs_segments, p2_mm)
                tc_params = {
                    "p2_mm": p2_mm,
                    "segments": [
                        seg.model_dump() if hasattr(seg, 'model_dump') else seg.__dict__
                        for seg in self.basin.nrcs_segments
                    ],
                }
                return tc_hr, tc_params
            else:
                return None

        return None

    def run(
        self,
        tc_methods: list[str],
        storm_code: str,
        return_periods: list[int],
        x_factors: list[float],
        runoff_method: str = None,
    ) -> int:
        """
        Ejecuta análisis adicionales.

        El Tc se calcula por análisis (no por cuenca) porque algunos métodos
        dependen de parámetros del análisis (ej: Desbordes depende de C).

        Args:
            tc_methods: Lista de métodos de Tc (desbordes, kirpich, temez, nrcs)
            storm_code: Código de tormenta
            return_periods: Lista de períodos de retorno
            x_factors: Lista de factores X
            runoff_method: Método de escorrentía ('racional', 'scs-cn' o None para ambos)

        Returns:
            Cantidad de análisis agregados
        """
        p3_10 = self.basin.p3_10
        area = self.basin.area_ha
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

        for tc_method in tc_methods:
            for tr in return_periods:
                for x in x_factors:
                    for r_method in runoff_methods:
                        # Obtener C ajustado
                        c_adjusted = None
                        if r_method == "racional" and self.c:
                            c_adjusted = get_c_for_tr_from_basin(self.basin, self.c, tr)

                        # Calcular Tc
                        tc_result = self._calculate_tc(tc_method, c_adjusted)
                        if tc_result is None:
                            continue
                        tc_hr, tc_params = tc_result

                        # Duración y dt
                        duration_hr, dt = get_storm_duration_and_dt(
                            storm_code, tc_hr, self.dt_min,
                            self.bimodal_duration_hr,
                            self.custom_duration_hr,
                        )

                        # Generar tormenta
                        hyetograph = generate_hyetograph(
                            storm_code, p3_10, tr, duration_hr, dt,
                            bimodal_peak1=self.bimodal_peak1,
                            bimodal_peak2=self.bimodal_peak2,
                            bimodal_vol_split=self.bimodal_vol_split,
                            bimodal_peak_width=self.bimodal_peak_width,
                            custom_depth_mm=self.custom_depth_mm,
                            custom_distribution=self.custom_distribution,
                            custom_hyetograph_time=self.custom_hyetograph_time,
                            custom_hyetograph_depth=self.custom_hyetograph_depth,
                        )

                        depths = np.array(hyetograph.depth_mm)
                        cumulative = np.array(hyetograph.cumulative_mm)

                        # Escorrentía
                        excess_mm, runoff_mm, cn_adjusted = calculate_runoff(
                            depths, cumulative, r_method,
                            c_adjusted=c_adjusted,
                            cn=self.cn,
                            amc=self.amc,
                            lambda_coef=self.lambda_coef,
                        )

                        if excess_mm is None:
                            continue

                        # Hidrograma unitario
                        dt_hr = dt / 60
                        x_val = x if storm_code == "gz" else 1.0
                        tp_unit_hr = scs_time_to_peak(tc_hr, dt_hr)

                        if r_method == "racional" or storm_code == "gz":
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

                        # Agregar parámetros de escorrentía
                        tc_params["runoff_method"] = r_method
                        if r_method == "racional" and c_adjusted:
                            tc_params["c"] = round(c_adjusted, 3)
                        elif r_method == "scs-cn" and cn_adjusted is not None:
                            tc_params["cn_adjusted"] = round(cn_adjusted, 1)
                            tc_params["amc"] = self.amc
                            tc_params["lambda"] = self.lambda_coef

                        # Crear resultados
                        bimodal_params = None
                        if storm_code == "bimodal":
                            bimodal_params = {
                                "peak1": self.bimodal_peak1,
                                "peak2": self.bimodal_peak2,
                                "vol_split": self.bimodal_vol_split,
                                "peak_width": self.bimodal_peak_width,
                            }
                        tc_result_obj, storm_result, hydrograph_result = create_analysis_results(
                            tc_method, tc_hr, tc_params,
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
                        n_analyses += 1

                    # Solo un X para tormentas no-GZ
                    if storm_code != "gz":
                        break

        print_success(f"{n_analyses} analisis agregados")
        print_info(f"Total en cuenca: {len(self.basin.analyses)} analisis")

        return n_analyses
