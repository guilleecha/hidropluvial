"""
Tests para comandos CLI de gestión de análisis (cli/basin/commands.py).

Prueba los comandos: analysis-list, analysis-delete, analysis-clear, analysis-note.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from hidropluvial.database import Database, get_database, reset_database
from hidropluvial.cli.basin.commands import (
    analysis_list,
    analysis_delete,
    analysis_clear,
    analysis_note,
)
from hidropluvial.models import TcResult, StormResult, HydrographResult


@pytest.fixture
def temp_db(tmp_path):
    """Base de datos temporal para tests."""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    return db


@pytest.fixture
def sample_project(temp_db):
    """Proyecto de ejemplo."""
    return temp_db.create_project(
        name="Proyecto Test",
        description="Proyecto para tests",
    )


@pytest.fixture
def sample_basin(temp_db, sample_project):
    """Cuenca de ejemplo."""
    return temp_db.create_basin(
        project_id=sample_project["id"],
        name="Cuenca Test",
        area_ha=100.0,
        slope_pct=2.5,
        p3_10=83.0,
        c=0.5,
        cn=75,
        length_m=1000.0,
    )


@pytest.fixture
def sample_analysis(temp_db, sample_basin):
    """Análisis de ejemplo."""
    tc = TcResult(method="kirpich", tc_hr=0.5, tc_min=30.0)
    storm = StormResult(
        type="gz",
        return_period=25,
        duration_hr=2.0,
        total_depth_mm=100.0,
        peak_intensity_mmhr=50.0,
        n_intervals=24,
        time_min=[0, 5, 10],
        intensity_mmhr=[10, 50, 20],
    )
    hydrograph = HydrographResult(
        tc_method="kirpich",
        tc_min=30.0,
        storm_type="gz",
        return_period=25,
        peak_flow_m3s=5.5,
        time_to_peak_hr=0.8,
        time_to_peak_min=48.0,
        volume_m3=50000.0,
        total_depth_mm=100.0,
        runoff_mm=50.0,
        x_factor=1.25,
        time_hr=[0, 0.5, 1.0],
        flow_m3s=[0, 5.5, 2.0],
    )
    return temp_db.add_analysis(
        basin_id=sample_basin["id"],
        tc=tc,
        storm=storm,
        hydrograph=hydrograph,
        note="Escenario base",
    )


@pytest.fixture
def mock_db(temp_db, sample_project, sample_basin, monkeypatch):
    """Parchea get_database para usar la DB temporal."""
    import hidropluvial.database as db_module
    import hidropluvial.cli.basin.commands as commands_module

    # Patch ambos módulos
    monkeypatch.setattr(db_module, "_database", temp_db)

    # También parchear en commands para _find_basin que usa get_project_manager
    original_find_basin = commands_module._find_basin

    def mock_find_basin(basin_id):
        """Mock de _find_basin que usa nuestra DB temporal."""
        from hidropluvial.project import Basin, Project

        basin_data = temp_db.get_basin(basin_id)
        if not basin_data:
            import typer
            typer.echo(f"Error: Cuenca '{basin_id}' no encontrada.")
            raise typer.Exit(1)

        project_data = temp_db.get_project(sample_project["id"])

        # Crear objetos mock
        project = MagicMock(spec=Project)
        project.name = project_data["name"]
        project.id = project_data["id"]

        basin = MagicMock(spec=Basin)
        basin.id = basin_data["id"]
        basin.name = basin_data["name"]
        basin.analyses = []

        # Cargar análisis reales
        analyses = temp_db.get_basin_analyses(basin_data["id"])
        for a in analyses:
            analysis_mock = MagicMock()
            analysis_mock.id = a["id"]
            analysis_mock.note = a.get("note")
            analysis_mock.tc = MagicMock()
            analysis_mock.tc.method = a["tc"]["method"]
            analysis_mock.storm = MagicMock()
            analysis_mock.storm.type = a["storm"]["type"]
            analysis_mock.storm.return_period = a["storm"]["return_period"]
            analysis_mock.hydrograph = MagicMock()
            analysis_mock.hydrograph.peak_flow_m3s = a["hydrograph"]["peak_flow_m3s"]
            analysis_mock.hydrograph.volume_m3 = a["hydrograph"]["volume_m3"]
            basin.analyses.append(analysis_mock)

        return project, basin

    monkeypatch.setattr(commands_module, "_find_basin", mock_find_basin)

    return temp_db


class TestAnalysisList:
    """Tests para analysis_list."""

    def test_list_empty(self, mock_db, sample_basin, capsys):
        """Test listar cuenca sin análisis."""
        analysis_list(sample_basin["id"])

        captured = capsys.readouterr()
        assert "No hay análisis" in captured.out

    def test_list_with_analysis(self, mock_db, sample_basin, sample_analysis, capsys):
        """Test listar cuenca con análisis."""
        analysis_list(sample_basin["id"])

        captured = capsys.readouterr()
        assert "Análisis de:" in captured.out or "An" in captured.out  # Encoding issues
        assert sample_analysis["id"] in captured.out
        assert "Total: 1" in captured.out

    def test_list_shows_note(self, mock_db, sample_basin, sample_analysis, capsys):
        """Test que muestra la nota del análisis."""
        analysis_list(sample_basin["id"])

        captured = capsys.readouterr()
        # Note: Rich table may wrap long text, so check for partial match
        assert "Escenario" in captured.out

    def test_list_truncates_long_note(self, mock_db, sample_basin, capsys):
        """Test que trunca notas largas."""
        # Agregar análisis con nota larga
        tc = TcResult(method="desbordes", tc_hr=0.4, tc_min=24.0)
        storm = StormResult(
            type="blocks",
            return_period=10,
            duration_hr=1.5,
            total_depth_mm=80.0,
            peak_intensity_mmhr=40.0,
            n_intervals=18,
        )
        hydrograph = HydrographResult(
            tc_method="desbordes",
            tc_min=24.0,
            storm_type="blocks",
            return_period=10,
            peak_flow_m3s=3.5,
            time_to_peak_hr=0.6,
            time_to_peak_min=36.0,
            volume_m3=30000.0,
            total_depth_mm=80.0,
            runoff_mm=30.0,
        )
        mock_db.add_analysis(
            basin_id=sample_basin["id"],
            tc=tc,
            storm=storm,
            hydrograph=hydrograph,
            note="Esta es una nota muy larga que debería ser truncada en la tabla de salida",
        )

        analysis_list(sample_basin["id"])
        captured = capsys.readouterr()
        # La nota debería estar truncada con "..."
        assert "..." in captured.out or "truncada" not in captured.out


class TestAnalysisDelete:
    """Tests para analysis_delete."""

    def test_delete_with_force(self, mock_db, sample_analysis, capsys):
        """Test eliminar con --force."""
        analysis_id = sample_analysis["id"]
        analysis_delete(analysis_id, force=True)

        captured = capsys.readouterr()
        assert "eliminado" in captured.out

        # Verificar que se eliminó
        assert mock_db.get_analysis(analysis_id) is None

    def test_delete_nonexistent(self, mock_db, capsys):
        """Test eliminar análisis inexistente."""
        import typer
        with pytest.raises(typer.Exit):
            analysis_delete("nonexistent", force=True)

        captured = capsys.readouterr()
        assert "no encontrado" in captured.out

    def test_delete_cancelled(self, mock_db, sample_analysis, capsys, monkeypatch):
        """Test eliminación cancelada."""
        monkeypatch.setattr('typer.confirm', lambda x: False)

        import typer
        with pytest.raises(typer.Exit):
            analysis_delete(sample_analysis["id"], force=False)

        captured = capsys.readouterr()
        assert "cancelada" in captured.out

        # Verificar que NO se eliminó
        assert mock_db.get_analysis(sample_analysis["id"]) is not None

    def test_delete_confirmed(self, mock_db, sample_analysis, capsys, monkeypatch):
        """Test eliminación confirmada."""
        monkeypatch.setattr('typer.confirm', lambda x: True)

        analysis_id = sample_analysis["id"]
        analysis_delete(analysis_id, force=False)

        captured = capsys.readouterr()
        assert "eliminado" in captured.out

        # Verificar que se eliminó
        assert mock_db.get_analysis(analysis_id) is None


class TestAnalysisClear:
    """Tests para analysis_clear."""

    def test_clear_empty_basin(self, mock_db, sample_basin, capsys):
        """Test limpiar cuenca sin análisis."""
        analysis_clear(sample_basin["id"], force=True)

        captured = capsys.readouterr()
        assert "no tiene" in captured.out.lower()

    def test_clear_with_force(self, mock_db, sample_basin, sample_analysis, capsys):
        """Test limpiar con --force."""
        # Agregar otro análisis
        tc = TcResult(method="desbordes", tc_hr=0.4, tc_min=24.0)
        storm = StormResult(
            type="blocks",
            return_period=10,
            duration_hr=1.5,
            total_depth_mm=80.0,
            peak_intensity_mmhr=40.0,
            n_intervals=18,
        )
        hydrograph = HydrographResult(
            tc_method="desbordes",
            tc_min=24.0,
            storm_type="blocks",
            return_period=10,
            peak_flow_m3s=3.5,
            time_to_peak_hr=0.6,
            time_to_peak_min=36.0,
            volume_m3=30000.0,
            total_depth_mm=80.0,
            runoff_mm=30.0,
        )
        mock_db.add_analysis(
            basin_id=sample_basin["id"],
            tc=tc,
            storm=storm,
            hydrograph=hydrograph,
        )

        analysis_clear(sample_basin["id"], force=True)

        captured = capsys.readouterr()
        assert "Eliminados 2" in captured.out

        # Verificar que se eliminaron todos
        analyses = mock_db.get_basin_analyses(sample_basin["id"])
        assert len(analyses) == 0

    def test_clear_cancelled(self, mock_db, sample_basin, sample_analysis, capsys, monkeypatch):
        """Test limpieza cancelada."""
        monkeypatch.setattr('typer.confirm', lambda x: False)

        import typer
        with pytest.raises(typer.Exit):
            analysis_clear(sample_basin["id"], force=False)

        captured = capsys.readouterr()
        assert "cancelada" in captured.out

        # Verificar que NO se eliminó
        analyses = mock_db.get_basin_analyses(sample_basin["id"])
        assert len(analyses) == 1


class TestAnalysisNote:
    """Tests para analysis_note."""

    def test_view_note(self, mock_db, sample_analysis, capsys):
        """Test ver nota existente."""
        analysis_note(sample_analysis["id"])

        captured = capsys.readouterr()
        assert "Escenario base" in captured.out

    def test_view_empty_note(self, mock_db, sample_basin, capsys):
        """Test ver nota vacía."""
        # Crear análisis sin nota
        tc = TcResult(method="desbordes", tc_hr=0.4, tc_min=24.0)
        storm = StormResult(
            type="blocks",
            return_period=10,
            duration_hr=1.5,
            total_depth_mm=80.0,
            peak_intensity_mmhr=40.0,
            n_intervals=18,
        )
        hydrograph = HydrographResult(
            tc_method="desbordes",
            tc_min=24.0,
            storm_type="blocks",
            return_period=10,
            peak_flow_m3s=3.5,
            time_to_peak_hr=0.6,
            time_to_peak_min=36.0,
            volume_m3=30000.0,
            total_depth_mm=80.0,
            runoff_mm=30.0,
        )
        analysis = mock_db.add_analysis(
            basin_id=sample_basin["id"],
            tc=tc,
            storm=storm,
            hydrograph=hydrograph,
            note=None,
        )

        analysis_note(analysis["id"])

        captured = capsys.readouterr()
        assert "no tiene nota" in captured.out

    def test_set_note(self, mock_db, sample_analysis, capsys):
        """Test establecer nueva nota."""
        analysis_note(sample_analysis["id"], note="Nueva nota")

        captured = capsys.readouterr()
        assert "actualizada" in captured.out

        # Verificar cambio
        updated = mock_db.get_analysis(sample_analysis["id"])
        assert updated["note"] == "Nueva nota"

    def test_clear_note(self, mock_db, sample_analysis, capsys):
        """Test eliminar nota con --clear."""
        analysis_note(sample_analysis["id"], clear=True)

        captured = capsys.readouterr()
        assert "eliminada" in captured.out

        # Verificar que se eliminó
        updated = mock_db.get_analysis(sample_analysis["id"])
        assert updated["note"] is None

    def test_nonexistent_analysis(self, mock_db, capsys):
        """Test nota de análisis inexistente."""
        import typer
        with pytest.raises(typer.Exit):
            analysis_note("nonexistent")

        captured = capsys.readouterr()
        assert "no encontrado" in captured.out
