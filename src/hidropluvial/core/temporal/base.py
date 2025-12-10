"""
Utilidades base para distribuciones temporales de lluvia.

Incluye:
- Carga de datos JSON con cache
- Función de distribución de bloques alternantes
"""

import json
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


# Directorio de datos
_DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Cache para datos JSON (evita recargar en cada llamada)
_scs_cache: dict | None = None
_huff_cache: dict | None = None


def load_scs_distributions() -> dict:
    """Carga distribuciones SCS desde JSON (con cache)."""
    global _scs_cache
    if _scs_cache is None:
        with open(_DATA_DIR / "scs_distributions.json") as f:
            _scs_cache = json.load(f)
    return _scs_cache


def load_huff_curves() -> dict:
    """Carga curvas Huff desde JSON (con cache)."""
    global _huff_cache
    if _huff_cache is None:
        with open(_DATA_DIR / "huff_curves.json") as f:
            _huff_cache = json.load(f)
    return _huff_cache


def distribute_alternating_blocks(
    sorted_increments: NDArray[np.floating],
    n_intervals: int,
    peak_position: float = 0.5,
) -> NDArray[np.floating]:
    """
    Distribuye incrementos alternando alrededor del pico.

    Algoritmo estándar de bloques alternantes:
    1. Coloca el mayor incremento en la posición del pico
    2. Alterna entre izquierda y derecha para los siguientes

    Args:
        sorted_increments: Incrementos ordenados de mayor a menor
        n_intervals: Número total de intervalos
        peak_position: Posición del pico (0-1), default 0.5 (centro)

    Returns:
        Array con incrementos distribuidos
    """
    peak_index = int(peak_position * n_intervals)
    result_depths = np.zeros(n_intervals)

    left = peak_index
    right = peak_index + 1
    toggle = True  # True = izquierda, False = derecha

    for inc in sorted_increments:
        if toggle and left >= 0:
            result_depths[left] = inc
            left -= 1
        elif not toggle and right < n_intervals:
            result_depths[right] = inc
            right += 1
        elif left >= 0:
            result_depths[left] = inc
            left -= 1
        elif right < n_intervals:
            result_depths[right] = inc
            right += 1
        toggle = not toggle

    return result_depths
