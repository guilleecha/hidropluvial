"""Tests para el módulo wizard y sus componentes."""

import pytest
from unittest.mock import patch, MagicMock

from hidropluvial.session import Session, SessionManager, CuencaConfig, TcResult
from hidropluvial.cli.wizard.menus import PostExecutionMenu, continue_session_menu
from hidropluvial.cli.wizard.runner import AdditionalAnalysisRunner


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
def sample_session(manager):
    """Sesión de ejemplo con datos completos."""
    session = manager.create(
        name="Test Session",
        area_ha=100.0,
        slope_pct=2.5,
        p3_10=83.0,
        c=0.5,
        cn=None,
        length_m=1000.0,
    )
    # Agregar resultado de Tc
    manager.add_tc_result(session, method="desbordes", tc_hr=0.75)
    return session


@pytest.fixture
def sample_session_cn(manager):
    """Sesión de ejemplo con CN en lugar de C."""
    session = manager.create(
        name="Test Session CN",
        area_ha=50.0,
        slope_pct=3.0,
        p3_10=83.0,
        c=None,
        cn=75,
        length_m=800.0,
    )
    manager.add_tc_result(session, method="kirpich", tc_hr=0.5)
    return session


class TestPostExecutionMenu:
    """Tests para PostExecutionMenu."""

    def test_init_with_explicit_values(self, sample_session):
        """Test inicialización con valores explícitos."""
        menu = PostExecutionMenu(
            session=sample_session,
            c=0.6,
            cn=80,
            length=1500.0,
        )

        assert menu.c == 0.6
        assert menu.cn == 80
        assert menu.length == 1500.0

    def test_init_fallback_to_session_values(self, sample_session):
        """Test que usa valores de sesión cuando no se pasan."""
        menu = PostExecutionMenu(session=sample_session)

        assert menu.c == sample_session.cuenca.c
        assert menu.cn == sample_session.cuenca.cn
        assert menu.length == sample_session.cuenca.length_m

    def test_init_with_c_session(self, sample_session):
        """Test con sesión que tiene coeficiente C."""
        menu = PostExecutionMenu(session=sample_session)

        assert menu.c == 0.5
        assert menu.cn is None
        assert menu.length == 1000.0

    def test_init_with_cn_session(self, sample_session_cn):
        """Test con sesión que tiene Curve Number."""
        menu = PostExecutionMenu(session=sample_session_cn)

        assert menu.c is None
        assert menu.cn == 75
        assert menu.length == 800.0

    def test_init_partial_override(self, sample_session):
        """Test override parcial de valores."""
        menu = PostExecutionMenu(
            session=sample_session,
            c=0.7,  # Override
            # cn y length no se pasan, deben venir de la sesión
        )

        assert menu.c == 0.7  # Override
        assert menu.cn is None  # De sesión
        assert menu.length == 1000.0  # De sesión

    def test_manager_initialized(self, sample_session):
        """Test que el manager se inicializa."""
        menu = PostExecutionMenu(session=sample_session)

        assert menu.manager is not None
        assert isinstance(menu.manager, SessionManager)


