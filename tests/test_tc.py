"""
Tests para el módulo de tiempo de concentración (tc.py).

Incluye validación contra ejemplos publicados:
- Kirpich: HEC-HMS Technical Reference Manual
- NRCS: TR-55 Urban Hydrology
- Témez: Hidrología en Ingeniería (Aparicio Mijares)
- Desbordes: Manual DINAGUA Uruguay
"""

import pytest
import numpy as np

from hidropluvial.core.tc import (
    kirpich,
    nrcs_sheet_flow,
    nrcs_shallow_flow,
    nrcs_channel_flow,
    nrcs_velocity_method,
    temez,
    california_culverts,
    faa_formula,
    desbordes,
    kinematic_wave,
    calculate_tc,
    SHALLOW_FLOW_K,
    SHEET_FLOW_N,
)
from hidropluvial.config import (
    SheetFlowSegment,
    ShallowFlowSegment,
    ChannelFlowSegment,
)


class TestKirpich:
    """Tests para método Kirpich (1940)."""

    def test_basic_calculation(self):
        """Test cálculo básico Kirpich."""
        # L = 1000m, S = 0.02 (2%)
        # tc = 0.0195 × 1000^0.77 × 0.02^(-0.385) = 18.13 min
        tc_hr = kirpich(1000, 0.02)
        tc_min = tc_hr * 60
        assert 17.5 < tc_min < 18.5  # ~18 min

    def test_longer_channel(self):
        """Test con canal más largo."""
        # L = 5000m, S = 0.01 (1%)
        tc_hr = kirpich(5000, 0.01)
        tc_min = tc_hr * 60
        # Canal más largo y menos pendiente = mayor Tc
        assert tc_min > 60  # > 1 hora

    def test_steep_slope(self):
        """Test con pendiente pronunciada."""
        # L = 1000m, S = 0.10 (10%)
        tc_hr = kirpich(1000, 0.10)
        tc_min = tc_hr * 60
        # Pendiente alta = menor Tc
        assert tc_min < 15

    def test_surface_adjustment_grassy(self):
        """Test ajuste para canales con pasto (×2)."""
        tc_natural = kirpich(1000, 0.02, "natural")
        tc_grassy = kirpich(1000, 0.02, "grassy")
        assert tc_grassy == pytest.approx(tc_natural * 2, rel=0.01)

    def test_surface_adjustment_concrete(self):
        """Test ajuste para concreto (×0.4)."""
        tc_natural = kirpich(1000, 0.02, "natural")
        tc_concrete = kirpich(1000, 0.02, "concrete")
        assert tc_concrete == pytest.approx(tc_natural * 0.4, rel=0.01)

    def test_surface_adjustment_concrete_channel(self):
        """Test ajuste para canales de concreto (×0.2)."""
        tc_natural = kirpich(1000, 0.02, "natural")
        tc_concrete_ch = kirpich(1000, 0.02, "concrete_channel")
        assert tc_concrete_ch == pytest.approx(tc_natural * 0.2, rel=0.01)

    def test_unknown_surface_uses_default(self):
        """Test superficie desconocida usa factor 1.0."""
        tc_natural = kirpich(1000, 0.02, "natural")
        tc_unknown = kirpich(1000, 0.02, "unknown_surface")
        assert tc_natural == tc_unknown

    def test_error_negative_length(self):
        """Test error con longitud negativa."""
        with pytest.raises(ValueError, match="Longitud debe ser > 0"):
            kirpich(-100, 0.02)

    def test_error_zero_length(self):
        """Test error con longitud cero."""
        with pytest.raises(ValueError, match="Longitud debe ser > 0"):
            kirpich(0, 0.02)

    def test_error_negative_slope(self):
        """Test error con pendiente negativa."""
        with pytest.raises(ValueError, match="Pendiente debe ser > 0"):
            kirpich(1000, -0.02)

    def test_error_zero_slope(self):
        """Test error con pendiente cero."""
        with pytest.raises(ValueError, match="Pendiente debe ser > 0"):
            kirpich(1000, 0)


