"""
Tests para comandos CLI de sesión (cli/session/base.py).

Usa typer.testing.CliRunner para simular invocaciones CLI.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from hidropluvial.session import SessionManager, Session
from hidropluvial.cli.session.base import (
    get_session_manager,
    session_create,
    session_list,
    session_show,
    session_tc,
    session_summary,
    session_delete,
    session_edit,
    _session_manager,
)


@pytest.fixture
def temp_sessions_dir(tmp_path):
    """Directorio temporal para sesiones."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    return sessions_dir


@pytest.fixture
def temp_manager(temp_sessions_dir):
    """SessionManager con directorio temporal."""
    return SessionManager(sessions_dir=temp_sessions_dir)


@pytest.fixture
def sample_session(temp_manager):
    """Sesión de ejemplo."""
    return temp_manager.create(
        name="Test Session",
        area_ha=100.0,
        slope_pct=2.5,
        p3_10=83.0,
        c=0.5,
        cn=75,
        length_m=1000.0,
        cuenca_nombre="Cuenca Test",
    )


@pytest.fixture
def mock_manager(temp_manager):
    """Parchea get_session_manager para usar directorio temporal."""
    import hidropluvial.cli.session.base as base_module
    original = base_module._session_manager
    base_module._session_manager = temp_manager
    yield temp_manager
    base_module._session_manager = original


class TestGetSessionManager:
    """Tests para get_session_manager."""

    def test_returns_session_manager(self):
        """Test que retorna un SessionManager."""
        import hidropluvial.cli.session.base as base_module
        original = base_module._session_manager
        base_module._session_manager = None  # Reset

        try:
            manager = get_session_manager()
            assert isinstance(manager, SessionManager)
        finally:
            base_module._session_manager = original

    def test_returns_same_instance(self):
        """Test que retorna la misma instancia (singleton)."""
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        assert manager1 is manager2


class TestSessionCreate:
    """Tests para session_create."""

    def test_creates_session(self, mock_manager, capsys):
        """Test crear sesión exitosamente."""
        session_create(
            name="Nueva Sesion",
            area_ha=50.0,
            slope_pct=3.0,
            p3_10=80.0,
            c=0.6,
            cn=None,
            length_m=500.0,
            cuenca_nombre="Mi Cuenca",
        )

        captured = capsys.readouterr()
        assert "SESION CREADA" in captured.out
        assert "Nueva Sesion" in captured.out
        assert "50.00 ha" in captured.out

        # Verificar que se guardó
        sessions = mock_manager.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["name"] == "Nueva Sesion"

    def test_creates_session_minimal(self, mock_manager, capsys):
        """Test crear sesión con parámetros mínimos."""
        session_create(
            name="Minimal",
            area_ha=10.0,
            slope_pct=1.0,
            p3_10=70.0,
            c=None,
            cn=None,
            length_m=None,
            cuenca_nombre="",
        )

        captured = capsys.readouterr()
        assert "SESION CREADA" in captured.out

    def test_creates_session_with_cn(self, mock_manager, capsys):
        """Test crear sesión con CN."""
        session_create(
            name="CN Session",
            area_ha=50.0,
            slope_pct=3.0,
            p3_10=80.0,
            c=None,
            cn=75,
            length_m=None,
            cuenca_nombre="",
        )

        captured = capsys.readouterr()
        assert "CN:" in captured.out
        assert "75" in captured.out


class TestSessionList:
    """Tests para session_list."""

    def test_list_empty(self, mock_manager, capsys):
        """Test listar cuando no hay sesiones."""
        session_list()

        captured = capsys.readouterr()
        assert "No hay sesiones guardadas" in captured.out

    def test_list_with_sessions(self, mock_manager, sample_session, capsys):
        """Test listar sesiones existentes."""
        session_list()

        captured = capsys.readouterr()
        assert "SESIONES DISPONIBLES" in captured.out
        assert "Test Session" in captured.out

    def test_list_multiple_sessions(self, mock_manager, capsys):
        """Test listar múltiples sesiones."""
        mock_manager.create(
            name="Session 1",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=80.0,
        )
        mock_manager.create(
            name="Session 2",
            area_ha=75.0,
            slope_pct=3.0,
            p3_10=85.0,
        )

        session_list()

        captured = capsys.readouterr()
        assert "Session 1" in captured.out
        assert "Session 2" in captured.out


