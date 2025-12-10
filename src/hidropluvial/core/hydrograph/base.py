"""
Tipos base y parámetros temporales para hidrogramas.

Incluye:
- HydrographOutput: Dataclass de resultado
- Funciones de parámetros temporales SCS
- Cache para datos de hidrogramas unitarios
"""

import json
from pathlib import Path
from dataclasses import dataclass

from hidropluvial.config import HydrographMethod


@dataclass
class HydrographOutput:
    """Resultado de cálculo de hidrograma (uso interno del módulo core)."""
    time_hr: list[float]
    flow_m3s: list[float]
    peak_flow_m3s: float
    time_to_peak_hr: float
    volume_m3: float
    method: HydrographMethod


_DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Cache para datos de hidrogramas unitarios
_uh_cache: dict | None = None


def load_uh_data() -> dict:
    """Carga datos de hidrogramas unitarios desde JSON (con cache)."""
    global _uh_cache
    if _uh_cache is None:
        with open(_DATA_DIR / "unit_hydrographs.json") as f:
            _uh_cache = json.load(f)
    return _uh_cache


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


def recommended_dt(
    tc_hr: float,
    storm_method: str | None = None,
    min_dt_min: float = 5.0,
) -> float:
    """
    Calcula intervalo de tiempo recomendado con límite mínimo.

    ΔD ≤ 0.25 × Tp (recomendado: ΔD = 0.133 × Tc)

    Límites mínimos por metodología:
    - SCS 24h (Type I/IA/II/III): 15 min (resolución original NRCS)
    - Bloques Alternados: 5 min
    - DINAGUA: 5 min
    - Bimodal: 5 min
    - Default: 5 min

    Args:
        tc_hr: Tiempo de concentración en horas
        storm_method: Método de tormenta (opcional, para ajustar mínimo)
        min_dt_min: Límite mínimo absoluto en minutos (default 5)

    Returns:
        Intervalo recomendado en horas
    """
    # Calcular dt teórico
    dt_hr = 0.133 * tc_hr

    # Determinar límite mínimo según metodología
    method_min_dt_min = min_dt_min  # default 5 min

    if storm_method:
        storm_lower = storm_method.lower()
        # SCS 24h usa resolución mínima de 15 min (original NRCS: 30 min)
        if any(x in storm_lower for x in ['scs', 'type_i', 'type_ii', 'nrcs', '24h']):
            method_min_dt_min = 15.0
        # Bloques alternados puede usar 5 min
        elif 'block' in storm_lower or 'alternan' in storm_lower:
            method_min_dt_min = 5.0
        # DINAGUA usa 5 min mínimo
        elif 'dinagua' in storm_lower:
            method_min_dt_min = 5.0

    # Usar el mayor entre el mínimo de metodología y el mínimo absoluto
    effective_min_hr = max(method_min_dt_min, min_dt_min) / 60.0

    # Aplicar límite mínimo
    return max(dt_hr, effective_min_hr)


def get_dt_limits(storm_method: str | None = None) -> dict:
    """
    Obtiene los límites de dt recomendados según la metodología.

    Returns:
        Diccionario con:
        - min_dt_min: Límite mínimo en minutos
        - recommended_range: Rango recomendado (min, max) en minutos
        - reason: Razón del límite
    """
    if storm_method:
        storm_lower = storm_method.lower()

        # SCS 24h distributions
        if any(x in storm_lower for x in ['scs', 'type_i', 'type_ii', 'nrcs', '24h']):
            return {
                "min_dt_min": 15.0,
                "recommended_range": (15.0, 30.0),
                "reason": "NRCS 24h usa resolución original de 30 min, mínimo interpolado 15 min",
            }

        # Bloques alternados
        if 'block' in storm_lower or 'alternan' in storm_lower:
            return {
                "min_dt_min": 5.0,
                "recommended_range": (5.0, 15.0),
                "reason": "Bloques alternados permite mayor resolución, mínimo 5 min",
            }

        # DINAGUA
        if 'dinagua' in storm_lower:
            return {
                "min_dt_min": 5.0,
                "recommended_range": (5.0, 10.0),
                "reason": "DINAGUA GZ usa intervalos de 5-10 min típicamente",
            }

        # Bimodal
        if 'bimodal' in storm_lower:
            return {
                "min_dt_min": 5.0,
                "recommended_range": (5.0, 15.0),
                "reason": "Tormentas bimodales permiten 5-15 min",
            }

    # Default
    return {
        "min_dt_min": 5.0,
        "recommended_range": (5.0, 15.0),
        "reason": "Límite mínimo general de 5 min para evitar picos irreales de IDF",
    }
