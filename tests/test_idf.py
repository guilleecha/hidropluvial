"""Tests para módulo IDF."""

import numpy as np
import pytest

from hidropluvial.core.idf import (
    sherman_intensity,
    bernard_intensity,
    koutsoyiannis_intensity,
    depth_from_intensity,
    intensity_from_depth,
    generate_idf_table,
    get_intensity,
    get_depth,
)
from hidropluvial.config import (
    ShermanCoefficients,
    BernardCoefficients,
    KoutsoyiannisCoefficients,
)


class TestShermanIntensity:
    """Tests para ecuación Sherman."""

    def test_basic_calculation(self, sherman_coeffs):
        """Test cálculo básico de intensidad."""
        intensity = sherman_intensity(60, 100, sherman_coeffs)
        assert intensity > 0
        assert isinstance(intensity, float)

    def test_intensity_decreases_with_duration(self, sherman_coeffs):
        """Intensidad debe disminuir con mayor duración."""
        i_30 = sherman_intensity(30, 100, sherman_coeffs)
        i_60 = sherman_intensity(60, 100, sherman_coeffs)
        i_120 = sherman_intensity(120, 100, sherman_coeffs)

        assert i_30 > i_60 > i_120

    def test_intensity_increases_with_return_period(self, sherman_coeffs):
        """Intensidad debe aumentar con mayor período de retorno."""
        i_10 = sherman_intensity(60, 10, sherman_coeffs)
        i_50 = sherman_intensity(60, 50, sherman_coeffs)
        i_100 = sherman_intensity(60, 100, sherman_coeffs)

        assert i_10 < i_50 < i_100

    def test_array_input(self, sherman_coeffs):
        """Test con array de duraciones."""
        durations = np.array([15, 30, 60, 120])
        intensities = sherman_intensity(durations, 100, sherman_coeffs)

        assert len(intensities) == 4
        assert all(intensities > 0)


class TestDepthIntensityConversion:
    """Tests para conversión profundidad-intensidad."""

    def test_depth_from_intensity(self):
        """Test conversión intensidad a profundidad."""
        intensity = 60.0  # mm/hr
        duration = 30.0  # min

        depth = depth_from_intensity(intensity, duration)
        assert depth == pytest.approx(30.0, rel=0.01)

    def test_intensity_from_depth(self):
        """Test conversión profundidad a intensidad."""
        depth = 30.0  # mm
        duration = 30.0  # min

        intensity = intensity_from_depth(depth, duration)
        assert intensity == pytest.approx(60.0, rel=0.01)

    def test_round_trip(self):
        """Test conversión ida y vuelta."""
        original_intensity = 75.5
        duration = 45.0

        depth = depth_from_intensity(original_intensity, duration)
        recovered_intensity = intensity_from_depth(depth, duration)

        assert recovered_intensity == pytest.approx(original_intensity, rel=0.001)


class TestIDFTable:
    """Tests para generación de tabla IDF."""

    def test_table_generation(self, sherman_coeffs):
        """Test generación de tabla completa."""
        durations = [15, 30, 60, 120]
        periods = [10, 50, 100]

        result = generate_idf_table(durations, periods, "sherman", sherman_coeffs)

        assert "durations" in result
        assert "return_periods" in result
        assert "intensities" in result
        assert "depths" in result

        assert result["intensities"].shape == (3, 4)
        assert result["depths"].shape == (3, 4)

    def test_table_values_positive(self, sherman_coeffs):
        """Todos los valores deben ser positivos."""
        result = generate_idf_table([15, 30, 60], [10, 100], "sherman", sherman_coeffs)

        assert np.all(result["intensities"] > 0)
        assert np.all(result["depths"] > 0)


