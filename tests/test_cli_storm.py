"""
Tests para cli/storm.py - Comandos de tormentas de diseno.
"""

import json
import os
import tempfile

import pytest
import typer
from typer.testing import CliRunner

from hidropluvial.cli.storm import (
    storm_app,
    storm_uruguay,
    storm_bimodal,
    storm_bimodal_uy,
    storm_gz,
    storm_scs,
    storm_chicago,
)


runner = CliRunner()


class TestStormUruguay:
    """Tests para comando storm uruguay."""

    def test_basic_blocks(self, capsys):
        """Test basico con bloques alternantes."""
        storm_uruguay(
            p3_10=83.0,
            duration=2.0,
            return_period=10,
            dt=5.0,
            area=None,
            method="blocks",
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIETOGRAMA DINAGUA URUGUAY" in captured.out
        assert "83.0 mm" in captured.out
        assert "10 a" in captured.out  # "10 anos" o "10 años"
        assert "Precipitaci" in captured.out

    def test_with_area(self, capsys):
        """Test con area de cuenca para reduccion areal."""
        storm_uruguay(
            p3_10=83.0,
            duration=2.0,
            return_period=25,
            dt=5.0,
            area=50.0,
            method="blocks",
            output=None,
        )

        captured = capsys.readouterr()
        assert "50.0 km" in captured.out

    def test_scs_method(self, capsys):
        """Test con metodo SCS."""
        storm_uruguay(
            p3_10=83.0,
            duration=2.0,
            return_period=10,
            dt=5.0,
            area=None,
            method="scs_type_ii",
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIETOGRAMA DINAGUA URUGUAY" in captured.out

    def test_export_json(self, capsys):
        """Test exportar a JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            storm_uruguay(
                p3_10=83.0,
                duration=2.0,
                return_period=10,
                dt=5.0,
                area=None,
                method="blocks",
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "guardado" in captured.out

            with open(output_file, 'r') as f:
                data = json.load(f)
                assert "total_depth_mm" in data
                assert "time_min" in data
                assert "depth_mm" in data

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_different_return_periods(self, capsys):
        """Test diferentes periodos de retorno."""
        for tr in [2, 5, 10, 25, 50, 100]:
            storm_uruguay(
                p3_10=83.0,
                duration=2.0,
                return_period=tr,
                dt=5.0,
                area=None,
                method="blocks",
                output=None,
            )

            captured = capsys.readouterr()
            assert str(tr) in captured.out


class TestStormBimodal:
    """Tests para comando storm bimodal."""

    def test_basic(self, capsys):
        """Test basico bimodal."""
        storm_bimodal(
            depth=50.0,
            duration=6.0,
            dt=5.0,
            peak1=0.25,
            peak2=0.75,
            split=0.5,
            output=None,
        )

        captured = capsys.readouterr()
        assert "Hietograma Bimodal" in captured.out
        assert "25%" in captured.out
        assert "75%" in captured.out

    def test_custom_peaks(self, capsys):
        """Test con picos personalizados."""
        storm_bimodal(
            depth=50.0,
            duration=6.0,
            dt=5.0,
            peak1=0.3,
            peak2=0.7,
            split=0.6,
            output=None,
        )

        captured = capsys.readouterr()
        assert "30%" in captured.out
        assert "70%" in captured.out
        assert "60%" in captured.out

    def test_export_json(self, capsys):
        """Test exportar bimodal a JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            storm_bimodal(
                depth=50.0,
                duration=6.0,
                dt=5.0,
                peak1=0.25,
                peak2=0.75,
                split=0.5,
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "guardado" in captured.out

            with open(output_file, 'r') as f:
                data = json.load(f)
                assert "total_depth_mm" in data

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestStormBimodalUY:
    """Tests para comando storm bimodal-uy."""

    def test_basic(self, capsys):
        """Test basico bimodal Uruguay."""
        storm_bimodal_uy(
            p3_10=83.0,
            return_period=2,
            duration=6.0,
            dt=5.0,
            peak1=0.25,
            peak2=0.75,
            split=0.5,
            area=None,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIETOGRAMA BIMODAL DINAGUA" in captured.out
        assert "83.0 mm" in captured.out

    def test_with_area(self, capsys):
        """Test bimodal Uruguay con area."""
        storm_bimodal_uy(
            p3_10=83.0,
            return_period=10,
            duration=6.0,
            dt=5.0,
            peak1=0.25,
            peak2=0.75,
            split=0.5,
            area=25.0,
            output=None,
        )

        captured = capsys.readouterr()
        assert "25.0 km2" in captured.out

    def test_export_json(self, capsys):
        """Test exportar bimodal Uruguay a JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            storm_bimodal_uy(
                p3_10=83.0,
                return_period=2,
                duration=6.0,
                dt=5.0,
                peak1=0.25,
                peak2=0.75,
                split=0.5,
                area=None,
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "guardado" in captured.out

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestStormGZ:
    """Tests para comando storm gz."""

    def test_basic(self, capsys):
        """Test basico GZ."""
        storm_gz(
            p3_10=83.0,
            return_period=2,
            duration=6.0,
            dt=5.0,
            area=None,
            output=None,
        )

        captured = capsys.readouterr()
        assert "HIETOGRAMA GZ" in captured.out
        assert "1ra hora" in captured.out

    def test_with_area(self, capsys):
        """Test GZ con area."""
        storm_gz(
            p3_10=83.0,
            return_period=10,
            duration=6.0,
            dt=5.0,
            area=50.0,
            output=None,
        )

        captured = capsys.readouterr()
        assert "50.0 km2" in captured.out

    def test_different_return_periods(self, capsys):
        """Test GZ diferentes periodos."""
        for tr in [2, 10, 25, 100]:
            storm_gz(
                p3_10=83.0,
                return_period=tr,
                duration=6.0,
                dt=5.0,
                area=None,
                output=None,
            )

            captured = capsys.readouterr()
            assert str(tr) in captured.out

    def test_export_json(self, capsys):
        """Test exportar GZ a JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            storm_gz(
                p3_10=83.0,
                return_period=2,
                duration=6.0,
                dt=5.0,
                area=None,
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "guardado" in captured.out

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestStormSCS:
    """Tests para comando storm scs."""

    def test_type_ii(self, capsys):
        """Test SCS Type II."""
        storm_scs(
            depth=100.0,
            duration=24.0,
            dt=15.0,
            storm_type="II",
            output=None,
        )

        captured = capsys.readouterr()
        assert "SCS Tipo II" in captured.out
        assert "100.00 mm" in captured.out

    def test_type_i(self, capsys):
        """Test SCS Type I."""
        storm_scs(
            depth=100.0,
            duration=24.0,
            dt=15.0,
            storm_type="I",
            output=None,
        )

        captured = capsys.readouterr()
        assert "SCS Tipo I" in captured.out

    def test_type_ia(self, capsys):
        """Test SCS Type IA."""
        storm_scs(
            depth=100.0,
            duration=24.0,
            dt=15.0,
            storm_type="IA",
            output=None,
        )

        captured = capsys.readouterr()
        assert "SCS Tipo IA" in captured.out

    def test_type_iii(self, capsys):
        """Test SCS Type III."""
        storm_scs(
            depth=100.0,
            duration=24.0,
            dt=15.0,
            storm_type="III",
            output=None,
        )

        captured = capsys.readouterr()
        assert "SCS Tipo III" in captured.out

    def test_lowercase_type(self, capsys):
        """Test tipo en minusculas."""
        storm_scs(
            depth=100.0,
            duration=24.0,
            dt=15.0,
            storm_type="ii",
            output=None,
        )

        captured = capsys.readouterr()
        assert "SCS Tipo II" in captured.out

    def test_invalid_type(self, capsys):
        """Test tipo invalido."""
        with pytest.raises(typer.Exit):
            storm_scs(
                depth=100.0,
                duration=24.0,
                dt=15.0,
                storm_type="X",
                output=None,
            )

        captured = capsys.readouterr()
        assert "Tipo" in captured.err

    def test_export_json(self, capsys):
        """Test exportar SCS a JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            storm_scs(
                depth=100.0,
                duration=24.0,
                dt=15.0,
                storm_type="II",
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "guardado" in captured.out

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestStormChicago:
    """Tests para comando storm chicago."""

    def test_basic(self, capsys):
        """Test Chicago basico."""
        storm_chicago(
            depth=50.0,
            duration=2.0,
            dt=5.0,
            return_period=100,
            r=0.375,
            k=2150.0,
            c=15.0,
            n=0.75,
            m_coef=0.22,
            output=None,
        )

        captured = capsys.readouterr()
        assert "Chicago" in captured.out
        assert "r=0.375" in captured.out

    def test_custom_r(self, capsys):
        """Test Chicago con r personalizado."""
        storm_chicago(
            depth=50.0,
            duration=2.0,
            dt=5.0,
            return_period=100,
            r=0.5,  # Pico centrado
            k=2150.0,
            c=15.0,
            n=0.75,
            m_coef=0.22,
            output=None,
        )

        captured = capsys.readouterr()
        assert "r=0.5" in captured.out

    def test_export_json(self, capsys):
        """Test exportar Chicago a JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_file = f.name

        try:
            storm_chicago(
                depth=50.0,
                duration=2.0,
                dt=5.0,
                return_period=100,
                r=0.375,
                k=2150.0,
                c=15.0,
                n=0.75,
                m_coef=0.22,
                output=output_file,
            )

            captured = capsys.readouterr()
            assert "guardado" in captured.out

        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestStormAppCLI:
    """Tests de integracion usando CliRunner."""

    def test_uruguay_via_cli(self):
        """Test comando uruguay via CLI."""
        result = runner.invoke(storm_app, ["uruguay", "83", "2"])
        assert result.exit_code == 0
        assert "DINAGUA" in result.output

    def test_uruguay_with_options(self):
        """Test uruguay con opciones."""
        result = runner.invoke(
            storm_app,
            ["uruguay", "83", "2", "--tr", "50", "--area", "25", "--dt", "10"]
        )
        assert result.exit_code == 0
        assert "50" in result.output

    def test_bimodal_via_cli(self):
        """Test comando bimodal via CLI."""
        result = runner.invoke(storm_app, ["bimodal", "50"])
        assert result.exit_code == 0
        assert "Bimodal" in result.output

    def test_bimodal_uy_via_cli(self):
        """Test comando bimodal-uy via CLI."""
        result = runner.invoke(storm_app, ["bimodal-uy", "83"])
        assert result.exit_code == 0
        assert "BIMODAL DINAGUA" in result.output

    def test_gz_via_cli(self):
        """Test comando gz via CLI."""
        result = runner.invoke(storm_app, ["gz", "83"])
        assert result.exit_code == 0
        assert "GZ" in result.output
        assert "1ra hora" in result.output

    def test_gz_with_options(self):
        """Test gz con opciones."""
        result = runner.invoke(
            storm_app,
            ["gz", "83", "--tr", "100", "--area", "50"]
        )
        assert result.exit_code == 0
        assert "100" in result.output

    def test_scs_via_cli(self):
        """Test comando scs via CLI."""
        result = runner.invoke(storm_app, ["scs", "100"])
        assert result.exit_code == 0
        assert "SCS Tipo II" in result.output

    def test_scs_type_options(self):
        """Test scs con diferentes tipos."""
        for storm_type in ["I", "IA", "II", "III"]:
            result = runner.invoke(
                storm_app,
                ["scs", "100", "--storm-type", storm_type]
            )
            assert result.exit_code == 0
            assert storm_type in result.output

    def test_scs_invalid_type_via_cli(self):
        """Test scs tipo invalido via CLI."""
        result = runner.invoke(
            storm_app,
            ["scs", "100", "--storm-type", "X"]
        )
        assert result.exit_code == 1

    def test_chicago_via_cli(self):
        """Test comando chicago via CLI."""
        result = runner.invoke(storm_app, ["chicago", "50"])
        assert result.exit_code == 0
        assert "Chicago" in result.output

    def test_chicago_custom_r(self):
        """Test chicago con r personalizado."""
        result = runner.invoke(
            storm_app,
            ["chicago", "50", "--r", "0.5"]
        )
        assert result.exit_code == 0
        assert "r=0.5" in result.output

    def test_help(self):
        """Test help del app."""
        result = runner.invoke(storm_app, ["--help"])
        assert result.exit_code == 0
        assert "uruguay" in result.output
        assert "bimodal" in result.output
        assert "scs" in result.output
        assert "chicago" in result.output
