"""Modelos Pydantic para configuración y validación de datos."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UnitSystem(str, Enum):
    """Sistema de unidades."""
    SI = "SI"
    US = "US"


class IDFMethod(str, Enum):
    """Métodos para curvas IDF."""
    SHERMAN = "sherman"
    BERNARD = "bernard"
    KOUTSOYIANNIS = "koutsoyiannis"
    CHEN = "chen"


class StormMethod(str, Enum):
    """Métodos de distribución temporal de lluvia."""
    ALTERNATING_BLOCKS = "alternating_blocks"
    CHICAGO = "chicago"
    SCS_TYPE_I = "scs_type_i"
    SCS_TYPE_IA = "scs_type_ia"
    SCS_TYPE_II = "scs_type_ii"
    SCS_TYPE_III = "scs_type_iii"
    HUFF_Q1 = "huff_q1"
    HUFF_Q2 = "huff_q2"
    HUFF_Q3 = "huff_q3"
    HUFF_Q4 = "huff_q4"


class TCMethod(str, Enum):
    """Métodos de tiempo de concentración."""
    KIRPICH = "kirpich"
    NRCS = "nrcs"
    TEMEZ = "temez"
    CALIFORNIA = "california"
    FAA = "faa"
    KINEMATIC = "kinematic"


class TCSegmentType(str, Enum):
    """Tipos de segmento para cálculo de Tc."""
    SHEET = "sheet"
    SHALLOW = "shallow"
    CHANNEL = "channel"


class HydrographMethod(str, Enum):
    """Métodos de hidrograma unitario."""
    SCS_TRIANGULAR = "scs_triangular"
    SCS_CURVILINEAR = "scs_curvilinear"
    SNYDER = "snyder"
    CLARK = "clark"


class HydrologicSoilGroup(str, Enum):
    """Grupos hidrológicos de suelo."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class AntecedentMoistureCondition(str, Enum):
    """Condición antecedente de humedad."""
    DRY = "I"
    AVERAGE = "II"
    WET = "III"


# ============================================================================
# Modelos de Coeficientes IDF
# ============================================================================

class ShermanCoefficients(BaseModel):
    """Coeficientes para ecuación Sherman: i = k * T^m / (t + c)^n"""
    k: float = Field(..., gt=0, description="Coeficiente k")
    m: float = Field(..., gt=0, lt=1, description="Exponente de período de retorno (0.1-0.5)")
    c: float = Field(..., ge=0, le=60, description="Constante de tiempo (0-60 min)")
    n: float = Field(..., gt=0, lt=2, description="Exponente de duración (0.5-1.0)")


class BernardCoefficients(BaseModel):
    """Coeficientes para ecuación Bernard: i = a * T^m / t^n"""
    a: float = Field(..., gt=0, description="Coeficiente a")
    m: float = Field(..., gt=0, lt=1, description="Exponente de período de retorno")
    n: float = Field(..., gt=0, lt=2, description="Exponente de duración")


class KoutsoyiannisCoefficients(BaseModel):
    """Coeficientes para método Koutsoyiannis."""
    mu: float = Field(..., description="Parámetro de ubicación (media)")
    sigma: float = Field(..., gt=0, description="Parámetro de escala")
    theta: float = Field(..., ge=0, description="Parámetro theta")
    eta: float = Field(..., gt=0, description="Parámetro eta (exponente)")


# ============================================================================
# Modelos de Segmentos de Tiempo de Concentración
# ============================================================================

class SheetFlowSegment(BaseModel):
    """Segmento de flujo laminar (sheet flow)."""
    type: TCSegmentType = TCSegmentType.SHEET
    length_m: float = Field(..., gt=0, le=100, description="Longitud máxima 100m")
    n: float = Field(..., gt=0, description="Coeficiente de Manning")
    slope: float = Field(..., gt=0, lt=1, description="Pendiente (m/m)")
    p2_mm: float = Field(default=50.0, gt=0, description="Lluvia 2 años, 24h (mm)")


class ShallowFlowSegment(BaseModel):
    """Segmento de flujo concentrado superficial."""
    type: TCSegmentType = TCSegmentType.SHALLOW
    length_m: float = Field(..., gt=0, description="Longitud (m)")
    slope: float = Field(..., gt=0, lt=1, description="Pendiente (m/m)")
    surface: str = Field(default="unpaved", description="Tipo de superficie")


class ChannelFlowSegment(BaseModel):
    """Segmento de flujo en canal."""
    type: TCSegmentType = TCSegmentType.CHANNEL
    length_m: float = Field(..., gt=0, description="Longitud (m)")
    n: float = Field(..., gt=0, description="Coeficiente de Manning")
    slope: float = Field(..., gt=0, lt=1, description="Pendiente (m/m)")
    hydraulic_radius_m: float = Field(..., gt=0, description="Radio hidráulico (m)")


