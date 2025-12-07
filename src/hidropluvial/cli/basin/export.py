"""
Exportación de cuencas a diferentes formatos.
"""

from pathlib import Path
from typing import Optional

import pandas as pd

from hidropluvial.models import Basin


def export_to_excel(basin: Basin, output_path: Path, include_timeseries: bool = True) -> None:
    """
    Exporta cuenca a Excel con múltiples hojas.

    Args:
        basin: Cuenca a exportar
        output_path: Ruta del archivo Excel
        include_timeseries: Si True, incluye hojas con series temporales (hietogramas e hidrogramas)
    """
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Hoja 1: Datos de la cuenca
        cuenca_data = _get_basin_dataframe(basin)
        cuenca_data.to_excel(writer, sheet_name="Cuenca", index=False)

        # Hoja 2: Resultados de Tc (valores base)
        if basin.tc_results:
            tc_data = _get_tc_dataframe(basin)
            tc_data.to_excel(writer, sheet_name="Tiempo Concentracion", index=False)

        # Hoja 2b: Tc por Tr (para Desbordes donde C varía con Tr)
        tc_by_tr_data = _get_tc_by_tr_dataframe(basin)
        if tc_by_tr_data is not None:
            tc_by_tr_data.to_excel(writer, sheet_name="Tc Desbordes por Tr", index=False)

        # Hoja 3: Resumen de análisis
        if basin.analyses:
            summary_data = _get_summary_dataframe(basin)
            summary_data.to_excel(writer, sheet_name="Resumen Analisis", index=False)

            # Hoja 4: Detalle por período de retorno
            pivot_data = _get_pivot_dataframe(basin)
            if pivot_data is not None:
                pivot_data.to_excel(writer, sheet_name="Por Periodo Retorno", index=True)

            # Hoja 5: Datos de tormentas (hietogramas)
            storm_data = _get_storms_dataframe(basin)
            if storm_data is not None:
                storm_data.to_excel(writer, sheet_name="Tormentas", index=False)

            # Hoja 6: Series temporales de tormentas (opcional)
            if include_timeseries:
                hyetograph_data = _get_hyetographs_dataframe(basin)
                if hyetograph_data is not None:
                    hyetograph_data.to_excel(writer, sheet_name="Hietogramas", index=False)

                # Hoja 7: Series temporales de hidrogramas
                hydrograph_data = _get_hydrographs_dataframe(basin)
                if hydrograph_data is not None:
                    hydrograph_data.to_excel(writer, sheet_name="Hidrogramas", index=False)

        # Hoja 8: Notas (si hay)
        notes_data = _get_notes_dataframe(basin)
        if notes_data is not None:
            notes_data.to_excel(writer, sheet_name="Notas", index=False)


def export_to_csv(basin: Basin, output_path: Path) -> None:
    """Exporta cuenca a CSV (solo resumen de análisis)."""
    if not basin.analyses:
        raise ValueError("La cuenca no tiene análisis para exportar.")

    summary_data = _get_summary_dataframe(basin)
    summary_data.to_csv(output_path, index=False)


