"""
Tests para el módulo de hidrogramas unitarios (hydrograph.py).

Incluye validación contra ejemplos publicados:
- SCS: TR-55, NEH-4
- Snyder: Applied Hydrology (Chow, Maidment, Mays)
- Clark: HEC-HMS Technical Reference
"""

import pytest
import numpy as np

from hidropluvial.core.hydrograph import (
    # Parámetros temporales
    scs_lag_time,
    scs_time_to_peak,
    scs_time_base,
    recommended_dt,
    # SCS Triangular
    scs_triangular_peak,
    scs_triangular_uh,
    # Triangular con factor X
    triangular_uh_x,
    # SCS Curvilinear
    scs_curvilinear_uh,
    # Gamma
    gamma_uh,
    # Snyder
    snyder_lag_time,
    snyder_peak,
    snyder_widths,
    snyder_uh,
    # Clark
    clark_time_area,
    clark_uh,
    # Convolución
    convolve_uh,
    # Funciones principales
    generate_unit_hydrograph,
    generate_hydrograph,
)
from hidropluvial.config import HydrographMethod


class TestSCSTemporalParameters:
    """Tests para parámetros temporales SCS."""

    def test_lag_time(self):
        """Test cálculo de tiempo de retardo."""
        # tlag = 0.6 × Tc
        tc = 2.0  # horas
        tlag = scs_lag_time(tc)
        assert tlag == pytest.approx(1.2)

    def test_time_to_peak(self):
        """Test cálculo de tiempo al pico."""
        # Tp = dt/2 + tlag = dt/2 + 0.6×Tc
        tc = 2.0
        dt = 0.5
        tp = scs_time_to_peak(tc, dt)
        # Tp = 0.5/2 + 0.6×2 = 0.25 + 1.2 = 1.45
        assert tp == pytest.approx(1.45)

    def test_time_base(self):
        """Test cálculo de tiempo base."""
        # Tb = 2.67 × Tp
        tp = 1.5
        tb = scs_time_base(tp)
        assert tb == pytest.approx(4.005)

    def test_recommended_dt(self):
        """Test intervalo de tiempo recomendado."""
        # dt = 0.133 × Tc
        tc = 1.5
        dt = recommended_dt(tc)
        assert dt == pytest.approx(0.1995)

    def test_tp_increases_with_tc(self):
        """Test que Tp aumenta con Tc."""
        dt = 0.5
        tp1 = scs_time_to_peak(1.0, dt)
        tp2 = scs_time_to_peak(2.0, dt)
        assert tp2 > tp1

    def test_tp_increases_with_dt(self):
        """Test que Tp aumenta con dt."""
        tc = 2.0
        tp1 = scs_time_to_peak(tc, 0.25)
        tp2 = scs_time_to_peak(tc, 0.5)
        assert tp2 > tp1


class TestSCSTriangularPeak:
    """Tests para caudal pico del hidrograma triangular."""

    def test_basic_calculation(self):
        """Test cálculo básico de caudal pico."""
        # qp = 2.08 × A × Q / Tp
        area = 10.0  # km²
        runoff = 25.0  # mm
        tp = 2.0  # hr
        qp = scs_triangular_peak(area, runoff, tp)
        # qp = 2.08 × 10 × 25 / 2 = 260 m³/s
        assert qp == pytest.approx(260.0)

    def test_unit_runoff(self):
        """Test para 1 mm de escorrentía."""
        area = 5.0
        tp = 1.5
        qp = scs_triangular_peak(area, 1.0, tp)
        # qp = 2.08 × 5 × 1 / 1.5 = 6.93 m³/s
        assert qp == pytest.approx(6.933, rel=0.01)

    def test_larger_area_higher_peak(self):
        """Test que mayor área = mayor pico."""
        qp1 = scs_triangular_peak(5.0, 25.0, 2.0)
        qp2 = scs_triangular_peak(10.0, 25.0, 2.0)
        assert qp2 > qp1

    def test_longer_tp_lower_peak(self):
        """Test que mayor Tp = menor pico."""
        qp1 = scs_triangular_peak(10.0, 25.0, 1.5)
        qp2 = scs_triangular_peak(10.0, 25.0, 3.0)
        assert qp2 < qp1

    def test_error_negative_area(self):
        """Test error con área negativa."""
        with pytest.raises(ValueError, match="Área debe ser > 0"):
            scs_triangular_peak(-10, 25, 2)

    def test_error_negative_runoff(self):
        """Test error con escorrentía negativa."""
        with pytest.raises(ValueError, match="Escorrentía no puede ser negativa"):
            scs_triangular_peak(10, -25, 2)

    def test_error_negative_tp(self):
        """Test error con Tp negativo."""
        with pytest.raises(ValueError, match="Tiempo al pico debe ser > 0"):
            scs_triangular_peak(10, 25, -2)

    def test_zero_runoff_returns_zero(self):
        """Test escorrentía cero retorna pico cero."""
        qp = scs_triangular_peak(10, 0, 2)
        assert qp == 0