TCSegment = SheetFlowSegment | ShallowFlowSegment | ChannelFlowSegment


# ============================================================================
# Modelos de Cuenca
# ============================================================================

class Catchment(BaseModel):
    """Modelo de cuenca hidrográfica."""
    name: str = Field(..., min_length=1, description="Nombre de la cuenca")
    area_km2: float = Field(..., gt=0, le=10000, description="Área (km²)")
    cn: int = Field(..., ge=30, le=100, description="Número de curva SCS")
    slope: float = Field(..., gt=0, lt=1, description="Pendiente media (m/m)")
    tc_hours: Optional[float] = Field(None, gt=0, description="Tc calculado o manual (hr)")
    tc_segments: Optional[list[TCSegment]] = Field(None, description="Segmentos para NRCS")
    length_km: Optional[float] = Field(None, gt=0, description="Longitud del cauce (km)")
    soil_group: Optional[HydrologicSoilGroup] = Field(None, description="Grupo hidrológico")

    @field_validator('cn')
    @classmethod
    def validate_cn(cls, v: int) -> int:
        if not 30 <= v <= 100:
            raise ValueError("CN debe estar entre 30 y 100")
        return v


# ============================================================================
# Modelos de Eventos de Tormenta
# ============================================================================

class StormEvent(BaseModel):
    """Evento de tormenta de diseño."""
    method: StormMethod = Field(..., description="Método de distribución temporal")
    duration_hr: float = Field(..., gt=0, description="Duración total (hr)")
    return_period_yr: int = Field(..., ge=1, description="Período de retorno (años)")
    total_depth_mm: float = Field(..., gt=0, description="Precipitación total (mm)")
    dt_min: float = Field(default=5.0, gt=0, description="Intervalo de tiempo (min)")
    advancement_coef: float = Field(default=0.375, gt=0, lt=1, description="Coef. avance Chicago")


class IDFConfig(BaseModel):
    """Configuración de curvas IDF."""
    method: IDFMethod = Field(..., description="Método de cálculo")
    coefficients: ShermanCoefficients | BernardCoefficients | KoutsoyiannisCoefficients


# ============================================================================
# Modelos de Resultados
# ============================================================================

class HyetographResult(BaseModel):
    """Resultado de hietograma."""
    time_min: list[float] = Field(..., description="Tiempo (min)")
    intensity_mmhr: list[float] = Field(..., description="Intensidad (mm/hr)")
    depth_mm: list[float] = Field(..., description="Profundidad incremental (mm)")
    cumulative_mm: list[float] = Field(..., description="Profundidad acumulada (mm)")
    method: str = Field(..., description="Método utilizado")
    total_depth_mm: float = Field(..., description="Precipitación total (mm)")
    peak_intensity_mmhr: float = Field(..., description="Intensidad pico (mm/hr)")


class RunoffResult(BaseModel):
    """Resultado de cálculo de escorrentía."""
    rainfall_mm: float = Field(..., description="Precipitación total (mm)")
    runoff_mm: float = Field(..., description="Escorrentía directa (mm)")
    initial_abstraction_mm: float = Field(..., description="Abstracción inicial (mm)")
    retention_mm: float = Field(..., description="Retención potencial S (mm)")
    cn_used: int = Field(..., description="CN utilizado")
    method: str = Field(..., description="Método utilizado")


class HydrographResult(BaseModel):
    """Resultado de hidrograma."""
    time_hr: list[float] = Field(..., description="Tiempo (hr)")
    flow_m3s: list[float] = Field(..., description="Caudal (m³/s)")
    peak_flow_m3s: float = Field(..., description="Caudal pico (m³/s)")
    time_to_peak_hr: float = Field(..., description="Tiempo al pico (hr)")
    volume_m3: float = Field(..., description="Volumen total (m³)")
    method: HydrographMethod = Field(..., description="Método utilizado")


# ============================================================================
# Configuración del Proyecto
# ============================================================================

class ProjectConfig(BaseModel):
    """Configuración completa del proyecto."""
    name: str = Field(..., description="Nombre del proyecto")
    location: str = Field(default="", description="Ubicación")
    engineer: str = Field(default="", description="Ingeniero responsable")
    date: str = Field(default="", description="Fecha")
    units: UnitSystem = Field(default=UnitSystem.SI, description="Sistema de unidades")


class HydrographConfig(BaseModel):
    """Configuración de cálculo de hidrogramas."""
    method: HydrographMethod = Field(
        default=HydrographMethod.SCS_CURVILINEAR,
        description="Método de hidrograma"
    )
    prf: int = Field(default=484, ge=100, le=600, description="Peak rate factor")
    dt_hr: float = Field(default=0.1, gt=0, description="Intervalo de tiempo (hr)")