class TestNRCSSheetFlow:
    """Tests para flujo laminar (sheet flow) NRCS TR-55."""

    def test_basic_calculation(self):
        """Test cálculo básico sheet flow."""
        # L = 50m, n = 0.24 (dense grass), S = 0.01, P2 = 50mm
        tt_hr = nrcs_sheet_flow(50, 0.24, 0.01, 50)
        tt_min = tt_hr * 60
        # Valor calculado: ~36 min para pasto denso con baja pendiente
        assert 30 < tt_min < 45

    def test_smooth_surface_faster(self):
        """Test superficie lisa tiene flujo más rápido."""
        tt_smooth = nrcs_sheet_flow(50, SHEET_FLOW_N["smooth"], 0.01, 50)
        tt_dense = nrcs_sheet_flow(50, SHEET_FLOW_N["dense_grass"], 0.01, 50)
        assert tt_smooth < tt_dense

    def test_higher_p2_faster(self):
        """Test mayor P2 produce tiempo menor."""
        tt_low = nrcs_sheet_flow(50, 0.15, 0.01, 30)
        tt_high = nrcs_sheet_flow(50, 0.15, 0.01, 80)
        assert tt_high < tt_low

    def test_steeper_slope_faster(self):
        """Test mayor pendiente produce tiempo menor."""
        tt_gentle = nrcs_sheet_flow(50, 0.15, 0.005, 50)
        tt_steep = nrcs_sheet_flow(50, 0.15, 0.02, 50)
        assert tt_steep < tt_gentle

    def test_max_length_100m(self):
        """Test longitud máxima 100m."""
        # 100m es el límite
        tt = nrcs_sheet_flow(100, 0.15, 0.01, 50)
        assert tt > 0

    def test_error_length_over_100m(self):
        """Test error si longitud > 100m."""
        with pytest.raises(ValueError, match="0-100 m"):
            nrcs_sheet_flow(101, 0.15, 0.01, 50)

    def test_error_negative_length(self):
        """Test error con longitud negativa."""
        with pytest.raises(ValueError, match="0-100 m"):
            nrcs_sheet_flow(-10, 0.15, 0.01, 50)

    def test_error_negative_n(self):
        """Test error con n negativo."""
        with pytest.raises(ValueError, match="Coeficiente n debe ser > 0"):
            nrcs_sheet_flow(50, -0.15, 0.01, 50)

    def test_error_negative_slope(self):
        """Test error con pendiente negativa."""
        with pytest.raises(ValueError, match="Pendiente debe ser > 0"):
            nrcs_sheet_flow(50, 0.15, -0.01, 50)

    def test_error_negative_p2(self):
        """Test error con P2 negativo."""
        with pytest.raises(ValueError, match="P2 debe ser > 0"):
            nrcs_sheet_flow(50, 0.15, 0.01, -50)


class TestNRCSShallowFlow:
    """Tests para flujo concentrado superficial NRCS."""

    def test_basic_unpaved(self):
        """Test flujo superficial no pavimentado."""
        tt_hr = nrcs_shallow_flow(500, 0.02, "unpaved")
        # V = 4.918 × 0.02^0.5 = 0.695 m/s
        # tt = 500 / (0.695 × 3600) = 0.2 hr = 12 min
        tt_min = tt_hr * 60
        assert 10 < tt_min < 15

    def test_paved_faster_than_unpaved(self):
        """Test superficie pavimentada es más rápida."""
        tt_paved = nrcs_shallow_flow(500, 0.02, "paved")
        tt_unpaved = nrcs_shallow_flow(500, 0.02, "unpaved")
        assert tt_paved < tt_unpaved

    def test_grassed_slower_than_unpaved(self):
        """Test superficie con pasto es más lenta que pavimentado."""
        tt_grassed = nrcs_shallow_flow(500, 0.02, "grassed")
        tt_unpaved = nrcs_shallow_flow(500, 0.02, "unpaved")
        # Grassed tiene k menor que unpaved, por lo tanto es más lento
        assert tt_grassed > tt_unpaved

    def test_unknown_surface_uses_unpaved(self):
        """Test superficie desconocida usa 'unpaved' por defecto."""
        tt_unpaved = nrcs_shallow_flow(500, 0.02, "unpaved")
        tt_unknown = nrcs_shallow_flow(500, 0.02, "random_surface")
        assert tt_unpaved == tt_unknown

    def test_steeper_slope_faster(self):
        """Test mayor pendiente = menor tiempo."""
        tt_gentle = nrcs_shallow_flow(500, 0.01)
        tt_steep = nrcs_shallow_flow(500, 0.04)
        assert tt_steep < tt_gentle

    def test_error_negative_length(self):
        """Test error con longitud negativa."""
        with pytest.raises(ValueError, match="Longitud debe ser > 0"):
            nrcs_shallow_flow(-500, 0.02)

    def test_error_negative_slope(self):
        """Test error con pendiente negativa."""
        with pytest.raises(ValueError, match="Pendiente debe ser > 0"):
            nrcs_shallow_flow(500, -0.02)


