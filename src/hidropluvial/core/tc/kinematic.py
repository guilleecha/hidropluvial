"""
Método de onda cinemática para tiempo de concentración.

Método iterativo que considera la relación entre intensidad
y tiempo de concentración.
"""


def kinematic_wave(
    length_m: float,
    n: float,
    slope: float,
    intensity_mmhr: float,
    max_iterations: int = 20,
    tolerance: float = 0.01,
) -> float:
    """
    Calcula Tc usando onda cinemática (método iterativo).

    tc = 6.99 × (n × L)^0.6 / (i^0.4 × S^0.3)  [tc: min, L: m, i: mm/hr]

    Args:
        length_m: Longitud del flujo en metros
        n: Coeficiente de Manning
        slope: Pendiente (m/m)
        intensity_mmhr: Intensidad de lluvia inicial (mm/hr)
        max_iterations: Máximo de iteraciones
        tolerance: Tolerancia para convergencia (horas)

    Returns:
        Tiempo de concentración en horas
    """
    if length_m <= 0:
        raise ValueError("Longitud debe ser > 0")
    if n <= 0:
        raise ValueError("Coeficiente n debe ser > 0")
    if slope <= 0:
        raise ValueError("Pendiente debe ser > 0")
    if intensity_mmhr <= 0:
        raise ValueError("Intensidad debe ser > 0")

    # Valor inicial
    i = intensity_mmhr
    tc_prev = 0.0

    for _ in range(max_iterations):
        # Fórmula de onda cinemática (resultado en minutos)
        tc_min = 6.99 * ((n * length_m) ** 0.6) / ((i ** 0.4) * (slope ** 0.3))
        tc_hr = tc_min / 60.0

        if abs(tc_hr - tc_prev) < tolerance:
            return tc_hr

        tc_prev = tc_hr
        # La intensidad podría actualizarse aquí si se tiene curva IDF

    return tc_hr
