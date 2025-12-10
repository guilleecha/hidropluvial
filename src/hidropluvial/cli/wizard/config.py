"""
WizardConfig - Recolecta datos de cuenca y parametros de analisis.
"""

from dataclasses import dataclass, field
from typing import Optional

import typer

from hidropluvial.cli.theme import (
    print_section,
    print_note,
)


@dataclass
class WizardConfig:
    """Configuracion recolectada por el wizard."""

    # Datos de cuenca
    nombre: str = ""
    area_ha: float = 0.0
    slope_pct: float = 0.0
    p3_10: float = 0.0
    c: Optional[float] = None
    cn: Optional[int] = None
    length_m: Optional[float] = None

    # Datos de ponderación (para recálculo por Tr)
    c_weighted_data: Optional[dict] = None  # {table_key, items con table_index}

    # Parámetros avanzados
    amc: str = "II"  # Condición de humedad antecedente: I, II, III
    lambda_coef: float = 0.2  # Coeficiente lambda para abstracción inicial
    t0_min: float = 5.0  # Tiempo de entrada inicial para Desbordes

    # Parametros de analisis
    tc_methods: list[str] = field(default_factory=list)
    storm_codes: list[str] = field(default_factory=lambda: ["gz"])
    return_periods: list[int] = field(default_factory=list)
    x_factors: list[float] = field(default_factory=lambda: [1.0])
    dt_min: float = 5.0  # Intervalo de tiempo del hietograma (minutos)

    # Parametros de tormenta bimodal
    bimodal_duration_hr: float = 6.0  # Duracion de la tormenta bimodal (horas)
    bimodal_peak1: float = 0.25  # Posicion del primer pico (0-1)
    bimodal_peak2: float = 0.75  # Posicion del segundo pico (0-1)
    bimodal_vol_split: float = 0.5  # Fraccion del volumen en el primer pico
    bimodal_peak_width: float = 0.15  # Ancho de cada pico (fraccion de duracion)

    # Parametros de tormenta personalizada
    custom_depth_mm: Optional[float] = None  # Precipitacion total personalizada (mm)
    custom_duration_hr: float = 6.0  # Duracion de tormenta personalizada (horas)
    custom_distribution: str = "alternating_blocks"  # Distribucion temporal
    custom_hyetograph_time: Optional[list[float]] = None  # Tiempos del hietograma (min)
    custom_hyetograph_depth: Optional[list[float]] = None  # Profundidades del hietograma (mm)

    # Salida
    output_name: Optional[str] = None

    @classmethod
    def from_wizard(cls) -> Optional["WizardConfig"]:
        """Recolecta datos interactivamente con navegación."""
        from hidropluvial.cli.wizard.steps import WizardNavigator

        navigator = WizardNavigator()
        state = navigator.run()

        if state is None:
            return None

        # Convertir WizardState a WizardConfig
        config = cls(
            nombre=state.nombre,
            area_ha=state.area_ha,
            slope_pct=state.slope_pct,
            p3_10=state.p3_10,
            c=state.c,
            cn=state.cn,
            length_m=state.length_m,
            c_weighted_data=state.c_weighted_data,
            amc=state.amc,
            lambda_coef=state.lambda_coef,
            t0_min=state.t0_min,
            tc_methods=state.tc_methods,
            storm_codes=state.storm_codes,
            return_periods=state.return_periods,
            x_factors=state.x_factors,
            dt_min=state.dt_min,
            bimodal_duration_hr=state.bimodal_duration_hr,
            bimodal_peak1=state.bimodal_peak1,
            bimodal_peak2=state.bimodal_peak2,
            bimodal_vol_split=state.bimodal_vol_split,
            bimodal_peak_width=state.bimodal_peak_width,
            custom_depth_mm=state.custom_depth_mm,
            custom_duration_hr=state.custom_duration_hr,
            custom_distribution=state.custom_distribution,
            custom_hyetograph_time=state.custom_hyetograph_time,
            custom_hyetograph_depth=state.custom_hyetograph_depth,
            output_name=state.output_name,
        )

        return config

    def get_n_combinations(self) -> int:
        """Calcula numero total de combinaciones."""
        n_tc = len(self.tc_methods)
        n_tr = len(self.return_periods)
        n_storms = len(self.storm_codes)
        # X solo aplica para tormentas GZ
        n_x = len(self.x_factors) if "gz" in self.storm_codes else 1
        n_non_gz = len([s for s in self.storm_codes if s != "gz"])
        n_gz = 1 if "gz" in self.storm_codes else 0
        return n_tc * n_tr * (n_gz * n_x + n_non_gz)

    def print_summary(self) -> None:
        """Imprime resumen de configuracion con formato mejorado."""
        n_total = self.get_n_combinations()
        n_tc = len(self.tc_methods)
        n_tr = len(self.return_periods)
        n_storms = len(self.storm_codes)
        n_x = len(self.x_factors) if "gz" in self.storm_codes else 1

        print_section("Resumen de Configuración")

        # Datos de la cuenca
        typer.echo(f"  Cuenca:       {self.nombre}")
        typer.echo(f"  Área:         {self.area_ha:.2f} ha")
        typer.echo(f"  Pendiente:    {self.slope_pct:.2f} %")
        typer.echo(f"  P(3h,Tr10):   {self.p3_10:.1f} mm")
        if self.c:
            typer.echo(f"  Coef. C:      {self.c:.2f}")
        if self.cn:
            typer.echo(f"  Curva CN:     {self.cn}")
        if self.length_m:
            typer.echo(f"  Longitud:     {self.length_m:.0f} m")

        typer.echo()  # Línea en blanco

        # Parámetros de análisis
        typer.echo(f"  Métodos Tc:   {', '.join(self.tc_methods)}")
        typer.echo(f"  Tormentas:    {', '.join(self.storm_codes)}")
        typer.echo(f"  Tr:           {', '.join(str(tr) for tr in self.return_periods)} años")
        if "gz" in self.storm_codes:
            typer.echo(f"  Factor X:     {', '.join(f'{x:.2f}' for x in self.x_factors)}")

        typer.echo()  # Línea en blanco

        # Destacar el conteo de análisis
        detail = f"{n_tc} Tc × {n_tr} Tr × {n_storms} tormentas"
        if "gz" in self.storm_codes and n_x > 1:
            detail += f" × {n_x} factores X"
        print_note(f"Se generarán {n_total} análisis ({detail})")
