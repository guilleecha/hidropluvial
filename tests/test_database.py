"""
Tests para el módulo de base de datos SQLite.
"""

import pytest
import tempfile
from pathlib import Path

from hidropluvial.database import Database, reset_database
from hidropluvial.models import TcResult, StormResult, HydrographResult


@pytest.fixture
def temp_db():
    """Crea una base de datos temporal para tests."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    db = Database(db_path)
    yield db

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def sample_tc():
    """TcResult de ejemplo."""
    return TcResult(
        method="kirpich",
        tc_hr=0.5,
        tc_min=30.0,
        parameters={"length_m": 1000, "slope_pct": 2.0},
    )


@pytest.fixture
def sample_storm():
    """StormResult de ejemplo."""
    return StormResult(
        type="gz",
        return_period=10,
        duration_hr=1.0,
        total_depth_mm=50.0,
        peak_intensity_mmhr=80.0,
        n_intervals=12,
        time_min=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60],
        intensity_mmhr=[10, 20, 40, 80, 60, 40, 30, 25, 20, 15, 10, 8, 5],
    )


@pytest.fixture
def sample_hydrograph():
    """HydrographResult de ejemplo."""
    return HydrographResult(
        tc_method="kirpich",
        tc_min=30.0,
        storm_type="gz",
        return_period=10,
        x_factor=1.25,
        peak_flow_m3s=5.5,
        time_to_peak_hr=0.4,
        time_to_peak_min=24.0,
        tp_unit_hr=0.35,
        tp_unit_min=21.0,
        tb_hr=0.93,
        tb_min=56.0,
        volume_m3=10000,
        total_depth_mm=50.0,
        runoff_mm=25.0,
        time_hr=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        flow_m3s=[0, 1.0, 2.5, 4.5, 5.5, 5.0, 4.0, 3.0, 2.0, 1.0, 0.5],
    )


class TestDatabaseProjects:
    """Tests para operaciones de proyectos."""

    def test_create_project(self, temp_db):
        """Crear un proyecto."""
        project = temp_db.create_project(
            name="Test Project",
            description="A test project",
            author="Test Author",
            location="Test Location",
        )

        assert project["name"] == "Test Project"
        assert project["description"] == "A test project"
        assert project["author"] == "Test Author"
        assert len(project["id"]) == 8

    def test_get_project(self, temp_db):
        """Obtener proyecto por ID."""
        created = temp_db.create_project(name="Get Test")
        retrieved = temp_db.get_project(created["id"])

        assert retrieved is not None
        assert retrieved["name"] == "Get Test"

    def test_get_project_partial_id(self, temp_db):
        """Obtener proyecto por ID parcial."""
        created = temp_db.create_project(name="Partial ID Test")
        partial_id = created["id"][:4]
        retrieved = temp_db.get_project(partial_id)

        assert retrieved is not None
        assert retrieved["id"] == created["id"]

    def test_get_nonexistent_project(self, temp_db):
        """Proyecto inexistente retorna None."""
        result = temp_db.get_project("nonexistent")
        assert result is None

    def test_list_projects(self, temp_db):
        """Listar proyectos."""
        temp_db.create_project(name="Project 1")
        temp_db.create_project(name="Project 2")
        temp_db.create_project(name="Project 3")

        projects = temp_db.list_projects()
        assert len(projects) == 3

    def test_list_projects_with_stats(self, temp_db):
        """Listar proyectos incluye estadísticas."""
        project = temp_db.create_project(name="Stats Test")
        temp_db.create_basin(
            project_id=project["id"],
            name="Basin 1",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        projects = temp_db.list_projects()
        assert projects[0]["n_basins"] == 1
        assert projects[0]["total_analyses"] == 0

    def test_update_project(self, temp_db):
        """Actualizar proyecto."""
        project = temp_db.create_project(name="Original")

        temp_db.update_project(project["id"], name="Updated", author="New Author")

        updated = temp_db.get_project(project["id"])
        assert updated["name"] == "Updated"
        assert updated["author"] == "New Author"

    def test_delete_project(self, temp_db):
        """Eliminar proyecto."""
        project = temp_db.create_project(name="To Delete")

        result = temp_db.delete_project(project["id"])
        assert result is True

        retrieved = temp_db.get_project(project["id"])
        assert retrieved is None

    def test_delete_project_cascades_basins(self, temp_db):
        """Eliminar proyecto elimina cuencas."""
        project = temp_db.create_project(name="Cascade Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        temp_db.delete_project(project["id"])

        retrieved_basin = temp_db.get_basin(basin["id"])
        assert retrieved_basin is None


class TestDatabaseBasins:
    """Tests para operaciones de cuencas."""

    def test_create_basin(self, temp_db):
        """Crear una cuenca."""
        project = temp_db.create_project(name="Basin Test Project")

        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Test Basin",
            area_ha=25.5,
            slope_pct=3.5,
            p3_10=55.0,
            c=0.65,
            cn=75,
            length_m=500,
        )

        assert basin["name"] == "Test Basin"
        assert basin["area_ha"] == 25.5
        assert basin["c"] == 0.65
        assert basin["cn"] == 75

    def test_get_basin_with_analyses(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Obtener cuenca con análisis incluidos."""
        project = temp_db.create_project(name="Full Basin Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Full Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        # Agregar Tc y análisis
        temp_db.add_tc_result(basin["id"], "kirpich", 0.5)
        temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)

        retrieved = temp_db.get_basin(basin["id"])

        assert len(retrieved["tc_results"]) == 1
        assert len(retrieved["analyses"]) == 1
        assert retrieved["analyses"][0]["storm"]["type"] == "gz"

    def test_get_project_basins(self, temp_db):
        """Obtener cuencas de un proyecto."""
        project = temp_db.create_project(name="Multi Basin")
        temp_db.create_basin(project_id=project["id"], name="B1", area_ha=10, slope_pct=2, p3_10=50)
        temp_db.create_basin(project_id=project["id"], name="B2", area_ha=20, slope_pct=3, p3_10=55)
        temp_db.create_basin(project_id=project["id"], name="B3", area_ha=30, slope_pct=4, p3_10=60)

        basins = temp_db.get_project_basins(project["id"])
        assert len(basins) == 3

    def test_update_basin(self, temp_db):
        """Actualizar cuenca."""
        project = temp_db.create_project(name="Update Basin Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Original Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        temp_db.update_basin(basin["id"], name="Updated Basin", c=0.7, cn=80)

        updated = temp_db.get_basin(basin["id"])
        assert updated["name"] == "Updated Basin"
        assert updated["c"] == 0.7
        assert updated["cn"] == 80

    def test_delete_basin(self, temp_db):
        """Eliminar cuenca."""
        project = temp_db.create_project(name="Delete Basin Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="To Delete",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        result = temp_db.delete_basin(basin["id"])
        assert result is True

        retrieved = temp_db.get_basin(basin["id"])
        assert retrieved is None


class TestDatabaseTcResults:
    """Tests para resultados de tiempo de concentración."""

    def test_add_tc_result(self, temp_db):
        """Agregar resultado de Tc."""
        project = temp_db.create_project(name="Tc Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Tc Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        tc = temp_db.add_tc_result(
            basin_id=basin["id"],
            method="kirpich",
            tc_hr=0.5,
            parameters={"length_m": 1000, "slope_pct": 2.0},
        )

        assert tc["method"] == "kirpich"
        assert tc["tc_hr"] == 0.5
        assert tc["tc_min"] == 30.0

    def test_add_tc_result_replaces_existing(self, temp_db):
        """Agregar Tc con mismo método reemplaza el anterior."""
        project = temp_db.create_project(name="Replace Tc Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Replace Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        temp_db.add_tc_result(basin["id"], "kirpich", 0.5)
        temp_db.add_tc_result(basin["id"], "kirpich", 0.75)  # Reemplaza

        tc_results = temp_db.get_tc_results(basin["id"])
        assert len(tc_results) == 1
        assert tc_results[0]["tc_hr"] == 0.75

    def test_multiple_tc_methods(self, temp_db):
        """Múltiples métodos de Tc."""
        project = temp_db.create_project(name="Multi Tc Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Multi Tc Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        temp_db.add_tc_result(basin["id"], "kirpich", 0.5)
        temp_db.add_tc_result(basin["id"], "temez", 0.6)
        temp_db.add_tc_result(basin["id"], "desbordes", 0.55)

        tc_results = temp_db.get_tc_results(basin["id"])
        assert len(tc_results) == 3

    def test_clear_tc_results(self, temp_db):
        """Limpiar resultados de Tc."""
        project = temp_db.create_project(name="Clear Tc Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Clear Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        temp_db.add_tc_result(basin["id"], "kirpich", 0.5)
        temp_db.add_tc_result(basin["id"], "temez", 0.6)

        deleted = temp_db.clear_tc_results(basin["id"])
        assert deleted == 2

        tc_results = temp_db.get_tc_results(basin["id"])
        assert len(tc_results) == 0


class TestDatabaseAnalyses:
    """Tests para análisis hidrológicos."""

    def test_add_analysis(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Agregar análisis completo."""
        project = temp_db.create_project(name="Analysis Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Analysis Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        analysis = temp_db.add_analysis(
            basin_id=basin["id"],
            tc=sample_tc,
            storm=sample_storm,
            hydrograph=sample_hydrograph,
            note="Test analysis",
        )

        assert len(analysis["id"]) == 8
        assert analysis["tc"]["method"] == "kirpich"
        assert analysis["storm"]["type"] == "gz"
        assert analysis["hydrograph"]["peak_flow_m3s"] == 5.5

    def test_get_analysis_with_timeseries(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Obtener análisis incluye series temporales."""
        project = temp_db.create_project(name="Timeseries Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="TS Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        created = temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)
        retrieved = temp_db.get_analysis(created["id"])

        # Verificar series temporales de tormenta
        assert len(retrieved["storm"]["time_min"]) == 13
        assert len(retrieved["storm"]["intensity_mmhr"]) == 13

        # Verificar series temporales de hidrograma
        assert len(retrieved["hydrograph"]["time_hr"]) == 11
        assert len(retrieved["hydrograph"]["flow_m3s"]) == 11

    def test_get_basin_analyses(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Obtener todos los análisis de una cuenca."""
        project = temp_db.create_project(name="Multiple Analyses")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Multi Analysis Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        # Agregar 3 análisis
        for _ in range(3):
            temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)

        analyses = temp_db.get_basin_analyses(basin["id"])
        assert len(analyses) == 3

    def test_get_analysis_summary(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Resumen de análisis (sin series temporales)."""
        project = temp_db.create_project(name="Summary Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Summary Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)

        summary = temp_db.get_analysis_summary(basin["id"])
        assert len(summary) == 1
        assert summary[0]["tc_method"] == "kirpich"
        assert summary[0]["storm"] == "gz"
        assert summary[0]["qpeak_m3s"] == 5.5

    def test_update_analysis_note(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Actualizar nota de análisis."""
        project = temp_db.create_project(name="Note Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Note Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        analysis = temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)

        temp_db.update_analysis_note(analysis["id"], "Updated note")

        retrieved = temp_db.get_analysis(analysis["id"])
        assert retrieved["note"] == "Updated note"

    def test_delete_analysis(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Eliminar análisis."""
        project = temp_db.create_project(name="Delete Analysis Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Delete Analysis Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        analysis = temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)

        result = temp_db.delete_analysis(analysis["id"])
        assert result is True

        retrieved = temp_db.get_analysis(analysis["id"])
        assert retrieved is None

    def test_clear_basin_analyses(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Limpiar todos los análisis de una cuenca."""
        project = temp_db.create_project(name="Clear Analyses Test")
        basin = temp_db.create_basin(
            project_id=project["id"],
            name="Clear Analyses Basin",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )

        for _ in range(5):
            temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)

        deleted = temp_db.clear_basin_analyses(basin["id"])
        assert deleted == 5

        analyses = temp_db.get_basin_analyses(basin["id"])
        assert len(analyses) == 0


class TestDatabaseQueries:
    """Tests para consultas y búsquedas."""

    def test_get_stats(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Estadísticas de la base de datos."""
        project = temp_db.create_project(name="Stats Project")
        basin1 = temp_db.create_basin(
            project_id=project["id"], name="B1", area_ha=10, slope_pct=2, p3_10=50
        )
        basin2 = temp_db.create_basin(
            project_id=project["id"], name="B2", area_ha=20, slope_pct=3, p3_10=55
        )

        temp_db.add_analysis(basin1["id"], sample_tc, sample_storm, sample_hydrograph)
        temp_db.add_analysis(basin2["id"], sample_tc, sample_storm, sample_hydrograph)

        stats = temp_db.get_stats()
        assert stats["n_projects"] == 1
        assert stats["n_basins"] == 2
        assert stats["n_analyses"] == 2
        assert stats["db_size_bytes"] > 0

    def test_search_basins_by_name(self, temp_db):
        """Buscar cuencas por nombre."""
        project = temp_db.create_project(name="Search Project")
        temp_db.create_basin(project_id=project["id"], name="Arroyo Norte", area_ha=10, slope_pct=2, p3_10=50)
        temp_db.create_basin(project_id=project["id"], name="Arroyo Sur", area_ha=20, slope_pct=3, p3_10=55)
        temp_db.create_basin(project_id=project["id"], name="Cuenca Principal", area_ha=5, slope_pct=1, p3_10=45)

        results = temp_db.search_basins(name="Arroyo")
        assert len(results) == 2

    def test_search_basins_by_area(self, temp_db):
        """Buscar cuencas por área."""
        project = temp_db.create_project(name="Area Search")
        temp_db.create_basin(project_id=project["id"], name="Small", area_ha=5, slope_pct=2, p3_10=50)
        temp_db.create_basin(project_id=project["id"], name="Medium", area_ha=15, slope_pct=2, p3_10=50)
        temp_db.create_basin(project_id=project["id"], name="Large", area_ha=50, slope_pct=2, p3_10=50)

        results = temp_db.search_basins(min_area=10, max_area=20)
        assert len(results) == 1
        assert results[0]["name"] == "Medium"

    def test_search_basins_has_cn(self, temp_db):
        """Buscar cuencas con/sin CN."""
        project = temp_db.create_project(name="CN Search")
        temp_db.create_basin(project_id=project["id"], name="With CN", area_ha=10, slope_pct=2, p3_10=50, cn=75)
        temp_db.create_basin(project_id=project["id"], name="Without CN", area_ha=20, slope_pct=2, p3_10=50)

        with_cn = temp_db.search_basins(has_cn=True)
        assert len(with_cn) == 1
        assert with_cn[0]["name"] == "With CN"

        without_cn = temp_db.search_basins(has_cn=False)
        assert len(without_cn) == 1
        assert without_cn[0]["name"] == "Without CN"

    def test_search_analyses(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Buscar análisis con filtros."""
        project = temp_db.create_project(name="Analysis Search")
        basin = temp_db.create_basin(
            project_id=project["id"], name="Search Basin", area_ha=10, slope_pct=2, p3_10=50
        )

        # Crear análisis con diferentes tormentas
        temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)

        storm2 = StormResult(
            type="blocks",
            return_period=25,
            duration_hr=2.0,
            total_depth_mm=80.0,
            peak_intensity_mmhr=100.0,
            n_intervals=24,
            time_min=[],
            intensity_mmhr=[],
        )
        hydro2 = HydrographResult(
            tc_method="kirpich",
            tc_min=30.0,
            storm_type="blocks",
            return_period=25,
            peak_flow_m3s=12.0,
            time_to_peak_hr=0.5,
            time_to_peak_min=30.0,
            volume_m3=20000,
            total_depth_mm=80.0,
            runoff_mm=40.0,
            time_hr=[],
            flow_m3s=[],
        )
        temp_db.add_analysis(basin["id"], sample_tc, storm2, hydro2)

        # Buscar por tipo de tormenta
        gz_results = temp_db.search_analyses(storm_type="gz")
        assert len(gz_results) == 1

        # Buscar por período de retorno
        tr25_results = temp_db.search_analyses(return_period=25)
        assert len(tr25_results) == 1

        # Buscar por caudal pico
        high_flow = temp_db.search_analyses(min_peak_flow=10.0)
        assert len(high_flow) == 1
        assert high_flow[0]["peak_flow_m3s"] == 12.0


class TestDatabaseIntegrity:
    """Tests de integridad de datos."""

    def test_cascade_delete_basin_analyses(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Al eliminar cuenca se eliminan sus análisis."""
        project = temp_db.create_project(name="Cascade Test")
        basin = temp_db.create_basin(
            project_id=project["id"], name="Cascade Basin", area_ha=10, slope_pct=2, p3_10=50
        )

        analysis = temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)
        analysis_id = analysis["id"]

        # Eliminar cuenca
        temp_db.delete_basin(basin["id"])

        # Verificar que análisis fue eliminado
        retrieved = temp_db.get_analysis(analysis_id)
        assert retrieved is None

    def test_cascade_delete_project_all(self, temp_db, sample_tc, sample_storm, sample_hydrograph):
        """Al eliminar proyecto se eliminan cuencas y análisis."""
        project = temp_db.create_project(name="Full Cascade")
        basin = temp_db.create_basin(
            project_id=project["id"], name="Basin", area_ha=10, slope_pct=2, p3_10=50
        )
        temp_db.add_tc_result(basin["id"], "kirpich", 0.5)
        analysis = temp_db.add_analysis(basin["id"], sample_tc, sample_storm, sample_hydrograph)

        basin_id = basin["id"]
        analysis_id = analysis["id"]

        # Eliminar proyecto
        temp_db.delete_project(project["id"])

        # Verificar todo eliminado
        assert temp_db.get_basin(basin_id) is None
        assert temp_db.get_analysis(analysis_id) is None
        assert len(temp_db.get_tc_results(basin_id)) == 0

    def test_project_timestamp_updates(self, temp_db):
        """Timestamp del proyecto se actualiza con cambios en cuencas."""
        project = temp_db.create_project(name="Timestamp Test")
        original_timestamp = project["updated_at"]

        import time
        time.sleep(0.01)  # Pequeña pausa para asegurar diferencia

        # Agregar cuenca
        temp_db.create_basin(
            project_id=project["id"], name="Basin", area_ha=10, slope_pct=2, p3_10=50
        )

        updated_project = temp_db.get_project(project["id"])
        assert updated_project["updated_at"] > original_timestamp
