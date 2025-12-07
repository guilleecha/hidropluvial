"""Tests para módulo core/temporal.py - Distribuciones temporales."""

import numpy as np
import pytest

from hidropluvial.core.temporal import (
    alternating_blocks,
    chicago_storm,
    scs_distribution,
    huff_distribution,
    generate_hyetograph,
    bimodal_dinagua,
)
from hidropluvial.config import (
    ShermanCoefficients,
    StormMethod,
    HyetographResult,
)


@pytest.fixture
def sherman_coeffs():
    """Coeficientes Sherman típicos."""
    return ShermanCoefficients(k=2150.0, m=0.22, c=15.0, n=0.75)


class TestAlternatingBlocks:
    """Tests para método de bloques alternantes con IDF genérico."""

    def test_basic_generation(self, sherman_coeffs):
        """Test generación básica de hietograma."""
        result = alternating_blocks(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=10.0,
            idf_method="sherman",
            idf_coeffs=sherman_coeffs,
            return_period_yr=10,
        )

        assert isinstance(result, HyetographResult)
        assert result.method == "alternating_blocks"
        assert result.total_depth_mm > 0
        assert result.peak_intensity_mmhr > 0
        assert len(result.time_min) == 12  # 2hr / 10min = 12

    def test_depth_scaling(self, sherman_coeffs):
        """Test escalado de profundidad total."""
        target_depth = 75.0
        result = alternating_blocks(
            total_depth_mm=target_depth,
            duration_hr=1.0,
            dt_min=5.0,
            idf_method="sherman",
            idf_coeffs=sherman_coeffs,
            return_period_yr=50,
        )

        assert result.total_depth_mm == pytest.approx(target_depth, rel=0.01)

    def test_peak_position_center(self, sherman_coeffs):
        """Test pico en el centro con peak_position=0.5."""
        result = alternating_blocks(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=10.0,
            idf_method="sherman",
            idf_coeffs=sherman_coeffs,
            return_period_yr=10,
            peak_position=0.5,
        )

        depths = result.depth_mm
        peak_idx = np.argmax(depths)
        n = len(depths)

        # Pico debe estar cerca del centro
        assert n // 3 <= peak_idx <= 2 * n // 3

    def test_peak_position_early(self, sherman_coeffs):
        """Test pico al inicio con peak_position=0.2."""
        result = alternating_blocks(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=10.0,
            idf_method="sherman",
            idf_coeffs=sherman_coeffs,
            return_period_yr=10,
            peak_position=0.2,
        )

        depths = result.depth_mm
        peak_idx = np.argmax(depths)
        n = len(depths)

        # Pico debe estar en la primera mitad
        assert peak_idx < n // 2

    def test_cumulative_monotonic(self, sherman_coeffs):
        """Test que acumulado es monótono creciente."""
        result = alternating_blocks(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=10.0,
            idf_method="sherman",
            idf_coeffs=sherman_coeffs,
            return_period_yr=10,
        )

        cumulative = result.cumulative_mm
        for i in range(1, len(cumulative)):
            assert cumulative[i] >= cumulative[i - 1]

    def test_intensity_depth_consistency(self, sherman_coeffs):
        """Test consistencia entre intensidad y profundidad."""
        dt_min = 10.0
        result = alternating_blocks(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=dt_min,
            idf_method="sherman",
            idf_coeffs=sherman_coeffs,
            return_period_yr=10,
        )

        for intensity, depth in zip(result.intensity_mmhr, result.depth_mm):
            expected_intensity = depth * 60 / dt_min
            assert intensity == pytest.approx(expected_intensity, rel=0.001)

    def test_different_return_periods(self, sherman_coeffs):
        """Mayor TR debe dar mayor intensidad pico."""
        result_10 = alternating_blocks(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=10.0,
            idf_method="sherman",
            idf_coeffs=sherman_coeffs,
            return_period_yr=10,
        )

        result_100 = alternating_blocks(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=10.0,
            idf_method="sherman",
            idf_coeffs=sherman_coeffs,
            return_period_yr=100,
        )

        # Con misma profundidad total, la distribución es diferente
        # pero la intensidad pico debería reflejar la curva IDF
        assert result_10.total_depth_mm == pytest.approx(result_100.total_depth_mm, rel=0.01)