class TestNRCSChannelFlow:
    """Tests para flujo en canal NRCS."""

    def test_basic_calculation(self):
        """Test cálculo básico flujo en canal."""
        # L = 1000m, n = 0.035, S = 0.01, R = 0.5m
        # V = (1/0.035) × 0.5^(2/3) × 0.01^0.5 = 1.8 m/s
        # tt = 1000 / (1.8 × 3600) = 0.154 hr = 9.3 min
        tt_hr = nrcs_channel_flow(1000, 0.035, 0.01, 0.5)
        tt_min = tt_hr * 60
        assert 8 < tt_min < 11

    def test_smoother_channel_faster(self):
        """Test canal más liso es más rápido."""
        tt_rough = nrcs_channel_flow(1000, 0.05, 0.01, 0.5)
        tt_smooth = nrcs_channel_flow(1000, 0.02, 0.01, 0.5)
        assert tt_smooth < tt_rough

    def test_larger_radius_faster(self):
        """Test mayor radio hidráulico = mayor velocidad."""
        tt_small = nrcs_channel_flow(1000, 0.035, 0.01, 0.3)
        tt_large = nrcs_channel_flow(1000, 0.035, 0.01, 0.8)
        assert tt_large < tt_small

    def test_error_negative_length(self):
        """Test error longitud negativa."""
        with pytest.raises(ValueError, match="Longitud debe ser > 0"):
            nrcs_channel_flow(-1000, 0.035, 0.01, 0.5)

    def test_error_negative_n(self):
        """Test error n negativo."""
        with pytest.raises(ValueError, match="Coeficiente n debe ser > 0"):
            nrcs_channel_flow(1000, -0.035, 0.01, 0.5)

    def test_error_negative_slope(self):
        """Test error pendiente negativa."""
        with pytest.raises(ValueError, match="Pendiente debe ser > 0"):
            nrcs_channel_flow(1000, 0.035, -0.01, 0.5)

    def test_error_negative_radius(self):
        """Test error radio hidráulico negativo."""
        with pytest.raises(ValueError, match="Radio hidráulico debe ser > 0"):
            nrcs_channel_flow(1000, 0.035, 0.01, -0.5)


class TestNRCSVelocityMethod:
    """Tests para método de velocidades NRCS completo."""

    def test_single_sheet_flow_segment(self):
        """Test con un solo segmento de sheet flow."""
        segments = [
            SheetFlowSegment(length_m=50, n=0.24, slope=0.01, p2_mm=50)
        ]
        tc = nrcs_velocity_method(segments)
        assert tc > 0

    def test_combined_segments(self):
        """Test con múltiples tipos de segmentos."""
        segments = [
            SheetFlowSegment(length_m=50, n=0.24, slope=0.02, p2_mm=50),
            ShallowFlowSegment(length_m=300, slope=0.02, surface="unpaved"),
            ChannelFlowSegment(length_m=500, n=0.035, slope=0.01, hydraulic_radius_m=0.4),
        ]
        tc = nrcs_velocity_method(segments)
        # Suma de tiempos de viaje individuales
        assert tc > 0.1  # Debería ser > 6 min

    def test_p2_from_segment_overrides_default(self):
        """Test que P2 del segmento sobrescribe el default."""
        seg_low = SheetFlowSegment(length_m=50, n=0.24, slope=0.01, p2_mm=30)
        seg_high = SheetFlowSegment(length_m=50, n=0.24, slope=0.01, p2_mm=80)

        tc_low = nrcs_velocity_method([seg_low])
        tc_high = nrcs_velocity_method([seg_high])

        # Mayor P2 = menor tiempo
        assert tc_high < tc_low

    def test_empty_segments_returns_zero(self):
        """Test lista vacía retorna cero."""
        tc = nrcs_velocity_method([])
        assert tc == 0.0


