"""
Constantes para cálculos de tiempo de concentración.

Coeficientes para flujo laminar y concentrado superficial.
"""

# Constantes para flujo concentrado superficial (shallow flow)
SHALLOW_FLOW_K = {
    "paved": 6.196,      # k = 20.3 ft/s convertido a m/s (×0.3048)
    "unpaved": 4.918,    # k = 16.1 ft/s
    "grassed": 4.572,    # k = 15.0 ft/s
    "short_grass": 2.134,  # k = 7.0 ft/s
}

# Coeficientes de Manning para flujo laminar (sheet flow)
SHEET_FLOW_N = {
    "smooth": 0.011,
    "fallow": 0.05,
    "short_grass": 0.15,
    "dense_grass": 0.24,
    "light_woods": 0.40,
    "dense_woods": 0.80,
}
