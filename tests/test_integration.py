"""
Tests de integración - Flujos de usuario completos.

Estos tests simulan los pasos que haría un usuario típico,
validando que todo el sistema funciona de manera cohesiva.
"""

import pytest
import tempfile
from pathlib import Path

from hidropluvial.database import Database
from hidropluvial.project import ProjectManager
from hidropluvial.core import kirpich, desbordes, temez
from hidropluvial.core.tc import nrcs_velocity_method
from hidropluvial.core.runoff import scs_runoff
from hidropluvial.config import (
    SheetFlowSegment,
    ShallowFlowSegment,
    ChannelFlowSegment,
)


@pytest.fixture
def temp_data_dir():
    """Crea directorio temporal para datos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def manager(temp_data_dir):
    """ProjectManager con directorio temporal."""
    return ProjectManager(data_dir=temp_data_dir)


class TestUserFlowUrbanBasin:
    """
    Flujo de usuario: Análisis de cuenca urbana pequeña.

    Escenario: Ingeniero analiza drenaje de un loteo residencial.
    - Cuenca: 15 ha, pendiente 2.5%
    - Método Tc: Desbordes (cuenca urbana)
    - Coeficiente: C = 0.65 (zona residencial)
    """

    def test_complete_urban_analysis_flow(self, manager):
        """Flujo completo: proyecto → cuenca → Tc → persistencia."""
        # 1. Usuario crea proyecto
        project = manager.create_project(
            name="Loteo Las Flores",
            description="Estudio de drenaje pluvial",
            author="Ing. García",
            location="Montevideo",
        )
        assert project.id is not None
        assert project.name == "Loteo Las Flores"

        # 2. Usuario crea cuenca
        basin = manager.create_basin(
            project=project,
            name="Cuenca Principal",
            area_ha=15.0,
            slope_pct=2.5,
            p3_10=80.0,  # mm
            c=0.65,
        )
        assert basin.id is not None
        assert basin.area_ha == 15.0

        # 3. Usuario calcula Tc con método Desbordes
        tc_hr = desbordes(
            area_ha=basin.area_ha,
            slope_pct=basin.slope_pct,
            c=basin.c,
        )
        tc_min = tc_hr * 60
        assert 10 < tc_min < 40  # Rango típico cuenca urbana pequeña

        # Guardar resultado de Tc
        manager.add_tc_result(
            project, basin, "desbordes", tc_hr,
            c=basin.c, area_ha=basin.area_ha,
        )

        # 4. Verificar persistencia
        reloaded = manager.load_project(project.id)
        assert reloaded.n_basins == 1
        assert len(reloaded.basins[0].tc_results) == 1
        assert reloaded.basins[0].tc_results[0].method == "desbordes"
        assert reloaded.basins[0].tc_results[0].tc_min == pytest.approx(tc_min, rel=0.01)


class TestUserFlowRuralBasin:
    """
    Flujo de usuario: Análisis de cuenca rural.

    Escenario: Diseño de alcantarilla en camino rural.
    - Cuenca: 500 ha, cauce de 3.5 km
    - Método Tc: Kirpich (cuenca rural con cauce definido)
    - Coeficiente: CN = 72 (pasturas en suelo B)
    """

    def test_complete_rural_analysis_flow(self, manager):
        """Flujo completo para cuenca rural con SCS-CN."""
        # 1. Crear proyecto
        project = manager.create_project(
            name="Alcantarilla Ruta 7 km 45",
            description="Dimensionamiento de alcantarilla",
            author="Ing. Rodríguez",
            location="Canelones",
        )

        # 2. Crear cuenca
        basin = manager.create_basin(
            project=project,
            name="Cuenca Arroyo Norte",
            area_ha=500.0,
            slope_pct=1.8,
            length_m=3500,  # 3.5 km de cauce
            p3_10=75.0,
            cn=72,
        )
        assert basin.length_m == 3500

        # 3. Calcular Tc con Kirpich
        slope_decimal = basin.slope_pct / 100
        tc_hr = kirpich(basin.length_m, slope_decimal)
        tc_min = tc_hr * 60
        assert tc_min > 30  # Cuenca grande, Tc mayor

        manager.add_tc_result(
            project, basin, "kirpich", tc_hr,
            length_m=basin.length_m, slope=slope_decimal,
        )

        # 4. Calcular escorrentía con SCS-CN (usando P total ejemplo)
        p_total_mm = 100.0  # Precipitación de ejemplo
        runoff_mm = scs_runoff(p_total_mm, basin.cn)
        assert runoff_mm < p_total_mm  # Escorrentía < precipitación
        assert runoff_mm > 0

        # 5. Verificar persistencia
        reloaded = manager.load_project(project.id)
        assert reloaded.basins[0].cn == 72
        assert reloaded.basins[0].length_m == 3500
        assert len(reloaded.basins[0].tc_results) == 1
        assert reloaded.basins[0].tc_results[0].method == "kirpich"


class TestUserFlowNRCSMethod:
    """
    Flujo de usuario: Análisis con método NRCS de velocidades.

    Escenario: Cuenca suburbana con diferentes tipos de flujo.
    """

    def test_nrcs_segments_flow(self, manager):
        """Flujo con configuración de segmentos NRCS."""
        # 1. Crear proyecto y cuenca
        project = manager.create_project(
            name="Barrio Nuevo",
            description="Drenaje zona en desarrollo",
        )

        basin = manager.create_basin(
            project=project,
            name="Subcuenca A",
            area_ha=25.0,
            slope_pct=2.0,
            p3_10=80.0,
            c=0.55,
            cn=75,
        )

        # 2. Configurar segmentos NRCS
        segments = [
            # Flujo laminar inicial (techos y patios)
            SheetFlowSegment(
                length_m=50,
                n=0.15,  # superficie lisa
                slope=0.02,
                p2_mm=50,
            ),
            # Flujo concentrado por cunetas
            ShallowFlowSegment(
                length_m=400,
                slope=0.015,
                surface="unpaved",
            ),
            # Canal natural hasta punto de control
            ChannelFlowSegment(
                length_m=800,
                n=0.035,
                slope=0.01,
                hydraulic_radius_m=0.4,
            ),
        ]

        # 3. Calcular Tc con NRCS
        tc_hr = nrcs_velocity_method(segments, p2_mm=50)
        tc_min = tc_hr * 60
        assert tc_min > 0

        # 4. Guardar segmentos en BD
        manager._db.set_nrcs_segments(basin.id, segments, p2_mm=50)

        # Actualizar modelo en memoria
        basin.nrcs_segments = segments
        basin.p2_mm = 50

        # 5. Guardar Tc
        manager.add_tc_result(
            project, basin, "nrcs", tc_hr,
            p2_mm=50, n_segments=len(segments),
        )

        # 6. Verificar persistencia
        reloaded = manager.load_project(project.id)
        reloaded_basin = reloaded.basins[0]

        assert reloaded_basin.p2_mm == 50
        assert len(reloaded_basin.nrcs_segments) == 3
        assert len(reloaded_basin.tc_results) == 1
        assert reloaded_basin.tc_results[0].method == "nrcs"


class TestUserFlowWeightedCoefficients:
    """
    Flujo de usuario: Análisis con coeficientes ponderados.

    Escenario: Cuenca con múltiples tipos de cobertura.
    """

    def test_weighted_c_flow(self, manager):
        """Flujo con cálculo de C ponderado."""
        # 1. Crear proyecto y cuenca
        project = manager.create_project(
            name="Centro Comercial",
            description="Drenaje estacionamiento y edificio",
        )

        basin = manager.create_basin(
            project=project,
            name="Predio completo",
            area_ha=5.0,
            slope_pct=1.5,
            p3_10=80.0,
        )

        # 2. Definir coberturas para C
        coverage_items = [
            {"description": "Techos edificio", "area_ha": 1.5, "value": 0.95, "percentage": 30},
            {"description": "Estacionamiento", "area_ha": 2.0, "value": 0.90, "percentage": 40},
            {"description": "Veredas", "area_ha": 0.5, "value": 0.85, "percentage": 10},
            {"description": "Áreas verdes", "area_ha": 1.0, "value": 0.25, "percentage": 20},
        ]

        # 3. Calcular C ponderado
        total_area = sum(item["area_ha"] for item in coverage_items)
        c_weighted = sum(
            item["area_ha"] * item["value"] for item in coverage_items
        ) / total_area

        assert 0.7 < c_weighted < 0.9  # Zona muy urbanizada

        # 4. Guardar en BD
        manager._db.set_weighted_coefficient(
            basin_id=basin.id,
            coef_type="c",
            weighted_value=c_weighted,
            items=coverage_items,
            table_used="fhwa",
        )

        # Actualizar C en la cuenca
        manager._db.update_basin(basin.id, c=c_weighted)
        basin.c = c_weighted

        # 5. Verificar persistencia
        reloaded = manager.load_project(project.id)
        reloaded_basin = reloaded.basins[0]

        assert reloaded_basin.c == pytest.approx(c_weighted, rel=0.01)
        assert reloaded_basin.c_weighted is not None
        assert len(reloaded_basin.c_weighted.items) == 4


class TestUserFlowMultipleBasins:
    """
    Flujo de usuario: Proyecto con múltiples cuencas.

    Escenario: Estudio de drenaje de urbanización grande.
    """

    def test_multiple_basins_flow(self, manager):
        """Flujo con varias cuencas en un proyecto."""
        # 1. Crear proyecto
        project = manager.create_project(
            name="Urbanización Los Olivos",
            description="Estudio hidrológico completo",
            author="Consultora ABC",
        )

        # 2. Crear múltiples cuencas
        basins_data = [
            {"name": "Cuenca Norte", "area_ha": 8, "slope_pct": 3.0, "c": 0.60},
            {"name": "Cuenca Centro", "area_ha": 12, "slope_pct": 2.5, "c": 0.70},
            {"name": "Cuenca Sur", "area_ha": 10, "slope_pct": 2.0, "c": 0.65},
        ]

        basins = []
        for data in basins_data:
            basin = manager.create_basin(
                project=project,
                p3_10=80.0,
                **data,
            )
            basins.append(basin)

        assert project.n_basins == 3

        # 3. Calcular Tc para cada cuenca
        for basin in basins:
            tc_hr = desbordes(basin.area_ha, basin.slope_pct, basin.c)
            manager.add_tc_result(project, basin, "desbordes", tc_hr)

        # 4. Verificar que cada cuenca tiene su Tc
        for basin in basins:
            assert len(basin.tc_results) == 1

        # 5. Comparar tiempos de concentración
        tc_values = [b.tc_results[0].tc_min for b in basins]
        # Cuenca más grande y menos pendiente debería tener Tc mayor
        # Cuenca Centro es la más grande
        assert tc_values[1] > tc_values[0]  # Centro > Norte

        # 6. Verificar persistencia
        reloaded = manager.load_project(project.id)
        assert reloaded.n_basins == 3
        assert reloaded.total_analyses == 0  # Solo Tc, no análisis completos


class TestUserFlowMultipleTcMethods:
    """
    Flujo de usuario: Comparación de métodos de Tc.

    Escenario: Usuario compara diferentes métodos para la misma cuenca.
    """

    def test_compare_tc_methods(self, manager):
        """Calcular Tc con múltiples métodos y comparar."""
        # 1. Crear proyecto y cuenca
        project = manager.create_project(name="Comparación Tc")

        basin = manager.create_basin(
            project=project,
            name="Cuenca Test",
            area_ha=20.0,
            slope_pct=2.5,
            length_m=1500,
            p3_10=80.0,
            c=0.55,
        )

        # 2. Calcular con método Desbordes
        tc_desbordes = desbordes(basin.area_ha, basin.slope_pct, basin.c)
        manager.add_tc_result(project, basin, "desbordes", tc_desbordes)

        # 3. Calcular con método Kirpich
        tc_kirpich = kirpich(basin.length_m, basin.slope_pct / 100)
        manager.add_tc_result(project, basin, "kirpich", tc_kirpich)

        # 4. Calcular con método Temez
        tc_temez = temez(basin.length_m / 1000, basin.slope_pct / 100)
        manager.add_tc_result(project, basin, "temez", tc_temez)

        # 5. Verificar que se guardaron los 3 métodos
        assert len(basin.tc_results) == 3

        methods = [tc.method for tc in basin.tc_results]
        assert "desbordes" in methods
        assert "kirpich" in methods
        assert "temez" in methods

        # 6. Verificar que los valores son del mismo orden de magnitud
        tc_values = [tc.tc_hr for tc in basin.tc_results]
        tc_min = min(tc_values)
        tc_max = max(tc_values)
        # Los métodos no deberían diferir más de 5x
        assert tc_max / tc_min < 5

        # 7. Persistencia
        reloaded = manager.load_project(project.id)
        assert len(reloaded.basins[0].tc_results) == 3


class TestUserFlowDeleteOperations:
    """
    Flujo de usuario: Operaciones de eliminación.

    Escenario: Usuario corrige errores eliminando elementos.
    """

    def test_delete_basin_preserves_others(self, manager):
        """Eliminar una cuenca no afecta otras."""
        project = manager.create_project(name="Delete Test")

        basin1 = manager.create_basin(
            project=project,
            name="Cuenca A",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
        )
        basin2 = manager.create_basin(
            project=project,
            name="Cuenca B",
            area_ha=20,
            slope_pct=3,
            p3_10=55,
        )

        assert project.n_basins == 2

        # Eliminar cuenca A
        manager.delete_basin(project, basin1.id)

        # Verificar
        reloaded = manager.load_project(project.id)
        assert reloaded.n_basins == 1
        assert reloaded.basins[0].name == "Cuenca B"

    def test_delete_project_removes_all(self, manager):
        """Eliminar proyecto elimina todo."""
        project = manager.create_project(name="Full Delete Test")

        basin = manager.create_basin(
            project=project,
            name="Cuenca",
            area_ha=10,
            slope_pct=2,
            p3_10=50,
            c=0.5,
        )

        manager.add_tc_result(project, basin, "desbordes", 0.3)

        # Guardar IDs
        project_id = project.id
        basin_id = basin.id

        # Eliminar proyecto
        result = manager.delete_project(project_id)
        assert result is True

        # Verificar que no existe
        assert manager.get_project(project_id) is None

        # Verificar que cuenca tampoco existe
        db_basin = manager._db.get_basin(basin_id)
        assert db_basin is None


class TestUserFlowReloadAndContinue:
    """
    Flujo de usuario: Cargar proyecto existente y continuar trabajo.

    Escenario: Usuario cierra y reabre la aplicación.
    """

    def test_reload_and_add_analysis(self, manager):
        """Cargar proyecto guardado y agregar nuevo análisis."""
        # Sesión 1: Crear proyecto y cuenca
        project = manager.create_project(
            name="Proyecto Continuo",
            description="Test de persistencia",
        )
        project_id = project.id

        basin = manager.create_basin(
            project=project,
            name="Cuenca Única",
            area_ha=15,
            slope_pct=2.5,
            p3_10=80,
            c=0.6,
        )

        tc_hr = desbordes(basin.area_ha, basin.slope_pct, basin.c)
        manager.add_tc_result(project, basin, "desbordes", tc_hr)

        # "Cerrar" sesión (el manager ya guarda automáticamente)

        # Sesión 2: Recargar proyecto
        reloaded = manager.load_project(project_id)
        assert reloaded is not None
        assert reloaded.name == "Proyecto Continuo"
        assert reloaded.n_basins == 1

        reloaded_basin = reloaded.basins[0]
        assert reloaded_basin.name == "Cuenca Única"
        assert len(reloaded_basin.tc_results) == 1

        # Agregar otro método de Tc en sesión 2
        if reloaded_basin.length_m is None:
            # Agregar longitud que faltaba
            manager._db.update_basin(reloaded_basin.id, length_m=1200)
            reloaded_basin.length_m = 1200

        tc_kirpich = kirpich(1200, reloaded_basin.slope_pct / 100)
        manager.add_tc_result(reloaded, reloaded_basin, "kirpich", tc_kirpich)

        # Verificar que se agregó
        final = manager.load_project(project_id)
        assert len(final.basins[0].tc_results) == 2


class TestDatabaseMigration:
    """Tests para migración de esquema de base de datos."""

    def test_fresh_database_has_latest_schema(self, temp_data_dir):
        """BD nueva tiene versión de esquema más reciente."""
        db = Database(temp_data_dir / "new.db")

        # Verificar versión
        with db._conn.connection() as conn:
            cursor = conn.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            )
            row = cursor.fetchone()
            assert row is not None
            version = int(row["value"])
            assert version >= 3  # Versión actual

    def test_tables_exist(self, temp_data_dir):
        """Todas las tablas necesarias existen."""
        db = Database(temp_data_dir / "tables.db")

        expected_tables = [
            "projects",
            "basins",
            "tc_results",
            "nrcs_segments",
            "weighted_coefficients",
            "coverage_items",
            "analyses",
            "storm_timeseries",
            "hydrograph_timeseries",
            "metadata",
        ]

        with db._conn.connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row["name"] for row in cursor]

            for table in expected_tables:
                assert table in tables, f"Tabla '{table}' no encontrada"
