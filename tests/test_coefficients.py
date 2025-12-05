"""
Tests para core/coefficients.py - Tablas de coeficientes C y CN.
"""

import pytest

from hidropluvial.core.coefficients import (
    # Dataclasses
    CoefficientEntry,
    ChowCEntry,
    FHWACEntry,
    CNEntry,
    # Tablas
    FHWA_C_TABLE,
    VEN_TE_CHOW_C_TABLE,
    URUGUAY_C_TABLE,
    SCS_CN_URBAN,
    SCS_CN_AGRICULTURAL,
    C_TABLES,
    CN_TABLES,
    # Funciones
    get_c_for_tr_from_table,
    adjust_c_for_tr,
    weighted_c,
    weighted_cn,
    format_c_table,
    format_cn_table,
)


class TestCoefficientEntry:
    """Tests para CoefficientEntry."""

    def test_c_range_property(self):
        """Test propiedad c_range."""
        entry = CoefficientEntry("Cat", "Desc", 0.30, 0.50, 0.40)
        assert entry.c_range == "0.30-0.50"

    def test_c_recommended_with_typical(self):
        """Test c_recommended cuando hay c_typical."""
        entry = CoefficientEntry("Cat", "Desc", 0.30, 0.50, 0.42)
        assert entry.c_recommended == 0.42

    def test_c_recommended_without_typical(self):
        """Test c_recommended sin c_typical (usa promedio)."""
        entry = CoefficientEntry("Cat", "Desc", 0.30, 0.50)
        assert entry.c_recommended == 0.40


class TestChowCEntry:
    """Tests para ChowCEntry (Ven Te Chow)."""

    def test_get_c_exact_tr(self):
        """Test get_c con Tr exactos."""
        entry = ChowCEntry("Cat", "Desc", 0.25, 0.30, 0.35, 0.40, 0.45, 0.50)
        assert entry.get_c(2) == 0.25
        assert entry.get_c(5) == 0.30
        assert entry.get_c(10) == 0.35
        assert entry.get_c(25) == 0.40
        assert entry.get_c(50) == 0.45
        assert entry.get_c(100) == 0.50

    def test_get_c_interpolation(self):
        """Test get_c con interpolacion."""
        entry = ChowCEntry("Cat", "Desc", 0.20, 0.30, 0.40, 0.50, 0.60, 0.70)
        # Tr = 7 esta entre 5 y 10
        c_7 = entry.get_c(7)
        assert 0.30 < c_7 < 0.40

        # Tr = 15 esta entre 10 y 25
        c_15 = entry.get_c(15)
        assert 0.40 < c_15 < 0.50

    def test_get_c_below_min(self):
        """Test get_c con Tr < 2."""
        entry = ChowCEntry("Cat", "Desc", 0.25, 0.30, 0.35, 0.40, 0.45, 0.50)
        assert entry.get_c(1) == 0.25

    def test_get_c_above_max(self):
        """Test get_c con Tr > 100."""
        entry = ChowCEntry("Cat", "Desc", 0.25, 0.30, 0.35, 0.40, 0.45, 0.50)
        assert entry.get_c(200) == 0.50


class TestFHWACEntry:
    """Tests para FHWACEntry."""

    def test_get_c_base_tr(self):
        """Test get_c con Tr <= 10 (sin ajuste)."""
        entry = FHWACEntry("Cat", "Desc", 0.60)
        assert entry.get_c(2) == 0.60
        assert entry.get_c(5) == 0.60
        assert entry.get_c(10) == 0.60

    def test_get_c_tr25(self):
        """Test get_c con Tr = 25 (factor 1.1)."""
        entry = FHWACEntry("Cat", "Desc", 0.60)
        assert entry.get_c(25) == pytest.approx(0.66, rel=0.01)

    def test_get_c_tr50(self):
        """Test get_c con Tr = 50 (factor 1.2)."""
        entry = FHWACEntry("Cat", "Desc", 0.60)
        assert entry.get_c(50) == pytest.approx(0.72, rel=0.01)

    def test_get_c_tr100(self):
        """Test get_c con Tr = 100 (factor 1.25)."""
        entry = FHWACEntry("Cat", "Desc", 0.60)
        assert entry.get_c(100) == pytest.approx(0.75, rel=0.01)

    def test_get_c_above_100(self):
        """Test get_c con Tr > 100."""
        entry = FHWACEntry("Cat", "Desc", 0.60)
        assert entry.get_c(200) == pytest.approx(0.75, rel=0.01)

    def test_get_c_max_one(self):
        """Test que C no excede 1.0."""
        entry = FHWACEntry("Cat", "Desc", 0.90)
        # Con factor 1.25, seria 1.125, pero debe ser max 1.0
        assert entry.get_c(100) == 1.0

    def test_get_c_interpolation_25_50(self):
        """Test interpolacion entre Tr 25 y 50."""
        entry = FHWACEntry("Cat", "Desc", 0.50)
        c_37 = entry.get_c(37)
        c_25 = entry.get_c(25)
        c_50 = entry.get_c(50)
        assert c_25 < c_37 < c_50


