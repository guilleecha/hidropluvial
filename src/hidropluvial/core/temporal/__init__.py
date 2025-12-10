"""
Módulo de distribuciones temporales de lluvia.

Implementa métodos para generar hietogramas de diseño:
- Método de Bloques Alternantes (con soporte DINAGUA Uruguay)
- Tormenta de Diseño Chicago (Keifer & Chu 1957)
- Distribuciones SCS 24h (Tipos I, IA, II, III)
- Curvas Huff (1967)
- Tormentas Bimodales
"""

# Bloques alternantes
from .blocks import alternating_blocks, alternating_blocks_dinagua

# Tormenta Chicago
from .chicago import chicago_storm

# Distribuciones SCS
from .scs import scs_distribution

# Curvas Huff
from .huff import huff_distribution

# Tormentas bimodales
from .bimodal import bimodal_storm, bimodal_dinagua, bimodal_chicago

# Custom y funciones principales
from .custom import (
    custom_depth_storm,
    custom_hyetograph,
    generate_hyetograph,
    generate_hyetograph_dinagua,
)

__all__ = [
    # Bloques alternantes
    "alternating_blocks",
    "alternating_blocks_dinagua",
    # Chicago
    "chicago_storm",
    # SCS
    "scs_distribution",
    # Huff
    "huff_distribution",
    # Bimodal
    "bimodal_storm",
    "bimodal_dinagua",
    "bimodal_chicago",
    # Custom
    "custom_depth_storm",
    "custom_hyetograph",
    # Dispatchers
    "generate_hyetograph",
    "generate_hyetograph_dinagua",
]
