"""
Tests para cli/runoff.py - Comandos de escorrentía.
"""

import pytest
from unittest.mock import patch, MagicMock

import typer
from typer.testing import CliRunner

from hidropluvial.cli.runoff import (
    runoff_app,
    runoff_cn,
    runoff_rational,
    show_tables,
    _validate_positive,
    _validate_area,
    _validate_c_range,
)


runner = CliRunner()


class TestRunoffCN:
    """Tests para comando runoff cn."""

    def test_basic_calculation(self, capsys):
        """Test cálculo básico SCS-CN."""
        runoff_cn(rainfall=100.0, cn=75, lambda_coef=0.2, amc="II")

        captured = capsys.readouterr()
        assert "Método SCS Curve Number" in captured.out
        assert "Precipitación:" in captured.out
        assert "100.00 mm" in captured.out
        assert "Escorrentía Q:" in captured.out

    def test_with_dry_amc(self, capsys):
        """Test con AMC I (seco)."""
        runoff_cn(rainfall=100.0, cn=75, lambda_coef=0.2, amc="I")

        captured = capsys.readouterr()
        assert "AMC I" in captured.out

    def test_with_wet_amc(self, capsys):
        """Test con AMC III (húmedo)."""
        runoff_cn(rainfall=100.0, cn=75, lambda_coef=0.2, amc="III")

        captured = capsys.readouterr()
        assert "AMC III" in captured.out

    def test_lowercase_amc(self, capsys):
        """Test AMC en minúsculas."""
        runoff_cn(rainfall=100.0, cn=75, lambda_coef=0.2, amc="ii")

        captured = capsys.readouterr()
        assert "Escorrentía Q:" in captured.out

    def test_invalid_amc(self, capsys):
        """Test AMC inválido."""
        with pytest.raises(typer.Exit):
            runoff_cn(rainfall=100.0, cn=75, lambda_coef=0.2, amc="X")

        captured = capsys.readouterr()
        assert "AMC debe ser I, II o III" in captured.err

    def test_custom_lambda(self, capsys):
        """Test con lambda personalizado."""
        runoff_cn(rainfall=100.0, cn=75, lambda_coef=0.05, amc="II")

        captured = capsys.readouterr()
        assert "Escorrentía Q:" in captured.out

    def test_high_cn_more_runoff(self, capsys):
        """Test que CN alto produce más escorrentía."""
        runoff_cn(rainfall=100.0, cn=90, lambda_coef=0.2, amc="II")
        captured1 = capsys.readouterr()

        runoff_cn(rainfall=100.0, cn=60, lambda_coef=0.2, amc="II")
        captured2 = capsys.readouterr()

        # Extraer valores de escorrentía (aproximado)
        assert "Escorrentía Q:" in captured1.out
        assert "Escorrentía Q:" in captured2.out


class TestRunoffRational:
    """Tests para comando runoff rational."""

    def test_basic_calculation(self, capsys):
        """Test cálculo básico método racional."""
        runoff_rational(c=0.5, intensity=50.0, area=10.0, return_period=10)

        captured = capsys.readouterr()
        assert "Método Racional" in captured.out
        assert "C = 0.50" in captured.out
        assert "i = 50.00 mm/hr" in captured.out
        assert "A = 10.00 ha" in captured.out
        assert "Q =" in captured.out

    def test_different_return_period(self, capsys):
        """Test con período de retorno diferente."""
        runoff_rational(c=0.5, intensity=50.0, area=10.0, return_period=25)

        captured = capsys.readouterr()
        assert "T = 25 años" in captured.out

    def test_high_c_more_flow(self, capsys):
        """Test que C alto produce más caudal."""
        runoff_rational(c=0.9, intensity=50.0, area=10.0, return_period=10)
        captured1 = capsys.readouterr()

        runoff_rational(c=0.3, intensity=50.0, area=10.0, return_period=10)
        captured2 = capsys.readouterr()

        # Ambos deben mostrar resultado
        assert "Q =" in captured1.out
        assert "Q =" in captured2.out


class TestShowTables:
    """Tests para comando show-tables."""

    def test_show_c_tables(self, capsys):
        """Test mostrar tablas de C."""
        show_tables("c")

        captured = capsys.readouterr()
        assert "Tablas de Coeficiente C" in captured.out
        assert "chow" in captured.out
        assert "fhwa" in captured.out

    def test_show_cn_tables(self, capsys):
        """Test mostrar tablas de CN."""
        show_tables("cn")

        captured = capsys.readouterr()
        assert "Tablas de Curva Numero CN" in captured.out
        assert "urban" in captured.out
        assert "agricultural" in captured.out

    def test_show_tables_invalid_type(self, capsys):
        """Test tipo de tabla inválido."""
        show_tables("invalid")

        captured = capsys.readouterr()
        assert "Tipo debe ser 'c' o 'cn'" in captured.out

    def test_show_c_tables_uppercase(self, capsys):
        """Test con mayúsculas."""
        show_tables("C")

        captured = capsys.readouterr()
        assert "Tablas de Coeficiente C" in captured.out


