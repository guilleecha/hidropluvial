"""
Tablas de coeficientes de escorrentia C y Curva Numero CN.

Fuentes:
- FHWA HEC-22 (Federal Highway Administration)
- Ven Te Chow - Applied Hydrology (Table 5.5.2)
- SCS/NRCS TR-55
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CoefficientEntry:
    """Entrada de tabla de coeficientes (rango simple)."""
    category: str
    description: str
    c_min: float
    c_max: float
    c_typical: Optional[float] = None

    @property
    def c_range(self) -> str:
        return f"{self.c_min:.2f}-{self.c_max:.2f}"

    @property
    def c_recommended(self) -> float:
        """Retorna valor tipico o promedio."""
        if self.c_typical:
            return self.c_typical
        return (self.c_min + self.c_max) / 2


@dataclass
class ChowCEntry:
    """
    Entrada de tabla Ven Te Chow con C por periodo de retorno.

    Tabla 5.5.2 de Applied Hydrology - C varia segun Tr.
    """
    category: str
    description: str
    c_tr2: float   # C para Tr = 2 anos
    c_tr5: float   # C para Tr = 5 anos
    c_tr10: float  # C para Tr = 10 anos
    c_tr25: float  # C para Tr = 25 anos
    c_tr50: float  # C para Tr = 50 anos
    c_tr100: float # C para Tr = 100 anos

    def get_c(self, tr: int) -> float:
        """Obtiene C para un periodo de retorno dado (interpola si es necesario)."""
        tr_values = [2, 5, 10, 25, 50, 100]
        c_values = [self.c_tr2, self.c_tr5, self.c_tr10, self.c_tr25, self.c_tr50, self.c_tr100]

        if tr <= 2:
            return self.c_tr2
        if tr >= 100:
            return self.c_tr100

        # Interpolacion lineal
        for i in range(len(tr_values) - 1):
            if tr_values[i] <= tr <= tr_values[i + 1]:
                t1, t2 = tr_values[i], tr_values[i + 1]
                c1, c2 = c_values[i], c_values[i + 1]
                return c1 + (c2 - c1) * (tr - t1) / (t2 - t1)

        return self.c_tr10  # Default


@dataclass
class FHWACEntry:
    """
    Entrada de tabla FHWA HEC-22.

    C base para Tr = 2-10 anos, con factor de ajuste para otros Tr.
    """
    category: str
    description: str
    c_base: float  # C para Tr = 2-10 anos

    def get_c(self, tr: int) -> float:
        """
        Obtiene C ajustado para periodo de retorno.

        Factores de ajuste FHWA:
        - Tr <= 10: factor = 1.0
        - Tr = 25: factor = 1.1
        - Tr = 50: factor = 1.2
        - Tr = 100: factor = 1.25
        """
        if tr <= 10:
            factor = 1.0
        elif tr <= 25:
            # Interpolar entre 10 y 25
            factor = 1.0 + 0.1 * (tr - 10) / 15
        elif tr <= 50:
            # Interpolar entre 25 y 50
            factor = 1.1 + 0.1 * (tr - 25) / 25
        elif tr <= 100:
            # Interpolar entre 50 y 100
            factor = 1.2 + 0.05 * (tr - 50) / 50
        else:
            factor = 1.25

        # C no puede exceder 1.0
        return min(self.c_base * factor, 1.0)


@dataclass
class CNEntry:
    """Entrada de tabla de Curva Numero."""
    category: str
    description: str
    condition: str  # Buena, Regular, Mala
    cn_a: int  # Grupo hidrologico A
    cn_b: int  # Grupo hidrologico B
    cn_c: int  # Grupo hidrologico C
    cn_d: int  # Grupo hidrologico D

    def get_cn(self, soil_group: str) -> int:
        """Obtiene CN para grupo de suelo."""
        group_map = {
            'A': self.cn_a,
            'B': self.cn_b,
            'C': self.cn_c,
            'D': self.cn_d,
        }
        return group_map.get(soil_group.upper(), self.cn_b)


# =============================================================================
# TABLAS DE COEFICIENTE C
# =============================================================================

# Tabla FHWA HEC-22 (Urban Drainage Design Manual)
# C base para Tr = 2-10 anos, usar get_c(tr) para ajustar
FHWA_C_TABLE = [
    # Zonas desarrolladas
    FHWACEntry("Comercial", "Centro comercial/negocios", 0.85),
    FHWACEntry("Comercial", "Vecindario comercial", 0.60),
    FHWACEntry("Industrial", "Industria liviana", 0.65),
    FHWACEntry("Industrial", "Industria pesada", 0.75),
    # Residencial
    FHWACEntry("Residencial", "Unifamiliar (lotes >1000 m2)", 0.40),
    FHWACEntry("Residencial", "Unifamiliar (lotes 500-1000 m2)", 0.50),
    FHWACEntry("Residencial", "Unifamiliar (lotes <500 m2)", 0.60),
    FHWACEntry("Residencial", "Multifamiliar/Apartamentos", 0.70),
    FHWACEntry("Residencial", "Condominios/Townhouse", 0.60),
    # Superficies
    FHWACEntry("Superficies", "Asfalto/Concreto", 0.85),
    FHWACEntry("Superficies", "Adoquin/Ladrillo", 0.78),
    FHWACEntry("Superficies", "Techos", 0.85),
    FHWACEntry("Superficies", "Grava/Ripio", 0.32),
    # Areas verdes (suelo arenoso)
    FHWACEntry("Cesped arenoso", "Pendiente plana <2%", 0.08),
    FHWACEntry("Cesped arenoso", "Pendiente media 2-7%", 0.12),
    FHWACEntry("Cesped arenoso", "Pendiente alta >7%", 0.18),
    # Areas verdes (suelo arcilloso)
    FHWACEntry("Cesped arcilloso", "Pendiente plana <2%", 0.15),
    FHWACEntry("Cesped arcilloso", "Pendiente media 2-7%", 0.20),
    FHWACEntry("Cesped arcilloso", "Pendiente alta >7%", 0.28),
]

# Tabla Ven Te Chow - Applied Hydrology (Table 5.5.2)
# Valores de C para diferentes periodos de retorno
#                                                    Tr2   Tr5   Tr10  Tr25  Tr50  Tr100
VEN_TE_CHOW_C_TABLE = [
    # Zonas desarrolladas
    ChowCEntry("Comercial", "Centro comercial denso",    0.75, 0.80, 0.85, 0.88, 0.90, 0.95),
    ChowCEntry("Comercial", "Vecindario comercial",      0.50, 0.55, 0.60, 0.65, 0.70, 0.75),
    ChowCEntry("Residencial", "Unifamiliar",             0.25, 0.30, 0.35, 0.40, 0.45, 0.50),
    ChowCEntry("Residencial", "Multifamiliar separado",  0.35, 0.40, 0.45, 0.50, 0.55, 0.60),
    ChowCEntry("Residencial", "Multifamiliar adosado",   0.45, 0.50, 0.55, 0.60, 0.65, 0.70),
    ChowCEntry("Residencial", "Suburbano",               0.20, 0.25, 0.30, 0.35, 0.40, 0.45),
    ChowCEntry("Residencial", "Apartamentos",            0.50, 0.55, 0.60, 0.65, 0.70, 0.75),
    ChowCEntry("Industrial", "Liviana",                  0.50, 0.55, 0.60, 0.65, 0.70, 0.80),
    ChowCEntry("Industrial", "Pesada",                   0.60, 0.65, 0.70, 0.75, 0.80, 0.85),
    # Superficies
    ChowCEntry("Superficies", "Pavimento asfaltico",     0.70, 0.75, 0.80, 0.85, 0.90, 0.95),
    ChowCEntry("Superficies", "Pavimento concreto",      0.75, 0.80, 0.85, 0.90, 0.92, 0.95),
    ChowCEntry("Superficies", "Techos",                  0.75, 0.80, 0.85, 0.90, 0.92, 0.95),
    ChowCEntry("Superficies", "Adoquin con juntas",      0.50, 0.55, 0.60, 0.65, 0.70, 0.75),
    ChowCEntry("Superficies", "Grava/Macadam",           0.25, 0.30, 0.35, 0.40, 0.45, 0.50),
    # Cesped suelo arenoso
    ChowCEntry("Cesped arenoso", "Plano (<2%)",          0.05, 0.08, 0.10, 0.13, 0.15, 0.18),
    ChowCEntry("Cesped arenoso", "Medio (2-7%)",         0.10, 0.13, 0.16, 0.19, 0.22, 0.25),
    ChowCEntry("Cesped arenoso", "Fuerte (>7%)",         0.15, 0.18, 0.21, 0.25, 0.29, 0.32),
    # Cesped suelo arcilloso pesado
    ChowCEntry("Cesped arcilloso", "Plano (<2%)",        0.13, 0.16, 0.19, 0.23, 0.26, 0.29),
    ChowCEntry("Cesped arcilloso", "Medio (2-7%)",       0.18, 0.21, 0.25, 0.29, 0.34, 0.37),
    ChowCEntry("Cesped arcilloso", "Fuerte (>7%)",       0.25, 0.29, 0.34, 0.40, 0.44, 0.50),
]

# Tabla simplificada Uruguay/Regional (rangos generales)
URUGUAY_C_TABLE = [
    # Zonas urbanas tipicas
    CoefficientEntry("Urbano", "Centro ciudad (muy denso)", 0.70, 0.90, 0.80),
    CoefficientEntry("Urbano", "Comercial/Mixto", 0.60, 0.80, 0.70),
    CoefficientEntry("Urbano", "Residencial alta densidad", 0.50, 0.70, 0.60),
    CoefficientEntry("Urbano", "Residencial media densidad", 0.40, 0.60, 0.50),
    CoefficientEntry("Urbano", "Residencial baja densidad", 0.30, 0.50, 0.40),
    CoefficientEntry("Urbano", "Industrial", 0.60, 0.85, 0.72),
    # Superficies
    CoefficientEntry("Superficies", "Calles pavimentadas", 0.80, 0.95, 0.88),
    CoefficientEntry("Superficies", "Veredas/Patios", 0.75, 0.90, 0.82),
    CoefficientEntry("Superficies", "Techos", 0.80, 0.95, 0.88),
    CoefficientEntry("Superficies", "Estacionamientos", 0.75, 0.90, 0.82),
    CoefficientEntry("Superficies", "Tierra/Tosca compactada", 0.30, 0.50, 0.40),
    # Areas verdes
    CoefficientEntry("Areas verdes", "Plazas/Parques", 0.10, 0.25, 0.18),
    CoefficientEntry("Areas verdes", "Jardines/Cesped", 0.08, 0.18, 0.12),
    CoefficientEntry("Areas verdes", "Baldios con vegetacion", 0.15, 0.35, 0.25),
]


# =============================================================================
# TABLAS DE CURVA NUMERO (CN)
# =============================================================================

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


# =============================================================================
# FUNCIONES DE AJUSTE POR PERIODO DE RETORNO
# =============================================================================

def get_c_for_tr_from_table(table_index: int, tr: int, table_key: str = "chow") -> float:
    """
    Obtiene el coeficiente C para un Tr específico desde la tabla original.

    Args:
        table_index: Índice de la entrada en la tabla
        tr: Período de retorno (años)
        table_key: Clave de la tabla ("chow", "fhwa", "uruguay")

    Returns:
        Coeficiente C para el Tr especificado
    """
    if table_key not in C_TABLES:
        raise ValueError(f"Tabla '{table_key}' no disponible")

    _, table_data = C_TABLES[table_key]

    if table_index < 0 or table_index >= len(table_data):
        raise ValueError(f"Índice {table_index} fuera de rango para tabla {table_key}")

    entry = table_data[table_index]

    if isinstance(entry, ChowCEntry):
        return entry.get_c(tr)
    elif isinstance(entry, FHWACEntry):
        return entry.get_c(tr)
    else:
        # CoefficientEntry - no varía con Tr
        return entry.c_recommended


def recalculate_weighted_c_for_tr(
    items: list,  # list[CoverageItem] - evitamos import circular
    tr: int,
    table_key: str = "chow",
) -> float:
    """
    Recalcula el coeficiente C ponderado para un período de retorno específico.

    Usa los índices guardados en cada CoverageItem para obtener el C
    correspondiente al Tr desde la tabla original.

    Args:
        items: Lista de CoverageItem con table_index definido
        tr: Período de retorno objetivo (años)
        table_key: Clave de la tabla usada

    Returns:
        C ponderado para el Tr especificado

    Example:
        >>> # items contiene coberturas con sus índices de tabla
        >>> recalculate_weighted_c_for_tr(items, tr=25, table_key="chow")
        0.45  # C ponderado para Tr=25
    """
    if not items:
        raise ValueError("La lista de coberturas no puede estar vacía")

    areas = []
    coefficients = []

    for item in items:
        if item.table_index is not None:
            # Obtener C desde la tabla para el Tr específico
            c_val = get_c_for_tr_from_table(item.table_index, tr, table_key)
        else:
            # Sin índice de tabla, usar el valor guardado (sin ajuste)
            c_val = item.value

        areas.append(item.area_ha)
        coefficients.append(c_val)

    return weighted_c(areas, coefficients)


def adjust_c_for_tr(c_base: float, tr: int, base_tr: int = 2) -> float:
    """
    Ajusta un coeficiente C base para un período de retorno diferente.

    NOTA: Esta función usa factores promedio y es menos precisa que
    recalculate_weighted_c_for_tr(). Se mantiene para compatibilidad
    con C ingresados manualmente (sin datos de ponderación).

    Args:
        c_base: Coeficiente C para el período de retorno base
        tr: Período de retorno objetivo (años)
        base_tr: Período de retorno del C base (default: 2 años)

    Returns:
        C ajustado para el Tr objetivo (máximo 1.0)
    """
    if tr == base_tr:
        return c_base

    # Factores promedio derivados de la tabla Ven Te Chow
    # (menos preciso que usar la tabla directamente)
    tr_factors = {
        2: 1.00,
        5: 1.17,
        10: 1.33,
        25: 1.50,
        50: 1.66,
        100: 1.84,
    }

    tr_values = sorted(tr_factors.keys())

    def get_factor(t: int) -> float:
        if t <= tr_values[0]:
            return tr_factors[tr_values[0]]
        if t >= tr_values[-1]:
            return tr_factors[tr_values[-1]]

        # Interpolar
        for i in range(len(tr_values) - 1):
            if tr_values[i] <= t <= tr_values[i + 1]:
                t1, t2 = tr_values[i], tr_values[i + 1]
                f1 = tr_factors[t1]
                f2 = tr_factors[t2]
                return f1 + (f2 - f1) * (t - t1) / (t2 - t1)

        return 1.0

    factor_base = get_factor(base_tr)
    factor_target = get_factor(tr)

    # Ajustar C manteniendo la proporción
    c_adjusted = c_base * (factor_target / factor_base)

    # C no puede exceder 1.0
    return min(c_adjusted, 1.0)


# =============================================================================
# FUNCIONES DE PONDERACION
# =============================================================================

def weighted_c(areas: list[float], coefficients: list[float]) -> float:
    """
    Calcula coeficiente C ponderado por area.

    Args:
        areas: Lista de areas en cualquier unidad (m2, ha, etc.)
        coefficients: Lista de coeficientes C correspondientes

    Returns:
        Coeficiente C ponderado
    """
    if len(areas) != len(coefficients):
        raise ValueError("Las listas de areas y coeficientes deben tener igual longitud")

    total_area = sum(areas)
    if total_area == 0:
        raise ValueError("El area total no puede ser cero")

    weighted_sum = sum(a * c for a, c in zip(areas, coefficients))
    return weighted_sum / total_area


def weighted_cn(areas: list[float], cn_values: list[int]) -> float:
    """
    Calcula Curva Numero CN ponderada por area.

    Args:
        areas: Lista de areas en cualquier unidad
        cn_values: Lista de valores CN correspondientes

    Returns:
        CN ponderado
    """
    if len(areas) != len(cn_values):
        raise ValueError("Las listas de areas y CN deben tener igual longitud")

    total_area = sum(areas)
    if total_area == 0:
        raise ValueError("El area total no puede ser cero")

    weighted_sum = sum(a * cn for a, cn in zip(areas, cn_values))
    return weighted_sum / total_area


# =============================================================================
# FUNCIONES DE FORMATO
# =============================================================================

def format_c_table(table: list, title: str, tr: int = 10, selection_mode: bool = False) -> str:
    """
    Formatea tabla de coeficientes C en ASCII.

    Soporta diferentes tipos de tablas:
    - CoefficientEntry: muestra rango min-max
    - ChowCEntry: muestra C para cada Tr
    - FHWACEntry: muestra C base y ajustado para Tr dado

    Args:
        table: Lista de entradas de coeficientes
        title: Titulo de la tabla
        tr: Periodo de retorno para mostrar C ajustado (FHWA)
        selection_mode: Si True, indica que Tr2 es seleccionable (Ven Te Chow)
    """
    lines = []
    lines.append("")
    lines.append(f"  {title}")

    if not table:
        return "\n".join(lines)

    # Detectar tipo de tabla
    first = table[0]

    if isinstance(first, ChowCEntry):
        # Tabla Ven Te Chow con C por Tr
        if selection_mode:
            # Modo selección: Tr2 es seleccionable, otros son referencia
            lines.append("  " + "=" * 85)
            lines.append(f"  {'#':<3} {'Categoria':<15} {'Descripcion':<22} {'*Tr2*':<6} {'(Tr5)':<6} {'(Tr10)':<7} {'(Tr25)':<7} {'(Tr50)':<7} {'(Tr100)':<7}")
            lines.append("  " + "-" * 85)

            current_category = ""
            for i, entry in enumerate(table):
                if entry.category != current_category:
                    if current_category:
                        lines.append("  " + "-" * 85)
                    current_category = entry.category

                lines.append(
                    f"  {i+1:<3} {entry.category:<15} {entry.description:<22} "
                    f"{entry.c_tr2:<6.2f} ({entry.c_tr5:.2f}) ({entry.c_tr10:.2f})  "
                    f"({entry.c_tr25:.2f})  ({entry.c_tr50:.2f})  ({entry.c_tr100:.2f})"
                )

            lines.append("  " + "=" * 85)
            lines.append("")
            lines.append("  NOTA: Selecciona el coeficiente C para Tr=2 anos (columna *Tr2*).")
            lines.append("        El valor se ajustara automaticamente segun el Tr del analisis.")
            lines.append("        Los valores entre parentesis son de referencia.")
        else:
            # Modo consulta: mostrar todos los valores
            lines.append("  " + "=" * 85)
            lines.append(f"  {'#':<3} {'Categoria':<15} {'Descripcion':<22} {'Tr2':<6} {'Tr5':<6} {'Tr10':<6} {'Tr25':<6} {'Tr50':<6} {'Tr100':<6}")
            lines.append("  " + "-" * 85)

            current_category = ""
            for i, entry in enumerate(table):
                if entry.category != current_category:
                    if current_category:
                        lines.append("  " + "-" * 85)
                    current_category = entry.category

                lines.append(
                    f"  {i+1:<3} {entry.category:<15} {entry.description:<22} "
                    f"{entry.c_tr2:<6.2f} {entry.c_tr5:<6.2f} {entry.c_tr10:<6.2f} "
                    f"{entry.c_tr25:<6.2f} {entry.c_tr50:<6.2f} {entry.c_tr100:<6.2f}"
                )

            lines.append("  " + "=" * 85)
            lines.append("")
            lines.append("  Nota: Para ponderacion, se usa C(Tr2) y se ajusta segun Tr del analisis.")

    elif isinstance(first, FHWACEntry):
        # Tabla FHWA con C base y factor
        lines.append("  " + "=" * 70)
        tr_header = f"C (Tr={tr})"
        lines.append(f"  {'#':<3} {'Categoria':<15} {'Descripcion':<28} {'C base':<8} {tr_header:<10}")
        lines.append("  " + "-" * 70)

        current_category = ""
        for i, entry in enumerate(table):
            if entry.category != current_category:
                if current_category:
                    lines.append("  " + "-" * 70)
                current_category = entry.category

            c_adj = entry.get_c(tr)
            lines.append(
                f"  {i+1:<3} {entry.category:<15} {entry.description:<28} "
                f"{entry.c_base:<8.2f} {c_adj:<10.2f}"
            )

        lines.append("  " + "=" * 70)
        lines.append("")
        lines.append("  Factores de ajuste FHWA por Tr:")
        lines.append("    Tr <= 10: 1.00 | Tr=25: 1.10 | Tr=50: 1.20 | Tr=100: 1.25")

    else:
        # Tabla simple con rango
        lines.append("  " + "=" * 70)
        lines.append(f"  {'#':<3} {'Categoria':<15} {'Descripcion':<28} {'C min':<7} {'C max':<7} {'C tip':<7}")
        lines.append("  " + "-" * 70)

        current_category = ""
        for i, entry in enumerate(table):
            if entry.category != current_category:
                if current_category:
                    lines.append("  " + "-" * 70)
                current_category = entry.category

            lines.append(
                f"  {i+1:<3} {entry.category:<15} {entry.description:<28} "
                f"{entry.c_min:<7.2f} {entry.c_max:<7.2f} {entry.c_recommended:<7.2f}"
            )

        lines.append("  " + "=" * 70)

    return "\n".join(lines)


def format_cn_table(table: list[CNEntry], title: str) -> str:
    """Formatea tabla de CN en ASCII."""
    lines = []
    lines.append("")
    lines.append(f"  {title}")
    lines.append("  " + "=" * 78)
    lines.append(f"  {'#':<3} {'Categoria':<12} {'Descripcion':<20} {'Cond.':<8} {'A':<5} {'B':<5} {'C':<5} {'D':<5}")
    lines.append("  " + "-" * 78)

    current_category = ""
    for i, entry in enumerate(table):
        if entry.category != current_category:
            if current_category:
                lines.append("  " + "-" * 78)
            current_category = entry.category

        lines.append(
            f"  {i+1:<3} {entry.category:<12} {entry.description:<20} {entry.condition:<8} "
            f"{entry.cn_a:<5} {entry.cn_b:<5} {entry.cn_c:<5} {entry.cn_d:<5}"
        )

    lines.append("  " + "=" * 78)
    lines.append("")
    lines.append("  Grupos hidrologicos de suelo:")
    lines.append("    A: Alta infiltracion (arena, grava)")
    lines.append("    B: Moderada infiltracion (limo arenoso)")
    lines.append("    C: Baja infiltracion (limo arcilloso)")
    lines.append("    D: Muy baja infiltracion (arcilla)")
    return "\n".join(lines)


# Diccionario de tablas disponibles
C_TABLES = {
    "fhwa": ("FHWA HEC-22 (Federal Highway Administration)", FHWA_C_TABLE),
    "chow": ("Ven Te Chow - Applied Hydrology", VEN_TE_CHOW_C_TABLE),
    "uruguay": ("Tabla Regional Uruguay", URUGUAY_C_TABLE),
}

CN_TABLES = {
    "unified": ("SCS TR-55 - Tabla Unificada", SCS_CN_TABLE),
    # Legacy - mantener por compatibilidad
    "urban": ("SCS TR-55 - Áreas Urbanas", SCS_CN_URBAN),
    "agricultural": ("SCS TR-55 - Áreas Agrícolas", SCS_CN_AGRICULTURAL),
}
