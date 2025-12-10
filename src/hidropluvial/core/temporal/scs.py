"""
Distribuciones SCS 24 horas (Tipos I, IA, II, III).

El Soil Conservation Service (ahora NRCS) definió cuatro distribuciones
temporales estándar para tormentas de 24 horas en Estados Unidos.
"""

import numpy as np

from hidropluvial.config import HyetographResult, StormMethod

from .base import load_scs_distributions


def scs_distribution(
    total_depth_mm: float,
    duration_hr: float,
    dt_min: float,
    storm_type: StormMethod,
) -> HyetographResult:
    """
    Genera hietograma usando distribución SCS 24 horas.

    Args:
        total_depth_mm: Profundidad total en mm
        duration_hr: Duración (normalmente 24 hr para SCS estándar)
        dt_min: Intervalo de tiempo en minutos
        storm_type: Tipo de tormenta SCS (I, IA, II, III)

    Returns:
        HyetographResult con el hietograma generado
    """
    # Mapear tipo de tormenta a clave JSON
    type_map = {
        StormMethod.SCS_TYPE_I: "scs_type_i",
        StormMethod.SCS_TYPE_IA: "scs_type_ia",
        StormMethod.SCS_TYPE_II: "scs_type_ii",
        StormMethod.SCS_TYPE_III: "scs_type_iii",
    }

    if storm_type not in type_map:
        raise ValueError(f"Tipo de tormenta inválido: {storm_type}")

    # Cargar distribución
    distributions = load_scs_distributions()
    dist_data = distributions[type_map[storm_type]]

    time_hr_ref = np.array(dist_data["time_hr"])
    ratio_ref = np.array(dist_data["ratio"])

    # Interpolar a intervalos dt_min
    n_intervals = int(duration_hr * 60 / dt_min)
    time_hr_interp = np.linspace(0, duration_hr, n_intervals + 1)

    # Escalar tiempo de referencia si duración != 24hr
    time_hr_scaled = time_hr_ref * duration_hr / 24.0

    # Interpolar ratios acumulados
    cumulative_ratio = np.interp(time_hr_interp, time_hr_scaled, ratio_ref)

    # Calcular profundidades incrementales
    cumulative_depth = cumulative_ratio * total_depth_mm
    incremental_depth = np.diff(cumulative_depth)

    # Tiempos centrales de cada intervalo
    time_centers_hr = (time_hr_interp[:-1] + time_hr_interp[1:]) / 2
    time_centers_min = time_centers_hr * 60

    # Intensidades
    intensities = incremental_depth * 60 / dt_min

    return HyetographResult(
        time_min=time_centers_min.tolist(),
        intensity_mmhr=intensities.tolist(),
        depth_mm=incremental_depth.tolist(),
        cumulative_mm=cumulative_depth[1:].tolist(),
        method=storm_type.value,
        total_depth_mm=float(np.sum(incremental_depth)),
        peak_intensity_mmhr=float(np.max(intensities)),
    )
