"""
Módulo de hidrogramas unitarios sintéticos.

Implementa métodos para generar hidrogramas:
- SCS Triangular Unit Hydrograph
- SCS/NRCS Curvilinear (Dimensionless) Unit Hydrograph
- Snyder Synthetic Unit Hydrograph (1938)
- Clark Unit Hydrograph
- Convolución de exceso de lluvia
"""

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from hidropluvial.config import HydrographMethod, HydrographResult


_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_uh_data() -> dict:
    """Carga datos de hidrogramas unitarios desde JSON."""
    with open(_DATA_DIR / "unit_hydrographs.json") as f:
        return json.load(f)


# ============================================================================
# Parámetros Temporales
# ============================================================================

def scs_lag_time(tc_hr: float) -> float:
    """
    Calcula tiempo de retardo SCS.

    tlag = 0.6 × Tc

    Args:
        tc_hr: Tiempo de concentración en horas

    Returns:
        Tiempo de retardo en horas
    """
    return 0.6 * tc_hr


def scs_time_to_peak(tc_hr: float, dt_hr: float) -> float:
    """
    Calcula tiempo al pico SCS.

    Tp = ΔD/2 + tlag = ΔD/2 + 0.6×Tc

    Args:
        tc_hr: Tiempo de concentración en horas
        dt_hr: Duración del intervalo de exceso de lluvia (horas)

    Returns:
        Tiempo al pico en horas
    """
    tlag = scs_lag_time(tc_hr)
    return dt_hr / 2 + tlag


def scs_time_base(tp_hr: float) -> float:
    """
    Calcula tiempo base del hidrograma triangular SCS.

    Tb = 2.67 × Tp

    Args:
        tp_hr: Tiempo al pico en horas

    Returns:
        Tiempo base en horas
    """
    return 2.67 * tp_hr


def recommended_dt(tc_hr: float) -> float:
    """
    Calcula intervalo de tiempo recomendado.

    ΔD ≤ 0.25 × Tp (recomendado: ΔD = 0.133 × Tc)

    Args:
        tc_hr: Tiempo de concentración en horas

    Returns:
        Intervalo recomendado en horas
    """
    return 0.133 * tc_hr


# ============================================================================
# SCS Triangular Unit Hydrograph
# ============================================================================

def scs_triangular_peak(
    area_km2: float,
    runoff_mm: float,
    tp_hr: float,
) -> float:
    """
    Calcula caudal pico del hidrograma triangular SCS.

    qp = 2.08 × A × Q / Tp  [qp: m³/s, A: km², Q: mm, Tp: hr]

    Args:
        area_km2: Área de la cuenca en km²
        runoff_mm: Escorrentía directa en mm
        tp_hr: Tiempo al pico en horas

    Returns:
        Caudal pico en m³/s
    """
    if area_km2 <= 0:
        raise ValueError("Área debe ser > 0")
    if runoff_mm < 0:
        raise ValueError("Escorrentía no puede ser negativa")
    if tp_hr <= 0:
        raise ValueError("Tiempo al pico debe ser > 0")

    return 2.08 * area_km2 * runoff_mm / tp_hr


def scs_triangular_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario triangular SCS (1 mm de escorrentía).

    Args:
        area_km2: Área de la cuenca en km²
        tc_hr: Tiempo de concentración en horas
        dt_hr: Intervalo de tiempo en horas

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    tp = scs_time_to_peak(tc_hr, dt_hr)
    tb = scs_time_base(tp)
    tr = 1.67 * tp  # tiempo de recesión

    # Caudal pico para 1 mm de escorrentía
    qp = scs_triangular_peak(area_km2, 1.0, tp)

    # Generar tiempos
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Generar ordenadas del triángulo
    flow = np.zeros_like(time)
    for i, t in enumerate(time):
        if t <= tp:
            # Rama ascendente
            flow[i] = qp * t / tp
        else:
            # Rama descendente
            flow[i] = qp * (tb - t) / tr

    flow = np.maximum(flow, 0)  # Asegurar valores no negativos

    return time, flow


# ============================================================================
# SCS Curvilinear (Dimensionless) Unit Hydrograph
# ============================================================================

def scs_curvilinear_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
    prf: int = 484,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario curvilíneo SCS (1 mm de escorrentía).

    Args:
        area_km2: Área de la cuenca en km²
        tc_hr: Tiempo de concentración en horas
        dt_hr: Intervalo de tiempo en horas
        prf: Peak Rate Factor (default 484)

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    tp = scs_time_to_peak(tc_hr, dt_hr)

    # Caudal pico para 1 mm usando PRF
    # qp = PRF × A × Q / Tp  donde PRF=484 es el estándar
    qp = (prf / 484) * scs_triangular_peak(area_km2, 1.0, tp)

    # Cargar hidrograma adimensional
    uh_data = _load_uh_data()
    t_tp_std = np.array(uh_data["scs_curvilinear"]["t_Tp"])
    q_qp_std = np.array(uh_data["scs_curvilinear"]["q_qp"])

    # Escalar a valores reales
    tb = t_tp_std[-1] * tp  # tiempo base
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Interpolar ordenadas
    t_tp = time / tp
    flow = qp * np.interp(t_tp, t_tp_std, q_qp_std, right=0)

    return time, flow


