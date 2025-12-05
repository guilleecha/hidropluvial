"""
Tests para cli/tc.py - Comandos de tiempo de concentración.
"""

import pytest
from typer.testing import CliRunner

from hidropluvial.cli.tc import (
    tc_app,
    tc_kirpich,
    tc_temez,
    tc_desbordes,
)


runner = CliRunner()


class TestTcKirpich:
    """Tests para comando tc kirpich."""

    def test_basic_calculation(self, capsys):
        """Test cálculo básico Kirpich."""
        tc_kirpich(length=1000.0, slope=0.02, surface="natural")

        captured = capsys.readouterr()
        assert "1000" in captured.out
        assert "0.02" in captured.out
        assert "natural" in captured.out
        assert "Tc =" in captured.out
        assert "horas" in captured.out
        assert "minutos" in captured.out

    def test_grassy_surface(self, capsys):
        """Test superficie grassy."""
        tc_kirpich(length=1500.0, slope=0.015, surface="grassy")

        captured = capsys.readouterr()
        assert "grassy" in captured.out
        assert "Tc =" in captured.out

    def test_concrete_surface(self, capsys):
        """Test superficie concrete."""
        tc_kirpich(length=500.0, slope=0.03, surface="concrete")

        captured = capsys.readouterr()
        assert "concrete" in captured.out
        assert "Tc =" in captured.out

    def test_shows_slope_percentage(self, capsys):
        """Test muestra pendiente en porcentaje."""
        tc_kirpich(length=1000.0, slope=0.0223, surface="natural")

        captured = capsys.readouterr()
        assert "2.23%" in captured.out or "2.23 %" in captured.out

    def test_different_lengths(self, capsys):
        """Test diferentes longitudes."""
        for length in [500.0, 1000.0, 2000.0, 5000.0]:
            tc_kirpich(length=length, slope=0.02, surface="natural")

            captured = capsys.readouterr()
            assert str(int(length)) in captured.out
            assert "Tc =" in captured.out

    def test_different_slopes(self, capsys):
        """Test diferentes pendientes."""
        for slope in [0.01, 0.02, 0.05, 0.10]:
            tc_kirpich(length=1000.0, slope=slope, surface="natural")

            captured = capsys.readouterr()
            assert "Tc =" in captured.out


class TestTcTemez:
    """Tests para comando tc temez."""

    def test_basic_calculation(self, capsys):
        """Test cálculo básico Temez."""
        tc_temez(length=2.5, slope=0.0223)

        captured = capsys.readouterr()
        assert "2.5" in captured.out
        assert "0.0223" in captured.out
        assert "Tc =" in captured.out
        assert "horas" in captured.out
        assert "minutos" in captured.out

    def test_shows_slope_percentage(self, capsys):
        """Test muestra pendiente en porcentaje."""
        tc_temez(length=1.0, slope=0.025)

        captured = capsys.readouterr()
        assert "2.5%" in captured.out or "2.50%" in captured.out

    def test_different_lengths(self, capsys):
        """Test diferentes longitudes."""
        for length in [1.0, 2.5, 5.0, 10.0]:
            tc_temez(length=length, slope=0.02)

            captured = capsys.readouterr()
            assert "Tc =" in captured.out
            assert "km" in captured.out

    def test_different_slopes(self, capsys):
        """Test diferentes pendientes."""
        for slope in [0.005, 0.01, 0.02, 0.05]:
            tc_temez(length=3.0, slope=slope)

            captured = capsys.readouterr()
            assert "Tc =" in captured.out


