#!/usr/bin/env python3
"""
Script para poblar la base de datos con casos de prueba variados.

Genera análisis con diferentes combinaciones de:
- Métodos de Tc (Kirpich, Temez, Desbordes)
- Tormentas (GZ, Bimodal, SCS-II, Huff)
- Métodos de escorrentía (Racional, SCS-CN)
- Con y sin ponderación de coeficientes
- Diferentes períodos de retorno y factores X
"""

import sys
import os
from pathlib import Path

# Forzar UTF-8 en Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hidropluvial.database import get_database
from hidropluvial.cli.wizard.config import WizardConfig
from hidropluvial.cli.wizard.runner import AnalysisRunner
from hidropluvial.models import CoverageItem


def create_test_basins():
    """Crea cuencas de prueba con diferentes configuraciones."""

    db = get_database()

    # Limpiar DB existente
    print("Limpiando base de datos...")
    with db.connection() as conn:
        conn.execute("DELETE FROM analyses")
        conn.execute("DELETE FROM tc_results")
        # Tablas que pueden o no existir
        try:
            conn.execute("DELETE FROM weighted_coefficients")
        except Exception:
            pass
        try:
            conn.execute("DELETE FROM weighted_items")
        except Exception:
            pass
        try:
            conn.execute("DELETE FROM coverage_items")
        except Exception:
            pass
        conn.execute("DELETE FROM basins")
        conn.execute("DELETE FROM projects")
        conn.commit()
    print("Base de datos limpiada.\n")

    # =========================================================================
    # Cuenca 1: Método Racional con C directo, tormenta GZ
    # =========================================================================
    print("=" * 60)
    print("Cuenca 1: Racional + C directo + GZ")
    print("=" * 60)

    config1 = WizardConfig(
        nombre="Cuenca Urbana Norte",
        area_ha=25.0,
        slope_pct=2.5,
        length_m=800,
        p3_10=45.0,
        c=0.65,
        tc_methods=["desbordes", "kirpich"],
        storm_codes=["gz"],
        return_periods=[2, 5, 10, 25],
        x_factors=[1.0, 1.25, 1.5],
        dt_min=5.0,
        t0_min=5.0,
    )

    runner1 = AnalysisRunner(config1)
    project1, basin1 = runner1.run()
    print(f"Proyecto: {project1.id}")
    print(f"Cuenca: {basin1.id} - {len(basin1.analyses)} análisis")

    # Guardar ponderación de C manualmente
    db.set_weighted_coefficient(
        basin_id=basin1.id,
        coef_type="c",
        weighted_value=0.65,
        items=[
            CoverageItem(description="Zona residencial densa", area_ha=10.0, value=0.70, percentage=40.0),
            CoverageItem(description="Calles pavimentadas", area_ha=8.0, value=0.85, percentage=32.0),
            CoverageItem(description="Parques y jardines", area_ha=7.0, value=0.35, percentage=28.0),
        ],
        table_used="manual",
    )
    print("Ponderación de C guardada.\n")

    # =========================================================================
    # Cuenca 2: Método SCS-CN, tormenta Bimodal
    # =========================================================================
    print("=" * 60)
    print("Cuenca 2: SCS-CN + Bimodal")
    print("=" * 60)

    config2 = WizardConfig(
        nombre="Cuenca Rural Sur",
        area_ha=150.0,
        slope_pct=5.0,
        length_m=2500,
        p3_10=50.0,
        cn=75,
        amc="II",
        lambda_coef=0.2,
        tc_methods=["kirpich", "temez"],
        storm_codes=["bimodal"],
        return_periods=[5, 10, 25, 50],
        x_factors=[1.0],
        dt_min=5.0,
        bimodal_duration_hr=6.0,
        bimodal_peak1=0.25,
        bimodal_peak2=0.75,
        bimodal_vol_split=0.4,
        bimodal_peak_width=0.15,
    )

    runner2 = AnalysisRunner(config2)
    project2, basin2 = runner2.run()
    print(f"Proyecto: {project2.id}")
    print(f"Cuenca: {basin2.id} - {len(basin2.analyses)} análisis\n")

    # =========================================================================
    # Cuenca 3: Ambos métodos (C y CN), tormenta GZ y Bimodal
    # =========================================================================
    print("=" * 60)
    print("Cuenca 3: Racional + SCS-CN + GZ + Bimodal")
    print("=" * 60)

    config3 = WizardConfig(
        nombre="Cuenca Mixta Centro",
        area_ha=80.0,
        slope_pct=3.0,
        length_m=1500,
        p3_10=48.0,
        c=0.55,
        cn=70,
        amc="II",
        lambda_coef=0.2,
        tc_methods=["desbordes", "kirpich", "temez"],
        storm_codes=["gz", "bimodal"],
        return_periods=[10, 25],
        x_factors=[1.0, 1.5],
        dt_min=5.0,
        bimodal_duration_hr=6.0,
        bimodal_peak1=0.30,
        bimodal_peak2=0.70,
        bimodal_vol_split=0.5,
        bimodal_peak_width=0.20,
    )

    runner3 = AnalysisRunner(config3)
    project3, basin3 = runner3.run()
    print(f"Proyecto: {project3.id}")
    print(f"Cuenca: {basin3.id} - {len(basin3.analyses)} análisis\n")

    # =========================================================================
    # Cuenca 4: SCS-CN con CN ponderado, tormenta SCS Type II
    # =========================================================================
    print("=" * 60)
    print("Cuenca 4: SCS-CN ponderado + SCS Type II")
    print("=" * 60)

    config4 = WizardConfig(
        nombre="Cuenca Agricola Este",
        area_ha=500.0,
        slope_pct=1.5,
        length_m=4000,
        p3_10=55.0,
        cn=68,  # CN ponderado
        amc="II",
        lambda_coef=0.2,
        tc_methods=["kirpich", "temez"],
        storm_codes=["scs_ii"],
        return_periods=[10, 25, 50, 100],
        x_factors=[1.0],
        dt_min=10.0,
    )

    runner4 = AnalysisRunner(config4)
    project4, basin4 = runner4.run()
    print(f"Proyecto: {project4.id}")
    print(f"Cuenca: {basin4.id} - {len(basin4.analyses)} análisis\n")

    # Guardar ponderación de CN manualmente para esta cuenca
    db.set_weighted_coefficient(
        basin_id=basin4.id,
        coef_type="cn",
        weighted_value=68,
        items=[
            CoverageItem(description="Cultivos en hilera", area_ha=200.0, value=72, percentage=40.0),
            CoverageItem(description="Pastizal regular", area_ha=150.0, value=69, percentage=30.0),
            CoverageItem(description="Bosque denso", area_ha=100.0, value=55, percentage=20.0),
            CoverageItem(description="Caminos rurales", area_ha=50.0, value=82, percentage=10.0),
        ],
        table_used="scs_tr55",
    )
    print("Ponderación de CN guardada.\n")

    # =========================================================================
    # Cuenca 5: Pequeña cuenca con Huff
    # =========================================================================
    print("=" * 60)
    print("Cuenca 5: Racional + Huff Q2")
    print("=" * 60)

    config5 = WizardConfig(
        nombre="Subcuenca Oeste",
        area_ha=12.0,
        slope_pct=4.0,
        length_m=400,
        p3_10=42.0,
        c=0.72,
        tc_methods=["desbordes"],
        storm_codes=["huff_q2"],
        return_periods=[2, 5, 10],
        x_factors=[1.0, 1.25],
        dt_min=5.0,
        t0_min=3.0,
    )

    runner5 = AnalysisRunner(config5)
    project5, basin5 = runner5.run()
    print(f"Proyecto: {project5.id}")
    print(f"Cuenca: {basin5.id} - {len(basin5.analyses)} análisis\n")

    # =========================================================================
    # Resumen final
    # =========================================================================
    print("=" * 60)
    print("RESUMEN")
    print("=" * 60)

    total_analyses = (
        len(basin1.analyses) +
        len(basin2.analyses) +
        len(basin3.analyses) +
        len(basin4.analyses) +
        len(basin5.analyses)
    )

    print(f"Cuencas creadas: 5")
    print(f"Total de análisis: {total_analyses}")
    print()
    print("Cuenca 1: Racional + C ponderado + GZ")
    print(f"  - {len(basin1.analyses)} análisis")
    print("Cuenca 2: SCS-CN + Bimodal")
    print(f"  - {len(basin2.analyses)} análisis")
    print("Cuenca 3: Racional + SCS-CN + GZ + Bimodal")
    print(f"  - {len(basin3.analyses)} análisis")
    print("Cuenca 4: SCS-CN ponderado + SCS Type II")
    print(f"  - {len(basin4.analyses)} análisis")
    print("Cuenca 5: Racional + Huff Q2")
    print(f"  - {len(basin5.analyses)} análisis")


if __name__ == "__main__":
    create_test_basins()
