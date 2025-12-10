"""
Opciones predefinidas para el formulario de análisis.

Define las opciones de tormenta, período de retorno, factor X, etc.
"""

# Opciones de tipo de tormenta
STORM_OPTIONS = [
    {"name": "GZ (6 horas) - DINAGUA Uruguay", "value": "gz"},
    {"name": "Bloques alternantes (2×Tc)", "value": "blocks"},
    {"name": "Bloques 24 horas", "value": "blocks24"},
    {"name": "Bimodal Uruguay", "value": "bimodal"},
]

# Opciones de período de retorno (años)
RETURN_PERIOD_OPTIONS = [
    {"name": "2 años", "value": 2},
    {"name": "5 años", "value": 5},
    {"name": "10 años", "value": 10},
    {"name": "25 años", "value": 25},
    {"name": "50 años", "value": 50},
    {"name": "100 años", "value": 100},
]

# Opciones de factor X (forma del hidrograma) - Porto, 1995
X_FACTOR_OPTIONS = [
    {"name": "1.00 - Racional/urbano", "value": 1.00},
    {"name": "1.25 - Urbano (pendiente)", "value": 1.25},
    {"name": "1.67 - NRCS estándar", "value": 1.67},
    {"name": "2.25 - Mixto rural/urbano", "value": 2.25},
    {"name": "3.33 - Rural sinuoso", "value": 3.33},
    {"name": "5.50 - Rural (pendiente baja)", "value": 5.50},
    {"name": "12.0 - Rural (pendiente muy baja)", "value": 12.0},
]

# Opciones de método de escorrentía
RUNOFF_METHOD_OPTIONS = [
    {"name": "Método Racional (C)", "value": "C"},
    {"name": "Método NRCS (CN)", "value": "CN"},
]

# Valores por defecto
DEFAULT_STORM = "gz"
DEFAULT_RETURN_PERIOD = 10
DEFAULT_X_FACTOR = 1.0
DEFAULT_RUNOFF_METHOD = "C"