class TestValidatePositive:
    """Tests para _validate_positive."""

    def test_valid_positive(self):
        """Test número positivo válido."""
        assert _validate_positive("10.5") is True

    def test_valid_integer(self):
        """Test entero positivo."""
        assert _validate_positive("100") is True

    def test_zero_invalid(self):
        """Test cero es inválido."""
        result = _validate_positive("0")
        assert "positivo" in result

    def test_negative_invalid(self):
        """Test negativo es inválido."""
        result = _validate_positive("-5")
        assert "positivo" in result

    def test_non_number_invalid(self):
        """Test texto no numérico."""
        result = _validate_positive("abc")
        assert "numero valido" in result

    def test_empty_invalid(self):
        """Test cadena vacía."""
        result = _validate_positive("")
        assert "numero valido" in result


class TestValidateArea:
    """Tests para _validate_area."""

    def test_valid_area(self):
        """Test área válida."""
        assert _validate_area("5.0", 10.0) is True

    def test_area_at_max(self):
        """Test área igual al máximo."""
        assert _validate_area("10.0", 10.0) is True

    def test_empty_is_valid(self):
        """Test cadena vacía es válida (permite terminar)."""
        assert _validate_area("", 10.0) is True
        assert _validate_area("   ", 10.0) is True

    def test_negative_invalid(self):
        """Test área negativa."""
        result = _validate_area("-5", 10.0)
        assert "negativa" in result

    def test_exceeds_max_invalid(self):
        """Test área excede máximo."""
        result = _validate_area("15", 10.0)
        assert "exceder" in result

    def test_non_number_invalid(self):
        """Test texto no numérico."""
        result = _validate_area("abc", 10.0)
        assert "numero valido" in result


class TestValidateCRange:
    """Tests para _validate_c_range."""

    def test_valid_in_range(self):
        """Test C dentro del rango."""
        assert _validate_c_range("0.5", 0.3, 0.7) is True

    def test_at_min(self):
        """Test C igual al mínimo."""
        assert _validate_c_range("0.3", 0.3, 0.7) is True

    def test_at_max(self):
        """Test C igual al máximo."""
        assert _validate_c_range("0.7", 0.3, 0.7) is True

    def test_below_min_invalid(self):
        """Test C bajo mínimo."""
        result = _validate_c_range("0.2", 0.3, 0.7)
        assert "entre" in result

    def test_above_max_invalid(self):
        """Test C sobre máximo."""
        result = _validate_c_range("0.8", 0.3, 0.7)
        assert "entre" in result

    def test_non_number_invalid(self):
        """Test texto no numérico."""
        result = _validate_c_range("abc", 0.3, 0.7)
        assert "numero valido" in result


class TestRunoffAppCLI:
    """Tests de integración usando CliRunner."""

    def test_cn_command_via_cli(self):
        """Test comando cn via CLI."""
        result = runner.invoke(runoff_app, ["cn", "100", "75"])
        assert result.exit_code == 0
        assert "Escorrentía Q:" in result.output

    def test_cn_command_with_options(self):
        """Test comando cn con opciones."""
        result = runner.invoke(runoff_app, ["cn", "100", "75", "--lambda", "0.1", "--amc", "III"])
        assert result.exit_code == 0
        assert "AMC III" in result.output

    def test_cn_invalid_amc_via_cli(self):
        """Test AMC inválido via CLI."""
        result = runner.invoke(runoff_app, ["cn", "100", "75", "--amc", "X"])
        assert result.exit_code == 1
        assert "AMC debe ser I, II o III" in result.output

    def test_rational_command_via_cli(self):
        """Test comando rational via CLI."""
        result = runner.invoke(runoff_app, ["rational", "0.5", "50", "10"])
        assert result.exit_code == 0
        assert "Método Racional" in result.output
        assert "Q =" in result.output

    def test_rational_with_return_period(self):
        """Test rational con período de retorno."""
        result = runner.invoke(runoff_app, ["rational", "0.5", "50", "10", "--return-period", "25"])
        assert result.exit_code == 0
        assert "T = 25" in result.output

    def test_show_tables_c_via_cli(self):
        """Test show-tables c via CLI."""
        result = runner.invoke(runoff_app, ["show-tables", "c"])
        assert result.exit_code == 0
        assert "chow" in result.output

    def test_show_tables_cn_via_cli(self):
        """Test show-tables cn via CLI."""
        result = runner.invoke(runoff_app, ["show-tables", "cn"])
        assert result.exit_code == 0
        assert "urban" in result.output


class TestWeightedCNonInteractive:
    """Tests para weighted-c sin interacción (errores de validación)."""

    def test_invalid_table(self, capsys):
        """Test tabla inválida."""
        from hidropluvial.cli.runoff import runoff_weighted_c

        with pytest.raises(typer.Exit):
            runoff_weighted_c(area_total=10.0, table="invalid_table")

        captured = capsys.readouterr()
        assert "no disponible" in captured.out


class TestWeightedCNNonInteractive:
    """Tests para weighted-cn sin interacción (errores de validación)."""

    def test_invalid_soil_group(self, capsys):
        """Test grupo hidrológico inválido."""
        from hidropluvial.cli.runoff import runoff_weighted_cn

        with pytest.raises(typer.Exit):
            runoff_weighted_cn(area_total=10.0, soil_group="X")

        captured = capsys.readouterr()
        assert "debe ser A, B, C o D" in captured.out
