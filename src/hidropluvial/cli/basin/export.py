"""
Exportación de cuencas a diferentes formatos.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from hidropluvial.models import Basin


def export_to_excel(basin: Basin, output_path: Path) -> None:
    """Exporta cuenca a Excel con múltiples hojas."""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Hoja 1: Datos de la cuenca
        cuenca_data = _get_basin_dataframe(basin)
        cuenca_data.to_excel(writer, sheet_name="Cuenca", index=False)

        # Hoja 2: Resultados de Tc
        if basin.tc_results:
            tc_data = _get_tc_dataframe(basin)
            tc_data.to_excel(writer, sheet_name="Tiempo Concentracion", index=False)

        # Hoja 3: Resumen de análisis
        if basin.analyses:
            summary_data = _get_summary_dataframe(basin)
            summary_data.to_excel(writer, sheet_name="Resumen Analisis", index=False)

            # Hoja 4: Detalle por período de retorno
            pivot_data = _get_pivot_dataframe(basin)
            if pivot_data is not None:
                pivot_data.to_excel(writer, sheet_name="Por Periodo Retorno", index=True)

        # Hoja 5: Notas (si hay)
        notes_data = _get_notes_dataframe(basin)
        if notes_data is not None:
            notes_data.to_excel(writer, sheet_name="Notas", index=False)


def export_to_csv(basin: Basin, output_path: Path) -> None:
    """Exporta cuenca a CSV (solo resumen de análisis)."""
    if not basin.analyses:
        raise ValueError("La cuenca no tiene análisis para exportar.")

    summary_data = _get_summary_dataframe(basin)
    summary_data.to_csv(output_path, index=False)


def _get_basin_dataframe(basin: Basin) -> pd.DataFrame:
    """Genera DataFrame con datos de la cuenca."""
    data = {
        "Parámetro": [
            "Nombre cuenca",
            "ID",
            "Área (ha)",
            "Área (km²)",
            "Pendiente (%)",
            "P3,10 (mm)",
            "Coeficiente C",
            "Curve Number CN",
            "Longitud cauce (m)",
        ],
        "Valor": [
            basin.name,
            basin.id,
            basin.area_ha,
            basin.area_ha / 100,
            basin.slope_pct,
            basin.p3_10,
            basin.c if basin.c else "-",
            basin.cn if basin.cn else "-",
            basin.length_m if basin.length_m else "-",
        ],
    }

    if basin.notes:
        data["Parámetro"].append("Notas")
        data["Valor"].append(basin.notes)

    return pd.DataFrame(data)


def _get_tc_dataframe(basin: Basin) -> pd.DataFrame:
    """Genera DataFrame con resultados de Tc."""
    rows = []
    for tc in basin.tc_results:
        row = {
            "Método": tc.method.capitalize(),
            "Tc (hr)": round(tc.tc_hr, 3),
            "Tc (min)": round(tc.tc_min, 1),
        }
        if tc.parameters:
            if "c" in tc.parameters:
                row["C"] = tc.parameters["c"]
            if "length_m" in tc.parameters:
                row["Longitud (m)"] = tc.parameters["length_m"]
            if "cn" in tc.parameters:
                row["CN"] = tc.parameters["cn"]
            if "t0_min" in tc.parameters:
                row["t0 (min)"] = tc.parameters["t0_min"]
        rows.append(row)
    return pd.DataFrame(rows)


def _get_summary_dataframe(basin: Basin) -> pd.DataFrame:
    """Genera DataFrame con resumen de todos los análisis."""
    rows = []
    for a in basin.analyses:
        runoff_method = "-"
        if a.tc.parameters and "runoff_method" in a.tc.parameters:
            rm = a.tc.parameters["runoff_method"]
            runoff_method = "Racional" if rm == "racional" else "SCS-CN"
        elif a.tc.parameters:
            if "cn_adjusted" in a.tc.parameters:
                runoff_method = "SCS-CN"
            elif "c" in a.tc.parameters:
                runoff_method = "Racional"

        row = {
            "ID": a.id,
            "Método Tc": a.tc.method.capitalize(),
            "Tc (min)": round(a.tc.tc_min, 1),
            "tp (min)": round(a.hydrograph.tp_unit_min, 1) if a.hydrograph.tp_unit_min else None,
            "tb (min)": round(a.hydrograph.tb_min, 1) if a.hydrograph.tb_min else None,
            "Método Pe": runoff_method,
            "Tormenta": a.storm.type.upper(),
            "Tr (años)": a.storm.return_period,
            "Duración (hr)": round(a.storm.duration_hr, 2),
            "P total (mm)": round(a.storm.total_depth_mm, 1),
            "i pico (mm/hr)": round(a.storm.peak_intensity_mmhr, 1),
            "Pe (mm)": round(a.hydrograph.runoff_mm, 1),
            "Qp (m³/s)": round(a.hydrograph.peak_flow_m3s, 2),
            "Tp (min)": round(a.hydrograph.time_to_peak_min, 1),
            "Vol (hm³)": round(a.hydrograph.volume_m3 / 1_000_000, 4),
        }

        if a.tc.parameters and "c" in a.tc.parameters:
            row["C"] = round(a.tc.parameters["c"], 3)
        if a.tc.parameters and "t0_min" in a.tc.parameters:
            row["t0 (min)"] = a.tc.parameters["t0_min"]
        if a.tc.parameters:
            if "cn_adjusted" in a.tc.parameters:
                row["CN ajustado"] = a.tc.parameters["cn_adjusted"]
            if "amc" in a.tc.parameters:
                row["AMC"] = a.tc.parameters["amc"]
            if "lambda" in a.tc.parameters:
                row["λ"] = a.tc.parameters["lambda"]

        if a.hydrograph.x_factor:
            row["Factor X"] = a.hydrograph.x_factor
        if a.note:
            row["Nota"] = a.note

        rows.append(row)

    return pd.DataFrame(rows)


def _get_pivot_dataframe(basin: Basin) -> Optional[pd.DataFrame]:
    """Genera tabla pivote de Q pico por Tr y método."""
    if not basin.analyses:
        return None

    rows = []
    for a in basin.analyses:
        method_label = a.tc.method

        if a.tc.parameters and "runoff_method" in a.tc.parameters:
            rm = a.tc.parameters["runoff_method"]
            esc_label = "C" if rm == "racional" else "CN"
            method_label = f"{method_label}+{esc_label}"
        elif a.tc.parameters:
            if "cn_adjusted" in a.tc.parameters:
                method_label = f"{method_label}+CN"
            elif "c" in a.tc.parameters:
                method_label = f"{method_label}+C"

        if a.hydrograph.x_factor:
            method_label = f"{method_label} X={a.hydrograph.x_factor:.2f}"

        rows.append({
            "Método": method_label,
            "Tr": a.storm.return_period,
            "Q pico (m³/s)": round(a.hydrograph.peak_flow_m3s, 3),
        })

    df = pd.DataFrame(rows)

    if len(df["Tr"].unique()) > 1 or len(df["Método"].unique()) > 1:
        pivot = df.pivot_table(
            index="Método",
            columns="Tr",
            values="Q pico (m³/s)",
            aggfunc="first",
        )
        pivot.columns = [f"Tr={tr}" for tr in pivot.columns]
        return pivot

    return None


def _get_notes_dataframe(basin: Basin) -> Optional[pd.DataFrame]:
    """Genera DataFrame con notas de cuenca y análisis."""
    rows = []

    if basin.notes:
        rows.append({
            "Tipo": "Cuenca",
            "ID": basin.id,
            "Descripción": basin.name,
            "Nota": basin.notes,
        })

    for a in basin.analyses:
        if a.note:
            desc = f"{a.tc.method} Tr{a.storm.return_period}"
            if a.hydrograph.x_factor:
                desc += f" X={a.hydrograph.x_factor:.2f}"
            rows.append({
                "Tipo": "Análisis",
                "ID": a.id,
                "Descripción": desc,
                "Nota": a.note,
            })

    if rows:
        return pd.DataFrame(rows)
    return None


def compare_basins(
    basins: list[Basin],
    tr_filter: Optional[int] = None,
) -> Optional[pd.DataFrame]:
    """
    Genera DataFrame comparativo de múltiples cuencas.

    Args:
        basins: Lista de cuencas a comparar
        tr_filter: Filtrar por período de retorno específico

    Returns:
        DataFrame con comparación o None si no hay datos
    """
    all_trs = set()
    for basin in basins:
        for a in basin.analyses:
            if tr_filter is None or a.storm.return_period == tr_filter:
                all_trs.add(a.storm.return_period)

    if not all_trs:
        return None

    rows = []
    for tr in sorted(all_trs):
        row = {"Tr (años)": tr}

        for basin in basins:
            max_q = None
            for a in basin.analyses:
                if a.storm.return_period == tr:
                    if max_q is None or a.hydrograph.peak_flow_m3s > max_q:
                        max_q = a.hydrograph.peak_flow_m3s

            col_name = f"{basin.name[:20]} (m³/s)"
            row[col_name] = round(max_q, 3) if max_q else "-"

        rows.append(row)

    return pd.DataFrame(rows)
