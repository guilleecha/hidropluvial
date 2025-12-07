# Diseño: Sistema de Tablas de Coeficientes Personalizables

## 1. Concepto General

```
┌─────────────────────────────────────────────────────────────────┐
│                         FUENTES DE DATOS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   SISTEMA (JSON, solo lectura)     USUARIO (DB, editables)      │
│   ┌─────────────────────────┐      ┌─────────────────────────┐  │
│   │ • cn_tables.json        │      │ • coefficient_tables    │  │
│   │ • c_tables (código)     │      │ • cover_types           │  │
│   │ • scs_distributions     │      │ • custom_idf_curves     │  │
│   │ • huff_curves           │      │                         │  │
│   └─────────────────────────┘      └─────────────────────────┘  │
│              │                              │                    │
│              └──────────┬──────────────────┘                    │
│                         ▼                                        │
│              ┌─────────────────────┐                            │
│              │   CoefficientLoader │                            │
│              │   (Unifica acceso)  │                            │
│              └─────────────────────┘                            │
│                         │                                        │
│                         ▼                                        │
│              ┌─────────────────────┐                            │
│              │   Cálculos Core     │                            │
│              └─────────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Modelo de Datos (Database)

### 2.1 Tablas de Coeficientes

```sql
-- Tabla principal de colecciones de coeficientes
CREATE TABLE coefficient_tables (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER REFERENCES users(id),  -- NULL = sistema

    -- Identificación
    name            TEXT NOT NULL,          -- "CN Uruguay Adaptado"
    slug            TEXT NOT NULL UNIQUE,   -- "cn-uruguay-adaptado"
    table_type      TEXT NOT NULL,          -- 'cn' | 'c' | 'idf'

    -- Origen
    source          TEXT,                   -- "TR-55", "Ven Te Chow", "Custom"
    source_table_id INTEGER,                -- Si es copia de otra tabla

    -- Metadata
    description     TEXT,
    region          TEXT,                   -- "Uruguay", "Montevideo", etc.
    reference       TEXT,                   -- Cita bibliográfica

    -- Control
    is_system       BOOLEAN DEFAULT FALSE,  -- TRUE = no editable
    is_public       BOOLEAN DEFAULT FALSE,  -- Compartida con otros usuarios

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_tables_user ON coefficient_tables(user_id);
CREATE INDEX idx_tables_type ON coefficient_tables(table_type);
CREATE INDEX idx_tables_slug ON coefficient_tables(slug);
```

### 2.2 Tipos de Cobertura (Cover Types)

```sql
-- Tipos de cobertura/uso de suelo personalizados
CREATE TABLE cover_types (
    id              INTEGER PRIMARY KEY,
    table_id        INTEGER NOT NULL REFERENCES coefficient_tables(id) ON DELETE CASCADE,

    -- Identificación
    code            TEXT NOT NULL,          -- "residential_high_density"
    name            TEXT NOT NULL,          -- "Residencial alta densidad"
    category        TEXT,                   -- "urban", "agricultural", "forest"

    -- Descripción
    description     TEXT,

    -- Ordenamiento
    sort_order      INTEGER DEFAULT 0,

    UNIQUE(table_id, code)
);

CREATE INDEX idx_cover_table ON cover_types(table_id);
```

### 2.3 Valores de Coeficientes

```sql
-- Valores CN por tipo de cobertura y grupo hidrológico
CREATE TABLE cn_values (
    id              INTEGER PRIMARY KEY,
    cover_type_id   INTEGER NOT NULL REFERENCES cover_types(id) ON DELETE CASCADE,

    -- Valores por grupo hidrológico
    cn_a            INTEGER,                -- Grupo A (0-100 o NULL)
    cn_b            INTEGER,                -- Grupo B
    cn_c            INTEGER,                -- Grupo C
    cn_d            INTEGER,                -- Grupo D

    -- Condición hidrológica (si aplica)
    hydrologic_condition TEXT,              -- 'poor', 'fair', 'good'

    -- Notas
    notes           TEXT
);

CREATE INDEX idx_cn_cover ON cn_values(cover_type_id);

-- Valores C por tipo de cobertura
CREATE TABLE c_values (
    id              INTEGER PRIMARY KEY,
    cover_type_id   INTEGER NOT NULL REFERENCES cover_types(id) ON DELETE CASCADE,

    -- Rango de C
    c_min           REAL NOT NULL,          -- 0.30
    c_max           REAL NOT NULL,          -- 0.50

    -- Por período de retorno (opcional, para tablas tipo Chow)
    return_period   INTEGER,                -- NULL = todos, o 2, 5, 10, 25, 50, 100

    -- Condiciones
    slope_condition TEXT,                   -- 'flat', 'moderate', 'steep'
    soil_condition  TEXT,                   -- 'sandy', 'clay'

    notes           TEXT
);

CREATE INDEX idx_c_cover ON c_values(cover_type_id);
```

### 2.4 Curvas IDF Personalizadas

```sql
-- Curvas IDF locales
CREATE TABLE custom_idf_curves (
    id              INTEGER PRIMARY KEY,
    table_id        INTEGER NOT NULL REFERENCES coefficient_tables(id) ON DELETE CASCADE,

    -- Ubicación
    location_name   TEXT NOT NULL,          -- "Estación Carrasco"
    latitude        REAL,
    longitude       REAL,

    -- Parámetros (formato Sherman: i = k*T^m / (t+c)^n)
    k               REAL NOT NULL,
    m               REAL NOT NULL,
    c               REAL NOT NULL,
    n               REAL NOT NULL,

    -- Rango de validez
    duration_min_minutes    INTEGER DEFAULT 5,
    duration_max_minutes    INTEGER DEFAULT 1440,
    return_period_min_years INTEGER DEFAULT 2,
    return_period_max_years INTEGER DEFAULT 100,

    -- Metadata
    data_source     TEXT,                   -- "INUMET 1980-2020"
    notes           TEXT
);
```

## 3. API de Acceso Unificado

```python
# src/hidropluvial/data/coefficient_loader.py

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class TableSource(Enum):
    """Origen de la tabla de coeficientes."""
    SYSTEM = "system"      # JSON del sistema
    USER = "user"          # Base de datos usuario
    PUBLIC = "public"      # Compartida por otro usuario


@dataclass
class CoefficientTable:
    """Metadata de una tabla de coeficientes."""
    id: str                         # "system:tr55" o "user:123"
    name: str
    table_type: str                 # 'cn', 'c', 'idf'
    source: TableSource
    description: Optional[str] = None
    region: Optional[str] = None
    is_editable: bool = False


class CoefficientLoader:
    """
    Cargador unificado de coeficientes.

    Combina tablas del sistema (JSON) con tablas de usuario (DB).
    """

    def __init__(self, db_session=None, user_id: int | None = None):
        self.db = db_session
        self.user_id = user_id
        self._system_tables = self._load_system_tables()

    def list_tables(
        self,
        table_type: str | None = None,
        include_system: bool = True,
        include_user: bool = True,
        include_public: bool = True,
    ) -> list[CoefficientTable]:
        """Lista todas las tablas disponibles."""
        tables = []

        if include_system:
            tables.extend(self._get_system_tables(table_type))

        if self.db and include_user and self.user_id:
            tables.extend(self._get_user_tables(table_type))

        if self.db and include_public:
            tables.extend(self._get_public_tables(table_type))

        return tables

    def get_cn_values(
        self,
        table_id: str,
        cover_type: str,
        soil_group: str,
    ) -> int | None:
        """
        Obtiene valor CN de cualquier fuente.

        Args:
            table_id: "system:tr55" o "user:123"
            cover_type: Código del tipo de cobertura
            soil_group: A, B, C, D

        Returns:
            Valor CN o None si no existe
        """
        source, id_part = table_id.split(":", 1)

        if source == "system":
            return self._get_system_cn(id_part, cover_type, soil_group)
        else:
            return self._get_db_cn(int(id_part), cover_type, soil_group)

    def get_c_range(
        self,
        table_id: str,
        cover_type: str,
        return_period: int | None = None,
    ) -> tuple[float, float] | None:
        """
        Obtiene rango de C de cualquier fuente.

        Returns:
            Tupla (c_min, c_max) o None
        """
        source, id_part = table_id.split(":", 1)

        if source == "system":
            return self._get_system_c(id_part, cover_type, return_period)
        else:
            return self._get_db_c(int(id_part), cover_type, return_period)

    def copy_table(
        self,
        source_table_id: str,
        new_name: str,
        new_slug: str,
    ) -> int:
        """
        Copia una tabla (sistema o usuario) a una nueva tabla del usuario.

        Returns:
            ID de la nueva tabla
        """
        if not self.db or not self.user_id:
            raise ValueError("Se requiere sesión de DB y usuario")

        # Implementar copia...
        pass

    def get_cover_types(self, table_id: str) -> list[dict]:
        """Lista tipos de cobertura de una tabla."""
        pass

    # ... métodos privados de implementación
```

## 4. Ejemplos de Uso

### 4.1 Listar tablas disponibles

```python
loader = CoefficientLoader(db_session, user_id=current_user.id)

# Todas las tablas CN disponibles
cn_tables = loader.list_tables(table_type="cn")

# Resultado:
# [
#   CoefficientTable(id="system:tr55", name="TR-55 (NRCS)", source=SYSTEM, is_editable=False),
#   CoefficientTable(id="system:tr55_urban", name="TR-55 Urbano", source=SYSTEM, is_editable=False),
#   CoefficientTable(id="user:45", name="CN Uruguay 2024", source=USER, is_editable=True),
#   CoefficientTable(id="public:23", name="CN Argentina Pampa", source=PUBLIC, is_editable=False),
# ]
```

### 4.2 Obtener CN

```python
# Desde tabla sistema
cn = loader.get_cn_values("system:tr55", "residential_1_acre", "B")
# → 68

# Desde tabla usuario
cn = loader.get_cn_values("user:45", "residencial_montevideo", "C")
# → 85
```

### 4.3 Copiar y modificar tabla

```python
# Usuario copia tabla TR-55 para personalizarla
new_table_id = loader.copy_table(
    source_table_id="system:tr55",
    new_name="CN Uruguay - Proyecto X",
    new_slug="cn-uruguay-proyecto-x",
)

# Ahora puede editar la copia
loader.update_cn_value(
    table_id=f"user:{new_table_id}",
    cover_type="open_space_good",
    soil_group="B",
    new_value=72,  # Ajustado para condiciones locales
)
```

### 4.4 En el wizard/API

```python
# Al crear análisis, usuario selecciona qué tabla usar
@router.post("/analysis")
def create_analysis(
    basin_id: int,
    cn_table_id: str = "system:tr55",  # Default a sistema
    c_table_id: str = "system:chow",
    ...
):
    loader = CoefficientLoader(db, current_user.id)

    # Obtener CN según tabla seleccionada
    cn = loader.get_cn_values(cn_table_id, basin.cover_type, basin.soil_group)

    # Calcular...
```

## 5. UI/UX Sugerido

```
┌─────────────────────────────────────────────────────────────────┐
│  TABLAS DE COEFICIENTES                              [+ Nueva]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  📋 TABLAS DEL SISTEMA                                          │
│  ├── TR-55 (NRCS)                    CN    🔒  [Copiar]         │
│  ├── TR-55 Urbano                    CN    🔒  [Copiar]         │
│  ├── Ven Te Chow                     C     🔒  [Copiar]         │
│  └── FHWA HEC-22                     C     🔒  [Copiar]         │
│                                                                  │
│  📁 MIS TABLAS                                                  │
│  ├── CN Uruguay 2024                 CN    ✏️  [Editar] [🗑️]    │
│  ├── C Montevideo                    C     ✏️  [Editar] [🗑️]    │
│  └── IDF Carrasco                    IDF   ✏️  [Editar] [🗑️]    │
│                                                                  │
│  🌐 TABLAS PÚBLICAS                                             │
│  └── CN Argentina Pampa (por @juan)  CN    👁️  [Copiar]         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Editor de tabla:

```
┌─────────────────────────────────────────────────────────────────┐
│  Editando: CN Uruguay 2024                        [Guardar]     │
├─────────────────────────────────────────────────────────────────┤
│  Basada en: TR-55 (NRCS)                                        │
│  Región: Uruguay                                                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Tipo de Cobertura          │  A  │  B  │  C  │  D  │     │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ Residencial 1/8 acre       │ 77  │ 85  │ 90  │ 92  │ ✏️  │   │
│  │ Residencial 1/4 acre       │ 61  │ 75  │ 83  │ 87  │ ✏️  │   │
│  │ Comercial/Industrial       │ 89  │ 92  │ 94  │ 95  │ ✏️  │   │
│  │ ► Montevideo Centro (new)  │ 92  │ 94  │ 96  │ 97  │ ✏️  │   │
│  │ Espacios abiertos          │ 39  │ 61  │ 74  │ 80  │ ✏️  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [+ Agregar tipo de cobertura]                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 6. Migración de Datos Actuales

Los JSON actuales se mantienen como están. El sistema los expone como "tablas del sistema":

```python
SYSTEM_TABLES = {
    "cn": {
        "tr55": {
            "name": "TR-55 (NRCS)",
            "source_file": "cn_tables.json",
            "description": "Curva Número según Technical Release 55",
        },
    },
    "c": {
        "chow": {
            "name": "Ven Te Chow",
            "source": "coefficients.py:CHOW_C_TABLE",
            "description": "Coeficientes C - Applied Hydrology Table 5.5.2",
        },
        "fhwa": {
            "name": "FHWA HEC-22",
            "source": "coefficients.py:FHWA_C_TABLE",
            "description": "Federal Highway Administration",
        },
    },
}
```

## 7. Ventajas de este Diseño

1. **Backwards compatible**: El código actual sigue funcionando sin DB
2. **Progresivo**: Se puede implementar por fases
3. **Flexible**: Usuarios pueden adaptar a normativas locales
4. **Trazable**: Se sabe de dónde viene cada valor
5. **Colaborativo**: Tablas públicas permiten compartir conocimiento
6. **Seguro**: Tablas sistema nunca se modifican
