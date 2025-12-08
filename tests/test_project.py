"""
Tests para el módulo de proyectos hidrológicos.
"""

import pytest
import tempfile
from pathlib import Path

from hidropluvial.project import ProjectManager
from hidropluvial.models import Project, Basin


class TestBasin:
    """Tests para el modelo Basin."""

    def test_basin_creation(self):
        """Basin se crea con parámetros básicos."""
        basin = Basin(
            name="Cuenca Test",
            area_ha=50.0,
            slope_pct=2.5,
            p3_10=80.0,
            c=0.55,
        )

        assert basin.name == "Cuenca Test"
        assert basin.area_ha == 50.0
        assert basin.slope_pct == 2.5
        assert basin.p3_10 == 80.0
        assert basin.c == 0.55
        assert basin.cn is None
        assert len(basin.id) == 8

    # NOTE: Los métodos from_session, to_session y cuenca fueron eliminados
    # como parte de la refactorización para eliminar la dependencia de Session.
    # Basin ahora es un modelo independiente sin relación directa con Session.


class TestProject:
    """Tests para el modelo Project."""

    def test_project_creation(self):
        """Project se crea con parámetros básicos."""
        project = Project(
            name="Estudio Test",
            description="Descripción del proyecto",
            author="Usuario",
            location="Montevideo",
        )

        assert project.name == "Estudio Test"
        assert project.description == "Descripción del proyecto"
        assert project.author == "Usuario"
        assert project.location == "Montevideo"
        assert project.n_basins == 0
        assert len(project.id) == 8

    def test_project_add_basin(self):
        """Project puede agregar cuencas."""
        project = Project(name="Test")
        basin = Basin(
            name="Cuenca 1",
            area_ha=50.0,
            slope_pct=2.5,
            p3_10=80.0,
        )

        project.add_basin(basin)

        assert project.n_basins == 1
        assert project.basins[0].name == "Cuenca 1"

    def test_project_get_basin(self):
        """Project puede obtener cuenca por ID."""
        project = Project(name="Test")
        basin = Basin(
            id="abc12345",
            name="Cuenca 1",
            area_ha=50.0,
            slope_pct=2.5,
            p3_10=80.0,
        )
        project.add_basin(basin)

        # ID completo
        found = project.get_basin("abc12345")
        assert found is not None
        assert found.name == "Cuenca 1"

        # ID parcial
        found = project.get_basin("abc")
        assert found is not None
        assert found.name == "Cuenca 1"

        # ID inexistente
        found = project.get_basin("xyz")
        assert found is None

    def test_project_remove_basin(self):
        """Project puede eliminar cuencas."""
        project = Project(name="Test")
        basin = Basin(
            id="abc12345",
            name="Cuenca 1",
            area_ha=50.0,
            slope_pct=2.5,
            p3_10=80.0,
        )
        project.add_basin(basin)

        assert project.n_basins == 1

        result = project.remove_basin("abc12345")

        assert result is True
        assert project.n_basins == 0

    def test_project_total_analyses(self):
        """Project cuenta total de análisis."""
        project = Project(name="Test")

        basin1 = Basin(
            name="Cuenca 1",
            area_ha=50.0,
            slope_pct=2.5,
            p3_10=80.0,
        )
        basin2 = Basin(
            name="Cuenca 2",
            area_ha=100.0,
            slope_pct=3.0,
            p3_10=90.0,
        )

        project.add_basin(basin1)
        project.add_basin(basin2)

        # Sin análisis
        assert project.total_analyses == 0


class TestProjectManager:
    """Tests para ProjectManager."""

    @pytest.fixture
    def temp_dir(self):
        """Crea directorio temporal para tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_create_project(self, temp_dir):
        """Manager crea proyecto correctamente."""
        manager = ProjectManager(data_dir=temp_dir)

        project = manager.create_project(
            name="Test Project",
            description="Descripción",
            author="Usuario",
        )

        assert project.name == "Test Project"
        assert project.description == "Descripción"

        # Verificar que se guardó en la base de datos
        db_path = temp_dir / "hidropluvial.db"
        assert db_path.exists()

    def test_list_projects(self, temp_dir):
        """Manager lista proyectos."""
        manager = ProjectManager(data_dir=temp_dir)

        manager.create_project(name="Proyecto 1")
        manager.create_project(name="Proyecto 2")

        projects = manager.list_projects()

        assert len(projects) == 2
        names = [p["name"] for p in projects]
        assert "Proyecto 1" in names
        assert "Proyecto 2" in names

    def test_get_project(self, temp_dir):
        """Manager obtiene proyecto por ID."""
        manager = ProjectManager(data_dir=temp_dir)

        created = manager.create_project(name="Test")

        # ID completo
        found = manager.get_project(created.id)
        assert found is not None
        assert found.name == "Test"

        # ID parcial
        found = manager.get_project(created.id[:4])
        assert found is not None
        assert found.name == "Test"

    def test_delete_project(self, temp_dir):
        """Manager elimina proyecto."""
        manager = ProjectManager(data_dir=temp_dir)

        project = manager.create_project(name="Test")
        project_id = project.id

        result = manager.delete_project(project_id)

        assert result is True

        # Verificar que ya no existe
        found = manager.get_project(project_id)
        assert found is None

    def test_create_basin(self, temp_dir):
        """Manager crea cuenca en proyecto."""
        manager = ProjectManager(data_dir=temp_dir)
        project = manager.create_project(name="Test")

        basin = manager.create_basin(
            project=project,
            name="Cuenca Test",
            area_ha=50.0,
            slope_pct=2.5,
            p3_10=80.0,
            c=0.55,
        )

        assert basin.name == "Cuenca Test"
        assert project.n_basins == 1

        # Recargar y verificar persistencia
        reloaded = manager.load_project(project.id)
        assert reloaded.n_basins == 1
        assert reloaded.basins[0].name == "Cuenca Test"

    def test_save_and_load_project(self, temp_dir):
        """Manager guarda y carga proyecto con cuencas."""
        manager = ProjectManager(data_dir=temp_dir)

        project = manager.create_project(
            name="Test",
            description="Descripción",
        )
        manager.create_basin(
            project=project,
            name="Cuenca 1",
            area_ha=50.0,
            slope_pct=2.5,
            p3_10=80.0,
            c=0.55,
            cn=75,
        )

        # Cargar de nuevo
        loaded = manager.load_project(project.id)

        assert loaded.name == "Test"
        assert loaded.description == "Descripción"
        assert loaded.n_basins == 1
        assert loaded.basins[0].name == "Cuenca 1"
        assert loaded.basins[0].c == 0.55
        assert loaded.basins[0].cn == 75
