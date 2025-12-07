"""
Tests para CoefficientLoader - Sistema unificado de tablas de coeficientes.
"""

import pytest

from hidropluvial.data import (
    CoefficientLoader,
    CoefficientTable,
    CNValue,
    CoverType,
    TableSource,
    TableType,
)


class TestCoefficientLoaderInit:
    """Tests de inicialización."""

    def test_init_without_db(self):
        """Test inicialización sin base de datos."""
        loader = CoefficientLoader()
        assert loader.db is None
        assert loader.user_id is None

    def test_init_with_future_db(self):
        """Test inicialización con DB (preparación futuro)."""
        loader = CoefficientLoader(db_session="mock", user_id=123)
        assert loader.db == "mock"
        assert loader.user_id == 123


class TestListTables:
    """Tests para listado de tablas."""

    def test_list_all_tables(self):
        """Test listar todas las tablas."""
        loader = CoefficientLoader()
        tables = loader.list_tables()

        assert len(tables) > 0
        assert all(isinstance(t, CoefficientTable) for t in tables)

    def test_list_cn_tables(self):
        """Test listar solo tablas CN."""
        loader = CoefficientLoader()
        tables = loader.list_tables(table_type=TableType.CN)

        assert len(tables) > 0
        assert all(t.table_type == TableType.CN for t in tables)

    def test_list_c_tables(self):
        """Test listar solo tablas C."""
        loader = CoefficientLoader()
        tables = loader.list_tables(table_type=TableType.C)

        assert len(tables) > 0
        assert all(t.table_type == TableType.C for t in tables)

    def test_system_tables_not_editable(self):
        """Test que tablas sistema no son editables."""
        loader = CoefficientLoader()
        tables = loader.list_tables()

        for table in tables:
            if table.source == TableSource.SYSTEM:
                assert table.is_editable is False

    def test_tr55_table_exists(self):
        """Test que existe tabla TR-55."""
        loader = CoefficientLoader()
        tables = loader.list_tables(table_type=TableType.CN)

        table_ids = [t.id for t in tables]
        assert "system:tr55" in table_ids

    def test_chow_table_exists(self):
        """Test que existe tabla Ven Te Chow."""
        loader = CoefficientLoader()
        tables = loader.list_tables(table_type=TableType.C)

        table_ids = [t.id for t in tables]
        assert "system:chow" in table_ids

    def test_table_has_metadata(self):
        """Test que tablas tienen metadata completa."""
        loader = CoefficientLoader()
        table = loader.get_table("system:tr55")

        assert table is not None
        assert table.name == "TR-55 (NRCS)"
        assert table.description is not None
        assert table.reference is not None


class TestGetTable:
    """Tests para obtener tabla específica."""

    def test_get_existing_table(self):
        """Test obtener tabla existente."""
        loader = CoefficientLoader()
        table = loader.get_table("system:tr55")

        assert table is not None
        assert table.id == "system:tr55"
        assert table.table_type == TableType.CN

    def test_get_nonexistent_table(self):
        """Test obtener tabla inexistente."""
        loader = CoefficientLoader()
        table = loader.get_table("system:nonexistent")

        assert table is None


class TestCoverTypes:
    """Tests para tipos de cobertura."""

    def test_get_cn_cover_types(self):
        """Test obtener tipos de cobertura CN."""
        loader = CoefficientLoader()
        covers = loader.get_cover_types("system:tr55")

        assert len(covers) > 0
        assert all(isinstance(c, CoverType) for c in covers)

    def test_cover_type_has_code_and_name(self):
        """Test que tipos de cobertura tienen código y nombre."""
        loader = CoefficientLoader()
        covers = loader.get_cover_types("system:tr55")

        for cover in covers:
            assert cover.code is not None
            assert cover.name is not None

    def test_get_c_cover_types(self):
        """Test obtener tipos de cobertura C."""
        loader = CoefficientLoader()
        covers = loader.get_cover_types("system:chow")

        assert len(covers) > 0
        assert all(isinstance(c, CoverType) for c in covers)


class TestGetCN:
    """Tests para obtención de valores CN."""

    def test_get_cn_residential(self):
        """Test obtener CN para zona residencial."""
        loader = CoefficientLoader()
        cn = loader.get_cn("system:tr55", "residential_1000m2", "B")

        assert cn is not None
        assert cn == 75  # Valor conocido de TR-55

    def test_get_cn_all_soil_groups(self):
        """Test obtener CN para todos los grupos hidrológicos."""
        loader = CoefficientLoader()

        cn_a = loader.get_cn("system:tr55", "residential_1000m2", "A")
        cn_b = loader.get_cn("system:tr55", "residential_1000m2", "B")
        cn_c = loader.get_cn("system:tr55", "residential_1000m2", "C")
        cn_d = loader.get_cn("system:tr55", "residential_1000m2", "D")

        assert cn_a == 61
        assert cn_b == 75
        assert cn_c == 83
        assert cn_d == 87

    def test_get_cn_impervious(self):
        """Test CN para superficie impermeable."""
        loader = CoefficientLoader()
        cn = loader.get_cn("system:tr55", "impervious", "B")

        assert cn == 98

    def test_get_cn_nonexistent_cover(self):
        """Test CN para cobertura inexistente."""
        loader = CoefficientLoader()
        cn = loader.get_cn("system:tr55", "nonexistent_type", "B")

        assert cn is None

    def test_get_cn_case_insensitive_soil_group(self):
        """Test que grupo hidrológico es case-insensitive."""
        loader = CoefficientLoader()

        cn_upper = loader.get_cn("system:tr55", "residential_1000m2", "B")
        cn_lower = loader.get_cn("system:tr55", "residential_1000m2", "b")

        assert cn_upper == cn_lower