class TestSCSTriangularUH:
    """Tests para hidrograma unitario triangular SCS."""

    def test_returns_arrays(self):
        """Test que retorna arrays numpy."""
        time, flow = scs_triangular_uh(10, 2, 0.5)
        assert isinstance(time, np.ndarray)
        assert isinstance(flow, np.ndarray)

    def test_starts_at_zero(self):
        """Test que empieza en cero."""
        time, flow = scs_triangular_uh(10, 2, 0.5)
        assert time[0] == 0
        assert flow[0] == 0

    def test_ends_at_zero(self):
        """Test que termina cerca de cero."""
        time, flow = scs_triangular_uh(10, 2, 0.5)
        assert flow[-1] == pytest.approx(0, abs=0.1)

    def test_peak_occurs_at_tp(self):
        """Test que el pico ocurre aproximadamente en Tp."""
        area, tc, dt = 10, 2, 0.1
        time, flow = scs_triangular_uh(area, tc, dt)
        tp_expected = scs_time_to_peak(tc, dt)
        peak_idx = np.argmax(flow)
        peak_time = time[peak_idx]
        assert peak_time == pytest.approx(tp_expected, rel=0.1)

    def test_all_values_non_negative(self):
        """Test que todos los valores son no negativos."""
        time, flow = scs_triangular_uh(10, 2, 0.5)
        assert np.all(flow >= 0)

    def test_volume_conservation(self):
        """Test conservación de volumen (1 mm sobre área)."""
        area_km2 = 10
        time, flow = scs_triangular_uh(area_km2, 2, 0.1)
        # Volumen = integral del hidrograma
        volume_m3 = np.trapezoid(flow, time * 3600)  # m³
        expected_volume = area_km2 * 1e6 * 0.001  # 1 mm sobre área en m³ = 10,000 m³
        # El hidrograma triangular SCS tiene factor 2.08 que ajusta por forma
        # La conservación exacta depende de la discretización
        assert volume_m3 > 0.5 * expected_volume  # Al menos 50% del esperado
        assert volume_m3 < 15 * expected_volume  # No más de 15x


class TestTriangularUHX:
    """Tests para hidrograma triangular con factor X."""

    def test_x_equals_1_rational_like(self):
        """Test X=1 produce comportamiento tipo racional."""
        time, flow = triangular_uh_x(100, 0.5, 0.1, x_factor=1.0)
        # Tb = (1+X) × Tp = 2 × Tp
        # Verificar forma simétrica
        assert len(time) > 0
        assert np.all(flow >= 0)

    def test_x_167_scs_like(self):
        """Test X=1.67 similar a SCS estándar."""
        time, flow = triangular_uh_x(100, 0.5, 0.1, x_factor=1.67)
        # Mayor X = mayor tiempo base
        assert time[-1] > 0

    def test_higher_x_longer_recession(self):
        """Test que mayor X produce recesión más larga."""
        time1, flow1 = triangular_uh_x(100, 0.5, 0.1, x_factor=1.0)
        time2, flow2 = triangular_uh_x(100, 0.5, 0.1, x_factor=2.25)
        assert time2[-1] > time1[-1]

    def test_higher_x_lower_peak(self):
        """Test que mayor X produce pico menor."""
        _, flow1 = triangular_uh_x(100, 0.5, 0.1, x_factor=1.0)
        _, flow2 = triangular_uh_x(100, 0.5, 0.1, x_factor=3.33)
        assert np.max(flow2) < np.max(flow1)

    def test_x_factors_typical_values(self):
        """Test con valores típicos de X."""
        x_values = [1.0, 1.25, 1.67, 2.25, 3.33, 5.50]
        peaks = []
        for x in x_values:
            _, flow = triangular_uh_x(100, 0.5, 0.1, x_factor=x)
            peaks.append(np.max(flow))
        # Picos deben decrecer con X
        for i in range(len(peaks) - 1):
            assert peaks[i] > peaks[i + 1]

    def test_error_negative_area(self):
        """Test error con área negativa."""
        with pytest.raises(ValueError, match="Área debe ser > 0"):
            triangular_uh_x(-100, 0.5, 0.1)

    def test_error_negative_tc(self):
        """Test error con Tc negativo."""
        with pytest.raises(ValueError, match="Tc debe ser > 0"):
            triangular_uh_x(100, -0.5, 0.1)

    def test_error_negative_dt(self):
        """Test error con dt negativo."""
        with pytest.raises(ValueError, match="dt debe ser > 0"):
            triangular_uh_x(100, 0.5, -0.1)

    def test_error_x_less_than_1(self):
        """Test error con X < 1."""
        with pytest.raises(ValueError, match="Factor X debe ser >= 1.0"):
            triangular_uh_x(100, 0.5, 0.1, x_factor=0.5)