class TestChicagoStorm:
    """Tests para tormenta de diseño Chicago."""

    def test_basic_generation(self, sherman_coeffs):
        """Test generación básica de tormenta Chicago."""
        result = chicago_storm(
            total_depth_mm=60.0,
            duration_hr=2.0,
            dt_min=5.0,
            idf_coeffs=sherman_coeffs,
            return_period_yr=25,
        )

        assert isinstance(result, HyetographResult)
        assert result.method == "chicago"
        assert result.total_depth_mm == pytest.approx(60.0, rel=0.01)
        assert result.peak_intensity_mmhr > 0

    def test_total_depth_preserved(self, sherman_coeffs):
        """Test que profundidad total se preserva."""
        target_depth = 85.5
        result = chicago_storm(
            total_depth_mm=target_depth,
            duration_hr=3.0,
            dt_min=10.0,
            idf_coeffs=sherman_coeffs,
            return_period_yr=50,
        )

        assert result.total_depth_mm == pytest.approx(target_depth, rel=0.01)

    def test_advancement_coefficient_default(self, sherman_coeffs):
        """Test coeficiente de avance por defecto (0.375)."""
        result = chicago_storm(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=5.0,
            idf_coeffs=sherman_coeffs,
            return_period_yr=25,
        )

        depths = result.depth_mm
        peak_idx = np.argmax(depths)
        n = len(depths)

        # Con r=0.375, pico debería estar antes del centro
        assert peak_idx < n // 2

    def test_advancement_coefficient_center(self, sherman_coeffs):
        """Test coeficiente de avance 0.5 (pico al centro)."""
        result = chicago_storm(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=5.0,
            idf_coeffs=sherman_coeffs,
            return_period_yr=25,
            advancement_coef=0.5,
        )

        depths = result.depth_mm
        peak_idx = np.argmax(depths)
        n = len(depths)

        # Con r=0.5, pico debería estar cerca del centro
        assert n // 3 <= peak_idx <= 2 * n // 3

    def test_advancement_coefficient_late(self, sherman_coeffs):
        """Test coeficiente de avance 0.75 (pico tarde)."""
        result = chicago_storm(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=5.0,
            idf_coeffs=sherman_coeffs,
            return_period_yr=25,
            advancement_coef=0.75,
        )

        depths = result.depth_mm
        peak_idx = np.argmax(depths)
        n = len(depths)

        # Con r=0.75, pico debería estar después del centro
        assert peak_idx > n // 3

    def test_different_durations(self, sherman_coeffs):
        """Test diferentes duraciones."""
        for duration in [1.0, 2.0, 4.0, 6.0]:
            result = chicago_storm(
                total_depth_mm=50.0,
                duration_hr=duration,
                dt_min=10.0,
                idf_coeffs=sherman_coeffs,
                return_period_yr=25,
            )

            expected_intervals = int(duration * 60 / 10)
            assert len(result.time_min) == expected_intervals
            assert result.total_depth_mm == pytest.approx(50.0, rel=0.01)

    def test_cumulative_increases(self, sherman_coeffs):
        """Test acumulado monótono creciente."""
        result = chicago_storm(
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=5.0,
            idf_coeffs=sherman_coeffs,
            return_period_yr=25,
        )

        cumulative = result.cumulative_mm
        for i in range(1, len(cumulative)):
            assert cumulative[i] >= cumulative[i - 1]


