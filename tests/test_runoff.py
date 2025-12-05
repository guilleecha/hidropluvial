"""Tests para módulo de escorrentía."""

import numpy as np
import pytest

from hidropluvial.core.runoff import (
    scs_potential_retention,
    scs_initial_abstraction,
    scs_runoff,
    adjust_cn_for_amc,
    composite_cn,
    get_cn_from_table,
    calculate_scs_runoff,
    rainfall_excess_series,
    rational_peak_flow,
    composite_c,
    RATIONAL_C,
    RATIONAL_CF,
    get_rational_c,
)
from hidropluvial.config import AntecedentMoistureCondition, HydrologicSoilGroup


class TestSCSPotentialRetention:
    """Tests para retención potencial S."""

    def test_basic_calculation(self):
        """Test cálculo básico de S."""
        s = scs_potential_retention(75)
        expected = (25400 / 75) - 254
        assert s == pytest.approx(expected, rel=0.001)

    def test_cn_100_zero_retention(self):
        """CN=100 debe dar S=0."""
        s = scs_potential_retention(100)
        assert s == pytest.approx(0.0, abs=0.01)

    def test_higher_cn_lower_retention(self):
        """Mayor CN debe dar menor retención."""
        s_60 = scs_potential_retention(60)
        s_80 = scs_potential_retention(80)
        assert s_60 > s_80

    def test_invalid_cn(self):
        """Test CN fuera de rango."""
        with pytest.raises(ValueError):
            scs_potential_retention(25)
        with pytest.raises(ValueError):
            scs_potential_retention(105)


class TestSCSRunoff:
    """Tests para cálculo de escorrentía SCS."""

    def test_no_runoff_below_ia(self):
        """Sin escorrentía si P <= Ia."""
        cn = 75
        s = scs_potential_retention(cn)
        ia = scs_initial_abstraction(s)

        q = scs_runoff(ia * 0.5, cn)
        assert q == 0.0

    def test_runoff_above_ia(self):
        """Escorrentía positiva si P > Ia."""
        q = scs_runoff(100, 75)
        assert q > 0

    def test_runoff_less_than_rainfall(self):
        """Escorrentía debe ser menor que precipitación."""
        rainfall = 150
        q = scs_runoff(rainfall, 80)
        assert q < rainfall

    def test_higher_cn_more_runoff(self):
        """Mayor CN debe producir más escorrentía."""
        rainfall = 100
        q_60 = scs_runoff(rainfall, 60)
        q_80 = scs_runoff(rainfall, 80)
        assert q_80 > q_60

    def test_array_input(self):
        """Test con array de precipitaciones."""
        rainfall = np.array([50, 100, 150])
        q = scs_runoff(rainfall, 75)
        assert len(q) == 3
        assert all(q >= 0)

    def test_tr55_example(self):
        """Validación contra ejemplo TR-55."""
        # Ejemplo típico: P=127mm, CN=75
        q = scs_runoff(127, 75, lambda_coef=0.2)
        # Valor esperado aproximado: ~61mm
        assert 55 < q < 70


class TestAMCAdjustment:
    """Tests para ajuste por condición antecedente."""

    def test_amc_ii_no_change(self):
        """AMC II no debe cambiar CN."""
        cn_ii = 75
        cn_adj = adjust_cn_for_amc(cn_ii, AntecedentMoistureCondition.AVERAGE)
        assert cn_adj == cn_ii

    def test_amc_i_lower_cn(self):
        """AMC I (seco) debe dar CN menor."""
        cn_ii = 75
        cn_i = adjust_cn_for_amc(cn_ii, AntecedentMoistureCondition.DRY)
        assert cn_i < cn_ii

    def test_amc_iii_higher_cn(self):
        """AMC III (húmedo) debe dar CN mayor."""
        cn_ii = 75
        cn_iii = adjust_cn_for_amc(cn_ii, AntecedentMoistureCondition.WET)
        assert cn_iii > cn_ii

    def test_cn_bounds(self):
        """CN ajustado debe estar entre 30 y 100."""
        cn_i = adjust_cn_for_amc(35, AntecedentMoistureCondition.DRY)
        cn_iii = adjust_cn_for_amc(95, AntecedentMoistureCondition.WET)

        assert 30 <= cn_i <= 100
        assert 30 <= cn_iii <= 100


