"""
Comando batch para análisis desde archivo YAML.
"""

from pathlib import Path
from typing import Annotated, Optional

import numpy as np
import typer

from hidropluvial.core import (
    alternating_blocks_dinagua,
    rainfall_excess_series,
    scs_triangular_uh,
)
from hidropluvial.cli.session.base import get_session_manager


def session_batch(
    config_file: Annotated[str, typer.Argument(help="Archivo YAML de configuración")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo LaTeX de salida")] = None,
):
    """
    Ejecuta análisis batch desde archivo YAML.

    Formato del archivo YAML:
    ```yaml
    session:
      name: "Cuenca Norte"
      cuenca:
        nombre: "Arroyo Las Piedras"
        area_ha: 62
        slope_pct: 3.41
        p3_10: 83
        c: 0.62
        cn: 81
        length_m: 800

    tc_methods:
      - kirpich
      - desbordes

    analyses:
      - storm: gz
        tr: [2, 10, 25]
        x: [1.0, 1.25]
      - storm: blocks
        tr: [10, 25]
    ```

    Ejemplo:
        hidropluvial session batch cuenca.yaml -o reporte.tex
    """
    import yaml

    from hidropluvial.core import convolve_uh, desbordes, kirpich, temez, triangular_uh_x

    config_path = Path(config_file)
    if not config_path.exists():
        typer.echo(f"Error: Archivo no encontrado: {config_file}", err=True)
        raise typer.Exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    manager = get_session_manager()

    # Crear sesión
    session_cfg = config.get("session", {})
    cuenca_cfg = session_cfg.get("cuenca", {})

    session = manager.create(
        name=session_cfg.get("name", "Batch Session"),
        area_ha=cuenca_cfg.get("area_ha"),
        slope_pct=cuenca_cfg.get("slope_pct"),
        p3_10=cuenca_cfg.get("p3_10"),
        c=cuenca_cfg.get("c"),
        cn=cuenca_cfg.get("cn"),
        length_m=cuenca_cfg.get("length_m"),
        cuenca_nombre=cuenca_cfg.get("nombre", ""),
    )

    typer.echo(f"\n{'='*55}")
    typer.echo(f"  BATCH: Sesión creada [{session.id}]")
    typer.echo(f"{'='*55}")

    # Calcular Tc con todos los métodos
    tc_methods = config.get("tc_methods", ["desbordes"])

    typer.echo(f"\n  Calculando Tc...")
    for method in tc_methods:
        tc_hr = None
        if method == "kirpich" and session.cuenca.length_m:
            tc_hr = kirpich(session.cuenca.length_m, session.cuenca.slope_pct / 100)
        elif method == "temez" and session.cuenca.length_m:
            tc_hr = temez(session.cuenca.length_m / 1000, session.cuenca.slope_pct / 100)
        elif method == "desbordes" and session.cuenca.c:
            tc_hr = desbordes(session.cuenca.area_ha, session.cuenca.slope_pct, session.cuenca.c)

        if tc_hr:
            result = manager.add_tc_result(session, method, tc_hr)
            typer.echo(f"    {method:15} Tc = {result.tc_min:>6.1f} min")

    # Ejecutar análisis
    analyses_cfg = config.get("analyses", [])
    n_analyses = 0

    typer.echo(f"\n  Ejecutando análisis...")

    for analysis_cfg in analyses_cfg:
        storm_type = analysis_cfg.get("storm", "gz")
        return_periods = analysis_cfg.get("tr", [2])
        x_factors = analysis_cfg.get("x", [1.0])
        dt = analysis_cfg.get("dt", 5.0)

        # Normalizar a listas
        if not isinstance(return_periods, list):
            return_periods = [return_periods]
        if not isinstance(x_factors, list):
            x_factors = [x_factors]

        # Para cada combinación de Tc method
        for tc_result in session.tc_results:
            for tr in return_periods:
                for x in x_factors:
                    # Solo usar X para tormenta gz
                    if storm_type != "gz":
                        x = None

                    tc_hr = tc_result.tc_hr

                    # Determinar duración y dt según tipo de tormenta
                    if storm_type == "gz":
                        duration_hr = 6.0
                        storm_dt = dt  # 5 min por defecto
                    elif storm_type == "blocks24":
                        duration_hr = 24.0
                        storm_dt = 10.0  # 10 min para tormentas de 24h
                    else:  # blocks, bimodal
                        duration_hr = max(tc_hr, 1.0)
                        storm_dt = dt

                    if storm_type == "gz":
                        peak_position = 1.0 / 6.0
                        hyetograph = alternating_blocks_dinagua(
                            session.cuenca.p3_10, tr, duration_hr, storm_dt, None, peak_position
                        )
                    elif storm_type in ("blocks", "blocks24"):
                        hyetograph = alternating_blocks_dinagua(
                            session.cuenca.p3_10, tr, duration_hr, storm_dt, None
                        )
                    elif storm_type == "bimodal":
                        from hidropluvial.core import bimodal_dinagua
                        hyetograph = bimodal_dinagua(session.cuenca.p3_10, tr, duration_hr, storm_dt)
                    else:
                        continue

                    depths = np.array(hyetograph.depth_mm)

                    if session.cuenca.c:
                        excess_mm = session.cuenca.c * depths
                        runoff_mm = float(np.sum(excess_mm))
                    elif session.cuenca.cn:
                        cumulative = np.array(hyetograph.cumulative_mm)
                        excess_mm = rainfall_excess_series(cumulative, session.cuenca.cn)
                        runoff_mm = float(np.sum(excess_mm))
                    else:
                        continue

                    dt_hr = storm_dt / 60
                    x_val = x if x else 1.0

                    # Calcular tp del hidrograma unitario SCS: Tp = ΔD/2 + 0.6×Tc
                    from hidropluvial.core import scs_time_to_peak
                    tp_unit_hr = scs_time_to_peak(tc_hr, dt_hr)

                    if storm_type == "gz" or session.cuenca.c:
                        uh_time, uh_flow = triangular_uh_x(session.cuenca.area_ha, tc_hr, dt_hr, x_val)
                    else:
                        uh_time, uh_flow = scs_triangular_uh(session.cuenca.area_ha / 100, tc_hr, dt_hr)
                        x_val = 1.67

                    hydrograph_flow = convolve_uh(excess_mm, uh_flow)
                    n_total = len(hydrograph_flow)
                    hydrograph_time = np.arange(n_total) * dt_hr

                    peak_idx = np.argmax(hydrograph_flow)
                    peak_flow = float(hydrograph_flow[peak_idx])
                    time_to_peak = float(hydrograph_time[peak_idx])
                    volume_m3 = float(np.trapezoid(hydrograph_flow, hydrograph_time * 3600))

                    manager.add_analysis(
                        session=session,
                        tc_method=tc_result.method,
                        tc_hr=tc_hr,
                        storm_type=storm_type,
                        return_period=tr,
                        duration_hr=duration_hr,
                        total_depth_mm=hyetograph.total_depth_mm,
                        peak_intensity_mmhr=hyetograph.peak_intensity_mmhr,
                        n_intervals=len(hyetograph.time_min),
                        peak_flow_m3s=peak_flow,
                        time_to_peak_hr=time_to_peak,
                        volume_m3=volume_m3,
                        runoff_mm=runoff_mm,
                        x_factor=x if storm_type == "gz" else None,
                        tp_unit_hr=tp_unit_hr,
                        # Series temporales para gráficos
                        storm_time_min=list(hyetograph.time_min),
                        storm_intensity_mmhr=list(hyetograph.intensity_mmhr),
                        hydrograph_time_hr=[float(t) for t in hydrograph_time],
                        hydrograph_flow_m3s=[float(q) for q in hydrograph_flow],
                    )

                    n_analyses += 1
                    x_str = f"X={x:.2f}" if x else ""
                    typer.echo(f"    {tc_result.method} + {storm_type} Tr{tr} {x_str} -> Qp={peak_flow:.3f} m³/s")

                    # Si no es gz, salir del bucle de x
                    if storm_type != "gz":
                        break

    typer.echo(f"\n  Total: {n_analyses} análisis completados")
    typer.echo(f"{'='*55}")

    # Mostrar resumen
    rows = manager.get_summary_table(session)
    if rows:
        typer.echo(f"\n  RESUMEN:")
        max_q = max(rows, key=lambda x: x['qpeak_m3s'])
        min_q = min(rows, key=lambda x: x['qpeak_m3s'])
        typer.echo(f"    Caudal máximo: {max_q['qpeak_m3s']:.3f} m³/s ({max_q['tc_method']} + {max_q['storm']} Tr{max_q['tr']})")
        typer.echo(f"    Caudal mínimo: {min_q['qpeak_m3s']:.3f} m³/s ({min_q['tc_method']} + {min_q['storm']} Tr{min_q['tr']})")

    typer.echo(f"\n  Sesión guardada: {session.id}")
    typer.echo(f"  Usa 'session summary {session.id}' para ver tabla completa")
    typer.echo(f"  Usa 'session report {session.id}' para generar reporte LaTeX\n")
