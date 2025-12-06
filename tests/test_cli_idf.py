"""
Tests para cli/idf.py - Comandos de curvas IDF.
"""

import json
import os
import tempfile

import pytest
from typer.testing import CliRunner

from hidropluvial.cli.idf import (
    idf_app,
    idf_uruguay,
    idf_tabla_uruguay,
    idf_departamentos,
    idf_intensity,
    idf_table,
)


runner = CliRunner()


class TestIDFUruguay:
    """Tests para comando idf uruguay."""

    def test_basic(self, capsys):
        """Test basico DINAGUA."""
        idf_uruguay(
            p3_10=83.0,
            duration=2.0,
            return_period=10,
            area=None,
        )

        captured = capsys.readouterr()
        assert "METODO DINAGUA URUGUAY" in captured.out
        assert "83.0 mm" in captured.out
        assert "INTENSIDAD:" in captured.out
        assert "PRECIPITACION:" in captured.out

    def test_with_area(self, capsys):
        """Test con area de cuenca."""
        idf_uruguay(
            p3_10=83.0,
            duration=2.0,
            return_period=25,
            area=50.0,
        )

        captured = capsys.readouterr()
        assert "50.0 km²" in captured.out

    def test_shows_factors(self, capsys):
        """Test muestra factores CT y CA."""
        idf_uruguay(
            p3_10=83.0,
            duration=2.0,
            return_period=10,
            area=None,
        )

        captured = capsys.readouterr()
        assert "Factor CT:" in captured.out
        assert "Factor CA:" in captured.out

    def test_different_return_periods(self, capsys):
        """Test diferentes periodos de retorno."""
        for tr in [2, 5, 10, 25, 50, 100]:
            idf_uruguay(
                p3_10=83.0,
                duration=2.0,
                return_period=tr,
                area=None,
            )

            captured = capsys.readouterr()
            assert str(tr) in captured.out

    def test_different_durations(self, capsys):
        """Test diferentes duraciones."""
        for dur in [0.5, 1.0, 2.0, 6.0, 12.0]:
            idf_uruguay(
                p3_10=83.0,
                duration=dur,
                return_period=10,
                area=None,
            )

            captured = capsys.readouterr()
            assert "INTENSIDAD:" in captured.out


