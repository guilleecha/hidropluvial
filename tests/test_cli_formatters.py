"""
Tests para cli/formatters.py - Utilidades de formateo CLI.
"""

import pytest

from hidropluvial.cli.formatters import format_flow, format_volume_hm3


class TestFormatFlow:
    """Tests para format_flow."""

    def test_none_value(self):
        """Test valor None."""
        assert format_flow(None) == "-"

    def test_zero(self):
        """Test valor cero."""
        assert format_flow(0) == "0"

    def test_large_flow(self):
        """Test caudales grandes (>=100)."""
        assert format_flow(100) == "100"
        assert format_flow(150.7) == "151"
        assert format_flow(1234.5) == "1234"  # f-string truncates

    def test_medium_flow(self):
        """Test caudales medianos (10-100)."""
        assert format_flow(10) == "10.0"
        assert format_flow(50.75) == "50.8"
        assert format_flow(99.99) == "100.0"

    def test_small_flow(self):
        """Test caudales pequeños (1-10)."""
        assert format_flow(1) == "1.00"
        assert format_flow(5.123) == "5.12"
        assert format_flow(9.999) == "10.00"

    def test_very_small_flow(self):
        """Test caudales muy pequeños (0.001-1) - usa 3 decimales."""
        assert format_flow(0.1) == "0.100"
        assert format_flow(0.567) == "0.567"
        assert format_flow(0.999) == "0.999"
        assert format_flow(0.05) == "0.050"
        assert format_flow(0.001) == "0.001"

    def test_tiny_flow(self):
        """Test caudales diminutos (<0.001) - muestra 0.00."""
        assert format_flow(0.0001234) == "0.00"
        assert format_flow(0.00001) == "0.00"


class TestFormatVolumeHm3:
    """Tests para format_volume_hm3 - máximo 3 decimales según rango."""

    def test_none_value(self):
        """Test valor None."""
        assert format_volume_hm3(None) == "-"

    def test_zero_volume(self):
        """Test volumen cero."""
        assert format_volume_hm3(0) == "0"

    def test_large_volume(self):
        """Test volúmenes grandes (>=1 hm³)."""
        # 1 hm³ = 1_000_000 m³
        assert format_volume_hm3(1_000_000) == "1.00"      # 1 hm³ -> 2 decimales
        assert format_volume_hm3(1_500_000) == "1.50"      # 1.5 hm³
        assert format_volume_hm3(10_000_000) == "10.0"     # 10 hm³ -> 1 decimal
        assert format_volume_hm3(12_000_000) == "12.0"     # 12 hm³
        assert format_volume_hm3(100_000_000) == "100"     # 100 hm³ -> 0 decimales

    def test_medium_volume(self):
        """Test volúmenes medianos (0.001-1 hm³) - usa 3 decimales."""
        assert format_volume_hm3(100_000) == "0.100"      # 0.1 hm³
        assert format_volume_hm3(500_000) == "0.500"      # 0.5 hm³
        assert format_volume_hm3(10_000) == "0.010"       # 0.01 hm³
        assert format_volume_hm3(15_000) == "0.015"       # 0.015 hm³
        assert format_volume_hm3(1_000) == "0.001"        # 0.001 hm³

    def test_small_volume(self):
        """Test volúmenes pequeños (<0.001 hm³) - muestra 0.00."""
        assert format_volume_hm3(100) == "0.00"          # 0.0001 hm³ -> muy pequeño
        assert format_volume_hm3(10) == "0.00"           # muy pequeño