class TestCNEntry:
    """Tests para CNEntry."""

    def test_get_cn_all_groups(self):
        """Test get_cn para todos los grupos."""
        entry = CNEntry("Cat", "Desc", "Buena", 39, 61, 74, 80)
        assert entry.get_cn("A") == 39
        assert entry.get_cn("B") == 61
        assert entry.get_cn("C") == 74
        assert entry.get_cn("D") == 80

    def test_get_cn_lowercase(self):
        """Test get_cn con minusculas."""
        entry = CNEntry("Cat", "Desc", "Buena", 39, 61, 74, 80)
        assert entry.get_cn("a") == 39
        assert entry.get_cn("b") == 61

    def test_get_cn_invalid_group(self):
        """Test get_cn con grupo invalido (default B)."""
        entry = CNEntry("Cat", "Desc", "Buena", 39, 61, 74, 80)
        assert entry.get_cn("X") == 61  # Default a B


class TestTables:
    """Tests para las tablas de datos."""

    def test_fhwa_table_not_empty(self):
        """Test tabla FHWA no vacia."""
        assert len(FHWA_C_TABLE) > 0
        assert all(isinstance(e, FHWACEntry) for e in FHWA_C_TABLE)

    def test_chow_table_not_empty(self):
        """Test tabla Ven Te Chow no vacia."""
        assert len(VEN_TE_CHOW_C_TABLE) > 0
        assert all(isinstance(e, ChowCEntry) for e in VEN_TE_CHOW_C_TABLE)

    def test_uruguay_table_not_empty(self):
        """Test tabla Uruguay no vacia."""
        assert len(URUGUAY_C_TABLE) > 0
        assert all(isinstance(e, CoefficientEntry) for e in URUGUAY_C_TABLE)

    def test_cn_urban_table_not_empty(self):
        """Test tabla CN urbana no vacia."""
        assert len(SCS_CN_URBAN) > 0
        assert all(isinstance(e, CNEntry) for e in SCS_CN_URBAN)

    def test_cn_agricultural_table_not_empty(self):
        """Test tabla CN agricola no vacia."""
        assert len(SCS_CN_AGRICULTURAL) > 0
        assert all(isinstance(e, CNEntry) for e in SCS_CN_AGRICULTURAL)

    def test_c_tables_dict(self):
        """Test diccionario C_TABLES."""
        assert "fhwa" in C_TABLES
        assert "chow" in C_TABLES
        assert "uruguay" in C_TABLES

    def test_cn_tables_dict(self):
        """Test diccionario CN_TABLES."""
        assert "urban" in CN_TABLES
        assert "agricultural" in CN_TABLES


class TestGetCForTRFromTable:
    """Tests para get_c_for_tr_from_table."""

    def test_chow_table(self):
        """Test con tabla Chow."""
        c = get_c_for_tr_from_table(0, 10, "chow")
        assert 0 < c < 1

    def test_fhwa_table(self):
        """Test con tabla FHWA."""
        c = get_c_for_tr_from_table(0, 10, "fhwa")
        assert 0 < c < 1

    def test_uruguay_table(self):
        """Test con tabla Uruguay."""
        c = get_c_for_tr_from_table(0, 10, "uruguay")
        assert 0 < c < 1

    def test_invalid_table(self):
        """Test con tabla invalida."""
        with pytest.raises(ValueError, match="no disponible"):
            get_c_for_tr_from_table(0, 10, "invalid_table")

    def test_invalid_index_negative(self):
        """Test con indice negativo."""
        with pytest.raises(ValueError, match="fuera de rango"):
            get_c_for_tr_from_table(-1, 10, "chow")

    def test_invalid_index_too_large(self):
        """Test con indice muy grande."""
        with pytest.raises(ValueError, match="fuera de rango"):
            get_c_for_tr_from_table(1000, 10, "chow")


