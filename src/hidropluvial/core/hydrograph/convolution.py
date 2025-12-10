"""
Convolución y funciones principales de hidrogramas.

Incluye:
- convolve_uh: Convolución de exceso de lluvia con hidrograma unitario
- generate_unit_hydrograph: Dispatcher para generar HU según método
- generate_hydrograph: Genera hidrograma completo desde exceso de lluvia
"""

import numpy as np
from numpy.typing import NDArray

from hidropluvial.config import HydrographMethod

from .base import HydrographOutput
from .scs import scs_triangular_uh, scs_curvilinear_uh
from .snyder import snyder_uh
from .clark import clark_uh


def convolve_uh(
    rainfall_excess: NDArray[np.floating],
    unit_hydrograph: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Convolución discreta de exceso de lluvia con hidrograma unitario.

    Qn = Σ(m=1 to M) [Pm × U(n-m+1)]

    Args:
        rainfall_excess: Array de exceso de lluvia incremental (mm)
        unit_hydrograph: Array de ordenadas del hidrograma unitario (m³/s por mm)

    Returns:
        Array del hidrograma resultante (m³/s)
    """
    return np.convolve(rainfall_excess, unit_hydrograph, mode='full')


def generate_unit_hydrograph(
    method: HydrographMethod,
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
    prf: int = 484,
    length_km: float | None = None,
    lc_km: float | None = None,
    ct: float = 2.0,
    cp: float = 0.6,
    r_hr: float | None = None,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario según el método especificado.

    Args:
        method: Método de hidrograma
        area_km2: Área de la cuenca (km²)
        tc_hr: Tiempo de concentración (hr)
        dt_hr: Intervalo de tiempo (hr)
        prf: Peak Rate Factor para SCS curvilíneo
        length_km: Longitud del cauce para Snyder (km)
        lc_km: Distancia al centroide para Snyder (km)
        ct: Coeficiente Ct para Snyder
        cp: Coeficiente Cp para Snyder
        r_hr: Coeficiente de almacenamiento para Clark (hr)

    Returns:
        Tupla (time_hr, flow_m3s)
    """
    if method == HydrographMethod.SCS_TRIANGULAR:
        return scs_triangular_uh(area_km2, tc_hr, dt_hr)

    elif method == HydrographMethod.SCS_CURVILINEAR:
        return scs_curvilinear_uh(area_km2, tc_hr, dt_hr, prf)

    elif method == HydrographMethod.SNYDER:
        if length_km is None or lc_km is None:
            raise ValueError("Snyder requiere length_km y lc_km")
        return snyder_uh(area_km2, length_km, lc_km, dt_hr, ct, cp)

    elif method == HydrographMethod.CLARK:
        if r_hr is None:
            # Usar ratio típico R/Tc = 2.0
            r_hr = 2.0 * tc_hr
        return clark_uh(area_km2, tc_hr, r_hr, dt_hr)

    else:
        raise ValueError(f"Método desconocido: {method}")


def generate_hydrograph(
    rainfall_excess_mm: NDArray[np.floating],
    method: HydrographMethod,
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
    **kwargs,
) -> HydrographOutput:
    """
    Genera hidrograma completo a partir de exceso de lluvia.

    Args:
        rainfall_excess_mm: Serie de exceso de lluvia (mm)
        method: Método de hidrograma unitario
        area_km2: Área de la cuenca (km²)
        tc_hr: Tiempo de concentración (hr)
        dt_hr: Intervalo de tiempo (hr)
        **kwargs: Parámetros adicionales según método

    Returns:
        HydrographOutput con el hidrograma resultante
    """
    # Generar hidrograma unitario
    uh_time, uh_flow = generate_unit_hydrograph(
        method, area_km2, tc_hr, dt_hr, **kwargs
    )

    # Convolución
    hydrograph = convolve_uh(rainfall_excess_mm, uh_flow)

    # Generar tiempos del hidrograma resultante
    n_excess = len(rainfall_excess_mm)
    n_uh = len(uh_flow)
    n_total = n_excess + n_uh - 1
    time = np.arange(n_total) * dt_hr

    # Encontrar pico
    peak_idx = np.argmax(hydrograph)
    peak_flow = float(hydrograph[peak_idx])
    time_to_peak = float(time[peak_idx])

    # Calcular volumen (integral trapezoidal)
    volume_m3 = float(np.trapezoid(hydrograph, time * 3600))  # m³

    return HydrographOutput(
        time_hr=time.tolist(),
        flow_m3s=hydrograph.tolist(),
        peak_flow_m3s=peak_flow,
        time_to_peak_hr=time_to_peak,
        volume_m3=volume_m3,
        method=method,
    )
