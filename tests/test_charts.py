"""Tests para el módulo de generación de gráficos TikZ."""

import pytest
import numpy as np

from hidropluvial.reports.charts import (
    HydrographSeries,
    generate_hydrograph_tikz,
    generate_hydrograph_comparison_tikz,
    generate_hyetograph_tikz,
    generate_hyetograph_filled_tikz,
    hydrograph_result_to_tikz,
    hyetograph_result_to_tikz,
    _minutes_to_hour_label,
    _generate_hour_ticks,
)
from hidropluvial.config import HydrographResult, HyetographResult, HydrographMethod


class TestHelperFunctions:
    """Tests para funciones auxiliares."""

    def test_minutes_to_hour_label_zero(self):
        """Test conversión de 0 minutos."""
        assert _minutes_to_hour_label(0) == "0:00"

    def test_minutes_to_hour_label_one_hour(self):
        """Test conversión de 60 minutos."""
        assert _minutes_to_hour_label(60) == "1:00"

    def test_minutes_to_hour_label_partial(self):
        """Test conversión de minutos parciales."""
        assert _minutes_to_hour_label(90) == "1:30"
        assert _minutes_to_hour_label(150) == "2:30"

    def test_minutes_to_hour_label_multiple_hours(self):
        """Test conversión de múltiples horas."""
        assert _minutes_to_hour_label(180) == "3:00"
        assert _minutes_to_hour_label(480) == "8:00"

    def test_generate_hour_ticks_short_duration(self):
        """Test generación de ticks para duración corta."""
        ticks, labels = _generate_hour_ticks(120)  # 2 horas
        assert 0 in ticks
        assert 60 in ticks
        assert 120 in ticks
        assert "0:00" in labels
        assert "1:00" in labels

    def test_generate_hour_ticks_long_duration(self):
        """Test generación de ticks para duración larga."""
        ticks, labels = _generate_hour_ticks(480)  # 8 horas
        assert 0 in ticks
        assert "0:00" in labels
        # Debe usar intervalos de 1 hora
        assert 60 in ticks

    def test_generate_hour_ticks_very_long_duration(self):
        """Test generación de ticks para duración muy larga."""
        ticks, labels = _generate_hour_ticks(1440)  # 24 horas
        assert 0 in ticks
        assert "0:00" in labels
        # Debe usar intervalos mayores


class TestHydrographTikz:
    """Tests para generación de hidrogramas TikZ."""

    @pytest.fixture
    def sample_hydrograph_data(self):
        """Datos de ejemplo para hidrograma."""
        time = list(range(0, 301, 5))  # 0 a 300 minutos
        flow = [0] * 10 + list(range(10, 0, -1)) + [0] * 41
        flow = flow[:len(time)]
        return time, flow

    def test_generate_hydrograph_single_series(self, sample_hydrograph_data):
        """Test generación con una sola serie."""
        time, flow = sample_hydrograph_data
        series = [HydrographSeries(time_min=time, flow_m3s=flow, label="Test")]

        result = generate_hydrograph_tikz(series, caption="Test", label="fig:test")

        assert "\\begin{figure}[H]" in result
        assert "\\begin{tikzpicture}" in result
        assert "\\begin{axis}" in result
        assert "Caudal" in result
        assert "Test" in result
        assert "\\addlegendentry{Test}" in result
        assert "\\end{figure}" in result

    def test_generate_hydrograph_multiple_series(self, sample_hydrograph_data):
        """Test generación con múltiples series."""
        time, flow = sample_hydrograph_data
        series = [
            HydrographSeries(time_min=time, flow_m3s=flow, label="Serie 1", color="red"),
            HydrographSeries(time_min=time, flow_m3s=[f * 0.8 for f in flow], label="Serie 2", color="blue"),
        ]

        result = generate_hydrograph_tikz(series)

        assert "Serie 1" in result
        assert "Serie 2" in result
        assert "red" in result
        assert "blue" in result

    def test_generate_hydrograph_empty_series_raises(self):
        """Test que series vacías lanzan error."""
        with pytest.raises(ValueError):
            generate_hydrograph_tikz([])

    def test_generate_hydrograph_hour_ticks(self, sample_hydrograph_data):
        """Test que los ticks están en formato hora."""
        time, flow = sample_hydrograph_data
        series = [HydrographSeries(time_min=time, flow_m3s=flow, label="Test")]

        result = generate_hydrograph_tikz(series)

        assert "0:00" in result
        assert "xticklabels={" in result

    def test_generate_hydrograph_custom_axes(self, sample_hydrograph_data):
        """Test con ejes personalizados."""
        time, flow = sample_hydrograph_data
        series = [HydrographSeries(time_min=time, flow_m3s=flow, label="Test")]

        result = generate_hydrograph_tikz(
            series,
            xlabel="Tiempo personalizado",
            ylabel="Caudal personalizado",
            ymax=100,
        )

        assert "Tiempo personalizado" in result
        assert "Caudal personalizado" in result
        assert "ymax=100" in result