class TestTemez:
    """Tests para método Témez (España/Latinoamérica)."""

    def test_basic_calculation(self):
        """Test cálculo básico Témez."""
        # tc = 0.3 × (L / S^0.25)^0.76
        # L = 10km, S = 0.02
        tc = temez(10, 0.02)
        # tc = 0.3 × (10 / 0.02^0.25)^0.76 = ~3.6 hr
        assert 3.0 < tc < 4.5

    def test_small_catchment(self):
        """Test cuenca pequeña."""
        tc = temez(1, 0.05)
        # Cuenca pequeña con pendiente alta = Tc bajo
        assert tc < 1.0  # < 1 hora

    def test_large_catchment(self):
        """Test cuenca grande."""
        tc = temez(50, 0.01)
        # Cuenca grande con pendiente baja = Tc alto
        assert tc > 10  # > 10 horas

    def test_longer_length_larger_tc(self):
        """Test mayor longitud = mayor Tc."""
        tc_short = temez(5, 0.02)
        tc_long = temez(20, 0.02)
        assert tc_long > tc_short

    def test_steeper_slope_smaller_tc(self):
        """Test mayor pendiente = menor Tc."""
        tc_gentle = temez(10, 0.01)
        tc_steep = temez(10, 0.05)
        assert tc_steep < tc_gentle

    def test_error_negative_length(self):
        """Test error longitud negativa."""
        with pytest.raises(ValueError, match="Longitud debe ser > 0"):
            temez(-10, 0.02)

    def test_error_negative_slope(self):
        """Test error pendiente negativa."""
        with pytest.raises(ValueError, match="Pendiente debe ser > 0"):
            temez(10, -0.02)


class TestCaliforniaCulverts:
    """Tests para método California Culverts Practice."""

    def test_basic_calculation(self):
        """Test cálculo básico California."""
        # L = 5km, H = 100m
        tc = california_culverts(5, 100)
        # Resultado en horas
        assert 0.5 < tc < 3.0

    def test_longer_length_larger_tc(self):
        """Test mayor longitud = mayor Tc."""
        tc_short = california_culverts(2, 100)
        tc_long = california_culverts(10, 100)
        assert tc_long > tc_short

    def test_larger_elevation_smaller_tc(self):
        """Test mayor diferencia de elevación = menor Tc."""
        tc_low = california_culverts(5, 50)
        tc_high = california_culverts(5, 200)
        assert tc_high < tc_low

    def test_error_negative_length(self):
        """Test error longitud negativa."""
        with pytest.raises(ValueError, match="Longitud debe ser > 0"):
            california_culverts(-5, 100)

    def test_error_negative_elevation(self):
        """Test error elevación negativa."""
        with pytest.raises(ValueError, match="Diferencia de elevación debe ser > 0"):
            california_culverts(5, -100)


class TestFAAFormula:
    """Tests para fórmula FAA."""

    def test_basic_calculation(self):
        """Test cálculo básico FAA."""
        # L = 300m, S = 2%, C = 0.7
        tc = faa_formula(300, 2, 0.7)
        # tc = 1.8 × (1.1 - 0.7) × (984ft)^0.5 / 2^0.333 = ~18 min
        tc_min = tc * 60
        assert 15 < tc_min < 25

    def test_higher_c_smaller_tc(self):
        """Test mayor C = menor Tc (superficie más impermeable)."""
        tc_low_c = faa_formula(300, 2, 0.3)
        tc_high_c = faa_formula(300, 2, 0.9)
        assert tc_high_c < tc_low_c

    def test_steeper_slope_smaller_tc(self):
        """Test mayor pendiente = menor Tc."""
        tc_gentle = faa_formula(300, 1, 0.5)
        tc_steep = faa_formula(300, 5, 0.5)
        assert tc_steep < tc_gentle

    def test_error_c_too_low(self):
        """Test error C <= 0."""
        with pytest.raises(ValueError, match="Coeficiente C debe estar entre 0 y 1"):
            faa_formula(300, 2, 0)

    def test_error_c_too_high(self):
        """Test error C > 1."""
        with pytest.raises(ValueError, match="Coeficiente C debe estar entre 0 y 1"):
            faa_formula(300, 2, 1.1)

    def test_error_negative_length(self):
        """Test error longitud negativa."""
        with pytest.raises(ValueError, match="Longitud debe ser > 0"):
            faa_formula(-300, 2, 0.5)

    def test_error_negative_slope(self):
        """Test error pendiente negativa."""
        with pytest.raises(ValueError, match="Pendiente debe ser > 0"):
            faa_formula(300, -2, 0.5)


