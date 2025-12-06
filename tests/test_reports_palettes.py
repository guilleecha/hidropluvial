"""
Tests para el módulo de paletas de colores.
"""

import pytest

from hidropluvial.reports.palettes import (
    ColorPalette,
    PaletteType,
    PALETTES,
    get_palette,
    list_palettes,
    set_active_palette,
    get_active_palette,
    get_series_colors,
    get_series_styles,
)


class TestColorPalette:
    """Tests para ColorPalette."""

    def test_create_palette(self):
        """Test crear paleta."""
        palette = ColorPalette(
            name="test",
            description="Test palette",
            colors=["red", "blue", "green"],
            styles=["solid", "dashed", "dotted"],
        )
        assert palette.name == "test"
        assert len(palette.colors) == 3
        assert len(palette.styles) == 3

    def test_get_color_cyclic(self):
        """Test obtener color cíclico."""
        palette = ColorPalette(
            name="test",
            description="Test",
            colors=["red", "blue"],
            styles=["solid"],
        )
        assert palette.get_color(0) == "red"
        assert palette.get_color(1) == "blue"
        assert palette.get_color(2) == "red"  # Cicla
        assert palette.get_color(3) == "blue"

    def test_get_style_cyclic(self):
        """Test obtener estilo cíclico."""
        palette = ColorPalette(
            name="test",
            description="Test",
            colors=["red"],
            styles=["solid", "dashed"],
        )
        assert palette.get_style(0) == "solid"
        assert palette.get_style(1) == "dashed"
        assert palette.get_style(2) == "solid"

    def test_default_fill_color(self):
        """Test color de relleno por defecto."""
        palette = ColorPalette(
            name="test",
            description="Test",
            colors=["red"],
            styles=["solid"],
        )
        assert palette.fill_color == "blue!30"


class TestPredefinedPalettes:
    """Tests para paletas predefinidas."""

    def test_all_palettes_exist(self):
        """Test que todas las paletas definidas en el enum existen."""
        for ptype in PaletteType:
            assert ptype.value in PALETTES

    def test_default_palette_exists(self):
        """Test paleta default existe."""
        assert "default" in PALETTES
        assert len(PALETTES["default"].colors) >= 5

    def test_professional_palette_exists(self):
        """Test paleta professional existe."""
        assert "professional" in PALETTES

    def test_grayscale_palette_exists(self):
        """Test paleta grayscale existe."""
        assert "grayscale" in PALETTES

    def test_hydrology_palette_exists(self):
        """Test paleta hydrology existe."""
        assert "hydrology" in PALETTES


class TestGetPalette:
    """Tests para get_palette."""

    def test_get_existing_palette(self):
        """Test obtener paleta existente."""
        palette = get_palette("default")
        assert isinstance(palette, ColorPalette)
        assert palette.name == "default"

    def test_get_palette_case_insensitive(self):
        """Test get_palette es case-insensitive."""
        palette = get_palette("DEFAULT")
        assert palette.name == "default"

    def test_get_nonexistent_palette_raises(self):
        """Test paleta inexistente lanza error."""
        with pytest.raises(ValueError) as exc_info:
            get_palette("nonexistent")
        assert "no encontrada" in str(exc_info.value)
        assert "Disponibles" in str(exc_info.value)


class TestListPalettes:
    """Tests para list_palettes."""

    def test_returns_list(self):
        """Test retorna lista."""
        result = list_palettes()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_list_contains_required_keys(self):
        """Test cada elemento tiene las claves requeridas."""
        result = list_palettes()
        for item in result:
            assert "name" in item
            assert "description" in item
            assert "n_colors" in item

    def test_default_in_list(self):
        """Test default está en la lista."""
        result = list_palettes()
        names = [p["name"] for p in result]
        assert "default" in names


class TestActivePalette:
    """Tests para paleta activa."""

    def test_set_and_get_active(self):
        """Test establecer y obtener paleta activa."""
        set_active_palette("professional")
        active = get_active_palette()
        assert active.name == "professional"

    def test_get_active_default(self):
        """Test obtener activa retorna default si no se estableció."""
        # Reset estado global
        import hidropluvial.reports.palettes as palettes
        palettes._active_palette = None

        active = get_active_palette()
        assert active.name == "default"

    def test_set_invalid_raises(self):
        """Test establecer paleta inválida lanza error."""
        with pytest.raises(ValueError):
            set_active_palette("invalid_palette")


class TestGetSeriesColorsAndStyles:
    """Tests para get_series_colors y get_series_styles."""

    def test_get_series_colors_default(self):
        """Test obtener colores por defecto."""
        colors = get_series_colors()
        assert isinstance(colors, list)
        assert len(colors) > 0

    def test_get_series_colors_specific_palette(self):
        """Test obtener colores de paleta específica."""
        colors = get_series_colors("grayscale")
        assert all("gray" in c or c == "black" for c in colors)

    def test_get_series_styles_default(self):
        """Test obtener estilos por defecto."""
        styles = get_series_styles()
        assert isinstance(styles, list)
        assert "solid" in styles

    def test_get_series_styles_specific_palette(self):
        """Test obtener estilos de paleta específica."""
        styles = get_series_styles("contrast")
        assert any("thick" in s for s in styles)