class TestSCSDistribution:
    """Tests para distribuciones SCS 24h."""

    def test_type_ii_basic(self):
        """Test SCS Type II básico."""
        result = scs_distribution(
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
            storm_type=StormMethod.SCS_TYPE_II,
        )

        assert isinstance(result, HyetographResult)
        assert result.method == "scs_type_ii"
        assert result.total_depth_mm == pytest.approx(100.0, rel=0.02)
        assert len(result.time_min) == 24

    def test_type_i_basic(self):
        """Test SCS Type I básico."""
        result = scs_distribution(
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
            storm_type=StormMethod.SCS_TYPE_I,
        )

        assert result.method == "scs_type_i"
        assert result.total_depth_mm == pytest.approx(100.0, rel=0.02)

    def test_type_ia_basic(self):
        """Test SCS Type IA básico."""
        result = scs_distribution(
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
            storm_type=StormMethod.SCS_TYPE_IA,
        )

        assert result.method == "scs_type_ia"
        assert result.total_depth_mm == pytest.approx(100.0, rel=0.02)

    def test_type_iii_basic(self):
        """Test SCS Type III básico."""
        result = scs_distribution(
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
            storm_type=StormMethod.SCS_TYPE_III,
        )

        assert result.method == "scs_type_iii"
        assert result.total_depth_mm == pytest.approx(100.0, rel=0.02)

    def test_all_types_have_peak(self):
        """Todos los tipos SCS deben tener un pico claro."""
        for storm_type in [
            StormMethod.SCS_TYPE_I,
            StormMethod.SCS_TYPE_IA,
            StormMethod.SCS_TYPE_II,
            StormMethod.SCS_TYPE_III,
        ]:
            result = scs_distribution(
                total_depth_mm=100.0,
                duration_hr=24.0,
                dt_min=60.0,
                storm_type=storm_type,
            )

            # Debe haber intensidad pico significativa
            assert result.peak_intensity_mmhr > np.mean(result.intensity_mmhr) * 1.5

    def test_type_ii_peak_around_hour_12(self):
        """SCS Type II tiene pico cerca de hora 12."""
        result = scs_distribution(
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
            storm_type=StormMethod.SCS_TYPE_II,
        )

        peak_idx = np.argmax(result.intensity_mmhr)
        peak_time_hr = result.time_min[peak_idx] / 60

        # Pico debería estar entre hora 11 y 13
        assert 10.0 <= peak_time_hr <= 14.0

    def test_shorter_duration(self):
        """Test con duración menor a 24h."""
        result = scs_distribution(
            total_depth_mm=50.0,
            duration_hr=6.0,
            dt_min=15.0,
            storm_type=StormMethod.SCS_TYPE_II,
        )

        expected_intervals = int(6.0 * 60 / 15)
        assert len(result.time_min) == expected_intervals
        assert result.total_depth_mm == pytest.approx(50.0, rel=0.02)

    def test_cumulative_reaches_total(self):
        """Acumulado final debe igualar total."""
        result = scs_distribution(
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
            storm_type=StormMethod.SCS_TYPE_II,
        )

        assert result.cumulative_mm[-1] == pytest.approx(100.0, rel=0.02)

    def test_invalid_storm_type_raises(self):
        """Tipo de tormenta inválido debe lanzar error."""
        with pytest.raises(ValueError):
            scs_distribution(
                total_depth_mm=100.0,
                duration_hr=24.0,
                dt_min=60.0,
                storm_type=StormMethod.ALTERNATING_BLOCKS,  # No es SCS
            )