def export_to_csv_complete(basin: Basin, output_dir: Path) -> dict[str, Path]:
    """
    Exporta cuenca a múltiples archivos CSV.

    Args:
        basin: Cuenca a exportar
        output_dir: Directorio donde crear los archivos

    Returns:
        Diccionario con nombres de archivo y rutas creadas
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = basin.name.lower().replace(" ", "_")
    created_files = {}

    # 1. Datos de cuenca
    cuenca_path = output_dir / f"{base_name}_cuenca.csv"
    cuenca_data = _get_basin_dataframe(basin)
    cuenca_data.to_csv(cuenca_path, index=False)
    created_files["cuenca"] = cuenca_path

    # 2. Tiempos de concentración
    if basin.tc_results:
        tc_path = output_dir / f"{base_name}_tc.csv"
        tc_data = _get_tc_dataframe(basin)
        tc_data.to_csv(tc_path, index=False)
        created_files["tc"] = tc_path

    # 2b. Tc por Tr (para Desbordes)
    tc_by_tr_data = _get_tc_by_tr_dataframe(basin)
    if tc_by_tr_data is not None:
        tc_by_tr_path = output_dir / f"{base_name}_tc_por_tr.csv"
        tc_by_tr_data.to_csv(tc_by_tr_path, index=False)
        created_files["tc_por_tr"] = tc_by_tr_path

    if basin.analyses:
        # 3. Resumen de análisis
        summary_path = output_dir / f"{base_name}_analisis.csv"
        summary_data = _get_summary_dataframe(basin)
        summary_data.to_csv(summary_path, index=False)
        created_files["analisis"] = summary_path

        # 4. Tabla de tormentas
        storms_path = output_dir / f"{base_name}_tormentas.csv"
        storms_data = _get_storms_dataframe(basin)
        if storms_data is not None:
            storms_data.to_csv(storms_path, index=False)
            created_files["tormentas"] = storms_path

        # 5. Hietogramas
        hyetograph_path = output_dir / f"{base_name}_hietogramas.csv"
        hyetograph_data = _get_hyetographs_dataframe(basin)
        if hyetograph_data is not None:
            hyetograph_data.to_csv(hyetograph_path, index=False)
            created_files["hietogramas"] = hyetograph_path

        # 6. Hidrogramas
        hydrograph_path = output_dir / f"{base_name}_hidrogramas.csv"
        hydrograph_data = _get_hydrographs_dataframe(basin)
        if hydrograph_data is not None:
            hydrograph_data.to_csv(hydrograph_path, index=False)
            created_files["hidrogramas"] = hydrograph_path

    return created_files


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


def _get_tc_by_tr_dataframe(basin: Basin) -> Optional[pd.DataFrame]:
    """
    Genera DataFrame con Tc por período de retorno para métodos que varían con Tr.

    Útil para Desbordes donde C cambia según Tr, afectando el Tc.
    """
    if not basin.analyses:
        return None

    # Buscar análisis con método Desbordes u otros que varíen con Tr
    desbordes_analyses = [
        a for a in basin.analyses
        if a.tc.method.lower() == "desbordes"
    ]

    if not desbordes_analyses:
        return None

    # Agrupar por Tr único
    tr_data = {}
    for a in desbordes_analyses:
        tr = a.storm.return_period
        if tr not in tr_data:
            c_val = a.tc.parameters.get("c") if a.tc.parameters else None
            tr_data[tr] = {
                "Tr (años)": tr,
                "C ajustado": round(c_val, 3) if c_val else "-",
                "Tc (min)": round(a.tc.tc_min, 1),
                "Tc (hr)": round(a.tc.tc_min / 60, 3),
            }

    if not tr_data:
        return None

    # Ordenar por Tr
    rows = [tr_data[tr] for tr in sorted(tr_data.keys())]
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


def _get_storms_dataframe(basin: Basin) -> Optional[pd.DataFrame]:
    """Genera DataFrame con resumen de todas las tormentas utilizadas."""
    if not basin.analyses:
        return None

    # Identificar tormentas únicas por tipo, Tr y duración
    storm_keys = set()
    storms = []

    for a in basin.analyses:
        s = a.storm
        key = (s.type, s.return_period, s.duration_hr)
        if key not in storm_keys:
            storm_keys.add(key)
            storms.append(s)

    if not storms:
        return None

    rows = []
    for s in storms:
        # Calcular dt desde time_min si está disponible
        dt_min = None
        if s.time_min and len(s.time_min) >= 2:
            dt_min = s.time_min[1] - s.time_min[0]

        row = {
            "Tipo": s.type.upper(),
            "Tr (años)": s.return_period,
            "Duración (hr)": round(s.duration_hr, 2),
            "dt (min)": round(dt_min, 1) if dt_min else None,
            "P total (mm)": round(s.total_depth_mm, 1),
            "i pico (mm/hr)": round(s.peak_intensity_mmhr, 1),
            "N intervalos": s.n_intervals,
        }

        # Calcular posición del pico desde intensidades
        if s.intensity_mmhr and len(s.intensity_mmhr) > 0:
            intensities = list(s.intensity_mmhr)
            peak_idx = intensities.index(max(intensities))
            n = len(intensities)
            peak_pos = (peak_idx + 0.5) / n
            row["Posición pico"] = f"{peak_pos:.0%}"

        rows.append(row)

    return pd.DataFrame(rows)


def _get_hyetographs_dataframe(basin: Basin) -> Optional[pd.DataFrame]:
    """
    Genera DataFrame con series temporales de hietogramas.

    Formato: columnas pareadas de tiempo e intensidad por cada tormenta única.
    """
    if not basin.analyses:
        return None

    # Identificar tormentas únicas con datos de series temporales
    storm_data = {}

    for a in basin.analyses:
        s = a.storm
        key = f"{s.type.upper()}_Tr{s.return_period}"
        if key not in storm_data and s.time_min and s.intensity_mmhr:
            # Calcular profundidades desde intensidades si no están disponibles
            dt_min = s.time_min[1] - s.time_min[0] if len(s.time_min) >= 2 else 5.0
            depths = [i * dt_min / 60.0 for i in s.intensity_mmhr]  # mm = mm/hr * hr
            cumulative = []
            cumsum = 0
            for d in depths:
                cumsum += d
                cumulative.append(cumsum)

            storm_data[key] = {
                "time": list(s.time_min),
                "depth": depths,
                "intensity": list(s.intensity_mmhr),
                "cumulative": cumulative,
            }

    if not storm_data:
        return None

    # Construir DataFrame con columnas pareadas (cada tormenta tiene su propio tiempo)
    # Encontrar la longitud máxima para padding
    max_len = max(len(data["time"]) for data in storm_data.values())

    result = {}
    for key, data in storm_data.items():
        n = len(data["time"])
        padding = [None] * (max_len - n)

        result[f"t_{key} (min)"] = data["time"] + padding
        result[f"P_{key} (mm)"] = [round(d, 2) for d in data["depth"]] + padding
        result[f"i_{key} (mm/hr)"] = [round(i, 2) for i in data["intensity"]] + padding
        result[f"Pacum_{key} (mm)"] = [round(c, 2) for c in data["cumulative"]] + padding

    return pd.DataFrame(result)


def _get_hydrographs_dataframe(basin: Basin) -> Optional[pd.DataFrame]:
    """
    Genera DataFrame con series temporales de hidrogramas.

    Formato: columnas pareadas de tiempo y caudal por cada análisis.
    """
    if not basin.analyses:
        return None

    # Filtrar análisis con datos de hidrograma
    valid_analyses = [
        a for a in basin.analyses
        if a.hydrograph.time_hr and a.hydrograph.flow_m3s
    ]

    if not valid_analyses:
        return None

    # Usar la serie de tiempo más larga como referencia para padding
    max_len = max(len(a.hydrograph.time_hr) for a in valid_analyses)

    result = {}

    # Construir etiquetas únicas para cada análisis
    for a in valid_analyses:
        h = a.hydrograph
        s = a.storm

        # Etiqueta: método + Tr + X (si aplica)
        label = f"{a.tc.method}_Tr{s.return_period}"
        if h.x_factor:
            label += f"_X{h.x_factor:.2f}"

        # Agregar método de escorrentía si es diferente
        if a.tc.parameters and "runoff_method" in a.tc.parameters:
            rm = a.tc.parameters["runoff_method"]
            if rm == "scs-cn":
                label += "_CN"

        # Convertir tiempo a minutos
        time_min = [t * 60 for t in h.time_hr]

        # Padding para igualar longitudes
        n = len(time_min)
        padding = [None] * (max_len - n)

        time_col = f"t_{label} (min)"
        q_col = f"Q_{label} (m3/s)"

        result[time_col] = [round(t, 1) for t in time_min] + padding
        result[q_col] = [round(q, 4) for q in h.flow_m3s] + padding

    return pd.DataFrame(result)


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
