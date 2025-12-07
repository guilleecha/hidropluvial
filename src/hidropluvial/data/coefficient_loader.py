"""
Cargador unificado de coeficientes hidrológicos.

Provee acceso a tablas de coeficientes del sistema (JSON/código)
y prepara la arquitectura para tablas personalizadas de usuario.

Fase 1: Solo lectura de tablas del sistema
Fase 2: (Futuro) Integración con base de datos para tablas de usuario
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class TableSource(Enum):
    """Origen de la tabla de coeficientes."""
    SYSTEM = "system"      # JSON/código del sistema (solo lectura)
    USER = "user"          # Base de datos usuario (futuro)
    PUBLIC = "public"      # Compartida por otro usuario (futuro)


class TableType(Enum):
    """Tipo de tabla de coeficientes."""
    CN = "cn"              # Curva Número (SCS/NRCS)
    C = "c"                # Coeficiente de escorrentía (Racional)
    IDF = "idf"            # Curvas IDF


@dataclass
class CoverType:
    """Tipo de cobertura/uso de suelo."""
    code: str                          # "residential_1000m2"
    name: str                          # "Residencial - Lote 1000 m²"
    category: Optional[str] = None     # "Residencial", "Comercial", etc.
    description: Optional[str] = None


@dataclass
class CNValue:
    """Valores CN para un tipo de cobertura."""
    cover_type: CoverType
    cn_a: Optional[int] = None
    cn_b: Optional[int] = None
    cn_c: Optional[int] = None
    cn_d: Optional[int] = None
    hydrologic_condition: Optional[str] = None  # 'poor', 'fair', 'good'

    def get_cn(self, soil_group: str) -> Optional[int]:
        """Obtiene CN para un grupo hidrológico."""
        group = soil_group.upper()
        return {
            "A": self.cn_a,
            "B": self.cn_b,
            "C": self.cn_c,
            "D": self.cn_d,
        }.get(group)


@dataclass
class CValue:
    """Valores C para un tipo de cobertura."""
    cover_type: CoverType
    c_min: float
    c_max: float
    c_by_tr: Optional[dict[int, float]] = None  # {2: 0.25, 5: 0.30, ...}

    def get_c(self, return_period: Optional[int] = None) -> tuple[float, float]:
        """
        Obtiene rango de C, opcionalmente para un período de retorno.

        Returns:
            Tupla (c_min, c_max) o (c_tr, c_tr) si hay valor específico
        """
        if return_period and self.c_by_tr and return_period in self.c_by_tr:
            c = self.c_by_tr[return_period]
            return (c, c)
        return (self.c_min, self.c_max)


@dataclass
class CoefficientTable:
    """Metadata de una tabla de coeficientes."""
    id: str                            # "system:tr55" o "user:123"
    name: str                          # "TR-55 (NRCS)"
    table_type: TableType
    source: TableSource
    description: Optional[str] = None
    region: Optional[str] = None
    reference: Optional[str] = None
    is_editable: bool = False

    @property
    def is_system(self) -> bool:
        return self.source == TableSource.SYSTEM


# =============================================================================
# Definición de tablas del sistema
# =============================================================================

SYSTEM_CN_TABLES = {
    "tr55": {
        "name": "TR-55 (NRCS)",
        "description": "Curva Número según Technical Release 55 - USDA NRCS",
        "reference": "USDA-NRCS TR-55, 1986",
        "source_file": "cn_tables.json",
    },
}

SYSTEM_C_TABLES = {
    "chow": {
        "name": "Ven Te Chow",
        "description": "Coeficientes C por período de retorno - Applied Hydrology Table 5.5.2",
        "reference": "Ven Te Chow, Applied Hydrology, 1988",
        "source": "coefficients.py:VEN_TE_CHOW_C_TABLE",
    },
    "fhwa": {
        "name": "FHWA HEC-22",
        "description": "Coeficientes C - Federal Highway Administration",
        "reference": "FHWA HEC-22, Urban Drainage Design Manual",
        "source": "coefficients.py:FHWA_C_TABLE",
    },
    "uruguay": {
        "name": "Uruguay Regional",
        "description": "Coeficientes C simplificados para Uruguay",
        "reference": "Adaptación regional",
        "source": "coefficients.py:URUGUAY_C_TABLE",
    },
}


class CoefficientLoader:
    """
    Cargador unificado de coeficientes.

    Combina tablas del sistema (JSON/código) con preparación para
    tablas de usuario (DB) en el futuro.

    Example:
        >>> loader = CoefficientLoader()
        >>> tables = loader.list_tables(table_type=TableType.CN)
        >>> cn = loader.get_cn("system:tr55", "residential_1000m2", "B")
        >>> print(cn)  # 75
    """

    _data_dir = Path(__file__).parent
    _cn_cache: Optional[dict] = None
    _c_tables_cache: Optional[dict] = None

    def __init__(
        self,
        db_session: Any = None,
        user_id: Optional[int] = None,
    ):
        """
        Inicializa el cargador.

        Args:
            db_session: Sesión de base de datos (futuro, para tablas usuario)
            user_id: ID del usuario actual (futuro)
        """
        self.db = db_session
        self.user_id = user_id

    # =========================================================================
    # Listado de tablas
    # =========================================================================

    def list_tables(
        self,
        table_type: Optional[TableType] = None,
        include_system: bool = True,
        include_user: bool = True,
    ) -> list[CoefficientTable]:
        """
        Lista todas las tablas disponibles.

        Args:
            table_type: Filtrar por tipo (CN, C, IDF)
            include_system: Incluir tablas del sistema
            include_user: Incluir tablas del usuario (futuro)

        Returns:
            Lista de CoefficientTable
        """
        tables = []

        if include_system:
            if table_type is None or table_type == TableType.CN:
                tables.extend(self._get_system_cn_tables())
            if table_type is None or table_type == TableType.C:
                tables.extend(self._get_system_c_tables())

        # Fase 2: Agregar tablas de usuario desde DB
        # if self.db and include_user and self.user_id:
        #     tables.extend(self._get_user_tables(table_type))

        return tables

    def _get_system_cn_tables(self) -> list[CoefficientTable]:
        """Lista tablas CN del sistema."""
        return [
            CoefficientTable(
                id=f"system:{key}",
                name=info["name"],
                table_type=TableType.CN,
                source=TableSource.SYSTEM,
                description=info.get("description"),
                reference=info.get("reference"),
                is_editable=False,
            )
            for key, info in SYSTEM_CN_TABLES.items()
        ]

    def _get_system_c_tables(self) -> list[CoefficientTable]:
        """Lista tablas C del sistema."""
        return [
            CoefficientTable(
                id=f"system:{key}",
                name=info["name"],
                table_type=TableType.C,
                source=TableSource.SYSTEM,
                description=info.get("description"),
                reference=info.get("reference"),
                is_editable=False,
            )
            for key, info in SYSTEM_C_TABLES.items()
        ]

    def get_table(self, table_id: str) -> Optional[CoefficientTable]:
        """
        Obtiene metadata de una tabla específica.

        Args:
            table_id: ID de la tabla ("system:tr55")

        Returns:
            CoefficientTable o None si no existe
        """
        for table in self.list_tables():
            if table.id == table_id:
                return table
        return None

    # =========================================================================
    # Tipos de cobertura
    # =========================================================================

    def get_cover_types(self, table_id: str) -> list[CoverType]:
        """
        Lista tipos de cobertura de una tabla.

        Args:
            table_id: ID de la tabla

        Returns:
            Lista de CoverType
        """
        source, key = self._parse_table_id(table_id)

        if source == "system":
            if key in SYSTEM_CN_TABLES:
                return self._get_cn_cover_types(key)
            elif key in SYSTEM_C_TABLES:
                return self._get_c_cover_types(key)

        return []

    def _get_cn_cover_types(self, table_key: str) -> list[CoverType]:
        """Obtiene tipos de cobertura de tabla CN."""
        data = self._load_cn_data()
        cover_types = []

        for code, info in data.get("cover_types", {}).items():
            cover_types.append(CoverType(
                code=code,
                name=info.get("description", code),
                description=info.get("description"),
            ))

        return cover_types

    def _get_c_cover_types(self, table_key: str) -> list[CoverType]:
        """Obtiene tipos de cobertura de tabla C."""
        tables = self._load_c_tables()
        if table_key not in tables:
            return []

        _, entries = tables[table_key]
        cover_types = []
        seen = set()

        for i, entry in enumerate(entries):
            # Crear código único
            code = f"{entry.category}_{entry.description}".lower().replace(" ", "_").replace("/", "_")
            if code in seen:
                code = f"{code}_{i}"
            seen.add(code)

            cover_types.append(CoverType(
                code=code,
                name=entry.description,
                category=entry.category,
            ))

        return cover_types

    # =========================================================================
    # Valores CN
    # =========================================================================

    def get_cn(
        self,
        table_id: str,
        cover_type: str,
        soil_group: str,
    ) -> Optional[int]:
        """
        Obtiene valor CN de cualquier fuente.

        Args:
            table_id: "system:tr55" o "user:123"
            cover_type: Código del tipo de cobertura
            soil_group: A, B, C, D

        Returns:
            Valor CN o None si no existe
        """
        source, key = self._parse_table_id(table_id)

        if source == "system":
            return self._get_system_cn(key, cover_type, soil_group)
        # Fase 2: elif source == "user": ...

        return None

    def get_cn_values(self, table_id: str, cover_type: str) -> Optional[CNValue]:
        """
        Obtiene todos los valores CN para un tipo de cobertura.

        Args:
            table_id: ID de la tabla
            cover_type: Código del tipo de cobertura

        Returns:
            CNValue con valores para todos los grupos
        """
        source, key = self._parse_table_id(table_id)

        if source == "system":
            data = self._load_cn_data()
            cover_data = data.get("cover_types", {}).get(cover_type)

            if cover_data:
                return CNValue(
                    cover_type=CoverType(
                        code=cover_type,
                        name=cover_data.get("description", cover_type),
                    ),
                    cn_a=cover_data.get("A"),
                    cn_b=cover_data.get("B"),
                    cn_c=cover_data.get("C"),
                    cn_d=cover_data.get("D"),
                )

        return None

    def _get_system_cn(
        self,
        table_key: str,
        cover_type: str,
        soil_group: str,
    ) -> Optional[int]:
        """Obtiene CN desde tabla del sistema."""
        data = self._load_cn_data()
        cover_data = data.get("cover_types", {}).get(cover_type)

        if cover_data:
            return cover_data.get(soil_group.upper())

        return None

    # =========================================================================
    # Valores C
    # =========================================================================

    def get_c(
        self,
        table_id: str,
        cover_type: str,
        return_period: Optional[int] = None,
    ) -> Optional[tuple[float, float]]:
        """
        Obtiene rango de C de cualquier fuente.

        Args:
            table_id: "system:chow" o "user:123"
            cover_type: Código del tipo de cobertura
            return_period: Período de retorno (para tablas que varían con Tr)

        Returns:
            Tupla (c_min, c_max) o None
        """
        source, key = self._parse_table_id(table_id)

        if source == "system":
            return self._get_system_c(key, cover_type, return_period)

        return None

    def get_c_by_index(
        self,
        table_id: str,
        index: int,
        return_period: Optional[int] = None,
    ) -> Optional[float]:
        """
        Obtiene C por índice de tabla (compatibilidad con sistema actual).

        Args:
            table_id: ID de la tabla
            index: Índice de la entrada
            return_period: Período de retorno

        Returns:
            Valor C o None
        """
        source, key = self._parse_table_id(table_id)

        if source == "system":
            tables = self._load_c_tables()
            if key not in tables:
                return None

            _, entries = tables[key]
            if 0 <= index < len(entries):
                entry = entries[index]
                if hasattr(entry, 'get_c'):
                    return entry.get_c(return_period or 10)
                elif hasattr(entry, 'c_recommended'):
                    return entry.c_recommended

        return None

    def _get_system_c(
        self,
        table_key: str,
        cover_type: str,
        return_period: Optional[int],
    ) -> Optional[tuple[float, float]]:
        """Obtiene C desde tabla del sistema."""
        tables = self._load_c_tables()
        if table_key not in tables:
            return None

        _, entries = tables[table_key]

        # Buscar por código de cobertura
        for entry in entries:
            code = f"{entry.category}_{entry.description}".lower().replace(" ", "_").replace("/", "_")
            if code == cover_type or cover_type in code:
                if hasattr(entry, 'get_c'):
                    # ChowCEntry o FHWACEntry
                    c = entry.get_c(return_period or 10)
                    return (c, c)
                elif hasattr(entry, 'c_min') and hasattr(entry, 'c_max'):
                    # CoefficientEntry
                    return (entry.c_min, entry.c_max)

        return None

    # =========================================================================
    # Carga de datos
    # =========================================================================

    def _load_cn_data(self) -> dict:
        """Carga datos CN desde JSON (con cache)."""
        if CoefficientLoader._cn_cache is None:
            json_path = self._data_dir / "cn_tables.json"
            with open(json_path, encoding="utf-8") as f:
                CoefficientLoader._cn_cache = json.load(f)
        return CoefficientLoader._cn_cache

    def _load_c_tables(self) -> dict:
        """Carga tablas C desde módulo coefficients (con cache)."""
        if CoefficientLoader._c_tables_cache is None:
            from hidropluvial.core.coefficients import C_TABLES
            CoefficientLoader._c_tables_cache = C_TABLES
        return CoefficientLoader._c_tables_cache

    # =========================================================================
    # Utilidades
    # =========================================================================

    def _parse_table_id(self, table_id: str) -> tuple[str, str]:
        """Parsea ID de tabla en (source, key)."""
        if ":" in table_id:
            source, key = table_id.split(":", 1)
            return (source, key)
        # Default a sistema si no tiene prefijo
        return ("system", table_id)

    # =========================================================================
    # Métodos para futuro (Fase 2)
    # =========================================================================

    def copy_table(
        self,
        source_table_id: str,
        new_name: str,
        new_slug: Optional[str] = None,
    ) -> str:
        """
        Copia una tabla a una nueva tabla del usuario.

        Args:
            source_table_id: ID de la tabla origen
            new_name: Nombre de la nueva tabla
            new_slug: Slug único (auto-generado si no se especifica)

        Returns:
            ID de la nueva tabla

        Raises:
            NotImplementedError: En Fase 1 (sin DB)
        """
        raise NotImplementedError(
            "Copiar tablas requiere base de datos (Fase 2). "
            "Por ahora solo están disponibles las tablas del sistema."
        )
