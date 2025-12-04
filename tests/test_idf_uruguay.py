"""Tests para módulo IDF Uruguay/DINAGUA."""

import pytest
import math

from hidropluvial.core.idf import (
    dinagua_ct,
    dinagua_ca,
    dinagua_intensity,
    dinagua_intensity_simple,
    generate_dinagua_idf_table,
    get_p3_10,
    P3_10_URUGUAY,
)


class TestDinaguaCT:
    """Tests para factor CT (corrección por período de retorno)."""

    def test_ct_t10_equals_1(self):
        """CT para T=10 años debe ser aproximadamente 1.0."""
        ct = dinagua_ct(10)
        assert ct == pytest.approx(1.0, rel=0.01)

    def test_ct_values_from_formula(self):
        """Verificar valores calculados con fórmula CT = 0.5786 - 0.4312 * log10(ln(Tr/(Tr-1)))."""
        # Valores calculados directamente de la fórmula documentada en DINAGUA
        # La fórmula da CT(10) = 1.0 exactamente (punto de referencia)
        expected = {
            2: 0.647,    # Fórmula: 0.6472
            5: 0.860,    # Fórmula: 0.8595
            10: 1.000,   # Punto de referencia exacto
            25: 1.178,   # Fórmula: 1.1776
            50: 1.309,   # Fórmula: 1.3093
            100: 1.440,  # Fórmula: 1.4401
        }
        for tr, ct_expected in expected.items():
            ct = dinagua_ct(tr)
            assert ct == pytest.approx(ct_expected, rel=0.01), f"CT({tr}) = {ct}, esperado {ct_expected}"

    def test_ct_increases_with_return_period(self):
        """CT debe aumentar con el período de retorno."""
        ct_10 = dinagua_ct(10)
        ct_50 = dinagua_ct(50)
        ct_100 = dinagua_ct(100)
        assert ct_10 < ct_50 < ct_100

    def test_ct_invalid_return_period(self):
        """Debe fallar para T < 2 años."""
        with pytest.raises(ValueError):
            dinagua_ct(1)


class TestDinaguaCA:
    """Tests para factor CA (corrección por área)."""

    def test_ca_small_area_equals_1(self):
        """CA = 1.0 para áreas <= 1 km²."""
        assert dinagua_ca(0.5, 1.0) == 1.0
        assert dinagua_ca(1.0, 1.0) == 1.0

    def test_ca_decreases_with_area(self):
        """CA debe disminuir con mayor área."""
        ca_10 = dinagua_ca(10, 1.0)
        ca_50 = dinagua_ca(50, 1.0)
        ca_100 = dinagua_ca(100, 1.0)
        assert ca_10 > ca_50 > ca_100

    def test_ca_increases_with_duration(self):
        """CA debe aumentar (menos reducción) con mayor duración."""
        ca_1hr = dinagua_ca(50, 1.0)
        ca_6hr = dinagua_ca(50, 6.0)
        ca_24hr = dinagua_ca(50, 24.0)
        assert ca_1hr < ca_6hr < ca_24hr

    def test_ca_always_le_1(self):
        """CA siempre debe ser <= 1.0."""
        for area in [10, 50, 100, 200]:
            for d in [0.5, 1, 3, 6, 12, 24]:
                ca = dinagua_ca(area, d)
                assert ca <= 1.0


class TestDinaguaIntensity:
    """Tests para cálculo de intensidad DINAGUA."""

    def test_example_maldonado(self):
        """Verificar cálculo para Maldonado usando fórmula DINAGUA."""
        # Datos: P3,10=83mm (mayorado), Tr=100, d=6hr, A=25km²
        result = dinagua_intensity(83, 100, 6.0, 25)

        # CT(100) usando fórmula = 1.4401
        assert result.ct == pytest.approx(1.440, rel=0.01)
        # CA(25, 6) debe estar cerca de 0.979
        assert result.ca == pytest.approx(0.979, rel=0.02)
        # Los valores de intensidad y profundidad dependen de CT real
        assert result.intensity_mmhr > 0
        assert result.depth_mm > 0
        # Verificar que intensidad * duración = profundidad
        assert result.depth_mm == pytest.approx(result.intensity_mmhr * 6.0, rel=0.01)

    def test_intensity_short_duration(self):
        """Test ecuación para d < 3 horas."""
        result = dinagua_intensity(78, 10, 1.0)
        # Para d=1hr < 3hr, usa primera ecuación
        assert result.intensity_mmhr > 0
        assert result.ct == pytest.approx(1.0, rel=0.01)

    def test_intensity_long_duration(self):
        """Test ecuación para d >= 3 horas."""
        result = dinagua_intensity(78, 10, 6.0)
        # Para d=6hr >= 3hr, usa segunda ecuación
        assert result.intensity_mmhr > 0

    def test_intensity_decreases_with_duration(self):
        """Intensidad debe disminuir con mayor duración."""
        i_1hr = dinagua_intensity_simple(78, 10, 1.0)
        i_3hr = dinagua_intensity_simple(78, 10, 3.0)
        i_6hr = dinagua_intensity_simple(78, 10, 6.0)
        assert i_1hr > i_3hr > i_6hr

    def test_depth_increases_with_duration(self):
        """Precipitación total debe aumentar con duración."""
        result_1hr = dinagua_intensity(78, 10, 1.0)
        result_3hr = dinagua_intensity(78, 10, 3.0)
        result_6hr = dinagua_intensity(78, 10, 6.0)
        assert result_1hr.depth_mm < result_3hr.depth_mm < result_6hr.depth_mm


class TestDinaguaTable:
    """Tests para generación de tabla IDF."""

    def test_table_generation(self):
        """Test generación de tabla completa."""
        result = generate_dinagua_idf_table(78)

        assert "p3_10" in result
        assert "durations_hr" in result
        assert "return_periods_yr" in result
        assert "intensities_mmhr" in result
        assert "depths_mm" in result

        # Verificar dimensiones
        n_durations = len(result["durations_hr"])
        n_periods = len(result["return_periods_yr"])
        assert result["intensities_mmhr"].shape == (n_periods, n_durations)

    def test_table_with_area(self):
        """Test tabla con corrección por área."""
        result_no_area = generate_dinagua_idf_table(78)
        result_with_area = generate_dinagua_idf_table(78, area_km2=50)

        # Intensidades con área deben ser menores
        assert (result_with_area["intensities_mmhr"] <= result_no_area["intensities_mmhr"]).all()


class TestP310Uruguay:
    """Tests para valores P3,10 por departamento."""

    def test_all_departments_have_values(self):
        """Verificar que hay 19 departamentos."""
        assert len(P3_10_URUGUAY) == 19

    def test_montevideo_value(self):
        """Verificar valor de Montevideo."""
        assert get_p3_10("montevideo") == 78

    def test_case_insensitive(self):
        """Debe funcionar sin importar mayúsculas."""
        assert get_p3_10("MONTEVIDEO") == 78
        assert get_p3_10("Montevideo") == 78

    def test_invalid_department(self):
        """Debe fallar para departamento inválido."""
        with pytest.raises(ValueError):
            get_p3_10("buenos_aires")

    def test_values_in_range(self):
        """Todos los valores deben estar entre 70-90 mm."""
        for depto, p310 in P3_10_URUGUAY.items():
            assert 70 <= p310 <= 90, f"{depto}: P3,10 = {p310} fuera de rango"