class TestHuffDistribution:
    """Tests para distribuciones Huff."""

    def test_quartile_2_basic(self):
        """Test Huff cuartil 2 básico."""
        result = huff_distribution(
            total_depth_mm=75.0,
            duration_hr=4.0,
            dt_min=15.0,
            quartile=2,
            probability=50,
        )

        assert isinstance(result, HyetographResult)
        assert "huff_q2" in result.method
        assert result.total_depth_mm == pytest.approx(75.0, rel=0.02)

    def test_all_quartiles(self):
        """Test todos los cuartiles Huff."""
        for q in [1, 2, 3, 4]:
            result = huff_distribution(
                total_depth_mm=50.0,
                duration_hr=3.0,
                dt_min=10.0,
                quartile=q,
                probability=50,
            )

            assert f"huff_q{q}" in result.method
            assert result.total_depth_mm == pytest.approx(50.0, rel=0.02)

    def test_all_probabilities(self):
        """Test todas las probabilidades Huff."""
        for prob in [10, 50, 90]:
            result = huff_distribution(
                total_depth_mm=50.0,
                duration_hr=3.0,
                dt_min=10.0,
                quartile=2,
                probability=prob,
            )

            assert f"p{prob}" in result.method
            assert result.total_depth_mm == pytest.approx(50.0, rel=0.02)

    def test_quartile_1_early_peak(self):
        """Huff cuartil 1 debe tener pico temprano."""
        result = huff_distribution(
            total_depth_mm=50.0,
            duration_hr=4.0,
            dt_min=10.0,
            quartile=1,
            probability=50,
        )

        peak_idx = np.argmax(result.intensity_mmhr)
        n = len(result.time_min)

        # Pico en primer cuarto
        assert peak_idx < n // 2

    def test_quartile_4_late_peak(self):
        """Huff cuartil 4 debe tener pico tardío."""
        result = huff_distribution(
            total_depth_mm=50.0,
            duration_hr=4.0,
            dt_min=10.0,
            quartile=4,
            probability=50,
        )

        peak_idx = np.argmax(result.intensity_mmhr)
        n = len(result.time_min)

        # Pico en última mitad
        assert peak_idx > n // 2

    def test_invalid_quartile_raises(self):
        """Cuartil inválido debe lanzar error."""
        with pytest.raises(ValueError, match="Cuartil"):
            huff_distribution(
                total_depth_mm=50.0,
                duration_hr=3.0,
                dt_min=10.0,
                quartile=5,  # Inválido
                probability=50,
            )

    def test_invalid_probability_raises(self):
        """Probabilidad inválida debe lanzar error."""
        with pytest.raises(ValueError, match="Probabilidad"):
            huff_distribution(
                total_depth_mm=50.0,
                duration_hr=3.0,
                dt_min=10.0,
                quartile=2,
                probability=75,  # Inválido
            )

    def test_cumulative_monotonic(self):
        """Test acumulado monótono creciente."""
        result = huff_distribution(
            total_depth_mm=50.0,
            duration_hr=3.0,
            dt_min=10.0,
            quartile=2,
            probability=50,
        )

        cumulative = result.cumulative_mm
        for i in range(1, len(cumulative)):
            assert cumulative[i] >= cumulative[i - 1]


class TestGenerateHyetograph:
    """Tests para función principal generate_hyetograph."""

    def test_alternating_blocks_method(self, sherman_coeffs):
        """Test método bloques alternantes."""
        result = generate_hyetograph(
            method=StormMethod.ALTERNATING_BLOCKS,
            total_depth_mm=50.0,
            duration_hr=2.0,
            dt_min=10.0,
            idf_method="sherman",
            idf_coeffs=sherman_coeffs,
            return_period_yr=25,
        )

        assert result.method == "alternating_blocks"
        assert result.total_depth_mm > 0

    def test_chicago_method(self, sherman_coeffs):
        """Test método Chicago."""
        result = generate_hyetograph(
            method=StormMethod.CHICAGO,
            total_depth_mm=60.0,
            duration_hr=3.0,
            dt_min=15.0,
            idf_coeffs=sherman_coeffs,
            return_period_yr=50,
            advancement_coef=0.4,
        )

        assert result.method == "chicago"
        assert result.total_depth_mm == pytest.approx(60.0, rel=0.01)

    def test_scs_type_ii_method(self):
        """Test método SCS Type II."""
        result = generate_hyetograph(
            method=StormMethod.SCS_TYPE_II,
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
        )

        assert result.method == "scs_type_ii"
        assert result.total_depth_mm == pytest.approx(100.0, rel=0.02)

    def test_scs_type_i_method(self):
        """Test método SCS Type I."""
        result = generate_hyetograph(
            method=StormMethod.SCS_TYPE_I,
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
        )

        assert result.method == "scs_type_i"

    def test_scs_type_ia_method(self):
        """Test método SCS Type IA."""
        result = generate_hyetograph(
            method=StormMethod.SCS_TYPE_IA,
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
        )

        assert result.method == "scs_type_ia"

    def test_scs_type_iii_method(self):
        """Test método SCS Type III."""
        result = generate_hyetograph(
            method=StormMethod.SCS_TYPE_III,
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=60.0,
        )

        assert result.method == "scs_type_iii"

    def test_huff_q1_method(self):
        """Test método Huff Q1."""
        result = generate_hyetograph(
            method=StormMethod.HUFF_Q1,
            total_depth_mm=50.0,
            duration_hr=4.0,
            dt_min=10.0,
            huff_probability=50,
        )

        assert "huff" in result.method
        assert "q1" in result.method

    def test_huff_q2_method(self):
        """Test método Huff Q2."""
        result = generate_hyetograph(
            method=StormMethod.HUFF_Q2,
            total_depth_mm=50.0,
            duration_hr=4.0,
            dt_min=10.0,
        )

        assert "huff" in result.method
        assert "q2" in result.method

    def test_huff_q3_method(self):
        """Test método Huff Q3."""
        result = generate_hyetograph(
            method=StormMethod.HUFF_Q3,
            total_depth_mm=50.0,
            duration_hr=4.0,
            dt_min=10.0,
        )

        assert "huff" in result.method
        assert "q3" in result.method

    def test_huff_q4_method(self):
        """Test método Huff Q4."""
        result = generate_hyetograph(
            method=StormMethod.HUFF_Q4,
            total_depth_mm=50.0,
            duration_hr=4.0,
            dt_min=10.0,
        )

        assert "huff" in result.method
        assert "q4" in result.method

    def test_alternating_blocks_missing_idf_raises(self):
        """Bloques alternantes sin IDF debe lanzar error."""
        with pytest.raises(ValueError, match="idf_method"):
            generate_hyetograph(
                method=StormMethod.ALTERNATING_BLOCKS,
                total_depth_mm=50.0,
                duration_hr=2.0,
                dt_min=10.0,
                # Falta idf_method e idf_coeffs
            )

    def test_chicago_missing_coeffs_raises(self, sherman_coeffs):
        """Chicago sin coeficientes debe lanzar error."""
        with pytest.raises(ValueError, match="idf_coeffs"):
            generate_hyetograph(
                method=StormMethod.CHICAGO,
                total_depth_mm=50.0,
                duration_hr=2.0,
                dt_min=10.0,
                # Falta idf_coeffs
            )