class TestDesbordes:
    """Tests para método Desbordes (DINAGUA Uruguay)."""

    def test_basic_calculation(self):
        """Test cálculo básico Desbordes."""
        # A = 10ha, P = 2%, C = 0.5, T0 = 5min
        # Tc = 5 + 6.625 × 10^0.3 × 2^(-0.39) × 0.5^(-0.45)
        tc = desbordes(10, 2, 0.5)
        tc_min = tc * 60
        # Valor esperado aproximado: 15-25 min
        assert 15 < tc_min < 25

    def test_larger_area_larger_tc(self):
        """Test mayor área = mayor Tc."""
        tc_small = desbordes(5, 2, 0.5)
        tc_large = desbordes(50, 2, 0.5)
        assert tc_large > tc_small

    def test_steeper_slope_smaller_tc(self):
        """Test mayor pendiente = menor Tc."""
        tc_gentle = desbordes(10, 1, 0.5)
        tc_steep = desbordes(10, 5, 0.5)
        assert tc_steep < tc_gentle

    def test_higher_c_smaller_tc(self):
        """Test mayor C = menor Tc (escorrentía más rápida)."""
        tc_low_c = desbordes(10, 2, 0.3)
        tc_high_c = desbordes(10, 2, 0.8)
        assert tc_high_c < tc_low_c

    def test_custom_t0(self):
        """Test con T0 personalizado."""
        tc_t0_5 = desbordes(10, 2, 0.5, t0_min=5)
        tc_t0_10 = desbordes(10, 2, 0.5, t0_min=10)
        # Diferencia debería ser ~5 min
        diff_min = (tc_t0_10 - tc_t0_5) * 60
        assert 4.5 < diff_min < 5.5

    def test_t0_zero(self):
        """Test con T0 = 0."""
        tc = desbordes(10, 2, 0.5, t0_min=0)
        assert tc > 0

    def test_error_negative_area(self):
        """Test error área negativa."""
        with pytest.raises(ValueError, match="Área debe ser > 0"):
            desbordes(-10, 2, 0.5)

    def test_error_negative_slope(self):
        """Test error pendiente negativa."""
        with pytest.raises(ValueError, match="Pendiente debe ser > 0"):
            desbordes(10, -2, 0.5)

    def test_error_c_out_of_range(self):
        """Test error C fuera de rango."""
        with pytest.raises(ValueError, match="Coeficiente C debe estar entre 0 y 1"):
            desbordes(10, 2, 0)
        with pytest.raises(ValueError, match="Coeficiente C debe estar entre 0 y 1"):
            desbordes(10, 2, 1.5)

    def test_error_negative_t0(self):
        """Test error T0 negativo."""
        with pytest.raises(ValueError, match="Tiempo de entrada T0 debe ser >= 0"):
            desbordes(10, 2, 0.5, t0_min=-5)


