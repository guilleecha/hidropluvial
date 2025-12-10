"""
Tipos de datos para coeficientes de escorrentía.

Define las estructuras para entradas de tablas de coeficientes C y CN.
"""

from dataclasses import dataclass
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