class TestSessionShow:
    """Tests para session_show."""

    def test_show_existing_session(self, mock_manager, sample_session, capsys):
        """Test mostrar sesión existente."""
        session_show(sample_session.id)

        captured = capsys.readouterr()
        assert "SESION: Test Session" in captured.out
        assert "100.00 ha" in captured.out
        assert "2.50 %" in captured.out
        assert "83.0 mm" in captured.out

    def test_show_session_by_name(self, mock_manager, sample_session, capsys):
        """Test mostrar sesión por nombre."""
        session_show("Test Session")

        captured = capsys.readouterr()
        assert "SESION: Test Session" in captured.out

    def test_show_nonexistent_session(self, mock_manager, capsys):
        """Test mostrar sesión inexistente."""
        import typer
        with pytest.raises(typer.Exit):
            session_show("nonexistent")

        captured = capsys.readouterr()
        assert "no encontrada" in captured.err

    def test_show_with_tc_results(self, mock_manager, sample_session, capsys):
        """Test mostrar sesión con resultados de Tc."""
        mock_manager.add_tc_result(sample_session, "kirpich", 0.5)

        session_show(sample_session.id)

        captured = capsys.readouterr()
        assert "TIEMPOS DE CONCENTRACION" in captured.out
        assert "kirpich" in captured.out

    def test_show_with_analyses(self, mock_manager, sample_session, capsys):
        """Test mostrar sesión con análisis."""
        mock_manager.add_analysis(
            sample_session,
            tc_method="desbordes",
            tc_hr=0.4,
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
            x_factor=1.25,
        )

        session_show(sample_session.id)

        captured = capsys.readouterr()
        assert "ANALISIS REALIZADOS: 1" in captured.out
        assert "desbordes" in captured.out


class TestSessionTc:
    """Tests para session_tc."""

    def test_tc_desbordes(self, mock_manager, sample_session, capsys):
        """Test calcular Tc con método desbordes."""
        session_tc(sample_session.id, methods="desbordes")

        captured = capsys.readouterr()
        assert "CALCULO DE TIEMPOS DE CONCENTRACION" in captured.out
        assert "desbordes" in captured.out
        assert "min" in captured.out

    def test_tc_kirpich(self, mock_manager, sample_session, capsys):
        """Test calcular Tc con método Kirpich."""
        session_tc(sample_session.id, methods="kirpich")

        captured = capsys.readouterr()
        assert "kirpich" in captured.out

    def test_tc_multiple_methods(self, mock_manager, sample_session, capsys):
        """Test calcular Tc con múltiples métodos."""
        session_tc(sample_session.id, methods="kirpich,desbordes")

        captured = capsys.readouterr()
        assert "kirpich" in captured.out
        assert "desbordes" in captured.out

    def test_tc_method_requires_length(self, mock_manager, capsys):
        """Test método que requiere longitud sin tenerla."""
        session = mock_manager.create(
            name="No Length",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=80.0,
            c=0.5,
            length_m=None,  # Sin longitud
        )

        session_tc(session.id, methods="kirpich")

        captured = capsys.readouterr()
        assert "Requiere longitud" in captured.err or "ERROR" in captured.out

    def test_tc_desbordes_requires_c(self, mock_manager, capsys):
        """Test desbordes requiere coeficiente C."""
        session = mock_manager.create(
            name="No C",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=80.0,
            c=None,  # Sin C
        )

        session_tc(session.id, methods="desbordes")

        captured = capsys.readouterr()
        assert "Requiere coeficiente C" in captured.err or "ERROR" in captured.out

    def test_tc_unknown_method(self, mock_manager, sample_session, capsys):
        """Test método desconocido."""
        session_tc(sample_session.id, methods="unknown_method")

        captured = capsys.readouterr()
        assert "desconocido" in captured.err or "ERROR" in captured.out

    def test_tc_nonexistent_session(self, mock_manager, capsys):
        """Test Tc para sesión inexistente."""
        import typer
        with pytest.raises(typer.Exit):
            session_tc("nonexistent")