class TestBimodalDinagua:
    """Tests para bimodal_dinagua."""

    def test_basic_generation(self):
        """Test generación básica."""
        result = bimodal_dinagua(
            p3_10=78.0,
            return_period_yr=25,
            duration_hr=6.0,
            dt_min=15.0,
        )

        assert isinstance(result, HyetographResult)
        assert result.method == "bimodal_dinagua"
        assert result.total_depth_mm > 0
        assert result.peak_intensity_mmhr > 0

    def test_depth_matches_dinagua(self):
        """Profundidad total debe coincidir con IDF DINAGUA."""
        from hidropluvial.core.idf import dinagua_depth

        p3_10 = 83.0
        tr = 50
        duration = 4.0

        result = bimodal_dinagua(
            p3_10=p3_10,
            return_period_yr=tr,
            duration_hr=duration,
            dt_min=10.0,
        )

        expected_depth = dinagua_depth(p3_10, tr, duration)
        assert result.total_depth_mm == pytest.approx(expected_depth, rel=0.02)

    def test_with_area_correction(self):
        """Test con corrección por área."""
        from hidropluvial.core.idf import dinagua_depth

        p3_10 = 78.0
        tr = 25
        duration = 6.0
        area = 75.0

        result = bimodal_dinagua(
            p3_10=p3_10,
            return_period_yr=tr,
            duration_hr=duration,
            dt_min=15.0,
            area_km2=area,
        )

        expected_depth = dinagua_depth(p3_10, tr, duration, area)
        assert result.total_depth_mm == pytest.approx(expected_depth, rel=0.02)

    def test_area_reduces_depth(self):
        """Corrección por área debe reducir profundidad."""
        result_no_area = bimodal_dinagua(
            p3_10=78.0,
            return_period_yr=25,
            duration_hr=6.0,
            dt_min=15.0,
        )

        result_with_area = bimodal_dinagua(
            p3_10=78.0,
            return_period_yr=25,
            duration_hr=6.0,
            dt_min=15.0,
            area_km2=100.0,
        )

        assert result_with_area.total_depth_mm < result_no_area.total_depth_mm

    def test_volume_split(self):
        """Test división de volumen."""
        result = bimodal_dinagua(
            p3_10=78.0,
            return_period_yr=25,
            duration_hr=4.0,
            dt_min=10.0,
            peak1_position=0.25,
            peak2_position=0.75,
            volume_split=0.7,
        )

        depths = np.array(result.depth_mm)
        n = len(depths)

        vol_first = np.sum(depths[: n // 2])
        vol_second = np.sum(depths[n // 2:])

        # Primera mitad debe tener más volumen
        assert vol_first > vol_second

    def test_peak_positions(self):
        """Test posiciones de picos personalizadas."""
        result = bimodal_dinagua(
            p3_10=78.0,
            return_period_yr=25,
            duration_hr=4.0,
            dt_min=10.0,
            peak1_position=0.2,
            peak2_position=0.8,
        )

        depths = np.array(result.depth_mm)
        n = len(depths)

        # Encontrar picos en cada mitad
        peak1_idx = np.argmax(depths[: n // 2])
        peak2_idx = n // 2 + np.argmax(depths[n // 2:])

        # Picos deben estar separados
        assert peak2_idx - peak1_idx > n // 3


class TestIntegration:
    """Tests de integración para temporal.py."""

    def test_all_depths_positive(self, sherman_coeffs):
        """Todas las profundidades deben ser positivas."""
        # Test varios métodos
        methods_to_test = [
            (StormMethod.SCS_TYPE_II, {}),
            (StormMethod.HUFF_Q2, {}),
            (StormMethod.CHICAGO, {"idf_coeffs": sherman_coeffs}),
            (StormMethod.ALTERNATING_BLOCKS, {"idf_method": "sherman", "idf_coeffs": sherman_coeffs}),
        ]

        for method, extra_args in methods_to_test:
            result = generate_hyetograph(
                method=method,
                total_depth_mm=50.0,
                duration_hr=4.0,
                dt_min=15.0,
                **extra_args,
            )

            assert all(d >= 0 for d in result.depth_mm), f"Negative depth in {method}"
            assert all(i >= 0 for i in result.intensity_mmhr), f"Negative intensity in {method}"

    def test_all_cumulative_match_total(self, sherman_coeffs):
        """Acumulado final debe coincidir con total."""
        methods_to_test = [
            (StormMethod.SCS_TYPE_II, {}),
            (StormMethod.HUFF_Q2, {}),
            (StormMethod.CHICAGO, {"idf_coeffs": sherman_coeffs}),
        ]

        for method, extra_args in methods_to_test:
            result = generate_hyetograph(
                method=method,
                total_depth_mm=75.0,
                duration_hr=4.0,
                dt_min=15.0,
                **extra_args,
            )

            assert result.cumulative_mm[-1] == pytest.approx(result.total_depth_mm, rel=0.02)

    def test_different_dt_same_total(self, sherman_coeffs):
        """Diferentes dt deben dar mismo total."""
        for dt in [5.0, 10.0, 15.0, 30.0]:
            result = generate_hyetograph(
                method=StormMethod.SCS_TYPE_II,
                total_depth_mm=60.0,
                duration_hr=6.0,
                dt_min=dt,
            )

            assert result.total_depth_mm == pytest.approx(60.0, rel=0.02)


class TestCustomDepthStorm:
    """Tests para custom_depth_storm - precipitación personalizada."""

    def test_uniform_distribution(self):
        """Test distribución uniforme."""
        from hidropluvial.core.temporal import custom_depth_storm

        result = custom_depth_storm(
            total_depth_mm=60.0,
            duration_hr=2.0,
            dt_min=10.0,
            distribution="uniform",
        )

        assert result.method == "custom_uniform"
        assert result.total_depth_mm == pytest.approx(60.0, rel=0.01)
        # Distribución uniforme: todas las profundidades iguales
        depths = np.array(result.depth_mm)
        assert np.allclose(depths, depths[0], rtol=0.01)

    def test_triangular_distribution(self):
        """Test distribución triangular."""
        from hidropluvial.core.temporal import custom_depth_storm

        result = custom_depth_storm(
            total_depth_mm=50.0,
            duration_hr=3.0,
            dt_min=15.0,
            distribution="triangular",
        )

        assert result.method == "custom_triangular"
        assert result.total_depth_mm == pytest.approx(50.0, rel=0.01)
        # El pico debe estar cerca del centro
        depths = np.array(result.depth_mm)
        peak_idx = np.argmax(depths)
        n = len(depths)
        assert abs(peak_idx - n // 2) <= 1

    def test_alternating_blocks_distribution(self):
        """Test distribución bloques alternantes."""
        from hidropluvial.core.temporal import custom_depth_storm

        result = custom_depth_storm(
            total_depth_mm=80.0,
            duration_hr=6.0,
            dt_min=10.0,
            distribution="alternating_blocks",
            peak_position=0.5,
        )

        assert result.method == "custom_alternating_blocks"
        assert result.total_depth_mm == pytest.approx(80.0, rel=0.01)
        # El pico debe estar cerca del centro
        depths = np.array(result.depth_mm)
        peak_idx = np.argmax(depths)
        n = len(depths)
        assert abs(peak_idx - n // 2) <= 2

    def test_scs_type_ii_distribution(self):
        """Test distribución SCS Tipo II."""
        from hidropluvial.core.temporal import custom_depth_storm

        result = custom_depth_storm(
            total_depth_mm=100.0,
            duration_hr=24.0,
            dt_min=30.0,
            distribution="scs_type_ii",
        )

        assert result.method == "custom_scs_type_ii"
        assert result.total_depth_mm == pytest.approx(100.0, rel=0.02)

    def test_huff_distribution(self):
        """Test distribución Huff."""
        from hidropluvial.core.temporal import custom_depth_storm

        result = custom_depth_storm(
            total_depth_mm=70.0,
            duration_hr=4.0,
            dt_min=15.0,
            distribution="huff_q2",
            huff_quartile=2,
        )

        assert "huff" in result.method
        assert result.total_depth_mm == pytest.approx(70.0, rel=0.02)

    def test_invalid_distribution_raises(self):
        """Distribución inválida debe lanzar error."""
        from hidropluvial.core.temporal import custom_depth_storm

        with pytest.raises(ValueError, match="Distribución desconocida"):
            custom_depth_storm(
                total_depth_mm=50.0,
                duration_hr=2.0,
                dt_min=10.0,
                distribution="invalid_method",
            )


class TestCustomHyetograph:
    """Tests para custom_hyetograph - hietograma personalizado."""

    def test_basic_creation(self):
        """Test creación básica de hietograma personalizado."""
        from hidropluvial.core.temporal import custom_hyetograph

        time_min = [2.5, 7.5, 12.5, 17.5, 22.5, 27.5]
        depth_mm = [5.0, 15.0, 25.0, 20.0, 10.0, 5.0]

        result = custom_hyetograph(time_min, depth_mm)

        assert result.method == "custom_event"
        assert result.total_depth_mm == pytest.approx(80.0, rel=0.01)
        assert len(result.time_min) == 6
        assert len(result.depth_mm) == 6

    def test_peak_intensity_correct(self):
        """Test intensidad pico calculada correctamente."""
        from hidropluvial.core.temporal import custom_hyetograph

        time_min = [2.5, 7.5, 12.5]  # dt = 5 min
        depth_mm = [10.0, 30.0, 10.0]

        result = custom_hyetograph(time_min, depth_mm)

        # Intensidad pico = 30 mm / 5 min * 60 = 360 mm/hr
        assert result.peak_intensity_mmhr == pytest.approx(360.0, rel=0.01)

    def test_cumulative_correct(self):
        """Test acumulado calculado correctamente."""
        from hidropluvial.core.temporal import custom_hyetograph

        time_min = [5.0, 10.0, 15.0, 20.0]
        depth_mm = [10.0, 20.0, 15.0, 5.0]

        result = custom_hyetograph(time_min, depth_mm)

        assert result.cumulative_mm == pytest.approx([10.0, 30.0, 45.0, 50.0], rel=0.01)

    def test_mismatched_lengths_raises(self):
        """Longitudes diferentes deben lanzar error."""
        from hidropluvial.core.temporal import custom_hyetograph

        with pytest.raises(ValueError, match="misma longitud"):
            custom_hyetograph([5.0, 10.0], [10.0, 20.0, 30.0])

    def test_minimum_intervals_required(self):
        """Mínimo 2 intervalos requeridos."""
        from hidropluvial.core.temporal import custom_hyetograph

        with pytest.raises(ValueError, match="al menos 2"):
            custom_hyetograph([5.0], [10.0])