class TestHydrographComparison:
    """Tests para comparación de hidrogramas."""

    def test_generate_comparison_basic(self):
        """Test comparación básica de hidrogramas."""
        time = list(range(0, 121, 10))
        flow1 = [0, 1, 3, 5, 4, 3, 2, 1, 0.5, 0.2, 0.1, 0, 0]
        flow2 = [0, 0.5, 2, 4, 3, 2, 1.5, 1, 0.4, 0.2, 0.1, 0, 0]

        result = generate_hydrograph_comparison_tikz(
            time, flow1,
            time, flow2,
            label_1="Sin MCE",
            label_2="Con MCE",
        )

        assert "Sin MCE" in result
        assert "Con MCE" in result
        assert "red" in result
        assert "dashed" in result
        assert "black" in result
        assert "solid" in result

    def test_generate_comparison_custom_labels(self):
        """Test comparación con etiquetas personalizadas."""
        time = list(range(0, 61, 10))
        flow = [0, 1, 2, 1, 0.5, 0.2, 0]

        result = generate_hydrograph_comparison_tikz(
            time, flow,
            time, [f * 0.5 for f in flow],
            label_1="Escenario A",
            label_2="Escenario B",
            caption="Comparación de escenarios",
        )

        assert "Escenario A" in result
        assert "Escenario B" in result
        assert "Comparación de escenarios" in result


class TestHyetographTikz:
    """Tests para generación de hietogramas TikZ."""

    @pytest.fixture
    def sample_hyetograph_data(self):
        """Datos de ejemplo para hietograma."""
        time = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        intensity = [10, 15, 25, 50, 100, 150, 100, 50, 25, 15, 10, 5]
        return time, intensity

    def test_generate_hyetograph_basic(self, sample_hyetograph_data):
        """Test generación básica de hietograma."""
        time, intensity = sample_hyetograph_data

        result = generate_hyetograph_tikz(
            time, intensity,
            caption="Test hietograma",
            label="fig:hyeto_test",
        )

        assert "\\begin{figure}[H]" in result
        assert "y dir=reverse" in result
        assert "ybar" in result
        assert "draw=black" in result
        assert "fill=none" in result
        assert "Test hietograma" in result

    def test_generate_hyetograph_with_title(self, sample_hyetograph_data):
        """Test hietograma con título interno."""
        time, intensity = sample_hyetograph_data

        result = generate_hyetograph_tikz(
            time, intensity,
            title="Tormenta Tr=10 años",
        )

        assert "title={Tormenta Tr=10 años}" in result

    def test_generate_hyetograph_hour_ticks(self, sample_hyetograph_data):
        """Test que los ticks están en formato hora."""
        time, intensity = sample_hyetograph_data

        result = generate_hyetograph_tikz(time, intensity)

        assert "0:00" in result
        assert "1:00" in result

    def test_generate_hyetograph_filled(self, sample_hyetograph_data):
        """Test hietograma con relleno."""
        time, intensity = sample_hyetograph_data

        result = generate_hyetograph_filled_tikz(
            time, intensity,
            fill_color="blue!50",
        )

        assert "fill=blue!50" in result
        assert "fill=none" not in result

    def test_generate_hyetograph_insufficient_data_raises(self):
        """Test que datos insuficientes lanzan error."""
        with pytest.raises(ValueError):
            generate_hyetograph_tikz([5], [10])


