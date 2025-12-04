"""Tests para funciones temporales DINAGUA y bimodales."""

import pytest
import numpy as np

from hidropluvial.core.temporal import (
    alternating_blocks_dinagua,
    bimodal_storm,
    bimodal_chicago,
    generate_hyetograph_dinagua,
)
from hidropluvial.core.idf import dinagua_depth
from hidropluvial.config import ShermanCoefficients


class TestAlternatingBlocksDinagua:
    """Tests para bloques alternantes con IDF DINAGUA."""

    def test_basic_generation(self):
        """Test generación básica de hietograma."""
        result = alternating_blocks_dinagua(
            p3_10=78,
            return_period_yr=10,
            duration_hr=2,
            dt_min=10,
        )

        assert result.method == "alternating_blocks_dinagua"
        assert result.total_depth_mm > 0
        assert result.peak_intensity_mmhr > 0
        assert len(result.time_min) == 12  # 2hr / 10min = 12 intervalos
        assert len(result.depth_mm) == 12

    def test_total_depth_matches_idf(self):
        """Profundidad total debe coincidir con IDF DINAGUA."""
        p3_10 = 78
        tr = 25
        duration = 3
        dt = 15

        result = alternating_blocks_dinagua(p3_10, tr, duration, dt)
        expected_depth = dinagua_depth(p3_10, tr, duration)

        assert result.total_depth_mm == pytest.approx(expected_depth, rel=0.01)

    def test_total_depth_with_area_correction(self):
        """Profundidad total debe considerar corrección por área."""
        p3_10 = 78
        tr = 25
        duration = 3
        dt = 15
        area = 50

        result = alternating_blocks_dinagua(p3_10, tr, duration, dt, area_km2=area)
        expected_depth = dinagua_depth(p3_10, tr, duration, area)

        assert result.total_depth_mm == pytest.approx(expected_depth, rel=0.01)

    def test_area_correction_reduces_depth(self):
        """Corrección por área debe reducir la precipitación total."""
        result_no_area = alternating_blocks_dinagua(78, 25, 3, 15)
        result_with_area = alternating_blocks_dinagua(78, 25, 3, 15, area_km2=50)

        assert result_with_area.total_depth_mm < result_no_area.total_depth_mm

    def test_peak_at_center(self):
        """Con peak_position=0.5, pico debe estar cerca del centro."""
        result = alternating_blocks_dinagua(78, 10, 2, 10, peak_position=0.5)

        depths = result.depth_mm
        peak_idx = np.argmax(depths)
        n_intervals = len(depths)

        # El pico debe estar en el tercio central
        assert n_intervals // 3 <= peak_idx <= 2 * n_intervals // 3

    def test_peak_at_beginning(self):
        """Con peak_position=0.2, pico debe estar al principio."""
        result = alternating_blocks_dinagua(78, 10, 2, 10, peak_position=0.2)

        depths = result.depth_mm
        peak_idx = np.argmax(depths)
        n_intervals = len(depths)

        # El pico debe estar en el primer tercio
        assert peak_idx < n_intervals // 2

    def test_cumulative_increases(self):
        """Precipitación acumulada debe ser monótonamente creciente."""
        result = alternating_blocks_dinagua(78, 10, 2, 10)

        cumulative = result.cumulative_mm
        for i in range(1, len(cumulative)):
            assert cumulative[i] >= cumulative[i - 1]

    def test_intensity_depth_consistency(self):
        """Intensidad y profundidad deben ser consistentes."""
        dt_min = 10
        result = alternating_blocks_dinagua(78, 10, 2, dt_min)

        for i, (intensity, depth) in enumerate(
            zip(result.intensity_mmhr, result.depth_mm)
        ):
            expected_intensity = depth * 60 / dt_min
            assert intensity == pytest.approx(expected_intensity, rel=0.001)