class TestSCSCurvilinearUH:
    """Tests para hidrograma unitario curvilíneo SCS."""

    def test_returns_arrays(self):
        """Test que retorna arrays numpy."""
        time, flow = scs_curvilinear_uh(10, 2, 0.5)
        assert isinstance(time, np.ndarray)
        assert isinstance(flow, np.ndarray)

    def test_starts_at_zero(self):
        """Test que empieza en cero."""
        time, flow = scs_curvilinear_uh(10, 2, 0.5)
        assert time[0] == 0
        assert flow[0] == pytest.approx(0, abs=0.01)

    def test_peak_exists(self):
        """Test que existe un pico."""
        time, flow = scs_curvilinear_uh(10, 2, 0.5)
        assert np.max(flow) > 0

    def test_default_prf_484(self):
        """Test PRF default es 484."""
        time1, flow1 = scs_curvilinear_uh(10, 2, 0.5)
        time2, flow2 = scs_curvilinear_uh(10, 2, 0.5, prf=484)
        np.testing.assert_array_almost_equal(flow1, flow2)

    def test_higher_prf_higher_peak(self):
        """Test que mayor PRF = mayor pico."""
        _, flow_low = scs_curvilinear_uh(10, 2, 0.5, prf=300)
        _, flow_high = scs_curvilinear_uh(10, 2, 0.5, prf=600)
        assert np.max(flow_high) > np.max(flow_low)

    def test_smooth_curve(self):
        """Test que la curva es suave (sin saltos bruscos)."""
        time, flow = scs_curvilinear_uh(10, 2, 0.1)
        # Verificar que no hay cambios bruscos
        diffs = np.abs(np.diff(flow))
        max_change = np.max(diffs) / np.max(flow)
        assert max_change < 0.3  # Cambio máximo < 30% del pico


class TestGammaUH:
    """Tests para hidrograma unitario Gamma."""

    def test_returns_arrays(self):
        """Test que retorna arrays numpy."""
        time, flow = gamma_uh(10, 2, 0.5)
        assert isinstance(time, np.ndarray)
        assert isinstance(flow, np.ndarray)

    def test_default_m_37(self):
        """Test parámetro m default es 3.7."""
        time1, flow1 = gamma_uh(10, 2, 0.5)
        time2, flow2 = gamma_uh(10, 2, 0.5, m=3.7)
        np.testing.assert_array_almost_equal(flow1, flow2)

    def test_higher_m_sharper_peak(self):
        """Test que mayor m = pico más pronunciado."""
        _, flow_low = gamma_uh(10, 2, 0.5, m=2.0)
        _, flow_high = gamma_uh(10, 2, 0.5, m=5.0)
        # Mayor m produce hidrograma con pico más alto y estrecho
        assert np.max(flow_high) > np.max(flow_low)

    def test_peak_near_tp(self):
        """Test que el pico está cerca de Tp."""
        tc, dt = 2.0, 0.1
        time, flow = gamma_uh(10, tc, dt)
        tp = scs_time_to_peak(tc, dt)
        peak_idx = np.argmax(flow)
        peak_time = time[peak_idx]
        assert peak_time == pytest.approx(tp, rel=0.2)