def gamma_uh(
    area_km2: float,
    tc_hr: float,
    dt_hr: float,
    m: float = 3.7,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario usando ecuación Gamma.

    q/qp = e^m × (t/Tp)^m × e^(-m × t/Tp)

    Args:
        area_km2: Área de la cuenca en km²
        tc_hr: Tiempo de concentración en horas
        dt_hr: Intervalo de tiempo en horas
        m: Parámetro de forma (3.7 para PRF=484)

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    tp = scs_time_to_peak(tc_hr, dt_hr)

    # PRF aproximado según m
    prf_approx = 130 * m + 3  # Aproximación lineal
    qp = (prf_approx / 484) * scs_triangular_peak(area_km2, 1.0, tp)

    # Generar tiempos (hasta que el flujo sea ~0)
    tb = 5 * tp  # Tiempo base aproximado
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Ecuación Gamma
    t_tp = time / tp
    t_tp = np.maximum(t_tp, 1e-10)  # Evitar log(0)

    # q/qp = e^m × (t/Tp)^m × e^(-m × t/Tp) = (t/Tp)^m × e^(m × (1 - t/Tp))
    q_qp = (t_tp ** m) * np.exp(m * (1 - t_tp))
    flow = qp * q_qp

    return time, flow


# ============================================================================
# Snyder Synthetic Unit Hydrograph
# ============================================================================

def snyder_lag_time(
    length_km: float,
    lc_km: float,
    ct: float = 2.0,
) -> float:
    """
    Calcula tiempo de retardo Snyder.

    tp = Ct × (L × Lc)^0.3  [tp: hr, L/Lc: km]

    Args:
        length_km: Longitud del cauce principal (km)
        lc_km: Distancia desde salida hasta centroide de la cuenca (km)
        ct: Coeficiente Ct (1.8-2.2 típico)

    Returns:
        Tiempo de retardo en horas
    """
    # Convertir a millas para fórmula original
    length_mi = length_km * 0.621371
    lc_mi = lc_km * 0.621371

    return ct * ((length_mi * lc_mi) ** 0.3)


def snyder_peak(
    area_km2: float,
    tp_hr: float,
    cp: float = 0.6,
) -> float:
    """
    Calcula caudal pico Snyder para 1 pulgada de escorrentía.

    Qp = 640 × Cp × A / tp  [Qp: cfs, A: mi²]

    Args:
        area_km2: Área de la cuenca (km²)
        tp_hr: Tiempo de retardo (hr)
        cp: Coeficiente Cp (0.4-0.8 típico)

    Returns:
        Caudal pico en m³/s (para 25.4 mm de escorrentía)
    """
    area_mi2 = area_km2 * 0.386102
    qp_cfs = 640 * cp * area_mi2 / tp_hr
    qp_m3s = qp_cfs * 0.0283168  # Convertir cfs a m³/s

    return qp_m3s


def snyder_widths(qp_m3s: float, area_km2: float) -> tuple[float, float]:
    """
    Calcula anchos del hidrograma Snyder al 50% y 75% del pico.

    W50 = 770 × (Qp/A)^(-1.08)  [hr]
    W75 = 440 × (Qp/A)^(-1.08)  [hr]

    Args:
        qp_m3s: Caudal pico (m³/s)
        area_km2: Área de la cuenca (km²)

    Returns:
        Tupla (W50_hr, W75_hr)
    """
    # Convertir a unidades inglesas
    qp_cfs = qp_m3s / 0.0283168
    area_mi2 = area_km2 * 0.386102

    qp_a = qp_cfs / area_mi2
    w50 = 770 * (qp_a ** -1.08)
    w75 = 440 * (qp_a ** -1.08)

    return w50, w75


def snyder_uh(
    area_km2: float,
    length_km: float,
    lc_km: float,
    dt_hr: float,
    ct: float = 2.0,
    cp: float = 0.6,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario Snyder (25.4 mm de escorrentía).

    Args:
        area_km2: Área de la cuenca (km²)
        length_km: Longitud del cauce principal (km)
        lc_km: Distancia al centroide (km)
        dt_hr: Intervalo de tiempo (hr)
        ct: Coeficiente Ct
        cp: Coeficiente Cp

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    tp = snyder_lag_time(length_km, lc_km, ct)
    qp = snyder_peak(area_km2, tp, cp)
    w50, w75 = snyder_widths(qp, area_km2)

    # Duración unitaria estándar
    tr_std = tp / 5.5

    # Tiempo base aproximado
    tb = tp + 3 * w50

    # Generar forma usando anchos
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)
    flow = np.zeros_like(time)

    # Puntos clave: 1/3 antes del pico, 2/3 después
    t_rise_50 = tp - w50 / 3
    t_fall_50 = tp + 2 * w50 / 3
    t_rise_75 = tp - w75 / 3
    t_fall_75 = tp + 2 * w75 / 3

    # Interpolar forma del hidrograma
    t_key = np.array([0, t_rise_50, t_rise_75, tp, t_fall_75, t_fall_50, tb])
    q_key = np.array([0, 0.5 * qp, 0.75 * qp, qp, 0.75 * qp, 0.5 * qp, 0])

    # Ordenar y eliminar duplicados
    sorted_idx = np.argsort(t_key)
    t_key = t_key[sorted_idx]
    q_key = q_key[sorted_idx]

    flow = np.interp(time, t_key, q_key)
    flow = np.maximum(flow, 0)

    return time, flow


# ============================================================================
# Clark Unit Hydrograph
# ============================================================================

def clark_time_area(
    t_tc: NDArray[np.floating],
) -> NDArray[np.floating]:
    """
    Calcula relación tiempo-área por defecto (forma de diamante).

    A(t) = 1.414 × (t/Tc)^1.5           para t/Tc ≤ 0.5
    A(t) = 1 - 1.414 × (1 - t/Tc)^1.5   para t/Tc > 0.5

    Args:
        t_tc: Array de t/Tc (tiempo normalizado)

    Returns:
        Array de A/A_total (área acumulada normalizada)
    """
    a_at = np.zeros_like(t_tc)

    mask_rise = t_tc <= 0.5
    a_at[mask_rise] = 1.414 * (t_tc[mask_rise] ** 1.5)
    a_at[~mask_rise] = 1 - 1.414 * ((1 - t_tc[~mask_rise]) ** 1.5)

    return np.clip(a_at, 0, 1)


def clark_uh(
    area_km2: float,
    tc_hr: float,
    r_hr: float,
    dt_hr: float,
) -> tuple[NDArray[np.floating], NDArray[np.floating]]:
    """
    Genera hidrograma unitario Clark (1 mm de escorrentía).

    Args:
        area_km2: Área de la cuenca (km²)
        tc_hr: Tiempo de concentración (hr)
        r_hr: Coeficiente de almacenamiento R (hr)
        dt_hr: Intervalo de tiempo (hr)

    Returns:
        Tupla (time_hr, flow_m3s) del hidrograma unitario
    """
    # Coeficientes de routing lineal
    c1 = dt_hr / (2 * r_hr + dt_hr)
    c2 = c1
    c0 = (2 * r_hr - dt_hr) / (2 * r_hr + dt_hr)

    # Tiempo base (aproximado)
    tb = tc_hr + 5 * r_hr
    n_points = int(np.ceil(tb / dt_hr)) + 1
    time = np.linspace(0, tb, n_points)

    # Calcular entrada al reservorio desde curva tiempo-área
    t_tc = time / tc_hr
    area_cum = clark_time_area(np.minimum(t_tc, 1.0))

    # Área incremental (histograma de entrada)
    area_incr = np.zeros(n_points)
    area_incr[1:] = np.diff(area_cum)
    area_incr[0] = area_cum[0]

    # Inflow al reservorio (mm/hr × área → m³/s)
    # Para 1 mm de escorrentía distribuido uniformemente en tc
    inflow = area_incr * area_km2 * 1000 / (dt_hr * 3600)  # m³/s

    # Routing a través del reservorio lineal
    outflow = np.zeros(n_points)
    for i in range(1, n_points):
        outflow[i] = c1 * inflow[i] + c2 * inflow[i-1] + c0 * outflow[i-1]

    return time, outflow


# ============================================================================
# Convolución
# ============================================================================

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


# ============================================================================
# Función Principal
# ============================================================================

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
) -> HydrographResult:
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
        HydrographResult con el hidrograma resultante
    """
    # Generar hidrograma unitario
    uh_time, uh_flow = generate_unit_hydrograph(
        method, area_km2, tc_hr, dt_hr, **kwargs
    )

    # Normalizar UH para que sea por mm de escorrentía
    # (ya debería estar normalizado)

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
    volume_m3 = float(np.trapz(hydrograph, time * 3600))  # m³

    return HydrographResult(
        time_hr=time.tolist(),
        flow_m3s=hydrograph.tolist(),
        peak_flow_m3s=peak_flow,
        time_to_peak_hr=time_to_peak,
        volume_m3=volume_m3,
        method=method,
    )