class TestCompositeCN:
    """Tests para CN compuesto."""

    def test_basic_composite(self):
        """Test cálculo básico de CN compuesto."""
        areas = [50, 50]
        cns = [60, 80]
        cn_comp = composite_cn(areas, cns)
        assert cn_comp == pytest.approx(70, rel=0.01)

    def test_weighted_composite(self):
        """Test CN compuesto ponderado."""
        areas = [75, 25]
        cns = [60, 80]
        cn_comp = composite_cn(areas, cns)
        expected = (75 * 60 + 25 * 80) / 100
        assert cn_comp == pytest.approx(expected, rel=0.001)


class TestRainfallExcess:
    """Tests para serie de exceso de lluvia."""

    def test_excess_series(self, sample_rainfall_series):
        """Test serie de exceso."""
        cumulative = np.cumsum(sample_rainfall_series)
        excess = rainfall_excess_series(cumulative, 75)

        assert len(excess) == len(sample_rainfall_series)
        assert np.sum(excess) <= np.sum(sample_rainfall_series)


class TestRationalMethod:
    """Tests para método racional."""

    def test_basic_calculation(self):
        """Test cálculo básico."""
        q = rational_peak_flow(0.5, 50, 10)
        # Q = 0.00278 × C × i × A
        expected = 0.00278 * 0.5 * 50 * 10
        assert q == pytest.approx(expected, rel=0.01)

    def test_return_period_adjustment(self):
        """Test ajuste por período de retorno."""
        q_10 = rational_peak_flow(0.5, 50, 10, return_period_yr=10)
        q_100 = rational_peak_flow(0.5, 50, 10, return_period_yr=100)
        assert q_100 > q_10

    def test_invalid_c(self):
        """Test C fuera de rango."""
        with pytest.raises(ValueError):
            rational_peak_flow(1.5, 50, 10)

    def test_invalid_c_zero(self):
        """Test C = 0."""
        with pytest.raises(ValueError):
            rational_peak_flow(0, 50, 10)

    def test_invalid_intensity(self):
        """Test intensidad <= 0."""
        with pytest.raises(ValueError):
            rational_peak_flow(0.5, 0, 10)

    def test_invalid_area(self):
        """Test area <= 0."""
        with pytest.raises(ValueError):
            rational_peak_flow(0.5, 50, 0)


class TestGetCNFromTable:
    """Tests para get_cn_from_table."""

    def test_valid_cover_type(self):
        """Test tipo de cobertura valido."""
        cn = get_cn_from_table("residential_1000m2", HydrologicSoilGroup.B)
        assert 30 <= cn <= 100

    def test_all_soil_groups(self):
        """Test todos los grupos de suelo."""
        for group in HydrologicSoilGroup:
            cn = get_cn_from_table("impervious", group)
            assert 30 <= cn <= 100

    def test_different_soil_groups_order(self):
        """Test orden de CN por grupos de suelo."""
        cn_a = get_cn_from_table("residential_1000m2", HydrologicSoilGroup.A)
        cn_b = get_cn_from_table("residential_1000m2", HydrologicSoilGroup.B)
        cn_c = get_cn_from_table("residential_1000m2", HydrologicSoilGroup.C)
        cn_d = get_cn_from_table("residential_1000m2", HydrologicSoilGroup.D)
        # Grupos menos permeables tienen mayor CN
        assert cn_a <= cn_b <= cn_c <= cn_d

    def test_invalid_cover_type(self):
        """Test tipo de cobertura invalido."""
        with pytest.raises(ValueError, match="desconocido"):
            get_cn_from_table("invalid_type", HydrologicSoilGroup.B)


class TestCalculateSCSRunoff:
    """Tests para calculate_scs_runoff."""

    def test_returns_result_object(self):
        """Test retorna RunoffResult."""
        result = calculate_scs_runoff(100.0, 75)
        assert hasattr(result, 'rainfall_mm')
        assert hasattr(result, 'runoff_mm')
        assert hasattr(result, 'initial_abstraction_mm')
        assert hasattr(result, 'retention_mm')
        assert hasattr(result, 'cn_used')
        assert hasattr(result, 'method')

    def test_correct_values(self):
        """Test valores correctos."""
        result = calculate_scs_runoff(100.0, 75)
        assert result.rainfall_mm == 100.0
        assert result.runoff_mm > 0
        assert result.retention_mm > 0
        assert result.initial_abstraction_mm > 0

    def test_method_string(self):
        """Test string de metodo."""
        result = calculate_scs_runoff(100.0, 75, lambda_coef=0.2)
        assert "SCS-CN" in result.method
        assert "0.2" in result.method

    def test_with_amc_i(self):
        """Test con AMC I."""
        result = calculate_scs_runoff(100.0, 75, amc=AntecedentMoistureCondition.DRY)
        assert "AMC=I" in result.method
        assert result.cn_used < 75

    def test_with_amc_iii(self):
        """Test con AMC III."""
        result = calculate_scs_runoff(100.0, 75, amc=AntecedentMoistureCondition.WET)
        assert "AMC=III" in result.method
        assert result.cn_used > 75

    def test_custom_lambda(self):
        """Test con lambda personalizado."""
        result = calculate_scs_runoff(100.0, 75, lambda_coef=0.05)
        assert "0.05" in result.method