class TestTcDesbordes:
    """Tests para comando tc desbordes."""

    def test_basic_calculation(self, capsys):
        """Test cálculo básico Desbordes."""
        tc_desbordes(area=10.0, slope_pct=2.0, c=0.5, t0=5.0)

        captured = capsys.readouterr()
        assert "DESBORDES" in captured.out or "Desbordes" in captured.out
        assert "DINAGUA" in captured.out
        assert "10" in captured.out
        assert "Tc =" in captured.out
        assert "horas" in captured.out
        assert "minutos" in captured.out

    def test_shows_all_parameters(self, capsys):
        """Test muestra todos los parámetros."""
        tc_desbordes(area=25.5, slope_pct=3.5, c=0.6, t0=7.0)

        captured = capsys.readouterr()
        assert "25.5" in captured.out or "25.50" in captured.out  # Area
        assert "3.5" in captured.out or "3.50" in captured.out    # Slope
        assert "0.6" in captured.out or "0.60" in captured.out    # C
        assert "7.0" in captured.out or "7" in captured.out       # T0
        assert "ha" in captured.out  # Unidad de área

    def test_default_t0(self, capsys):
        """Test T0 por defecto."""
        tc_desbordes(area=10.0, slope_pct=2.0, c=0.5, t0=5.0)

        captured = capsys.readouterr()
        assert "5" in captured.out  # T0 default = 5

    def test_custom_t0(self, capsys):
        """Test T0 personalizado."""
        tc_desbordes(area=10.0, slope_pct=2.0, c=0.5, t0=10.0)

        captured = capsys.readouterr()
        assert "10" in captured.out

    def test_different_areas(self, capsys):
        """Test diferentes áreas."""
        for area in [5.0, 10.0, 50.0, 100.0]:
            tc_desbordes(area=area, slope_pct=2.0, c=0.5, t0=5.0)

            captured = capsys.readouterr()
            assert "Tc =" in captured.out

    def test_different_slopes(self, capsys):
        """Test diferentes pendientes."""
        for slope in [1.0, 2.0, 5.0, 10.0]:
            tc_desbordes(area=20.0, slope_pct=slope, c=0.5, t0=5.0)

            captured = capsys.readouterr()
            assert "Tc =" in captured.out

    def test_different_c_values(self, capsys):
        """Test diferentes coeficientes C."""
        for c in [0.3, 0.5, 0.7, 0.9]:
            tc_desbordes(area=20.0, slope_pct=2.0, c=c, t0=5.0)

            captured = capsys.readouterr()
            assert "Tc =" in captured.out


class TestTcAppCLI:
    """Tests de integración usando CliRunner."""

    def test_kirpich_via_cli(self):
        """Test comando kirpich via CLI."""
        result = runner.invoke(tc_app, ["kirpich", "1000", "0.02"])
        assert result.exit_code == 0
        assert "Tc =" in result.output

    def test_kirpich_with_surface_option(self):
        """Test kirpich con opción surface."""
        result = runner.invoke(tc_app, ["kirpich", "1500", "0.015", "--surface", "grassy"])
        assert result.exit_code == 0
        assert "grassy" in result.output

    def test_kirpich_all_surfaces(self):
        """Test kirpich con todas las superficies."""
        for surface in ["natural", "grassy", "concrete"]:
            result = runner.invoke(tc_app, ["kirpich", "1000", "0.02", "--surface", surface])
            assert result.exit_code == 0
            assert surface in result.output

    def test_temez_via_cli(self):
        """Test comando temez via CLI."""
        result = runner.invoke(tc_app, ["temez", "2.5", "0.0223"])
        assert result.exit_code == 0
        assert "Tc =" in result.output
        assert "km" in result.output

    def test_desbordes_via_cli(self):
        """Test comando desbordes via CLI."""
        result = runner.invoke(tc_app, ["desbordes", "10", "2.0", "0.5"])
        assert result.exit_code == 0
        assert "DESBORDES" in result.output or "Desbordes" in result.output
        assert "Tc =" in result.output

    def test_desbordes_with_t0(self):
        """Test desbordes con opción t0."""
        result = runner.invoke(tc_app, ["desbordes", "10", "2.0", "0.5", "--t0", "8"])
        assert result.exit_code == 0
        assert "8" in result.output

    def test_help(self):
        """Test help del app."""
        result = runner.invoke(tc_app, ["--help"])
        assert result.exit_code == 0
        assert "kirpich" in result.output
        assert "temez" in result.output
        assert "desbordes" in result.output

    def test_kirpich_help(self):
        """Test help de kirpich."""
        result = runner.invoke(tc_app, ["kirpich", "--help"])
        assert result.exit_code == 0
        assert "Longitud" in result.output or "length" in result.output.lower()
        assert "Pendiente" in result.output or "slope" in result.output.lower()

    def test_temez_help(self):
        """Test help de temez."""
        result = runner.invoke(tc_app, ["temez", "--help"])
        assert result.exit_code == 0
        assert "Longitud" in result.output or "length" in result.output.lower()

    def test_desbordes_help(self):
        """Test help de desbordes."""
        result = runner.invoke(tc_app, ["desbordes", "--help"])
        assert result.exit_code == 0
        assert "Area" in result.output or "area" in result.output.lower()
        assert "t0" in result.output

    def test_invalid_command(self):
        """Test comando inválido."""
        result = runner.invoke(tc_app, ["invalid"])
        assert result.exit_code != 0

    def test_missing_arguments_kirpich(self):
        """Test argumentos faltantes kirpich."""
        result = runner.invoke(tc_app, ["kirpich"])
        assert result.exit_code != 0

    def test_missing_arguments_temez(self):
        """Test argumentos faltantes temez."""
        result = runner.invoke(tc_app, ["temez"])
        assert result.exit_code != 0

    def test_missing_arguments_desbordes(self):
        """Test argumentos faltantes desbordes."""
        result = runner.invoke(tc_app, ["desbordes", "10"])
        assert result.exit_code != 0