class TestGetIntensity:
    """Tests para función get_intensity."""

    def test_sherman_method(self, sherman_coeffs):
        """Test método Sherman."""
        intensity = get_intensity(60, 100, "sherman", sherman_coeffs)
        assert intensity > 0

    def test_invalid_method(self, sherman_coeffs):
        """Test método inválido."""
        with pytest.raises(ValueError, match="Método desconocido"):
            get_intensity(60, 100, "invalid_method", sherman_coeffs)

    def test_bernard_method(self):
        """Test método Bernard."""
        coeffs = BernardCoefficients(a=1500.0, m=0.2, n=0.7)
        intensity = get_intensity(60, 100, "bernard", coeffs)
        assert intensity > 0

    def test_koutsoyiannis_method(self):
        """Test método Koutsoyiannis."""
        coeffs = KoutsoyiannisCoefficients(mu=50.0, sigma=15.0, theta=10.0, eta=0.7)
        intensity = get_intensity(60, 10, "koutsoyiannis", coeffs)
        assert intensity > 0

    def test_wrong_coeffs_type_sherman(self):
        """Test tipo de coeficientes incorrecto para Sherman."""
        coeffs = BernardCoefficients(a=1500.0, m=0.2, n=0.7)
        with pytest.raises(TypeError, match="ShermanCoefficients"):
            get_intensity(60, 100, "sherman", coeffs)

    def test_wrong_coeffs_type_bernard(self, sherman_coeffs):
        """Test tipo de coeficientes incorrecto para Bernard."""
        with pytest.raises(TypeError, match="BernardCoefficients"):
            get_intensity(60, 100, "bernard", sherman_coeffs)

    def test_wrong_coeffs_type_koutsoyiannis(self, sherman_coeffs):
        """Test tipo de coeficientes incorrecto para Koutsoyiannis."""
        with pytest.raises(TypeError, match="KoutsoyiannisCoefficients"):
            get_intensity(60, 100, "koutsoyiannis", sherman_coeffs)


class TestGetDepth:
    """Tests para función get_depth."""

    def test_sherman_method(self, sherman_coeffs):
        """Test profundidad con método Sherman."""
        depth = get_depth(60, 100, "sherman", sherman_coeffs)
        assert depth > 0

    def test_depth_equals_intensity_times_duration(self, sherman_coeffs):
        """Test que depth = intensity * duration / 60."""
        duration = 60  # minutos
        intensity = get_intensity(duration, 100, "sherman", sherman_coeffs)
        depth = get_depth(duration, 100, "sherman", sherman_coeffs)
        expected_depth = intensity * duration / 60
        assert depth == pytest.approx(expected_depth, rel=0.01)


class TestBernardIntensity:
    """Tests para ecuación Bernard."""

    def test_basic_calculation(self):
        """Test cálculo básico de intensidad Bernard."""
        coeffs = BernardCoefficients(a=1500.0, m=0.2, n=0.7)
        intensity = bernard_intensity(60, 100, coeffs)
        assert intensity > 0
        assert isinstance(intensity, float)

    def test_intensity_decreases_with_duration(self):
        """Intensidad debe disminuir con mayor duración."""
        coeffs = BernardCoefficients(a=1500.0, m=0.2, n=0.7)
        i_30 = bernard_intensity(30, 100, coeffs)
        i_60 = bernard_intensity(60, 100, coeffs)
        i_120 = bernard_intensity(120, 100, coeffs)
        assert i_30 > i_60 > i_120

    def test_intensity_increases_with_return_period(self):
        """Intensidad debe aumentar con mayor período de retorno."""
        coeffs = BernardCoefficients(a=1500.0, m=0.2, n=0.7)
        i_10 = bernard_intensity(60, 10, coeffs)
        i_50 = bernard_intensity(60, 50, coeffs)
        i_100 = bernard_intensity(60, 100, coeffs)
        assert i_10 < i_50 < i_100

    def test_array_input(self):
        """Test con array de duraciones."""
        coeffs = BernardCoefficients(a=1500.0, m=0.2, n=0.7)
        durations = np.array([15, 30, 60, 120])
        intensities = bernard_intensity(durations, 100, coeffs)
        assert len(intensities) == 4
        assert all(intensities > 0)

    def test_very_short_duration(self):
        """Test con duración muy corta (evita división por cero)."""
        coeffs = BernardCoefficients(a=1500.0, m=0.2, n=0.7)
        # Duración muy pequeña, debe manejar sin error
        intensity = bernard_intensity(0.01, 10, coeffs)
        assert intensity > 0