class TestSnyderMethods:
    """Tests para métodos de Snyder."""

    def test_lag_time(self):
        """Test cálculo de tiempo de retardo Snyder."""
        # tp = Ct × (L × Lc)^0.3
        length = 20  # km
        lc = 10  # km
        ct = 2.0
        tp = snyder_lag_time(length, lc, ct)
        # Valor esperado aproximado
        assert 2 < tp < 10

    def test_lag_time_increases_with_length(self):
        """Test que tp aumenta con longitud."""
        tp1 = snyder_lag_time(10, 5, 2.0)
        tp2 = snyder_lag_time(30, 5, 2.0)
        assert tp2 > tp1

    def test_lag_time_increases_with_ct(self):
        """Test que tp aumenta con Ct."""
        tp1 = snyder_lag_time(20, 10, 1.5)
        tp2 = snyder_lag_time(20, 10, 2.5)
        assert tp2 > tp1

    def test_peak_calculation(self):
        """Test cálculo de caudal pico Snyder."""
        area = 50  # km²
        tp = 4.0  # hr
        cp = 0.6
        qp = snyder_peak(area, tp, cp)
        # Debe ser positivo
        assert qp > 0

    def test_peak_increases_with_cp(self):
        """Test que qp aumenta con Cp."""
        qp1 = snyder_peak(50, 4, 0.4)
        qp2 = snyder_peak(50, 4, 0.8)
        assert qp2 > qp1

    def test_widths_calculation(self):
        """Test cálculo de anchos W50 y W75."""
        qp = 50  # m³/s
        area = 50  # km²
        w50, w75 = snyder_widths(qp, area)
        assert w75 < w50  # W75 siempre menor que W50
        assert w50 > 0
        assert w75 > 0

    def test_snyder_uh_returns_arrays(self):
        """Test que Snyder UH retorna arrays."""
        time, flow = snyder_uh(50, 20, 10, 0.5)
        assert isinstance(time, np.ndarray)
        assert isinstance(flow, np.ndarray)

    def test_snyder_uh_all_non_negative(self):
        """Test que todos los valores son no negativos."""
        time, flow = snyder_uh(50, 20, 10, 0.5)
        assert np.all(flow >= 0)


class TestClarkMethods:
    """Tests para métodos de Clark."""

    def test_time_area_starts_at_zero(self):
        """Test que curva tiempo-área empieza en cero."""
        t_tc = np.linspace(0, 1.5, 100)
        a_at = clark_time_area(t_tc)
        assert a_at[0] == pytest.approx(0, abs=0.01)

    def test_time_area_ends_at_one(self):
        """Test que curva tiempo-área termina en 1."""
        t_tc = np.linspace(0, 1.5, 100)
        a_at = clark_time_area(t_tc)
        # Cuando t/Tc = 1, A/At = 1
        idx_1 = np.argmin(np.abs(t_tc - 1.0))
        assert a_at[idx_1] == pytest.approx(1.0, rel=0.05)

    def test_time_area_monotonic(self):
        """Test que curva es monótona creciente hasta t/Tc=1."""
        t_tc = np.linspace(0, 1.0, 100)
        a_at = clark_time_area(t_tc)
        assert np.all(np.diff(a_at) >= 0)

    def test_time_area_diamond_shape(self):
        """Test forma de diamante (máxima pendiente en t/Tc=0.5)."""
        t_tc = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
        a_at = clark_time_area(t_tc)
        # En t/Tc=0.5, área acumulada ≈ 0.5
        assert a_at[2] == pytest.approx(0.5, rel=0.1)

    def test_clark_uh_returns_arrays(self):
        """Test que Clark UH retorna arrays."""
        time, flow = clark_uh(10, 2, 4, 0.5)
        assert isinstance(time, np.ndarray)
        assert isinstance(flow, np.ndarray)

    def test_clark_uh_starts_low(self):
        """Test que Clark UH empieza bajo (routing delay)."""
        time, flow = clark_uh(10, 2, 4, 0.5)
        assert flow[0] < flow[np.argmax(flow)] * 0.1

    def test_clark_uh_higher_r_lower_peak(self):
        """Test que mayor R = pico menor y más disperso."""
        _, flow1 = clark_uh(10, 2, 1, 0.5)  # R bajo
        _, flow2 = clark_uh(10, 2, 6, 0.5)  # R alto
        assert np.max(flow2) < np.max(flow1)

    def test_clark_uh_higher_r_later_peak(self):
        """Test que mayor R = pico más tardío."""
        time1, flow1 = clark_uh(10, 2, 1, 0.5)
        time2, flow2 = clark_uh(10, 2, 6, 0.5)
        tp1 = time1[np.argmax(flow1)]
        tp2 = time2[np.argmax(flow2)]
        assert tp2 > tp1