class TestTcIntegration:
    """Tests de integración para cli/tc.py."""

    def test_kirpich_tc_increases_with_length(self):
        """Tc debe aumentar con mayor longitud."""
        result_short = runner.invoke(tc_app, ["kirpich", "500", "0.02"])
        result_long = runner.invoke(tc_app, ["kirpich", "2000", "0.02"])

        # Extraer Tc de la salida
        tc_short = _extract_tc_hours(result_short.output)
        tc_long = _extract_tc_hours(result_long.output)

        assert tc_long > tc_short

    def test_kirpich_tc_decreases_with_slope(self):
        """Tc debe disminuir con mayor pendiente."""
        result_gentle = runner.invoke(tc_app, ["kirpich", "1000", "0.01"])
        result_steep = runner.invoke(tc_app, ["kirpich", "1000", "0.05"])

        tc_gentle = _extract_tc_hours(result_gentle.output)
        tc_steep = _extract_tc_hours(result_steep.output)

        assert tc_gentle > tc_steep

    def test_temez_tc_increases_with_length(self):
        """Tc debe aumentar con mayor longitud."""
        result_short = runner.invoke(tc_app, ["temez", "1.0", "0.02"])
        result_long = runner.invoke(tc_app, ["temez", "5.0", "0.02"])

        tc_short = _extract_tc_hours(result_short.output)
        tc_long = _extract_tc_hours(result_long.output)

        assert tc_long > tc_short

    def test_temez_tc_decreases_with_slope(self):
        """Tc debe disminuir con mayor pendiente."""
        result_gentle = runner.invoke(tc_app, ["temez", "3.0", "0.01"])
        result_steep = runner.invoke(tc_app, ["temez", "3.0", "0.05"])

        tc_gentle = _extract_tc_hours(result_gentle.output)
        tc_steep = _extract_tc_hours(result_steep.output)

        assert tc_gentle > tc_steep

    def test_desbordes_tc_increases_with_area(self):
        """Tc debe aumentar con mayor área."""
        result_small = runner.invoke(tc_app, ["desbordes", "5", "2.0", "0.5"])
        result_large = runner.invoke(tc_app, ["desbordes", "50", "2.0", "0.5"])

        tc_small = _extract_tc_hours(result_small.output)
        tc_large = _extract_tc_hours(result_large.output)

        assert tc_large > tc_small

    def test_desbordes_tc_decreases_with_slope(self):
        """Tc debe disminuir con mayor pendiente."""
        result_gentle = runner.invoke(tc_app, ["desbordes", "20", "1.0", "0.5"])
        result_steep = runner.invoke(tc_app, ["desbordes", "20", "5.0", "0.5"])

        tc_gentle = _extract_tc_hours(result_gentle.output)
        tc_steep = _extract_tc_hours(result_steep.output)

        assert tc_gentle > tc_steep


def _extract_tc_hours(output: str) -> float:
    """Extrae Tc en horas de la salida del CLI."""
    import re
    # Busca "Tc = X.XX horas"
    match = re.search(r"Tc\s*=\s*(\d+\.?\d*)\s*horas", output)
    if match:
        return float(match.group(1))
    raise ValueError(f"No se pudo extraer Tc de: {output}")
