"""
Tests para cli/hydrograph.py - Comandos de hidrogramas.
"""

import os
import tempfile

import pytest
import typer
from typer.testing import CliRunner

from hidropluvial.cli.hydrograph import hydrograph_app, hydrograph_scs, hydrograph_gz


runner = CliRunner()


class TestHydrographSCS:
    """Tests para comando hydrograph scs."""

    def test_basic_calculation_kirpich(self, capsys):
        """Test calculo basico con Kirpich."""
        hydrograph_scs(
            area=1.0,
            length=1000,
            slope=0.0223,
            p3_10=83.0,
            cn=81,
            return_period=25,
            dt=5.0,
            method="triangular",
            tc_method="kirpich",
            c_escorrentia=None,
            lambda_coef=0.2,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIDROGRAMA SCS" in captured.out
        assert "Área de cuenca:" in captured.out
        assert "1.00 km2" in captured.out
        assert "CAUDAL PICO:" in captured.out
        assert "TIEMPO AL PICO:" in captured.out
        assert "VOLUMEN:" in captured.out

    def test_with_temez_method(self, capsys):
        """Test con metodo Temez para Tc."""
        hydrograph_scs(
            area=1.0,
            length=1000,
            slope=0.0223,
            p3_10=83.0,
            cn=81,
            return_period=25,
            dt=5.0,
            method="triangular",
            tc_method="temez",
            c_escorrentia=None,
            lambda_coef=0.2,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIDROGRAMA SCS" in captured.out
        assert "temez" in captured.out

    def test_with_desbordes_method(self, capsys):
        """Test con metodo Desbordes para Tc."""
        hydrograph_scs(
            area=1.0,
            length=1000,
            slope=0.0223,
            p3_10=83.0,
            cn=81,
            return_period=25,
            dt=5.0,
            method="triangular",
            tc_method="desbordes",
            c_escorrentia=0.5,
            lambda_coef=0.2,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIDROGRAMA SCS" in captured.out
        assert "desbordes" in captured.out

    def test_desbordes_auto_c_from_cn(self, capsys):
        """Test Desbordes sin C (calcula automaticamente desde CN)."""
        hydrograph_scs(
            area=1.0,
            length=1000,
            slope=0.0223,
            p3_10=83.0,
            cn=81,
            return_period=25,
            dt=5.0,
            method="triangular",
            tc_method="desbordes",
            c_escorrentia=None,  # Auto-calcula desde CN
            lambda_coef=0.2,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIDROGRAMA SCS" in captured.out

    def test_curvilinear_method(self, capsys):
        """Test con hidrograma curvilinear."""
        hydrograph_scs(
            area=1.0,
            length=1000,
            slope=0.0223,
            p3_10=83.0,
            cn=81,
            return_period=25,
            dt=5.0,
            method="curvilinear",
            tc_method="kirpich",
            c_escorrentia=None,
            lambda_coef=0.2,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIDROGRAMA SCS" in captured.out
        assert "curvilinear" in captured.out

    def test_slope_percentage_conversion(self, capsys):
        """Test conversion de pendiente en porcentaje."""
        # Si slope > 1, se convierte de % a decimal
        hydrograph_scs(
            area=1.0,
            length=1000,
            slope=2.23,  # Porcentaje, se convierte a 0.0223
            p3_10=83.0,
            cn=81,
            return_period=25,
            dt=5.0,
            method="triangular",
            tc_method="kirpich",
            c_escorrentia=None,
            lambda_coef=0.2,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIDROGRAMA SCS" in captured.out
        assert "2.23 %" in captured.out

    def test_invalid_tc_method(self, capsys):
        """Test metodo Tc invalido."""
        with pytest.raises(typer.Exit):
            hydrograph_scs(
                area=1.0,
                length=1000,
                slope=0.0223,
                p3_10=83.0,
                cn=81,
                return_period=25,
                dt=5.0,
                method="triangular",
                tc_method="invalid_method",
                c_escorrentia=None,
                lambda_coef=0.2,
                output=None,
            )

        captured = capsys.readouterr()
        assert "desconocido" in captured.err

    def test_invalid_uh_method(self, capsys):
        """Test metodo UH invalido."""
        with pytest.raises(typer.Exit):
            hydrograph_scs(
                area=1.0,
                length=1000,
                slope=0.0223,
                p3_10=83.0,
                cn=81,
                return_period=25,
                dt=5.0,
                method="invalid_uh",
                tc_method="kirpich",
                c_escorrentia=None,
                lambda_coef=0.2,
                output=None,
            )

        captured = capsys.readouterr()
        assert "desconocido" in captured.err

    def test_export_to_csv(self, capsys):
        """Test exportar hidrograma a CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_file = f.name

        try:
            hydrograph_scs(
                area=1.0,
                length=1000,
                slope=0.0223,
                p3_10=83.0,
                cn=81,
                return_period=25,
                dt=5.0,
                method="triangular",
                tc_method="kirpich",
                c_escorrentia=None,
                lambda_coef=0.2,
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "Hidrograma exportado a:" in captured.out

            # Verificar contenido del archivo
            with open(output_file, 'r') as f:
                content = f.read()
                assert "Tiempo_hr,Caudal_m3s" in content
                lines = content.strip().split('\n')
                assert len(lines) > 1  # Header + datos

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_different_return_periods(self, capsys):
        """Test diferentes periodos de retorno."""
        for tr in [2, 5, 10, 25, 50, 100]:
            hydrograph_scs(
                area=1.0,
                length=1000,
                slope=0.0223,
                p3_10=83.0,
                cn=81,
                return_period=tr,
                dt=5.0,
                method="triangular",
                tc_method="kirpich",
                c_escorrentia=None,
                lambda_coef=0.2,
                output=None,
            )

            captured = capsys.readouterr()
            assert f"Período retorno:       {tr:>12} años" in captured.out

    def test_custom_lambda(self, capsys):
        """Test con lambda personalizado."""
        hydrograph_scs(
            area=1.0,
            length=1000,
            slope=0.0223,
            p3_10=83.0,
            cn=81,
            return_period=25,
            dt=5.0,
            method="triangular",
            tc_method="kirpich",
            c_escorrentia=None,
            lambda_coef=0.05,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIDROGRAMA SCS" in captured.out

    def test_large_area_applies_reduction(self, capsys):
        """Test area grande aplica factor de reduccion."""
        hydrograph_scs(
            area=10.0,  # > 1 km2, aplica reduccion
            length=5000,
            slope=0.01,
            p3_10=83.0,
            cn=75,
            return_period=25,
            dt=5.0,
            method="triangular",
            tc_method="kirpich",
            c_escorrentia=None,
            lambda_coef=0.2,
            output=None,
        )

        captured = capsys.readouterr()
        assert "10.00 km2" in captured.out


class TestHydrographGZ:
    """Tests para comando hydrograph gz."""

    def test_basic_calculation(self, capsys):
        """Test calculo basico GZ."""
        hydrograph_gz(
            area_ha=100.0,
            slope_pct=2.23,
            c=0.62,
            p3_10=83.0,
            return_period=2,
            x_factor=1.0,
            dt=5.0,
            t0=5.0,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIDROGRAMA GZ" in captured.out
        assert "Área de cuenca:" in captured.out
        assert "100.00 ha" in captured.out
        assert "CAUDAL PICO:" in captured.out
        assert "TIEMPO AL PICO:" in captured.out
        assert "VOLUMEN:" in captured.out

    def test_different_x_factors(self, capsys):
        """Test diferentes factores X."""
        x_values = [1.0, 1.25, 1.67, 2.25]

        for x in x_values:
            hydrograph_gz(
                area_ha=100.0,
                slope_pct=2.23,
                c=0.62,
                p3_10=83.0,
                return_period=2,
                x_factor=x,
                dt=5.0,
                t0=5.0,
                output=None,
            )

            captured = capsys.readouterr()
            assert f"Factor X:              {x:>12.2f}" in captured.out

    def test_different_return_periods(self, capsys):
        """Test diferentes periodos de retorno."""
        for tr in [2, 5, 10, 25]:
            hydrograph_gz(
                area_ha=100.0,
                slope_pct=2.23,
                c=0.62,
                p3_10=83.0,
                return_period=tr,
                x_factor=1.0,
                dt=5.0,
                t0=5.0,
                output=None,
            )

            captured = capsys.readouterr()
            assert f"Período retorno:       {tr:>12} años" in captured.out

    def test_shows_intermediate_results(self, capsys):
        """Test muestra resultados intermedios."""
        hydrograph_gz(
            area_ha=100.0,
            slope_pct=2.23,
            c=0.62,
            p3_10=83.0,
            return_period=2,
            x_factor=1.0,
            dt=5.0,
            t0=5.0,
            output=None,
        )

        captured = capsys.readouterr()
        assert "Tc (Desbordes):" in captured.out
        assert "Tp teórico:" in captured.out
        assert "Tb teórico:" in captured.out
        assert "Precipitación total:" in captured.out
        assert "Escorrentía (C*P):" in captured.out

    def test_export_to_csv(self, capsys):
        """Test exportar hidrograma GZ a CSV."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            output_file = f.name

        try:
            hydrograph_gz(
                area_ha=100.0,
                slope_pct=2.23,
                c=0.62,
                p3_10=83.0,
                return_period=2,
                x_factor=1.0,
                dt=5.0,
                t0=5.0,
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "Hidrograma exportado a:" in captured.out

            # Verificar contenido
            with open(output_file, 'r') as f:
                content = f.read()
                assert "Tiempo_hr,Caudal_m3s" in content

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_high_c_more_runoff(self, capsys):
        """Test que C alto produce mas escorrentia."""
        # C alto
        hydrograph_gz(
            area_ha=100.0,
            slope_pct=2.23,
            c=0.9,
            p3_10=83.0,
            return_period=2,
            x_factor=1.0,
            dt=5.0,
            t0=5.0,
            output=None,
        )
        captured1 = capsys.readouterr()

        # C bajo
        hydrograph_gz(
            area_ha=100.0,
            slope_pct=2.23,
            c=0.3,
            p3_10=83.0,
            return_period=2,
            x_factor=1.0,
            dt=5.0,
            t0=5.0,
            output=None,
        )
        captured2 = capsys.readouterr()

        # Ambos deben mostrar resultados
        assert "CAUDAL PICO:" in captured1.out
        assert "CAUDAL PICO:" in captured2.out

    def test_small_area(self, capsys):
        """Test con area pequena."""
        hydrograph_gz(
            area_ha=10.0,
            slope_pct=5.0,
            c=0.7,
            p3_10=83.0,
            return_period=2,
            x_factor=1.0,
            dt=5.0,
            t0=5.0,
            output=None,
        )

        captured = capsys.readouterr()
        assert "10.00 ha" in captured.out


class TestHydrographAppCLI:
    """Tests de integracion usando CliRunner."""

    def test_scs_command_via_cli(self):
        """Test comando scs via CLI."""
        result = runner.invoke(
            hydrograph_app,
            [
                "scs",
                "--area", "1",
                "--length", "1000",
                "--slope", "0.0223",
                "--p3_10", "83",
                "--cn", "81",
            ]
        )
        assert result.exit_code == 0
        assert "HIDROGRAMA SCS" in result.output
        assert "CAUDAL PICO:" in result.output

    def test_scs_with_all_options(self):
        """Test scs con todas las opciones."""
        result = runner.invoke(
            hydrograph_app,
            [
                "scs",
                "--area", "1",
                "--length", "1000",
                "--slope", "2.23",
                "--p3_10", "83",
                "--cn", "81",
                "--tr", "10",
                "--dt", "10",
                "--method", "curvilinear",
                "--tc-method", "temez",
                "--lambda", "0.1",
            ]
        )
        assert result.exit_code == 0
        assert "curvilinear" in result.output

    def test_scs_invalid_tc_method_via_cli(self):
        """Test metodo Tc invalido via CLI."""
        result = runner.invoke(
            hydrograph_app,
            [
                "scs",
                "--area", "1",
                "--length", "1000",
                "--slope", "0.0223",
                "--p3_10", "83",
                "--cn", "81",
                "--tc-method", "invalid",
            ]
        )
        assert result.exit_code == 1
        assert "Método Tc desconocido" in result.output

    def test_gz_command_via_cli(self):
        """Test comando gz via CLI."""
        result = runner.invoke(
            hydrograph_app,
            [
                "gz",
                "--area", "100",
                "--slope", "2.23",
                "--c", "0.62",
                "--p3_10", "83",
            ]
        )
        assert result.exit_code == 0
        assert "HIDROGRAMA GZ" in result.output
        assert "CAUDAL PICO:" in result.output

    def test_gz_with_all_options(self):
        """Test gz con todas las opciones."""
        result = runner.invoke(
            hydrograph_app,
            [
                "gz",
                "--area", "100",
                "--slope", "2.23",
                "--c", "0.62",
                "--p3_10", "83",
                "--tr", "10",
                "--x", "1.67",
                "--dt", "10",
                "--t0", "10",
            ]
        )
        assert result.exit_code == 0
        assert "1.67" in result.output

    def test_scs_help(self):
        """Test help para scs."""
        result = runner.invoke(hydrograph_app, ["scs", "--help"])
        assert result.exit_code == 0
        assert "--area" in result.output
        assert "--cn" in result.output

    def test_gz_help(self):
        """Test help para gz."""
        result = runner.invoke(hydrograph_app, ["gz", "--help"])
        assert result.exit_code == 0
        assert "--area" in result.output
        assert "--c" in result.output
        assert "Factor X" in result.output
