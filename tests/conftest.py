"""Configuración de pytest para tests de hidropluvial."""

import pytest
import numpy as np

from hidropluvial.config import ShermanCoefficients


@pytest.fixture
def sherman_coeffs():
    """Coeficientes Sherman típicos para tests."""
    return ShermanCoefficients(k=2150.0, m=0.22, c=15.0, n=0.75)


@pytest.fixture
def sample_catchment_params():
    """Parámetros de cuenca de ejemplo."""
    return {
        "area_km2": 25.0,
        "cn": 75,
        "tc_hr": 1.5,
        "slope": 0.02,
    }


@pytest.fixture
def sample_rainfall_series():
    """Serie de precipitación de ejemplo (mm)."""
    return np.array([0.5, 1.2, 3.5, 8.2, 15.0, 12.0, 6.5, 3.0, 1.5, 0.8])