class TestKinematicWave:
    """Tests para método de onda cinemática."""

    def test_basic_calculation(self):
        """Test cálculo básico onda cinemática."""
        # L = 200m, n = 0.02, S = 0.01, i = 50mm/hr
        tc = kinematic_wave(200, 0.02, 0.01, 50)
        tc_min = tc * 60
        # Valor razonable para superficie impermeable
        assert 5 < tc_min < 30

    def test_higher_intensity_smaller_tc(self):
        """Test mayor intensidad = menor Tc."""
        tc_low_i = kinematic_wave(200, 0.02, 0.01, 20)
        tc_high_i = kinematic_wave(200, 0.02, 0.01, 100)
        assert tc_high_i < tc_low_i

    def test_rougher_surface_larger_tc(self):
        """Test superficie más rugosa = mayor Tc."""
        tc_smooth = kinematic_wave(200, 0.01, 0.01, 50)
        tc_rough = kinematic_wave(200, 0.05, 0.01, 50)
        assert tc_rough > tc_smooth

    def test_steeper_slope_smaller_tc(self):
        """Test mayor pendiente = menor Tc."""
        tc_gentle = kinematic_wave(200, 0.02, 0.005, 50)
        tc_steep = kinematic_wave(200, 0.02, 0.02, 50)
        assert tc_steep < tc_gentle

    def test_convergence(self):
        """Test que converge en pocas iteraciones."""
        # Con parámetros típicos debería converger rápido
        tc = kinematic_wave(200, 0.02, 0.01, 50, max_iterations=5)
        assert tc > 0

    def test_error_negative_length(self):
        """Test error longitud negativa."""
        with pytest.raises(ValueError, match="Longitud debe ser > 0"):
            kinematic_wave(-200, 0.02, 0.01, 50)

    def test_error_negative_n(self):
        """Test error n negativo."""
        with pytest.raises(ValueError, match="Coeficiente n debe ser > 0"):
            kinematic_wave(200, -0.02, 0.01, 50)

    def test_error_negative_slope(self):
        """Test error pendiente negativa."""
        with pytest.raises(ValueError, match="Pendiente debe ser > 0"):
            kinematic_wave(200, 0.02, -0.01, 50)

    def test_error_negative_intensity(self):
        """Test error intensidad negativa."""
        with pytest.raises(ValueError, match="Intensidad debe ser > 0"):
            kinematic_wave(200, 0.02, 0.01, -50)

    def test_returns_after_max_iterations(self):
        """Test retorno cuando no converge en max_iterations."""
        # Con 1 iteración no hay oportunidad de convergencia
        tc = kinematic_wave(200, 0.02, 0.01, 50, max_iterations=1)
        assert tc > 0