class TestBimodalStorm:
    """Tests para tormentas bimodales triangulares."""

    def test_basic_generation(self):
        """Test generación básica de hietograma bimodal."""
        result = bimodal_storm(
            total_depth_mm=100,
            duration_hr=6,
            dt_min=15,
        )

        assert result.method == "bimodal"
        assert result.total_depth_mm == pytest.approx(100, rel=0.01)
        assert result.peak_intensity_mmhr > 0
        assert len(result.time_min) == 24  # 6hr / 15min = 24 intervalos

    def test_volume_split(self):
        """Test división de volumen entre picos."""
        # 70% primer pico, 30% segundo pico
        result = bimodal_storm(
            total_depth_mm=100,
            duration_hr=4,
            dt_min=10,
            peak1_position=0.25,
            peak2_position=0.75,
            volume_split=0.7,
        )

        depths = np.array(result.depth_mm)
        n = len(depths)

        # Calcular volumen en cada mitad
        vol_first_half = np.sum(depths[: n // 2])
        vol_second_half = np.sum(depths[n // 2 :])

        # Primera mitad debe tener más volumen
        assert vol_first_half > vol_second_half

    def test_two_peaks_visible(self):
        """Deben existir dos picos distinguibles."""
        result = bimodal_storm(
            total_depth_mm=100,
            duration_hr=6,
            dt_min=10,
            peak1_position=0.25,
            peak2_position=0.75,
        )

        depths = np.array(result.depth_mm)
        n = len(depths)

        # Encontrar máximos en cada mitad
        peak1_idx = np.argmax(depths[: n // 2])
        peak2_idx = n // 2 + np.argmax(depths[n // 2 :])

        # Los picos deben estar separados
        assert peak2_idx - peak1_idx > n // 4

        # Debe haber un valle entre los picos
        valley_region = depths[n // 3 : 2 * n // 3]
        assert np.min(valley_region) < np.max(depths) * 0.8

    def test_custom_peak_positions(self):
        """Test posiciones personalizadas de picos."""
        result = bimodal_storm(
            total_depth_mm=100,
            duration_hr=4,
            dt_min=10,
            peak1_position=0.15,
            peak2_position=0.85,
        )

        depths = np.array(result.depth_mm)
        n = len(depths)

        # Primer pico debe estar muy al principio
        peak1_idx = np.argmax(depths[: n // 2])
        assert peak1_idx < n // 4

    def test_equal_volume_split(self):
        """Con split=0.5, ambos picos deben tener similar altura."""
        result = bimodal_storm(
            total_depth_mm=100,
            duration_hr=4,
            dt_min=10,
            peak1_position=0.25,
            peak2_position=0.75,
            volume_split=0.5,
        )

        depths = np.array(result.depth_mm)
        n = len(depths)

        max_first = np.max(depths[: n // 2])
        max_second = np.max(depths[n // 2 :])

        # Las alturas deben ser similares (dentro del 30%)
        ratio = max_first / max_second if max_second > 0 else 0
        assert 0.7 < ratio < 1.4


class TestBimodalChicago:
    """Tests para tormentas bimodales Chicago."""

    @pytest.fixture
    def sherman_coeffs(self):
        """Coeficientes Sherman típicos."""
        return ShermanCoefficients(k=1200, m=0.15, c=10, n=0.75)

    def test_basic_generation(self, sherman_coeffs):
        """Test generación básica de hietograma bimodal Chicago."""
        result = bimodal_chicago(
            total_depth_mm=100,
            duration_hr=4,
            dt_min=10,
            idf_coeffs=sherman_coeffs,
            return_period_yr=25,
        )

        assert result.method == "bimodal_chicago"
        assert result.total_depth_mm == pytest.approx(100, rel=0.01)
        assert result.peak_intensity_mmhr > 0

    def test_preserves_total_depth(self, sherman_coeffs):
        """Profundidad total debe conservarse."""
        target_depth = 85.5
        result = bimodal_chicago(
            total_depth_mm=target_depth,
            duration_hr=3,
            dt_min=15,
            idf_coeffs=sherman_coeffs,
            return_period_yr=50,
        )

        assert result.total_depth_mm == pytest.approx(target_depth, rel=0.01)

    def test_volume_split_effect(self, sherman_coeffs):
        """División de volumen debe afectar altura relativa de picos."""
        result_equal = bimodal_chicago(
            total_depth_mm=100,
            duration_hr=4,
            dt_min=10,
            idf_coeffs=sherman_coeffs,
            return_period_yr=25,
            volume_split=0.5,
        )

        result_unequal = bimodal_chicago(
            total_depth_mm=100,
            duration_hr=4,
            dt_min=10,
            idf_coeffs=sherman_coeffs,
            return_period_yr=25,
            volume_split=0.8,
        )

        # Con split desigual, primer pico debe ser mayor
        depths_unequal = np.array(result_unequal.depth_mm)
        n = len(depths_unequal)
        max_first = np.max(depths_unequal[: n // 2])
        max_second = np.max(depths_unequal[n // 2 :])

        assert max_first > max_second


class TestGenerateHyetographDinagua:
    """Tests para función principal generate_hyetograph_dinagua."""

    def test_alternating_blocks_method(self):
        """Test método bloques alternantes."""
        result = generate_hyetograph_dinagua(
            p3_10=78,
            return_period_yr=25,
            duration_hr=3,
            dt_min=15,
            method="alternating_blocks",
        )

        assert result.method == "alternating_blocks_dinagua"
        assert result.total_depth_mm > 0

    def test_scs_type_ii_method(self):
        """Test método SCS Type II."""
        result = generate_hyetograph_dinagua(
            p3_10=78,
            return_period_yr=25,
            duration_hr=24,
            dt_min=60,
            method="scs_type_ii",
        )

        assert result.method == "scs_type_ii"
        expected_depth = dinagua_depth(78, 25, 24)
        assert result.total_depth_mm == pytest.approx(expected_depth, rel=0.02)

    def test_scs_type_i_method(self):
        """Test método SCS Type I."""
        result = generate_hyetograph_dinagua(
            p3_10=78,
            return_period_yr=25,
            duration_hr=24,
            dt_min=60,
            method="scs_type_i",
        )

        assert result.method == "scs_type_i"

    def test_huff_q2_method(self):
        """Test método Huff Q2."""
        result = generate_hyetograph_dinagua(
            p3_10=78,
            return_period_yr=25,
            duration_hr=6,
            dt_min=30,
            method="huff_q2",
        )

        assert "huff" in result.method
        expected_depth = dinagua_depth(78, 25, 6)
        assert result.total_depth_mm == pytest.approx(expected_depth, rel=0.02)

    def test_invalid_method_raises(self):
        """Método inválido debe lanzar error."""
        with pytest.raises(ValueError):
            generate_hyetograph_dinagua(
                p3_10=78,
                return_period_yr=25,
                duration_hr=3,
                dt_min=15,
                method="invalid_method",
            )

    def test_area_correction_applied(self):
        """Corrección por área debe aplicarse."""
        result_no_area = generate_hyetograph_dinagua(
            p3_10=78,
            return_period_yr=25,
            duration_hr=3,
            dt_min=15,
            method="alternating_blocks",
        )

        result_with_area = generate_hyetograph_dinagua(
            p3_10=78,
            return_period_yr=25,
            duration_hr=3,
            dt_min=15,
            method="alternating_blocks",
            area_km2=100,
        )

        assert result_with_area.total_depth_mm < result_no_area.total_depth_mm

    def test_different_return_periods(self):
        """Mayor período de retorno debe dar mayor precipitación."""
        result_10yr = generate_hyetograph_dinagua(
            p3_10=78,
            return_period_yr=10,
            duration_hr=3,
            dt_min=15,
        )

        result_100yr = generate_hyetograph_dinagua(
            p3_10=78,
            return_period_yr=100,
            duration_hr=3,
            dt_min=15,
        )

        assert result_100yr.total_depth_mm > result_10yr.total_depth_mm
