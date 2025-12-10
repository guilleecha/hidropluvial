"""
Tablas de Curva Número (CN) SCS/NRCS.

Fuente: SCS/NRCS TR-55
"""

from .types import CNEntry


# Tabla unificada SCS TR-55 (urbanas + agrícolas)
SCS_CN_TABLE = [
    # ===== ÁREAS URBANAS =====
    # Residencial por tamaño de lote
    CNEntry("Residencial", "Lotes 500 m² (65% impermeable)", "N/A", 77, 85, 90, 92),
    CNEntry("Residencial", "Lotes 1000 m² (38% impermeable)", "N/A", 61, 75, 83, 87),
    CNEntry("Residencial", "Lotes 1500 m² (30% impermeable)", "N/A", 57, 72, 81, 86),
    CNEntry("Residencial", "Lotes 2000 m² (25% impermeable)", "N/A", 54, 70, 80, 85),
    CNEntry("Residencial", "Lotes 4000 m² (20% impermeable)", "N/A", 51, 68, 79, 84),
    # Comercial e industrial
    CNEntry("Comercial", "Distritos comerciales (85% imp)", "N/A", 89, 92, 94, 95),
    CNEntry("Industrial", "Distritos industriales (72% imp)", "N/A", 81, 88, 91, 93),
    # Superficies impermeables
    CNEntry("Superficies", "Pavimento impermeable", "N/A", 98, 98, 98, 98),
    CNEntry("Superficies", "Grava", "N/A", 76, 85, 89, 91),
    CNEntry("Superficies", "Tierra", "N/A", 72, 82, 87, 89),
    # Espacios abiertos
    CNEntry("Espacios abiertos", "Césped >75% cubierto", "Buena", 39, 61, 74, 80),
    CNEntry("Espacios abiertos", "Césped 50-75% cubierto", "Regular", 49, 69, 79, 84),
    CNEntry("Espacios abiertos", "Césped <50% cubierto", "Mala", 68, 79, 86, 89),
    # ===== ÁREAS AGRÍCOLAS =====
    CNEntry("Barbecho", "Suelo desnudo", "N/A", 77, 86, 91, 94),
    CNEntry("Cultivos", "Hileras rectas", "Mala", 72, 81, 88, 91),
    CNEntry("Cultivos", "Hileras rectas", "Buena", 67, 78, 85, 89),
    CNEntry("Cultivos", "Hileras en contorno", "Mala", 70, 79, 84, 88),
    CNEntry("Cultivos", "Hileras en contorno", "Buena", 65, 75, 82, 86),
    CNEntry("Cultivos", "Terrazas", "Mala", 66, 74, 80, 82),
    CNEntry("Cultivos", "Terrazas", "Buena", 62, 71, 78, 81),
    CNEntry("Pasturas", "Continua", "Mala", 68, 79, 86, 89),
    CNEntry("Pasturas", "Continua", "Regular", 49, 69, 79, 84),
    CNEntry("Pasturas", "Continua", "Buena", 39, 61, 74, 80),
    CNEntry("Pradera", "Natural", "Buena", 30, 58, 71, 78),
    CNEntry("Bosque", "Con mantillo", "Mala", 45, 66, 77, 83),
    CNEntry("Bosque", "Con mantillo", "Regular", 36, 60, 73, 79),
    CNEntry("Bosque", "Con mantillo", "Buena", 30, 55, 70, 77),
]

# Mantener referencias legacy para compatibilidad
SCS_CN_URBAN = SCS_CN_TABLE[:13]  # Primeras 13 entradas (urbanas)
SCS_CN_AGRICULTURAL = SCS_CN_TABLE[13:]  # Resto (agrícolas)


# Diccionario de tablas disponibles
CN_TABLES = {
    "unified": ("SCS TR-55 - Tabla Unificada", SCS_CN_TABLE),
    # Legacy - mantener por compatibilidad
    "urban": ("SCS TR-55 - Áreas Urbanas", SCS_CN_URBAN),
    "agricultural": ("SCS TR-55 - Áreas Agrícolas", SCS_CN_AGRICULTURAL),
}