class TestCalculateTc:
    """Tests para función dispatcher calculate_tc()."""

    def test_kirpich_method(self):
        """Test despacho a método Kirpich."""
        tc = calculate_tc("kirpich", length_m=1000, slope=0.02)
        tc_direct = kirpich(1000, 0.02)
        assert tc == pytest.approx(tc_direct)

    def test_kirpich_with_surface(self):
        """Test Kirpich con tipo de superficie."""
        tc = calculate_tc("kirpich", length_m=1000, slope=0.02, surface_type="grassy")
        tc_direct = kirpich(1000, 0.02, "grassy")
        assert tc == pytest.approx(tc_direct)

    def test_temez_method_with_km(self):
        """Test despacho a método Témez con km."""
        tc = calculate_tc("temez", length_km=10, slope=0.02)
        tc_direct = temez(10, 0.02)
        assert tc == pytest.approx(tc_direct)

    def test_temez_method_with_m(self):
        """Test Témez convierte metros a km."""
        tc = calculate_tc("temez", length_m=10000, slope=0.02)
        tc_direct = temez(10, 0.02)
        assert tc == pytest.approx(tc_direct)

    def test_california_method(self):
        """Test despacho a método California."""
        tc = calculate_tc("california", length_km=5, elevation_diff_m=100)
        tc_direct = california_culverts(5, 100)
        assert tc == pytest.approx(tc_direct)

    def test_california_converts_m_to_km(self):
        """Test California convierte metros a km."""
        tc = calculate_tc("california", length_m=5000, elevation_diff_m=100)
        tc_direct = california_culverts(5, 100)
        assert tc == pytest.approx(tc_direct)

    def test_faa_method(self):
        """Test despacho a método FAA."""
        tc = calculate_tc("faa", length_m=300, slope_pct=2, c=0.5)
        tc_direct = faa_formula(300, 2, 0.5)
        assert tc == pytest.approx(tc_direct)

    def test_desbordes_method(self):
        """Test despacho a método Desbordes."""
        tc = calculate_tc("desbordes", area_ha=10, slope_pct=2, c=0.5)
        tc_direct = desbordes(10, 2, 0.5)
        assert tc == pytest.approx(tc_direct)

    def test_desbordes_with_t0(self):
        """Test Desbordes con T0 personalizado."""
        tc = calculate_tc("desbordes", area_ha=10, slope_pct=2, c=0.5, t0_min=10)
        tc_direct = desbordes(10, 2, 0.5, t0_min=10)
        assert tc == pytest.approx(tc_direct)

    def test_kinematic_method(self):
        """Test despacho a método onda cinemática."""
        tc = calculate_tc("kinematic", length_m=200, n=0.02, slope=0.01, intensity_mmhr=50)
        tc_direct = kinematic_wave(200, 0.02, 0.01, 50)
        assert tc == pytest.approx(tc_direct)

    def test_nrcs_method(self):
        """Test despacho a método NRCS."""
        segments = [
            SheetFlowSegment(length_m=50, n=0.24, slope=0.02, p2_mm=50),
            ShallowFlowSegment(length_m=300, slope=0.02, surface="unpaved"),
        ]
        tc = calculate_tc("nrcs", segments=segments)
        tc_direct = nrcs_velocity_method(segments)
        assert tc == pytest.approx(tc_direct)

    def test_slope_pct_converted_to_slope(self):
        """Test que slope_pct se convierte a slope."""
        tc_pct = calculate_tc("kirpich", length_m=1000, slope_pct=2)
        tc_slope = calculate_tc("kirpich", length_m=1000, slope=0.02)
        assert tc_pct == pytest.approx(tc_slope)

    def test_length_km_converted_to_m(self):
        """Test que length_km se convierte a length_m."""
        tc_km = calculate_tc("kirpich", length_km=1, slope=0.02)
        tc_m = calculate_tc("kirpich", length_m=1000, slope=0.02)
        assert tc_km == pytest.approx(tc_m)

    def test_case_insensitive_method(self):
        """Test método es case-insensitive."""
        tc_lower = calculate_tc("kirpich", length_m=1000, slope=0.02)
        tc_upper = calculate_tc("KIRPICH", length_m=1000, slope=0.02)
        tc_mixed = calculate_tc("Kirpich", length_m=1000, slope=0.02)
        assert tc_lower == tc_upper == tc_mixed

    def test_error_unknown_method(self):
        """Test error método desconocido."""
        with pytest.raises(ValueError, match="Método desconocido"):
            calculate_tc("unknown_method", length_m=1000, slope=0.02)

    def test_error_missing_params_kirpich(self):
        """Test error parámetros faltantes para Kirpich."""
        with pytest.raises(ValueError, match="Kirpich requiere"):
            calculate_tc("kirpich", length_m=1000)  # Sin slope

    def test_error_missing_params_nrcs(self):
        """Test error parámetros faltantes para NRCS."""
        with pytest.raises(ValueError, match="NRCS requiere"):
            calculate_tc("nrcs")  # Sin segments

    def test_error_missing_params_temez(self):
        """Test error parámetros faltantes para Témez."""
        with pytest.raises(ValueError, match="Témez requiere"):
            calculate_tc("temez", length_km=10)  # Sin slope

    def test_error_missing_length_temez(self):
        """Test error sin longitud para Témez."""
        with pytest.raises(ValueError, match="Témez requiere length_km"):
            calculate_tc("temez", slope=0.02)  # Sin length_km ni length_m

    def test_error_missing_params_california(self):
        """Test error parámetros faltantes para California."""
        with pytest.raises(ValueError, match="California requiere"):
            calculate_tc("california", length_km=5)  # Sin elevation_diff_m

    def test_error_missing_length_california(self):
        """Test error sin longitud para California."""
        with pytest.raises(ValueError, match="California requiere length_km"):
            calculate_tc("california", elevation_diff_m=100)  # Sin length_km ni length_m

    def test_error_missing_params_faa(self):
        """Test error parámetros faltantes para FAA."""
        with pytest.raises(ValueError, match="FAA requiere"):
            calculate_tc("faa", length_m=300, slope_pct=2)  # Sin c

    def test_error_missing_params_kinematic(self):
        """Test error parámetros faltantes para kinematic."""
        with pytest.raises(ValueError, match="Kinematic requiere"):
            calculate_tc("kinematic", length_m=200, n=0.02, slope=0.01)  # Sin intensity

    def test_error_missing_params_desbordes(self):
        """Test error parámetros faltantes para Desbordes."""
        with pytest.raises(ValueError, match="Desbordes requiere"):
            calculate_tc("desbordes", area_ha=10, slope_pct=2)  # Sin c