class TestGetCNValues:
    """Tests para obtención de todos los valores CN."""

    def test_get_cn_values_returns_all_groups(self):
        """Test que get_cn_values retorna todos los grupos."""
        loader = CoefficientLoader()
        values = loader.get_cn_values("system:tr55", "residential_1000m2")

        assert values is not None
        assert values.cn_a == 61
        assert values.cn_b == 75
        assert values.cn_c == 83
        assert values.cn_d == 87

    def test_cn_value_get_cn_method(self):
        """Test método get_cn de CNValue."""
        loader = CoefficientLoader()
        values = loader.get_cn_values("system:tr55", "commercial_85")

        assert values.get_cn("A") == 89
        assert values.get_cn("B") == 92
        assert values.get_cn("C") == 94
        assert values.get_cn("D") == 95


class TestGetC:
    """Tests para obtención de valores C."""

    def test_get_c_by_index(self):
        """Test obtener C por índice de tabla."""
        loader = CoefficientLoader()
        c = loader.get_c_by_index("system:chow", 0, return_period=10)

        assert c is not None
        assert 0 < c <= 1

    def test_get_c_varies_with_tr_chow(self):
        """Test que C varía con Tr en tabla Chow."""
        loader = CoefficientLoader()

        c_tr2 = loader.get_c_by_index("system:chow", 0, return_period=2)
        c_tr100 = loader.get_c_by_index("system:chow", 0, return_period=100)

        assert c_tr2 is not None
        assert c_tr100 is not None
        assert c_tr100 > c_tr2  # C aumenta con Tr

    def test_get_c_invalid_table(self):
        """Test obtener C de tabla inexistente."""
        loader = CoefficientLoader()
        c = loader.get_c_by_index("system:nonexistent", 0)

        assert c is None

    def test_get_c_invalid_index(self):
        """Test obtener C con índice inválido."""
        loader = CoefficientLoader()
        c = loader.get_c_by_index("system:chow", 9999)

        assert c is None


class TestTableIdParsing:
    """Tests para parsing de IDs de tabla."""

    def test_parse_system_id(self):
        """Test parsear ID de sistema."""
        loader = CoefficientLoader()
        source, key = loader._parse_table_id("system:tr55")

        assert source == "system"
        assert key == "tr55"

    def test_parse_user_id(self):
        """Test parsear ID de usuario."""
        loader = CoefficientLoader()
        source, key = loader._parse_table_id("user:123")

        assert source == "user"
        assert key == "123"

    def test_parse_id_without_prefix(self):
        """Test parsear ID sin prefijo (default sistema)."""
        loader = CoefficientLoader()
        source, key = loader._parse_table_id("tr55")

        assert source == "system"
        assert key == "tr55"


class TestCopyTable:
    """Tests para copia de tablas (Fase 2)."""

    def test_copy_table_not_implemented(self):
        """Test que copiar tabla lanza NotImplementedError."""
        loader = CoefficientLoader()

        with pytest.raises(NotImplementedError) as excinfo:
            loader.copy_table("system:tr55", "Mi tabla")

        assert "Fase 2" in str(excinfo.value)


class TestCaching:
    """Tests para caching de datos."""

    def test_cn_data_cached(self):
        """Test que datos CN se cachean."""
        loader1 = CoefficientLoader()
        loader2 = CoefficientLoader()

        # Primera carga
        cn1 = loader1.get_cn("system:tr55", "residential_1000m2", "B")
        # Segunda carga (debería usar cache)
        cn2 = loader2.get_cn("system:tr55", "residential_1000m2", "B")

        assert cn1 == cn2
        # Cache es de clase, ambos usan el mismo
        assert CoefficientLoader._cn_cache is not None


class TestIntegration:
    """Tests de integración."""

    def test_full_workflow_cn(self):
        """Test flujo completo para CN."""
        loader = CoefficientLoader()

        # 1. Listar tablas CN
        cn_tables = loader.list_tables(table_type=TableType.CN)
        assert len(cn_tables) > 0

        # 2. Seleccionar TR-55
        table = loader.get_table("system:tr55")
        assert table is not None

        # 3. Listar coberturas
        covers = loader.get_cover_types("system:tr55")
        assert len(covers) > 0

        # 4. Obtener CN para una cobertura
        cn = loader.get_cn("system:tr55", covers[0].code, "B")
        assert cn is not None
        assert 30 <= cn <= 100

    def test_full_workflow_c(self):
        """Test flujo completo para C."""
        loader = CoefficientLoader()

        # 1. Listar tablas C
        c_tables = loader.list_tables(table_type=TableType.C)
        assert len(c_tables) > 0

        # 2. Seleccionar Chow
        table = loader.get_table("system:chow")
        assert table is not None

        # 3. Obtener C para diferentes Tr
        c_values = []
        for tr in [2, 5, 10, 25, 50, 100]:
            c = loader.get_c_by_index("system:chow", 0, return_period=tr)
            if c is not None:
                c_values.append(c)

        # C debe aumentar con Tr
        assert len(c_values) > 1
        assert c_values == sorted(c_values)