class TestAdjustCForTR:
    """Tests para adjust_c_for_tr."""

    def test_same_tr(self):
        """Test con mismo Tr."""
        assert adjust_c_for_tr(0.5, 2, 2) == 0.5

    def test_higher_tr_increases_c(self):
        """Test que Tr mayor incrementa C."""
        c_base = 0.5
        c_10 = adjust_c_for_tr(c_base, 10, 2)
        c_25 = adjust_c_for_tr(c_base, 25, 2)
        c_100 = adjust_c_for_tr(c_base, 100, 2)

        assert c_10 > c_base
        assert c_25 > c_10
        assert c_100 > c_25

    def test_max_one(self):
        """Test que C no excede 1.0."""
        result = adjust_c_for_tr(0.9, 100, 2)
        assert result <= 1.0

    def test_below_min_tr(self):
        """Test con Tr < 2."""
        result = adjust_c_for_tr(0.5, 1, 2)
        # Deberia usar factor para Tr=2
        assert result == pytest.approx(0.5, rel=0.1)

    def test_above_max_tr(self):
        """Test con Tr > 100."""
        result = adjust_c_for_tr(0.5, 200, 2)
        # Deberia usar factor para Tr=100
        assert result == pytest.approx(adjust_c_for_tr(0.5, 100, 2), rel=0.01)


class TestWeightedC:
    """Tests para weighted_c."""

    def test_equal_areas(self):
        """Test con areas iguales."""
        areas = [10, 10, 10]
        coeffs = [0.3, 0.5, 0.7]
        result = weighted_c(areas, coeffs)
        assert result == pytest.approx(0.5, rel=0.01)

    def test_different_areas(self):
        """Test con areas diferentes."""
        areas = [100, 50]
        coeffs = [0.3, 0.6]
        # (100*0.3 + 50*0.6) / 150 = (30 + 30) / 150 = 0.4
        result = weighted_c(areas, coeffs)
        assert result == pytest.approx(0.4, rel=0.01)

    def test_single_area(self):
        """Test con una sola area."""
        result = weighted_c([100], [0.5])
        assert result == 0.5

    def test_mismatched_lengths(self):
        """Test con listas de diferente longitud."""
        with pytest.raises(ValueError, match="igual longitud"):
            weighted_c([10, 20], [0.5])

    def test_zero_total_area(self):
        """Test con area total cero."""
        with pytest.raises(ValueError, match="no puede ser cero"):
            weighted_c([0, 0], [0.5, 0.6])


class TestWeightedCN:
    """Tests para weighted_cn."""

    def test_equal_areas(self):
        """Test con areas iguales."""
        areas = [10, 10]
        cns = [70, 80]
        result = weighted_cn(areas, cns)
        assert result == pytest.approx(75, rel=0.01)

    def test_different_areas(self):
        """Test con areas diferentes."""
        areas = [100, 50]
        cns = [60, 90]
        # (100*60 + 50*90) / 150 = (6000 + 4500) / 150 = 70
        result = weighted_cn(areas, cns)
        assert result == pytest.approx(70, rel=0.01)

    def test_single_area(self):
        """Test con una sola area."""
        result = weighted_cn([100], [75])
        assert result == 75

    def test_mismatched_lengths(self):
        """Test con listas de diferente longitud."""
        with pytest.raises(ValueError, match="igual longitud"):
            weighted_cn([10, 20], [75])

    def test_zero_total_area(self):
        """Test con area total cero."""
        with pytest.raises(ValueError, match="no puede ser cero"):
            weighted_cn([0, 0], [75, 80])