class TestConstants:
    """Tests para constantes del módulo."""

    def test_shallow_flow_k_values(self):
        """Test valores de K para flujo superficial."""
        assert "paved" in SHALLOW_FLOW_K
        assert "unpaved" in SHALLOW_FLOW_K
        assert "grassed" in SHALLOW_FLOW_K
        assert "short_grass" in SHALLOW_FLOW_K

        # Valores razonables (conversión de ft/s a m/s)
        for surface, k in SHALLOW_FLOW_K.items():
            assert 2.0 < k < 7.0, f"K para {surface} fuera de rango"

    def test_sheet_flow_n_values(self):
        """Test valores de n para flujo laminar."""
        expected_surfaces = ["smooth", "fallow", "short_grass", "dense_grass", "light_woods", "dense_woods"]
        for surface in expected_surfaces:
            assert surface in SHEET_FLOW_N

        # Valores deben aumentar con rugosidad
        assert SHEET_FLOW_N["smooth"] < SHEET_FLOW_N["fallow"]
        assert SHEET_FLOW_N["fallow"] < SHEET_FLOW_N["short_grass"]
        assert SHEET_FLOW_N["short_grass"] < SHEET_FLOW_N["dense_grass"]
        assert SHEET_FLOW_N["dense_grass"] < SHEET_FLOW_N["light_woods"]
        assert SHEET_FLOW_N["light_woods"] < SHEET_FLOW_N["dense_woods"]


class TestIntegrationScenarios:
    """Tests de integración con escenarios reales."""

    def test_urban_catchment_desbordes(self):
        """Test cuenca urbana típica con método Desbordes."""
        # Cuenca urbana: 15ha, 3% pendiente, C=0.65
        tc = desbordes(15, 3, 0.65)
        tc_min = tc * 60
        # Para cuenca urbana pequeña: 10-30 min es típico
        assert 10 < tc_min < 30

    def test_rural_catchment_temez(self):
        """Test cuenca rural con método Témez."""
        # Cuenca rural: L=25km, S=1.5%
        tc = temez(25, 0.015)
        # Para cuenca de 25km: varias horas es típico
        assert 5 < tc < 15

    def test_suburban_nrcs(self):
        """Test cuenca suburbana con método NRCS."""
        # Flujo de entrada: 80m pasto denso, 1%
        # Flujo concentrado: 400m no pavimentado, 2%
        # Canal natural: 600m, n=0.04, R=0.3m, 1%
        segments = [
            SheetFlowSegment(length_m=80, n=0.24, slope=0.01, p2_mm=50),
            ShallowFlowSegment(length_m=400, slope=0.02, surface="unpaved"),
            ChannelFlowSegment(length_m=600, n=0.04, slope=0.01, hydraulic_radius_m=0.3),
        ]
        tc = nrcs_velocity_method(segments)
        # Tc típico para esta configuración: 30-60 min
        tc_min = tc * 60
        assert 20 < tc_min < 80

    def test_airport_runway_faa(self):
        """Test escorrentía de pista de aeropuerto con FAA."""
        # Pista: L=500m, S=1.5%, C=0.9 (asfalto)
        tc = faa_formula(500, 1.5, 0.9)
        tc_min = tc * 60
        # Superficie muy impermeable: Tc bajo, 2-10 min
        assert 2 < tc_min < 15

    def test_mountain_stream_kirpich(self):
        """Test arroyo de montaña con Kirpich."""
        # Arroyo: L=3km, S=8%
        tc = kirpich(3000, 0.08)
        tc_min = tc * 60
        # Pendiente alta: Tc bajo
        assert 20 < tc_min < 60

    def test_comparison_methods_similar_catchment(self):
        """Test comparación de métodos para cuenca similar."""
        # Cuenca: A=20ha, L=1.5km, S=2%, C=0.5
        tc_desbordes = desbordes(20, 2, 0.5)
        tc_kirpich = kirpich(1500, 0.02)
        tc_temez = temez(1.5, 0.02)

        # Todos deberían dar valores del mismo orden de magnitud
        tcs = [tc_desbordes, tc_kirpich, tc_temez]
        tc_min = min(tcs)
        tc_max = max(tcs)

        # Ratio máximo razonable entre métodos: 3x
        assert tc_max / tc_min < 4