class TestCompositeC:
    """Tests para composite_c."""

    def test_equal_areas(self):
        """Test con areas iguales."""
        areas = [100, 100]
        cs = [0.3, 0.7]
        result = composite_c(areas, cs)
        assert result == pytest.approx(0.5, rel=0.01)

    def test_weighted_average(self):
        """Test promedio ponderado."""
        areas = [100, 50]
        cs = [0.3, 0.6]
        # (100*0.3 + 50*0.6) / 150 = (30 + 30) / 150 = 0.4
        result = composite_c(areas, cs)
        assert result == pytest.approx(0.4, rel=0.01)

    def test_single_area(self):
        """Test con una sola area."""
        result = composite_c([100], [0.5])
        assert result == 0.5

    def test_mismatched_lengths(self):
        """Test listas de diferente longitud."""
        with pytest.raises(ValueError, match="igual longitud"):
            composite_c([100, 100], [0.5])

    def test_zero_area(self):
        """Test area total cero."""
        with pytest.raises(ValueError, match="cero"):
            composite_c([0, 0], [0.5, 0.6])


class TestRationalCF:
    """Tests para factores de ajuste Cf."""

    def test_cf_values(self):
        """Test valores de Cf definidos."""
        assert RATIONAL_CF[2] == 1.00
        assert RATIONAL_CF[10] == 1.00
        assert RATIONAL_CF[25] == 1.10
        assert RATIONAL_CF[50] == 1.20
        assert RATIONAL_CF[100] == 1.25


class TestRationalCTable:
    """Tests para tabla RATIONAL_C."""

    def test_table_not_empty(self):
        """Test tabla no vacia."""
        assert len(RATIONAL_C) > 0

    def test_values_in_range(self):
        """Test valores en rango 0-1."""
        for key, (c_low, c_high) in RATIONAL_C.items():
            assert 0 < c_low < 1
            assert 0 < c_high <= 1
            assert c_low <= c_high


class TestGetRationalC:
    """Tests para get_rational_c."""

    def test_average_condition(self):
        """Test condicion promedio."""
        c = get_rational_c("asphalt", "average")
        c_low, c_high = RATIONAL_C["asphalt"]
        expected = (c_low + c_high) / 2
        assert c == pytest.approx(expected, rel=0.01)

    def test_low_condition(self):
        """Test condicion baja."""
        c = get_rational_c("asphalt", "low")
        assert c == RATIONAL_C["asphalt"][0]

    def test_high_condition(self):
        """Test condicion alta."""
        c = get_rational_c("asphalt", "high")
        assert c == RATIONAL_C["asphalt"][1]

    def test_invalid_land_use(self):
        """Test uso de suelo invalido."""
        with pytest.raises(ValueError, match="desconocido"):
            get_rational_c("invalid_type", "average")


class TestIntegrationRunoff:
    """Tests de integracion para escorrentia."""

    def test_scs_complete_workflow(self):
        """Test flujo completo SCS-CN."""
        rainfall = 100.0
        cn = 75

        s = scs_potential_retention(cn)
        ia = scs_initial_abstraction(s)
        q = scs_runoff(rainfall, cn)

        assert s > 0
        assert ia == pytest.approx(0.2 * s, rel=0.01)
        assert 0 < q < rainfall

    def test_rational_complete_workflow(self):
        """Test flujo completo metodo racional."""
        areas = [50, 30, 20]
        cs = [0.8, 0.5, 0.2]

        c_comp = composite_c(areas, cs)
        intensity = 60
        total_area = sum(areas)
        q = rational_peak_flow(c_comp, intensity, total_area)

        assert 0 < c_comp < 1
        assert q > 0

    def test_cn_amc_comparison(self):
        """Test comparacion AMC I, II, III."""
        rainfall = 100.0
        cn = 75

        q_i = calculate_scs_runoff(rainfall, cn, amc=AntecedentMoistureCondition.DRY)
        q_ii = calculate_scs_runoff(rainfall, cn, amc=AntecedentMoistureCondition.AVERAGE)
        q_iii = calculate_scs_runoff(rainfall, cn, amc=AntecedentMoistureCondition.WET)

        assert q_i.runoff_mm < q_ii.runoff_mm < q_iii.runoff_mm