class TestIDFTablaUruguay:
    """Tests para comando idf tabla-uy."""

    def test_basic(self, capsys):
        """Test tabla basica."""
        idf_tabla_uruguay(
            p3_10=83.0,
            area=None,
            output=None,
        )

        captured = capsys.readouterr()
        assert "Tabla IDF DINAGUA Uruguay" in captured.out
        assert "Dur (hr)" in captured.out
        assert "T=" in captured.out

    def test_with_area(self, capsys):
        """Test tabla con area."""
        idf_tabla_uruguay(
            p3_10=83.0,
            area=25.0,
            output=None,
        )

        captured = capsys.readouterr()
        assert "25" in captured.out

    def test_export_json(self, capsys):
        """Test exportar tabla a JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            idf_tabla_uruguay(
                p3_10=83.0,
                area=None,
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "guardada" in captured.out

            with open(output_file, 'r') as f:
                data = json.load(f)
                assert "p3_10_mm" in data
                assert "intensities_mmhr" in data
                assert "depths_mm" in data

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestIDFDepartamentos:
    """Tests para comando idf departamentos."""

    def test_lists_departments(self, capsys):
        """Test lista departamentos."""
        idf_departamentos()

        captured = capsys.readouterr()
        # Case-insensitive check (output may use "Departamento")
        assert "p3,10 por departamento" in captured.out.lower()
        assert "mm" in captured.out
        # Verificar algunos departamentos conocidos
        assert "Montevideo" in captured.out or "montevideo" in captured.out.lower()

    def test_shows_note(self, capsys):
        """Test muestra nota sobre cambio climatico."""
        idf_departamentos()

        captured = capsys.readouterr()
        assert "cambio clim" in captured.out.lower()


class TestIDFSherman:
    """Tests para comando idf sherman."""

    def test_basic(self, capsys):
        """Test Sherman basico."""
        idf_intensity(
            duration=60.0,
            return_period=10,
            k=2150.0,
            m=0.22,
            c=15.0,
            n=0.75,
        )

        captured = capsys.readouterr()
        assert "60" in captured.out
        assert "10" in captured.out
        assert "Intensidad:" in captured.out
        assert "mm/hr" in captured.out

    def test_different_durations(self, capsys):
        """Test diferentes duraciones."""
        for dur in [15, 30, 60, 120]:
            idf_intensity(
                duration=float(dur),
                return_period=10,
                k=2150.0,
                m=0.22,
                c=15.0,
                n=0.75,
            )

            captured = capsys.readouterr()
            assert "Intensidad:" in captured.out

    def test_custom_coefficients(self, capsys):
        """Test coeficientes personalizados."""
        idf_intensity(
            duration=60.0,
            return_period=10,
            k=3000.0,
            m=0.3,
            c=10.0,
            n=0.8,
        )

        captured = capsys.readouterr()
        assert "Intensidad:" in captured.out


class TestIDFTable:
    """Tests para comando idf table (Sherman)."""

    def test_basic(self, capsys):
        """Test tabla Sherman basica."""
        idf_table(
            k=2150.0,
            m=0.22,
            c=15.0,
            n=0.75,
            output=None,
        )

        captured = capsys.readouterr()
        assert "Intensidades" in captured.out
        assert "T=" in captured.out

    def test_export_json(self, capsys):
        """Test exportar tabla Sherman a JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            idf_table(
                k=2150.0,
                m=0.22,
                c=15.0,
                n=0.75,
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "guardada" in captured.out

            with open(output_file, 'r') as f:
                data = json.load(f)
                assert "durations_min" in data
                assert "intensities_mmhr" in data

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestIDFAppCLI:
    """Tests de integracion usando CliRunner."""

    def test_uruguay_via_cli(self):
        """Test comando uruguay via CLI."""
        result = runner.invoke(idf_app, ["uruguay", "83", "2"])
        assert result.exit_code == 0
        assert "DINAGUA" in result.output

    def test_uruguay_with_options(self):
        """Test uruguay con opciones."""
        result = runner.invoke(
            idf_app,
            ["uruguay", "83", "2", "--tr", "100", "--area", "25"]
        )
        assert result.exit_code == 0
        assert "100" in result.output

    def test_tabla_uy_via_cli(self):
        """Test comando tabla-uy via CLI."""
        result = runner.invoke(idf_app, ["tabla-uy", "83"])
        assert result.exit_code == 0
        assert "Tabla IDF" in result.output

    def test_tabla_uy_with_area(self):
        """Test tabla-uy con area."""
        result = runner.invoke(idf_app, ["tabla-uy", "83", "--area", "50"])
        assert result.exit_code == 0
        assert "50" in result.output

    def test_departamentos_via_cli(self):
        """Test comando departamentos via CLI."""
        result = runner.invoke(idf_app, ["departamentos"])
        assert result.exit_code == 0
        assert "departamento" in result.output.lower()

    def test_sherman_via_cli(self):
        """Test comando sherman via CLI."""
        result = runner.invoke(idf_app, ["sherman", "60", "10"])
        assert result.exit_code == 0
        assert "Intensidad" in result.output

    def test_sherman_custom_coeffs(self):
        """Test sherman con coeficientes personalizados."""
        result = runner.invoke(
            idf_app,
            ["sherman", "60", "10", "--k", "3000", "--m", "0.3"]
        )
        assert result.exit_code == 0

    def test_table_via_cli(self):
        """Test comando table via CLI."""
        result = runner.invoke(idf_app, ["table"])
        assert result.exit_code == 0
        assert "Intensidades" in result.output

    def test_help(self):
        """Test help del app."""
        result = runner.invoke(idf_app, ["--help"])
        assert result.exit_code == 0
        assert "uruguay" in result.output
        assert "sherman" in result.output
        assert "departamentos" in result.output
