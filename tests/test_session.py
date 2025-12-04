"""Tests para el módulo de gestión de sesiones."""

import json
import pytest
from pathlib import Path

from hidropluvial.session import (
    Session,
    SessionManager,
    CuencaConfig,
    TcResult,
    AnalysisRun,
    StormResult,
    HydrographResult,
)


@pytest.fixture
def temp_sessions_dir(tmp_path):
    """Directorio temporal para sesiones."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    return sessions_dir


@pytest.fixture
def manager(temp_sessions_dir):
    """SessionManager con directorio temporal."""
    return SessionManager(sessions_dir=temp_sessions_dir)


@pytest.fixture
def sample_cuenca_config():
    """Configuración de cuenca de ejemplo."""
    return {
        "name": "Test Session",
        "area_ha": 100.0,
        "slope_pct": 2.5,
        "p3_10": 83.0,
        "c": 0.5,
        "cn": None,
        "length_m": 1000.0,
        "cuenca_nombre": "Cuenca Test",
    }


class TestSessionManager:
    """Tests para SessionManager."""

    def test_create_session(self, manager, sample_cuenca_config):
        """Test crear una sesión nueva."""
        session = manager.create(**sample_cuenca_config)

        assert session.id is not None
        assert len(session.id) == 8
        assert session.name == "Test Session"
        assert session.cuenca.area_ha == 100.0
        assert session.cuenca.slope_pct == 2.5
        assert session.cuenca.p3_10 == 83.0
        assert session.cuenca.c == 0.5
        assert session.cuenca.cn is None
        assert session.cuenca.length_m == 1000.0

    def test_save_and_load_session(self, manager, sample_cuenca_config):
        """Test guardar y cargar sesión."""
        session = manager.create(**sample_cuenca_config)
        session_id = session.id

        # Cargar la sesión
        loaded = manager.load(session_id)

        assert loaded.id == session_id
        assert loaded.name == session.name
        assert loaded.cuenca.area_ha == session.cuenca.area_ha

    def test_load_nonexistent_session(self, manager):
        """Test cargar sesión inexistente."""
        with pytest.raises(FileNotFoundError):
            manager.load("nonexistent")

    def test_get_session_by_id(self, manager, sample_cuenca_config):
        """Test obtener sesión por ID."""
        session = manager.create(**sample_cuenca_config)

        found = manager.get_session(session.id)
        assert found is not None
        assert found.id == session.id

    def test_get_session_partial_id(self, manager, sample_cuenca_config):
        """Test obtener sesión por ID parcial."""
        session = manager.create(**sample_cuenca_config)

        # Buscar por primeros 4 caracteres
        found = manager.get_session(session.id[:4])
        assert found is not None
        assert found.id == session.id

    def test_get_session_nonexistent(self, manager):
        """Test obtener sesión inexistente retorna None."""
        found = manager.get_session("nonexistent")
        assert found is None

    def test_list_sessions(self, manager, sample_cuenca_config):
        """Test listar sesiones."""
        # Crear varias sesiones
        manager.create(**sample_cuenca_config)
        sample_cuenca_config["name"] = "Test Session 2"
        manager.create(**sample_cuenca_config)

        sessions = manager.list_sessions()
        assert len(sessions) == 2
        assert all("id" in s for s in sessions)
        assert all("name" in s for s in sessions)
        assert all("n_analyses" in s for s in sessions)

    def test_list_sessions_returns_dicts(self, manager, sample_cuenca_config):
        """Test que list_sessions retorna diccionarios, no objetos Session."""
        manager.create(**sample_cuenca_config)
        sessions = manager.list_sessions()

        assert len(sessions) == 1
        assert isinstance(sessions[0], dict)
        assert "id" in sessions[0]
        assert "n_analyses" in sessions[0]

    def test_delete_session(self, manager, sample_cuenca_config):
        """Test eliminar sesión."""
        session = manager.create(**sample_cuenca_config)
        session_id = session.id

        result = manager.delete(session_id)
        assert result is True

        # Verificar que no existe
        assert manager.get_session(session_id) is None

    def test_delete_nonexistent_session(self, manager):
        """Test eliminar sesión inexistente."""
        result = manager.delete("nonexistent")
        assert result is False

    def test_find_by_name(self, manager, sample_cuenca_config):
        """Test buscar sesión por nombre."""
        session = manager.create(**sample_cuenca_config)

        found = manager.find("Test Session")
        assert found.id == session.id

    def test_find_by_id(self, manager, sample_cuenca_config):
        """Test buscar sesión por ID."""
        session = manager.create(**sample_cuenca_config)

        found = manager.find(session.id)
        assert found.id == session.id

    def test_add_tc_result(self, manager, sample_cuenca_config):
        """Test agregar resultado de Tc."""
        session = manager.create(**sample_cuenca_config)

        result = manager.add_tc_result(
            session,
            method="kirpich",
            tc_hr=0.5,
            length_m=1000.0,
            slope=0.02,
        )

        assert result.method == "kirpich"
        assert result.tc_hr == 0.5
        assert result.tc_min == 30.0
        assert len(session.tc_results) == 1

    def test_add_tc_result_no_duplicates(self, manager, sample_cuenca_config):
        """Test que agregar Tc del mismo método reemplaza el anterior."""
        session = manager.create(**sample_cuenca_config)

        manager.add_tc_result(session, method="kirpich", tc_hr=0.5)
        manager.add_tc_result(session, method="kirpich", tc_hr=0.6)

        assert len(session.tc_results) == 1
        assert session.tc_results[0].tc_hr == 0.6

    def test_add_analysis(self, manager, sample_cuenca_config):
        """Test agregar análisis completo."""
        session = manager.create(**sample_cuenca_config)

        analysis = manager.add_analysis(
            session,
            tc_method="kirpich",
            tc_hr=0.5,
            storm_type="gz",
            return_period=10,
            duration_hr=6.0,
            total_depth_mm=100.0,
            peak_intensity_mmhr=50.0,
            n_intervals=72,
            peak_flow_m3s=5.0,
            time_to_peak_hr=1.0,
            volume_m3=10000.0,
            runoff_mm=50.0,
            x_factor=1.0,
        )

        assert analysis.id is not None
        assert analysis.tc.method == "kirpich"
        assert analysis.storm.return_period == 10
        assert analysis.hydrograph.peak_flow_m3s == 5.0
        assert len(session.analyses) == 1

    def test_get_summary_table(self, manager, sample_cuenca_config):
        """Test generar tabla resumen."""
        session = manager.create(**sample_cuenca_config)

        manager.add_analysis(
            session,
            tc_method="kirpich",
            tc_hr=0.5,
            storm_type="gz",
            return_period=10,
            duration_hr=6.0,
            total_depth_mm=100.0,
            peak_intensity_mmhr=50.0,
            n_intervals=72,
            peak_flow_m3s=5.0,
            time_to_peak_hr=1.0,
            volume_m3=10000.0,
            runoff_mm=50.0,
        )

        summary = manager.get_summary_table(session)
        assert len(summary) == 1
        assert summary[0]["tc_method"] == "kirpich"
        assert summary[0]["qpeak_m3s"] == 5.0


class TestUpdateCuenca:
    """Tests para modificación de cuenca."""

    def test_update_cuenca_in_place(self, manager, sample_cuenca_config):
        """Test actualizar cuenca en sitio."""
        session = manager.create(**sample_cuenca_config)

        changes = manager.update_cuenca_in_place(
            session,
            area_ha=150.0,
            slope_pct=3.0,
        )

        assert len(changes) == 2
        assert session.cuenca.area_ha == 150.0
        assert session.cuenca.slope_pct == 3.0

    def test_update_cuenca_clears_tc(self, manager, sample_cuenca_config):
        """Test que actualizar cuenca borra resultados de Tc."""
        session = manager.create(**sample_cuenca_config)
        manager.add_tc_result(session, method="kirpich", tc_hr=0.5)

        manager.update_cuenca_in_place(session, area_ha=150.0)

        assert len(session.tc_results) == 0

    def test_update_cuenca_clears_analyses(self, manager, sample_cuenca_config):
        """Test que actualizar cuenca borra análisis."""
        session = manager.create(**sample_cuenca_config)
        manager.add_analysis(
            session,
            tc_method="kirpich",
            tc_hr=0.5,
            storm_type="gz",
            return_period=10,
            duration_hr=6.0,
            total_depth_mm=100.0,
            peak_intensity_mmhr=50.0,
            n_intervals=72,
            peak_flow_m3s=5.0,
            time_to_peak_hr=1.0,
            volume_m3=10000.0,
            runoff_mm=50.0,
        )

        changes = manager.update_cuenca_in_place(session, area_ha=150.0)

        assert len(session.analyses) == 0
        assert "eliminados 1 análisis" in changes[-1]

    def test_clone_with_modified_cuenca(self, manager, sample_cuenca_config):
        """Test clonar sesión con datos modificados."""
        session = manager.create(**sample_cuenca_config)

        new_session, changes = manager.clone_with_modified_cuenca(
            session,
            new_name="Cloned Session",
            area_ha=200.0,
        )

        assert new_session.id != session.id
        assert new_session.name == "Cloned Session"
        assert new_session.cuenca.area_ha == 200.0
        assert session.cuenca.area_ha == 100.0  # Original sin cambios
        assert len(changes) == 1


class TestCuencaConfig:
    """Tests para CuencaConfig."""

    def test_cuenca_config_with_c(self):
        """Test config con coeficiente C."""
        config = CuencaConfig(
            nombre="Test",
            area_ha=100.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
        )
        assert config.c == 0.5
        assert config.cn is None

    def test_cuenca_config_with_cn(self):
        """Test config con Curve Number."""
        config = CuencaConfig(
            nombre="Test",
            area_ha=100.0,
            slope_pct=2.0,
            p3_10=83.0,
            cn=75,
        )
        assert config.cn == 75
        assert config.c is None


class TestTcResult:
    """Tests para TcResult."""

    def test_tc_result_conversion(self):
        """Test conversión hr a min."""
        result = TcResult(method="test", tc_hr=1.5, tc_min=90.0)
        assert result.tc_hr == 1.5
        assert result.tc_min == 90.0


class TestAnalysisRun:
    """Tests para AnalysisRun."""

    def test_analysis_run_creation(self):
        """Test creación de análisis."""
        tc = TcResult(method="kirpich", tc_hr=0.5, tc_min=30.0)
        storm = StormResult(
            type="gz",
            return_period=10,
            duration_hr=6.0,
            total_depth_mm=100.0,
            peak_intensity_mmhr=50.0,
            n_intervals=72,
        )
        hydro = HydrographResult(
            tc_method="kirpich",
            tc_min=30.0,
            storm_type="gz",
            return_period=10,
            peak_flow_m3s=5.0,
            time_to_peak_hr=1.0,
            time_to_peak_min=60.0,
            volume_m3=10000.0,
            total_depth_mm=100.0,
            runoff_mm=50.0,
        )

        analysis = AnalysisRun(tc=tc, storm=storm, hydrograph=hydro)

        assert analysis.id is not None
        assert analysis.timestamp is not None
        assert analysis.tc.method == "kirpich"