class TestSessionSummary:
    """Tests para session_summary."""

    def test_summary_no_analyses(self, mock_manager, sample_session, capsys):
        """Test resumen sin análisis."""
        session_summary(sample_session.id)

        captured = capsys.readouterr()
        assert "No hay análisis" in captured.out

    def test_summary_with_analyses(self, mock_manager, sample_session, capsys):
        """Test resumen con análisis."""
        mock_manager.add_analysis(
            sample_session,
            tc_method="desbordes",
            tc_hr=0.4,
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

        session_summary(sample_session.id)

        captured = capsys.readouterr()
        assert "RESUMEN COMPARATIVO" in captured.out
        assert "desbordes" in captured.out
        assert "5.000" in captured.out  # peak flow

    def test_summary_multiple_analyses(self, mock_manager, sample_session, capsys):
        """Test resumen con múltiples análisis muestra max/min."""
        # Agregar dos análisis con diferentes caudales
        mock_manager.add_analysis(
            sample_session,
            tc_method="desbordes",
            tc_hr=0.4,
            storm_type="gz",
            return_period=10,
            duration_hr=6.0,
            total_depth_mm=100.0,
            peak_intensity_mmhr=50.0,
            n_intervals=72,
            peak_flow_m3s=3.0,
            time_to_peak_hr=1.0,
            volume_m3=10000.0,
            runoff_mm=50.0,
        )
        mock_manager.add_analysis(
            sample_session,
            tc_method="kirpich",
            tc_hr=0.5,
            storm_type="blocks",
            return_period=25,
            duration_hr=2.0,
            total_depth_mm=120.0,
            peak_intensity_mmhr=60.0,
            n_intervals=24,
            peak_flow_m3s=8.0,
            time_to_peak_hr=1.2,
            volume_m3=15000.0,
            runoff_mm=60.0,
        )

        session_summary(sample_session.id)

        captured = capsys.readouterr()
        assert "Caudal máximo" in captured.out
        assert "Caudal mínimo" in captured.out
        assert "Variación" in captured.out

    def test_summary_nonexistent_session(self, mock_manager, capsys):
        """Test resumen para sesión inexistente."""
        import typer
        with pytest.raises(typer.Exit):
            session_summary("nonexistent")


class TestSessionDelete:
    """Tests para session_delete."""

    def test_delete_with_force(self, mock_manager, sample_session, capsys):
        """Test eliminar con --force."""
        session_id = sample_session.id
        session_delete(session_id, force=True)

        captured = capsys.readouterr()
        assert "eliminada" in captured.out

        # Verificar que se eliminó
        assert mock_manager.get_session(session_id) is None

    def test_delete_nonexistent(self, mock_manager, capsys):
        """Test eliminar sesión inexistente."""
        import typer
        with pytest.raises(typer.Exit):
            session_delete("nonexistent", force=True)


class TestSessionEdit:
    """Tests para session_edit."""

    def test_edit_area(self, mock_manager, sample_session, capsys, monkeypatch):
        """Test editar área."""
        # Simular confirmación
        monkeypatch.setattr('typer.confirm', lambda x: True)

        session_edit(
            sample_session.id,
            area_ha=150.0,
            slope_pct=None,
            p3_10=None,
            c=None,
            cn=None,
            length_m=None,
            clone=False,
            new_name=None,
        )

        captured = capsys.readouterr()
        assert "actualizada" in captured.out

        # Verificar cambio
        updated = mock_manager.load(sample_session.id)
        assert updated.cuenca.area_ha == 150.0

    def test_edit_multiple_params(self, mock_manager, sample_session, capsys, monkeypatch):
        """Test editar múltiples parámetros."""
        monkeypatch.setattr('typer.confirm', lambda x: True)

        session_edit(
            sample_session.id,
            area_ha=200.0,
            slope_pct=4.0,
            p3_10=90.0,
            c=0.7,
            cn=None,
            length_m=None,
            clone=False,
            new_name=None,
        )

        updated = mock_manager.load(sample_session.id)
        assert updated.cuenca.area_ha == 200.0
        assert updated.cuenca.slope_pct == 4.0
        assert updated.cuenca.p3_10 == 90.0
        assert updated.cuenca.c == 0.7

    def test_edit_clone_mode(self, mock_manager, sample_session, capsys, monkeypatch):
        """Test editar en modo clone."""
        monkeypatch.setattr('typer.confirm', lambda x: True)

        session_edit(
            sample_session.id,
            area_ha=150.0,
            slope_pct=None,
            p3_10=None,
            c=None,
            cn=None,
            length_m=None,
            clone=True,
            new_name="Cloned Session",
        )

        captured = capsys.readouterr()
        assert "Nueva sesión creada" in captured.out

        # Original sin cambios
        original = mock_manager.load(sample_session.id)
        assert original.cuenca.area_ha == 100.0

        # Nueva sesión existe
        sessions = mock_manager.list_sessions()
        assert len(sessions) == 2

    def test_edit_no_params_error(self, mock_manager, sample_session, capsys):
        """Test error si no hay parámetros a editar."""
        import typer
        with pytest.raises(typer.Exit):
            session_edit(
                sample_session.id,
                area_ha=None,
                slope_pct=None,
                p3_10=None,
                c=None,
                cn=None,
                length_m=None,
                clone=False,
                new_name=None,
            )

        captured = capsys.readouterr()
        assert "especificar al menos un parámetro" in captured.out

    def test_edit_nonexistent_session(self, mock_manager, capsys):
        """Test editar sesión inexistente."""
        import typer
        with pytest.raises(typer.Exit):
            session_edit(
                "nonexistent",
                area_ha=150.0,
                slope_pct=None,
                p3_10=None,
                c=None,
                cn=None,
                length_m=None,
                clone=False,
                new_name=None,
            )

    def test_edit_cancelled(self, mock_manager, sample_session, capsys, monkeypatch):
        """Test edición cancelada por usuario."""
        monkeypatch.setattr('typer.confirm', lambda x: False)

        import typer
        with pytest.raises(typer.Exit):
            session_edit(
                sample_session.id,
                area_ha=150.0,
                slope_pct=None,
                p3_10=None,
                c=None,
                cn=None,
                length_m=None,
                clone=False,
                new_name=None,
            )

        # Sin cambios
        original = mock_manager.load(sample_session.id)
        assert original.cuenca.area_ha == 100.0
