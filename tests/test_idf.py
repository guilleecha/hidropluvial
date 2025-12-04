"""Tests para módulo IDF."""

import numpy as np
import pytest

from hidropluvial.core.idf import (
    sherman_intensity,
    bernard_intensity,
    depth_from_intensity,
    intensity_from_depth,
    generate_idf_table,
    get_intensity,
)
from hidropluvial.config import ShermanCoefficients, BernardCoefficients


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