class TestKoutsoyiannisIntensity:
    """Tests para ecuación Koutsoyiannis."""

    def test_basic_calculation(self):
        """Test cálculo básico de intensidad Koutsoyiannis."""
        coeffs = KoutsoyiannisCoefficients(mu=50.0, sigma=15.0, theta=10.0, eta=0.7)
        intensity = koutsoyiannis_intensity(60, 10, coeffs)
        assert intensity > 0
        assert isinstance(intensity, float)

    def test_intensity_decreases_with_duration(self):
        """Intensidad debe disminuir con mayor duración."""
        coeffs = KoutsoyiannisCoefficients(mu=50.0, sigma=15.0, theta=10.0, eta=0.7)
        i_30 = koutsoyiannis_intensity(30, 10, coeffs)
        i_60 = koutsoyiannis_intensity(60, 10, coeffs)
        i_120 = koutsoyiannis_intensity(120, 10, coeffs)
        assert i_30 > i_60 > i_120

    def test_intensity_increases_with_return_period(self):
        """Intensidad debe aumentar con mayor período de retorno."""
        coeffs = KoutsoyiannisCoefficients(mu=50.0, sigma=15.0, theta=10.0, eta=0.7)
        i_10 = koutsoyiannis_intensity(60, 10, coeffs)
        i_50 = koutsoyiannis_intensity(60, 50, coeffs)
        i_100 = koutsoyiannis_intensity(60, 100, coeffs)
        assert i_10 < i_50 < i_100

    def test_array_input(self):
        """Test con array de duraciones."""
        coeffs = KoutsoyiannisCoefficients(mu=50.0, sigma=15.0, theta=10.0, eta=0.7)
        durations = np.array([15, 30, 60, 120])
        intensities = koutsoyiannis_intensity(durations, 10, coeffs)
        assert len(intensities) == 4
        assert all(intensities > 0)

    def test_invalid_return_period(self):
        """Test con período de retorno <= 1."""
        coeffs = KoutsoyiannisCoefficients(mu=50.0, sigma=15.0, theta=10.0, eta=0.7)
        with pytest.raises(ValueError, match="> 1"):
            koutsoyiannis_intensity(60, 1, coeffs)


class TestGenerateIDFTableMethods:
    """Tests adicionales para generación de tabla IDF con diferentes métodos."""

    def test_bernard_table(self):
        """Test generación de tabla con método Bernard."""
        coeffs = BernardCoefficients(a=1500.0, m=0.2, n=0.7)
        durations = [15, 30, 60, 120]
        periods = [10, 50, 100]

        result = generate_idf_table(durations, periods, "bernard", coeffs)

        assert result["intensities"].shape == (3, 4)
        assert np.all(result["intensities"] > 0)

    def test_koutsoyiannis_table(self):
        """Test generación de tabla con método Koutsoyiannis."""
        coeffs = KoutsoyiannisCoefficients(mu=50.0, sigma=15.0, theta=10.0, eta=0.7)
        durations = [15, 30, 60, 120]
        periods = [10, 50, 100]

        result = generate_idf_table(durations, periods, "koutsoyiannis", coeffs)

        assert result["intensities"].shape == (3, 4)
        assert np.all(result["intensities"] > 0)

    def test_invalid_method_table(self, sherman_coeffs):
        """Test método inválido en generación de tabla."""
        with pytest.raises(ValueError, match="Método desconocido"):
            generate_idf_table([60], [10], "invalid", sherman_coeffs)

    def test_wrong_coeffs_type_in_table(self, sherman_coeffs):
        """Test tipo de coeficientes incorrecto en tabla Bernard."""
        with pytest.raises(TypeError):
            generate_idf_table([60], [10], "bernard", sherman_coeffs)


class TestDepthIntensityArrays:
    """Tests adicionales para conversiones con arrays."""

    def test_depth_from_intensity_array(self):
        """Test conversión con arrays."""
        intensities = np.array([120, 60, 30])
        durations = np.array([30, 60, 120])
        depths = depth_from_intensity(intensities, durations)
        # 120 * 30/60 = 60, 60 * 60/60 = 60, 30 * 120/60 = 60
        expected = np.array([60, 60, 60])
        np.testing.assert_array_almost_equal(depths, expected)

    def test_intensity_from_depth_array(self):
        """Test conversión inversa con arrays."""
        depths = np.array([60, 60, 60])
        durations = np.array([30, 60, 120])
        intensities = intensity_from_depth(depths, durations)
        # 60 * 60/30 = 120, 60 * 60/60 = 60, 60 * 60/120 = 30
        expected = np.array([120, 60, 30])
        np.testing.assert_array_almost_equal(intensities, expected)