class TestFormatCTable:
    """Tests para format_c_table."""

    def test_empty_table(self):
        """Test con tabla vacia."""
        result = format_c_table([], "Test Table")
        assert "Test Table" in result

    def test_coefficient_entry_table(self):
        """Test con tabla CoefficientEntry."""
        table = [
            CoefficientEntry("Urban", "Centro", 0.70, 0.90, 0.80),
            CoefficientEntry("Urban", "Residencial", 0.40, 0.60, 0.50),
        ]
        result = format_c_table(table, "Test Uruguay")
        assert "Test Uruguay" in result
        assert "Centro" in result
        assert "0.70" in result
        assert "0.90" in result

    def test_chow_entry_table(self):
        """Test con tabla ChowCEntry."""
        table = [
            ChowCEntry("Comercial", "Centro", 0.75, 0.80, 0.85, 0.88, 0.90, 0.95),
        ]
        result = format_c_table(table, "Test Chow")
        assert "Test Chow" in result
        assert "Centro" in result
        assert "0.75" in result

    def test_chow_selection_mode(self):
        """Test Chow en modo seleccion."""
        table = [
            ChowCEntry("Comercial", "Centro", 0.75, 0.80, 0.85, 0.88, 0.90, 0.95),
        ]
        result = format_c_table(table, "Test Chow", selection_mode=True)
        assert "*Tr2*" in result
        assert "referencia" in result.lower()

    def test_fhwa_entry_table(self):
        """Test con tabla FHWACEntry."""
        table = [
            FHWACEntry("Comercial", "Centro comercial", 0.85),
        ]
        result = format_c_table(table, "Test FHWA", tr=25)
        assert "Test FHWA" in result
        assert "0.85" in result
        assert "Tr=25" in result


class TestFormatCNTable:
    """Tests para format_cn_table."""

    def test_basic_format(self):
        """Test formato basico."""
        table = [
            CNEntry("Residencial", "Lotes 500 m2", "N/A", 77, 85, 90, 92),
            CNEntry("Comercial", "Distritos", "N/A", 89, 92, 94, 95),
        ]
        result = format_cn_table(table, "Test CN Table")
        assert "Test CN Table" in result
        assert "Residencial" in result
        assert "Comercial" in result
        assert "77" in result
        assert "85" in result

    def test_includes_soil_groups(self):
        """Test incluye descripcion de grupos."""
        table = [CNEntry("Cat", "Desc", "Buena", 39, 61, 74, 80)]
        result = format_cn_table(table, "Test")
        assert "Grupos hidrologicos" in result
        assert "Alta infiltracion" in result
        assert "arcilla" in result


class TestIntegration:
    """Tests de integracion."""

    def test_weighted_c_from_table_entries(self):
        """Test ponderacion con entradas de tabla real."""
        # Simular seleccion de la tabla Uruguay
        areas = [50, 30, 20]  # hectareas
        # Centro ciudad, Residencial media, Areas verdes
        coeffs = [0.80, 0.50, 0.18]

        result = weighted_c(areas, coeffs)
        # (50*0.80 + 30*0.50 + 20*0.18) / 100 = (40 + 15 + 3.6) / 100 = 0.586
        assert result == pytest.approx(0.586, rel=0.01)

    def test_weighted_cn_from_table_entries(self):
        """Test ponderacion CN con entradas reales."""
        areas = [60, 40]
        # Residencial y Cesped
        cns = [85, 61]

        result = weighted_cn(areas, cns)
        # (60*85 + 40*61) / 100 = (5100 + 2440) / 100 = 75.4
        assert result == pytest.approx(75.4, rel=0.01)

    def test_chow_c_progression(self):
        """Test que C de Chow aumenta con Tr."""
        entry = VEN_TE_CHOW_C_TABLE[0]  # Primera entrada

        c_2 = entry.get_c(2)
        c_10 = entry.get_c(10)
        c_50 = entry.get_c(50)
        c_100 = entry.get_c(100)

        assert c_2 < c_10 < c_50 < c_100

    def test_fhwa_c_progression(self):
        """Test que C de FHWA aumenta con Tr."""
        entry = FHWA_C_TABLE[0]  # Primera entrada

        c_10 = entry.get_c(10)
        c_25 = entry.get_c(25)
        c_50 = entry.get_c(50)
        c_100 = entry.get_c(100)

        assert c_10 <= c_25 <= c_50 <= c_100