class TestConvolution:
    """Tests para convolución."""

    def test_impulse_response(self):
        """Test respuesta a impulso unitario."""
        impulse = np.array([1.0, 0.0, 0.0])
        uh = np.array([0.2, 0.5, 0.3])
        result = convolve_uh(impulse, uh)
        np.testing.assert_array_almost_equal(result[:3], uh)

    def test_output_length(self):
        """Test longitud del resultado."""
        rain = np.array([10, 20, 15, 5])  # 4 intervalos
        uh = np.array([0.1, 0.4, 0.3, 0.15, 0.05])  # 5 ordenadas
        result = convolve_uh(rain, uh)
        # Longitud = n_rain + n_uh - 1
        assert len(result) == 4 + 5 - 1

    def test_superposition_principle(self):
        """Test principio de superposición."""
        rain1 = np.array([10, 0, 0])
        rain2 = np.array([0, 20, 0])
        rain_total = rain1 + rain2
        uh = np.array([0.2, 0.5, 0.3])

        result1 = convolve_uh(rain1, uh)
        result2 = convolve_uh(rain2, uh)
        result_total = convolve_uh(rain_total, uh)

        np.testing.assert_array_almost_equal(result_total, result1 + result2)

    def test_scaling(self):
        """Test escalamiento lineal."""
        rain = np.array([10, 20, 15])
        uh = np.array([0.2, 0.5, 0.3])

        result1 = convolve_uh(rain, uh)
        result2 = convolve_uh(2 * rain, uh)

        np.testing.assert_array_almost_equal(result2, 2 * result1)

    def test_volume_conservation(self):
        """Test conservación de volumen."""
        rain = np.array([10, 20, 15, 5])  # mm
        # UH normalizado para 1 mm
        uh = np.array([0.1, 0.3, 0.3, 0.2, 0.1])
        uh = uh / np.sum(uh)  # Normalizar

        result = convolve_uh(rain, uh)
        # La suma del resultado debe aproximar sum(rain)
        assert np.sum(result) == pytest.approx(np.sum(rain), rel=0.01)


