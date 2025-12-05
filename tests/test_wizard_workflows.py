"""Tests para flujos de trabajo completos del wizard."""

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass

from hidropluvial.session import Session, SessionManager, CuencaConfig, TcResult
from hidropluvial.project import Project, Basin, ProjectManager, get_project_manager
from hidropluvial.cli.wizard.config import WizardConfig
from hidropluvial.cli.wizard.runner import AnalysisRunner, AdditionalAnalysisRunner
from hidropluvial.cli.wizard.steps import (
    WizardState,
    WizardNavigator,
    StepResult,
    StepNombre,
    StepDatosCuenca,
    StepMetodoEscorrentia,
    StepLongitud,
    StepMetodosTc,
    StepTormenta,
    StepSalida,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_sessions_dir(tmp_path):
    """Directorio temporal para sesiones."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    return sessions_dir


@pytest.fixture
def temp_projects_dir(tmp_path):
    """Directorio temporal para proyectos."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()
    return projects_dir


@pytest.fixture
def session_manager(temp_sessions_dir):
    """SessionManager con directorio temporal."""
    return SessionManager(sessions_dir=temp_sessions_dir)


@pytest.fixture
def project_manager(temp_projects_dir):
    """ProjectManager con directorio temporal."""
    return ProjectManager(data_dir=temp_projects_dir)


@pytest.fixture(autouse=True)
def mock_managers(session_manager, project_manager):
    """Mock managers globales para usar directorios temporales."""
    with patch(
        "hidropluvial.cli.wizard.runner.get_session_manager",
        return_value=session_manager,
    ), patch(
        "hidropluvial.cli.wizard.runner.get_project_manager",
        return_value=project_manager,
    ), patch(
        "hidropluvial.cli.wizard.menus.base.get_session_manager",
        return_value=session_manager,
    ), patch(
        "hidropluvial.project.get_project_manager",
        return_value=project_manager,
    ):
        yield {"session": session_manager, "project": project_manager}


# ============================================================================
# Tests para WizardState
# ============================================================================


class TestWizardState:
    """Tests para el estado del wizard."""

    def test_initial_state(self):
        """Test estado inicial del wizard."""
        state = WizardState()

        assert state.nombre == ""
        assert state.area_ha == 0.0
        assert state.slope_pct == 0.0
        assert state.p3_10 == 0.0
        assert state.c is None
        assert state.cn is None
        assert state.length_m is None
        assert state.amc == "II"
        assert state.lambda_coef == 0.2
        assert state.t0_min == 5.0
        assert state.tc_methods == []
        assert state.storm_codes == ["gz"]  # Default
        assert state.return_periods == []
        assert state.x_factors == [1.0]  # Default

    def test_state_modification(self):
        """Test modificación del estado."""
        state = WizardState()

        state.nombre = "Cuenca Test"
        state.area_ha = 100.0
        state.slope_pct = 2.5
        state.p3_10 = 83.0
        state.c = 0.6
        state.cn = 75
        state.length_m = 1000.0
        state.amc = "III"
        state.lambda_coef = 0.05
        state.t0_min = 3.0
        state.tc_methods = ["Desbordes", "Kirpich"]
        state.storm_codes = ["gz", "blocks"]
        state.return_periods = [2, 10, 25]
        state.x_factors = [1.0, 1.25]

        assert state.nombre == "Cuenca Test"
        assert state.area_ha == 100.0
        assert state.c == 0.6
        assert state.cn == 75
        assert state.amc == "III"
        assert len(state.tc_methods) == 2
        assert len(state.return_periods) == 3


# ============================================================================
# Tests para WizardConfig
# ============================================================================


class TestWizardConfig:
    """Tests para la configuración del wizard."""

    def test_config_defaults(self):
        """Test valores por defecto de configuración."""
        config = WizardConfig()

        assert config.nombre == ""
        assert config.area_ha == 0.0
        assert config.c is None
        assert config.cn is None
        assert config.amc == "II"
        assert config.lambda_coef == 0.2
        assert config.t0_min == 5.0
        assert config.storm_codes == ["gz"]
        assert config.x_factors == [1.0]

    def test_config_with_values(self):
        """Test configuración con valores específicos."""
        config = WizardConfig(
            nombre="Cuenca Las Piedras",
            area_ha=62.0,
            slope_pct=3.41,
            p3_10=78.0,
            c=0.62,
            cn=None,
            length_m=800.0,
            amc="II",
            lambda_coef=0.2,
            t0_min=5.0,
            tc_methods=["Desbordes", "Kirpich"],
            storm_codes=["gz"],
            return_periods=[2, 10, 25],
            x_factors=[1.0, 1.25],
        )

        assert config.nombre == "Cuenca Las Piedras"
        assert config.area_ha == 62.0
        assert config.c == 0.62
        assert config.cn is None
        assert len(config.tc_methods) == 2
        assert len(config.return_periods) == 3

    def test_get_n_combinations_simple(self):
        """Test cálculo de combinaciones simple."""
        config = WizardConfig(
            tc_methods=["Desbordes"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        assert config.get_n_combinations() == 1

    def test_get_n_combinations_multiple(self):
        """Test cálculo de combinaciones múltiples."""
        config = WizardConfig(
            tc_methods=["Desbordes", "Kirpich"],
            storm_codes=["gz"],
            return_periods=[2, 10, 25],
            x_factors=[1.0, 1.25],
        )

        # 2 Tc × 3 Tr × 1 tormenta × 2 X = 12
        assert config.get_n_combinations() == 12

    def test_get_n_combinations_mixed_storms(self):
        """Test combinaciones con tormentas mixtas."""
        config = WizardConfig(
            tc_methods=["Desbordes"],
            storm_codes=["gz", "blocks"],
            return_periods=[10],
            x_factors=[1.0, 1.25],
        )

        # 1 Tc × 1 Tr × (1 GZ × 2 X + 1 blocks × 1) = 3
        assert config.get_n_combinations() == 3


# ============================================================================
# Tests para AnalysisRunner
# ============================================================================


class TestAnalysisRunner:
    """Tests para el ejecutor de análisis."""

    def test_runner_with_c_method(self, mock_managers):
        """Test runner con método racional (coeficiente C)."""
        config = WizardConfig(
            nombre="Test Cuenca C",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            cn=None,
            length_m=None,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        assert project is not None
        assert basin is not None
        assert basin.name == "Test Cuenca C"
        assert basin.area_ha == 50.0
        assert basin.c == 0.5
        assert len(basin.analyses) >= 1

    def test_runner_with_cn_method(self, mock_managers):
        """Test runner con método SCS-CN."""
        config = WizardConfig(
            nombre="Test Cuenca CN",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=None,
            cn=75,
            length_m=1000.0,
            amc="II",
            lambda_coef=0.2,
            tc_methods=["Kirpich (cuencas rurales)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        assert project is not None
        assert basin is not None
        assert basin.cn == 75
        assert len(basin.analyses) >= 1

    def test_runner_with_both_methods(self, mock_managers):
        """Test runner con ambos métodos (C y CN)."""
        config = WizardConfig(
            nombre="Test Cuenca Ambos",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            cn=75,
            length_m=1000.0,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        assert basin.c == 0.5
        assert basin.cn == 75
        # Debería tener análisis con ambos métodos
        assert len(basin.analyses) >= 2

    def test_runner_multiple_tc_methods(self, mock_managers):
        """Test runner con múltiples métodos de Tc."""
        config = WizardConfig(
            nombre="Test Multi Tc",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            cn=None,
            length_m=1000.0,
            t0_min=5.0,
            tc_methods=[
                "Desbordes (recomendado cuencas urbanas)",
                "Kirpich (cuencas rurales)",
            ],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        # Debería tener resultados de Tc para ambos métodos
        tc_methods = {tc.method for tc in basin.tc_results}
        assert "desbordes" in tc_methods
        assert "kirpich" in tc_methods

    def test_runner_multiple_return_periods(self, mock_managers):
        """Test runner con múltiples períodos de retorno."""
        config = WizardConfig(
            nombre="Test Multi Tr",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            cn=None,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[2, 10, 25],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        # Debería tener análisis para cada Tr
        trs = {a.storm.return_period for a in basin.analyses}
        assert trs == {2, 10, 25}

    def test_runner_creates_project(self, mock_managers):
        """Test que el runner crea un proyecto."""
        config = WizardConfig(
            nombre="Test Proyecto",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        assert project is not None
        assert project.id is not None
        assert len(project.basins) == 1
        assert project.basins[0].id == basin.id

    def test_runner_uses_existing_project(self, mock_managers):
        """Test que el runner usa un proyecto existente."""
        project_manager = mock_managers["project"]

        # Crear proyecto existente
        existing_project = project_manager.create_project(
            name="Proyecto Existente",
            description="Test",
        )

        config = WizardConfig(
            nombre="Nueva Cuenca",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config, project_id=existing_project.id)
        project, basin = runner.run()

        assert project.id == existing_project.id
        assert len(project.basins) == 1


# ============================================================================
# Tests para AdditionalAnalysisRunner
# ============================================================================


class TestAdditionalAnalysisRunnerWorkflow:
    """Tests para agregar análisis adicionales."""

    def test_add_analyses_to_session(self, session_manager):
        """Test agregar análisis a sesión existente."""
        # Crear sesión
        session = session_manager.create(
            name="Test Session",
            area_ha=100.0,
            slope_pct=2.5,
            p3_10=83.0,
            c=0.5,
            cn=None,
            length_m=1000.0,
        )
        session_manager.add_tc_result(session, method="desbordes", tc_hr=0.75)

        # Agregar análisis
        runner = AdditionalAnalysisRunner(session, c=0.5)
        n_added = runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[10, 25],
            x_factors=[1.0],
        )

        assert n_added == 2
        assert len(session.analyses) == 2

    def test_add_analyses_with_different_storms(self, session_manager):
        """Test agregar análisis con diferentes tormentas."""
        session = session_manager.create(
            name="Test Storm Types",
            area_ha=100.0,
            slope_pct=2.5,
            p3_10=83.0,
            c=0.5,
        )
        session_manager.add_tc_result(session, method="desbordes", tc_hr=0.75)

        runner = AdditionalAnalysisRunner(session, c=0.5)

        # Agregar GZ
        n_gz = runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0],
        )

        # Agregar Bimodal
        n_bimodal = runner.run(
            tc_methods=["desbordes"],
            storm_code="bimodal",
            return_periods=[10],
            x_factors=[1.0],
        )

        assert n_gz == 1
        assert n_bimodal == 1
        assert len(session.analyses) == 2

        storm_types = {a.storm.type for a in session.analyses}
        assert "gz" in storm_types
        assert "bimodal" in storm_types

    def test_add_analyses_with_cn(self, session_manager):
        """Test agregar análisis con método CN."""
        session = session_manager.create(
            name="Test CN",
            area_ha=100.0,
            slope_pct=2.5,
            p3_10=83.0,
            c=None,
            cn=75,
            length_m=1000.0,
        )
        session_manager.add_tc_result(session, method="kirpich", tc_hr=0.5)

        runner = AdditionalAnalysisRunner(
            session,
            cn=75,
            amc="II",
            lambda_coef=0.2,
        )
        n_added = runner.run(
            tc_methods=["kirpich"],
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0],
        )

        assert n_added == 1


# ============================================================================
# Tests para flujos de trabajo completos
# ============================================================================


class TestCompleteWorkflows:
    """Tests de integración para flujos completos."""

    def test_workflow_nueva_cuenca_con_c(self, mock_managers):
        """Test flujo completo: nueva cuenca con coeficiente C."""
        config = WizardConfig(
            nombre="Cuenca Las Piedras",
            area_ha=62.0,
            slope_pct=3.41,
            p3_10=78.0,
            c=0.62,
            cn=None,
            length_m=800.0,
            t0_min=5.0,
            tc_methods=[
                "Desbordes (recomendado cuencas urbanas)",
                "Kirpich (cuencas rurales)",
            ],
            storm_codes=["gz"],
            return_periods=[2, 10, 25],
            x_factors=[1.0, 1.25],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        # Verificar proyecto
        assert project is not None
        assert len(project.basins) == 1

        # Verificar cuenca
        assert basin.name == "Cuenca Las Piedras"
        assert basin.area_ha == 62.0
        assert basin.c == 0.62

        # Verificar Tc (2 métodos)
        assert len(basin.tc_results) == 2

        # Verificar análisis (2 Tc × 3 Tr × 2 X = 12)
        assert len(basin.analyses) == 12

        # Verificar que hay resultados para cada Tr
        trs = {a.storm.return_period for a in basin.analyses}
        assert trs == {2, 10, 25}

        # Verificar que hay resultados con diferentes X
        x_factors = {a.hydrograph.x_factor for a in basin.analyses}
        assert 1.0 in x_factors
        assert 1.25 in x_factors

    def test_workflow_nueva_cuenca_con_cn(self, mock_managers):
        """Test flujo completo: nueva cuenca con CN."""
        config = WizardConfig(
            nombre="Cuenca Rural",
            area_ha=100.0,
            slope_pct=5.0,
            p3_10=85.0,
            c=None,
            cn=70,
            length_m=1500.0,
            amc="II",
            lambda_coef=0.2,
            tc_methods=["Kirpich (cuencas rurales)"],
            storm_codes=["gz"],
            return_periods=[10, 25],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        assert basin.cn == 70
        assert len(basin.analyses) == 2

    def test_workflow_comparar_c_vs_cn(self, mock_managers):
        """Test flujo: comparar metodologías C vs CN."""
        config = WizardConfig(
            nombre="Cuenca Comparativa",
            area_ha=50.0,
            slope_pct=3.0,
            p3_10=83.0,
            c=0.55,
            cn=75,
            length_m=800.0,
            t0_min=5.0,
            amc="II",
            lambda_coef=0.2,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        # Debería tener 2 análisis (uno con C, otro con CN)
        assert len(basin.analyses) == 2

        # Verificar que hay uno de cada método
        runoff_methods = set()
        for a in basin.analyses:
            if a.tc.parameters:
                runoff_methods.add(a.tc.parameters.get("runoff_method"))

        assert "racional" in runoff_methods
        assert "scs-cn" in runoff_methods

    def test_workflow_agregar_cuenca_a_proyecto(self, mock_managers):
        """Test flujo: agregar cuenca a proyecto existente."""
        project_manager = mock_managers["project"]

        # Crear proyecto
        project = project_manager.create_project(
            name="Estudio Drenaje Norte",
            description="Análisis hidrológico zona norte",
        )

        # Agregar primera cuenca
        config1 = WizardConfig(
            nombre="Subcuenca A",
            area_ha=30.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner1 = AnalysisRunner(config1, project_id=project.id)
        project, basin1 = runner1.run()

        assert len(project.basins) == 1

        # Agregar segunda cuenca al mismo proyecto
        config2 = WizardConfig(
            nombre="Subcuenca B",
            area_ha=45.0,
            slope_pct=2.5,
            p3_10=83.0,
            c=0.6,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner2 = AnalysisRunner(config2, project_id=project.id)
        project, basin2 = runner2.run()

        assert len(project.basins) == 2
        assert project.basins[0].name == "Subcuenca A"
        assert project.basins[1].name == "Subcuenca B"

    def test_workflow_diferentes_tormentas(self, mock_managers):
        """Test flujo: análisis con diferentes tipos de tormenta."""
        config = WizardConfig(
            nombre="Test Tormentas",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz", "blocks", "bimodal"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        # Verificar tipos de tormenta
        storm_types = {a.storm.type for a in basin.analyses}
        assert "gz" in storm_types
        assert "blocks" in storm_types
        assert "bimodal" in storm_types

    def test_workflow_amc_variations(self, mock_managers):
        """Test flujo: verificar efecto de AMC en resultados."""
        # Crear tres análisis con diferentes AMC
        results = {}

        for amc in ["I", "II", "III"]:
            config = WizardConfig(
                nombre=f"Test AMC {amc}",
                area_ha=50.0,
                slope_pct=2.0,
                p3_10=83.0,
                c=None,
                cn=75,
                length_m=1000.0,
                amc=amc,
                lambda_coef=0.2,
                tc_methods=["Kirpich (cuencas rurales)"],
                storm_codes=["gz"],
                return_periods=[10],
                x_factors=[1.0],
            )

            runner = AnalysisRunner(config)
            project, basin = runner.run()

            # Guardar caudal pico
            results[amc] = basin.analyses[0].hydrograph.peak_flow_m3s

        # AMC III (húmedo) debería dar mayor caudal que AMC I (seco)
        assert results["III"] > results["II"] > results["I"]


# ============================================================================
# Tests para validaciones y casos de borde
# ============================================================================


class TestEdgeCases:
    """Tests para casos de borde y validaciones."""

    def test_cuenca_sin_longitud_solo_desbordes(self, mock_managers):
        """Test cuenca sin longitud solo puede usar Desbordes."""
        config = WizardConfig(
            nombre="Sin Longitud",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            cn=None,
            length_m=None,  # Sin longitud
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        # Solo debería tener método Desbordes
        tc_methods = {tc.method for tc in basin.tc_results}
        assert tc_methods == {"desbordes"}

    def test_cuenca_solo_cn_sin_c(self, mock_managers):
        """Test cuenca solo con CN no puede usar Desbordes."""
        config = WizardConfig(
            nombre="Solo CN",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=None,  # Sin C
            cn=75,
            length_m=1000.0,
            tc_methods=["Kirpich (cuencas rurales)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        # Solo debería tener método Kirpich
        tc_methods = {tc.method for tc in basin.tc_results}
        assert tc_methods == {"kirpich"}

    def test_valores_extremos_area(self, mock_managers):
        """Test con valores extremos de área."""
        # Área muy pequeña
        config_small = WizardConfig(
            nombre="Cuenca Pequeña",
            area_ha=0.5,
            slope_pct=5.0,
            p3_10=83.0,
            c=0.7,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner_small = AnalysisRunner(config_small)
        project, basin = runner_small.run()

        assert basin is not None
        assert len(basin.analyses) == 1

    def test_valores_extremos_pendiente(self, mock_managers):
        """Test con valores extremos de pendiente."""
        # Pendiente muy alta
        config = WizardConfig(
            nombre="Cuenca Empinada",
            area_ha=50.0,
            slope_pct=15.0,  # 15%
            p3_10=83.0,
            c=0.6,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        assert basin is not None
        # Mayor pendiente = menor Tc
        tc_result = basin.tc_results[0]
        assert tc_result.tc_min < 60  # Menos de 1 hora


class TestPersistence:
    """Tests para persistencia de datos."""

    def test_session_persistence(self, session_manager):
        """Test que las sesiones se persisten correctamente."""
        # Crear sesión
        session = session_manager.create(
            name="Persistence Test",
            area_ha=100.0,
            slope_pct=2.5,
            p3_10=83.0,
            c=0.5,
        )
        session_manager.add_tc_result(session, method="desbordes", tc_hr=0.75)

        # Agregar análisis
        runner = AdditionalAnalysisRunner(session, c=0.5)
        runner.run(
            tc_methods=["desbordes"],
            storm_code="gz",
            return_periods=[10],
            x_factors=[1.0],
        )

        # Guardar
        session_manager.save(session)

        # Cargar y verificar
        loaded = session_manager.load(session.id)

        assert loaded.name == "Persistence Test"
        assert loaded.cuenca.area_ha == 100.0
        assert len(loaded.tc_results) == 1
        assert len(loaded.analyses) == 1

    def test_project_persistence(self, mock_managers):
        """Test que los proyectos se persisten correctamente."""
        project_manager = mock_managers["project"]

        config = WizardConfig(
            nombre="Persistence Project Test",
            area_ha=50.0,
            slope_pct=2.0,
            p3_10=83.0,
            c=0.5,
            tc_methods=["Desbordes (recomendado cuencas urbanas)"],
            storm_codes=["gz"],
            return_periods=[10],
            x_factors=[1.0],
        )

        runner = AnalysisRunner(config)
        project, basin = runner.run()

        # Cargar proyecto y verificar
        loaded_project = project_manager.get_project(project.id)

        assert loaded_project is not None
        assert len(loaded_project.basins) == 1
        assert loaded_project.basins[0].name == "Persistence Project Test"