class TestResultConversion:
    """Tests para conversión de resultados a TikZ."""

    def test_hydrograph_result_to_tikz(self):
        """Test conversión de HydrographResult."""
        result = HydrographResult(
            time_hr=[0, 0.5, 1.0, 1.5, 2.0],
            flow_m3s=[0, 5, 10, 5, 2],
            peak_flow_m3s=10,
            time_to_peak_hr=1.0,
            volume_m3=1000,
            method=HydrographMethod.SCS_TRIANGULAR,
        )

        tikz = hydrograph_result_to_tikz(
            result,
            caption="Hidrograma SCS",
            label="fig:hydro_scs",
        )

        assert "\\begin{figure}" in tikz
        assert "scs_triangular" in tikz
        assert "Hidrograma SCS" in tikz
        # Verificar conversión de horas a minutos (1 hr = 60 min)
        assert "(60," in tikz or "(60.0," in tikz or "(60," in tikz

    def test_hyetograph_result_to_tikz(self):
        """Test conversión de HyetographResult."""
        result = HyetographResult(
            time_min=[5, 10, 15, 20, 25, 30],
            intensity_mmhr=[10, 30, 80, 30, 15, 5],
            depth_mm=[0.83, 2.5, 6.67, 2.5, 1.25, 0.42],
            cumulative_mm=[0.83, 3.33, 10.0, 12.5, 13.75, 14.17],
            method="alternating_blocks",
            total_depth_mm=14.17,
            peak_intensity_mmhr=80,
        )

        tikz = hyetograph_result_to_tikz(
            result,
            caption="Hietograma de diseño",
            label="fig:hyeto_design",
            title="Tormenta Tr=25 años",
        )

        assert "\\begin{figure}" in tikz
        assert "y dir=reverse" in tikz
        assert "Hietograma de diseño" in tikz
        assert "Tormenta Tr=25 años" in tikz


class TestOutputFormat:
    """Tests para verificar formato de salida LaTeX."""

    def test_hydrograph_has_required_latex_elements(self):
        """Test que el hidrograma tiene todos los elementos LaTeX necesarios."""
        time = list(range(0, 61, 10))
        flow = [0, 1, 2, 1, 0.5, 0.2, 0]
        series = [HydrographSeries(time_min=time, flow_m3s=flow, label="Test")]

        result = generate_hydrograph_tikz(series)

        required_elements = [
            "\\begin{figure}[H]",
            "\\centering",
            "\\begin{tikzpicture}",
            "\\begin{axis}",
            "\\addplot",
            "\\end{axis}",
            "\\end{tikzpicture}",
            "\\caption",
            "\\label",
            "\\end{figure}",
        ]

        for elem in required_elements:
            assert elem in result, f"Falta elemento: {elem}"

    def test_hyetograph_has_required_latex_elements(self):
        """Test que el hietograma tiene todos los elementos LaTeX necesarios."""
        time = [5, 10, 15, 20]
        intensity = [10, 20, 15, 5]

        result = generate_hyetograph_tikz(time, intensity)

        required_elements = [
            "\\begin{figure}[H]",
            "\\centering",
            "\\begin{tikzpicture}",
            "\\begin{axis}",
            "ybar",
            "y dir=reverse",
            "\\addplot",
            "\\end{axis}",
            "\\end{tikzpicture}",
            "\\caption",
            "\\label",
            "\\end{figure}",
        ]

        for elem in required_elements:
            assert elem in result, f"Falta elemento: {elem}"

    def test_coordinates_format(self):
        """Test formato de coordenadas."""
        time = [5, 10, 15]
        flow = [1.5, 2.5, 1.0]
        series = [HydrographSeries(time_min=time, flow_m3s=flow, label="Test")]

        result = generate_hydrograph_tikz(series)

        # Verificar que las coordenadas están en formato correcto
        assert "(5, 1.50)" in result or "(5, 1.5)" in result
        assert "(10, 2.50)" in result or "(10, 2.5)" in result