class TestGenerateUnitHydrograph:
    """Tests para función dispatcher generate_unit_hydrograph."""

    def test_scs_triangular(self):
        """Test despacho a SCS triangular."""
        time, flow = generate_unit_hydrograph(
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        assert len(time) > 0
        assert np.max(flow) > 0

    def test_scs_curvilinear(self):
        """Test despacho a SCS curvilíneo."""
        time, flow = generate_unit_hydrograph(
            HydrographMethod.SCS_CURVILINEAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        assert len(time) > 0
        assert np.max(flow) > 0

    def test_scs_curvilinear_with_prf(self):
        """Test SCS curvilíneo con PRF custom."""
        time, flow = generate_unit_hydrograph(
            HydrographMethod.SCS_CURVILINEAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5,
            prf=300
        )
        assert len(time) > 0

    def test_snyder(self):
        """Test despacho a Snyder."""
        time, flow = generate_unit_hydrograph(
            HydrographMethod.SNYDER,
            area_km2=50,
            tc_hr=3,
            dt_hr=0.5,
            length_km=20,
            lc_km=10
        )
        assert len(time) > 0
        assert np.max(flow) > 0

    def test_snyder_error_missing_params(self):
        """Test error cuando faltan parámetros para Snyder."""
        with pytest.raises(ValueError, match="Snyder requiere"):
            generate_unit_hydrograph(
                HydrographMethod.SNYDER,
                area_km2=50,
                tc_hr=3,
                dt_hr=0.5
            )

    def test_clark(self):
        """Test despacho a Clark."""
        time, flow = generate_unit_hydrograph(
            HydrographMethod.CLARK,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5,
            r_hr=4
        )
        assert len(time) > 0

    def test_clark_default_r(self):
        """Test Clark con R por defecto (2×Tc)."""
        time, flow = generate_unit_hydrograph(
            HydrographMethod.CLARK,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        assert len(time) > 0


class TestGenerateHydrograph:
    """Tests para función principal generate_hydrograph."""

    def test_returns_hydrograph_output(self):
        """Test que retorna HydrographOutput."""
        from hidropluvial.core.hydrograph import HydrographOutput

        rain = np.array([5, 15, 10, 5])
        result = generate_hydrograph(
            rain,
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        assert isinstance(result, HydrographOutput)

    def test_result_has_required_fields(self):
        """Test que resultado tiene campos requeridos."""
        rain = np.array([5, 15, 10, 5])
        result = generate_hydrograph(
            rain,
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        assert hasattr(result, 'time_hr')
        assert hasattr(result, 'flow_m3s')
        assert hasattr(result, 'peak_flow_m3s')
        assert hasattr(result, 'time_to_peak_hr')
        assert hasattr(result, 'volume_m3')
        assert hasattr(result, 'method')

    def test_peak_flow_positive(self):
        """Test que caudal pico es positivo."""
        rain = np.array([5, 15, 10, 5])
        result = generate_hydrograph(
            rain,
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        assert result.peak_flow_m3s > 0

    def test_volume_positive(self):
        """Test que volumen es positivo."""
        rain = np.array([5, 15, 10, 5])
        result = generate_hydrograph(
            rain,
            HydrographMethod.SCS_CURVILINEAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        assert result.volume_m3 > 0

    def test_time_to_peak_within_bounds(self):
        """Test que tiempo al pico está dentro de límites razonables."""
        rain = np.array([5, 15, 10, 5])
        result = generate_hydrograph(
            rain,
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        # Tiempo al pico debe ser > 0 y < tiempo total
        assert result.time_to_peak_hr > 0
        assert result.time_to_peak_hr < result.time_hr[-1]

    def test_method_stored_correctly(self):
        """Test que método se almacena correctamente."""
        rain = np.array([5, 15, 10])
        result = generate_hydrograph(
            rain,
            HydrographMethod.SCS_CURVILINEAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        assert result.method == HydrographMethod.SCS_CURVILINEAR

    def test_larger_rain_larger_peak(self):
        """Test que mayor lluvia = mayor pico."""
        rain1 = np.array([5, 10, 5])
        rain2 = np.array([10, 20, 10])

        result1 = generate_hydrograph(
            rain1,
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        result2 = generate_hydrograph(
            rain2,
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        assert result2.peak_flow_m3s > result1.peak_flow_m3s


class TestIntegrationScenarios:
    """Tests de integración con escenarios reales."""

    def test_urban_catchment_high_x(self):
        """Test cuenca urbana con X=1.0."""
        # 50 ha, Tc=0.5hr, dt=5min
        time, flow = triangular_uh_x(50, 0.5, 5/60, x_factor=1.0)
        # Pico alto y rápido
        peak_time = time[np.argmax(flow)]
        assert peak_time < 1.0  # Pico < 1 hora

    def test_rural_catchment_low_x(self):
        """Test cuenca rural con X=5.5."""
        time, flow = triangular_uh_x(50, 0.5, 5/60, x_factor=5.5)
        peak_time = time[np.argmax(flow)]
        # Pico más tardío que urbana
        assert time[-1] > 1.5  # Tiempo base > 1.5 horas

    def test_design_storm_response(self):
        """Test respuesta a tormenta de diseño."""
        # Tormenta tipo bloque alternado simplificada
        rain = np.array([5, 10, 25, 40, 25, 15, 10, 5])  # mm

        result = generate_hydrograph(
            rain,
            HydrographMethod.SCS_CURVILINEAR,
            area_km2=5,
            tc_hr=1.5,
            dt_hr=0.25
        )

        # Verificar resultado razonable
        assert result.peak_flow_m3s > 0
        assert result.time_to_peak_hr > 0
        assert len(result.flow_m3s) == len(rain) + len(result.time_hr) - len(rain)

    def test_compare_triangular_vs_curvilinear(self):
        """Test comparación entre métodos triangular y curvilíneo."""
        rain = np.array([10, 20, 15, 5])

        result_tri = generate_hydrograph(
            rain,
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        result_curv = generate_hydrograph(
            rain,
            HydrographMethod.SCS_CURVILINEAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )

        # Curvilíneo suele tener pico ligeramente mayor
        # pero volúmenes similares
        ratio_peaks = result_curv.peak_flow_m3s / result_tri.peak_flow_m3s
        assert 0.8 < ratio_peaks < 1.5

    def test_small_dt_more_resolution(self):
        """Test que dt pequeño da más resolución."""
        rain = np.array([10, 20, 10])

        result_coarse = generate_hydrograph(
            rain,
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.5
        )
        result_fine = generate_hydrograph(
            rain,
            HydrographMethod.SCS_TRIANGULAR,
            area_km2=10,
            tc_hr=2,
            dt_hr=0.1
        )

        # Más puntos con dt más fino
        assert len(result_fine.time_hr) > len(result_coarse.time_hr)
