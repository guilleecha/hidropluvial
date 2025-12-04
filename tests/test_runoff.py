"""Tests para módulo de escorrentía."""

import numpy as np
import pytest

from hidropluvial.core.runoff import (
    scs_potential_retention,
    scs_initial_abstraction,
    scs_runoff,
    adjust_cn_for_amc,
    composite_cn,
    rainfall_excess_series,
    rational_peak_flow,
)
from hidropluvial.config import AntecedentMoistureCondition


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
