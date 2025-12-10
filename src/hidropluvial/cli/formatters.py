"""
Utilidades de formateo para la CLI de HidroPluvial.
"""


def format_flow(flow_m3s: float) -> str:
    """
    Formatea caudal con máximo 3 decimales.

    Args:
        flow_m3s: Caudal en m³/s

    Returns:
        String formateado (ej: "0.15", "1.2", "12", "120")
    """
    if flow_m3s is None:
        return "-"
    if flow_m3s == 0:
        return "0"
    if flow_m3s >= 100:
        return f"{flow_m3s:.0f}"
    elif flow_m3s >= 10:
        return f"{flow_m3s:.1f}"
    elif flow_m3s >= 1:
        return f"{flow_m3s:.2f}"
    elif flow_m3s >= 0.001:
        return f"{flow_m3s:.3f}"
    else:
        # Valores muy pequeños: mostrar como 0.00
        return "0.00"


def format_volume_hm3(volume_m3: float) -> str:
    """
    Formatea volumen en hm³ (1 hm³ = 1,000,000 m³) con máximo 3 decimales.

    Args:
        volume_m3: Volumen en m³

    Returns:
        String formateado en hm³ (ej: "0.012", "0.15", "1.2")
    """
    if volume_m3 is None:
        return "-"
    hm3 = volume_m3 / 1_000_000
    if hm3 == 0:
        return "0"
    # Formatear según magnitud, máximo 3 decimales
    if hm3 >= 100:
        return f"{hm3:.0f}"
    elif hm3 >= 10:
        return f"{hm3:.1f}"
    elif hm3 >= 1:
        return f"{hm3:.2f}"
    elif hm3 >= 0.001:
        return f"{hm3:.3f}"
    else:
        # Valores muy pequeños: mostrar como 0.00
        return "0.00"