class TestAdditionalAnalysisRunner:
    """Tests para AdditionalAnalysisRunner."""

    def test_init(self, sample_session):
        """Test inicialización del runner."""
        runner = AdditionalAnalysisRunner(
            session=sample_session,
            c=0.5,
            cn=None,
        )

        assert runner.session == sample_session
        assert runner.c == 0.5
        assert runner.cn is None

    def test_run_with_c(self, sample_session):
        """Test ejecutar análisis con coeficiente C."""
        runner = AdditionalAnalysisRunner(
            session=sample_session,
            c=0.5,
        )

        n_added = runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0],
        )

        assert n_added == 1
        assert len(sample_session.analyses) == 1
        assert sample_session.analyses[0].storm.type == "gz"
        assert sample_session.analyses[0].storm.return_period == 10

    def test_run_with_cn(self, sample_session_cn):
        """Test ejecutar análisis con Curve Number."""
        runner = AdditionalAnalysisRunner(
            session=sample_session_cn,
            cn=75,
        )

        n_added = runner.run(
            tc_methods=["kirpich"],
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0],
        )

        assert n_added == 1
        assert len(sample_session_cn.analyses) == 1

    def test_run_multiple_return_periods(self, sample_session):
        """Test múltiples períodos de retorno."""
        runner = AdditionalAnalysisRunner(
            session=sample_session,
            c=0.5,
        )

        n_added = runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[2, 10, 25],
            x_factors=[1.0],
        )

        assert n_added == 3
        assert len(sample_session.analyses) == 3
        trs = [a.storm.return_period for a in sample_session.analyses]
        assert sorted(trs) == [2, 10, 25]

    def test_run_multiple_x_factors(self, sample_session):
        """Test múltiples factores X."""
        runner = AdditionalAnalysisRunner(
            session=sample_session,
            c=0.5,
        )

        n_added = runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0, 1.25],
        )

        assert n_added == 2
        x_vals = [a.hydrograph.x_factor for a in sample_session.analyses]
        assert sorted(x_vals) == [1.0, 1.25]

    def test_run_blocks24_storm(self, sample_session):
        """Test tormenta blocks24."""
        runner = AdditionalAnalysisRunner(
            session=sample_session,
            c=0.5,
        )

        n_added = runner.run(
            tc_methods=["desbordes"],
            storm_code="blocks24",
            return_periods=[10],
            x_factors=[1.0],
        )

        assert n_added == 1
        # blocks24 usa duración de 24 horas
        assert sample_session.analyses[0].storm.duration_hr == 24.0

    def test_run_bimodal_storm(self, sample_session):
        """Test tormenta bimodal."""
        runner = AdditionalAnalysisRunner(
            session=sample_session,
            c=0.5,
        )

        n_added = runner.run(
            tc_methods=["desbordes"],
            storm_code="bimodal",
            return_periods=[10],
            x_factors=[1.0],
        )

        assert n_added == 1
        assert sample_session.analyses[0].storm.type == "bimodal"

    def test_run_without_c_or_cn_skips(self, sample_session):
        """Test que sin C ni CN no agrega análisis."""
        runner = AdditionalAnalysisRunner(
            session=sample_session,
            c=None,
            cn=None,
        )

        n_added = runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0],
        )

        assert n_added == 0
        assert len(sample_session.analyses) == 0

    def test_run_wrong_tc_method_skips(self, sample_session):
        """Test que método de Tc no existente no agrega análisis."""
        runner = AdditionalAnalysisRunner(
            session=sample_session,
            c=0.5,
        )

        n_added = runner.run(
            tc_methods=["kirpich"],  # La sesión solo tiene desbordes
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0],
        )

        assert n_added == 0

    def test_run_stores_time_series(self, sample_session):
        """Test que guarda series temporales."""
        runner = AdditionalAnalysisRunner(
            session=sample_session,
            c=0.5,
        )

        runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0],
        )

        analysis = sample_session.analyses[0]
        # Debe tener series temporales
        assert len(analysis.storm.time_min) > 0
        assert len(analysis.storm.intensity_mmhr) > 0
        assert len(analysis.hydrograph.time_hr) > 0
        assert len(analysis.hydrograph.flow_m3s) > 0


class TestContinueSessionMenu:
    """Tests para continue_session_menu."""

    def test_no_sessions_shows_message(self, manager, capsys):
        """Test mensaje cuando no hay sesiones."""
        with patch(
            "hidropluvial.cli.wizard.menus.get_session_manager",
            return_value=manager,
        ):
            continue_session_menu()

        captured = capsys.readouterr()
        assert "No hay sesiones guardadas" in captured.out

    def test_sessions_listed_correctly(self, manager, sample_session):
        """Test que las sesiones se listan como diccionarios."""
        sessions = manager.list_sessions()

        assert len(sessions) == 1
        assert isinstance(sessions[0], dict)
        assert sessions[0]["id"] == sample_session.id
        assert sessions[0]["name"] == "Test Session"
        assert sessions[0]["n_analyses"] == 0


class TestIntegrationFlow:
    """Tests de integración para flujos completos."""

    def test_create_session_add_tc_add_analysis(self, manager):
        """Test flujo completo: crear sesión, agregar Tc, agregar análisis."""
        # 1. Crear sesión
        session = manager.create(
            name="Integration Test",
            area_ha=100.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
        )

        # 2. Agregar Tc
        manager.add_tc_result(session, method="desbordes", tc_hr=0.8)

        # 3. Agregar análisis via runner
        runner = AdditionalAnalysisRunner(session, c=0.5)
        n_added = runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[2, 10],
            x_factors=[1.0, 1.25],
        )

        # Verificar en el objeto session (en memoria)
        assert n_added == 4  # 2 TR × 2 X
        assert len(session.analyses) == 4

        # 4. Guardar y verificar persistencia
        # Nota: El runner usa su propio manager, así que guardamos con nuestro manager
        manager.save(session)
        loaded = manager.load(session.id)
        assert len(loaded.analyses) == 4

    def test_continue_session_preserves_values(self, manager):
        """Test que continuar sesión preserva C/CN/length."""
        # Crear sesión con valores específicos
        session = manager.create(
            name="Continue Test",
            area_ha=200.0,
            slope_pct=3.0,
            p3_10=85.0,
            c=0.62,
            cn=None,
            length_m=1200.0,
        )

        # Simular "continuar sesión" - crear PostExecutionMenu sin pasar valores
        menu = PostExecutionMenu(session=session)

        # Verificar que los valores vienen de la sesión
        assert menu.c == 0.62
        assert menu.cn is None
        assert menu.length == 1200.0

        # El runner debería poder usar estos valores
        manager.add_tc_result(session, method="desbordes", tc_hr=0.7)
        runner = AdditionalAnalysisRunner(session, c=menu.c, cn=menu.cn)
        n_added = runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0],
        )

        assert n_added == 1
