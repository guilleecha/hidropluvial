"""
Exportación de sesiones a diferentes formatos.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
import pandas as pd

from hidropluvial.cli.session.base import get_session_manager
from hidropluvial.session import Session


def session_export(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de sesión")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo de salida")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Formato: xlsx, csv")] = "xlsx",
) -> None:
    """
    Exporta los resultados de una sesión a Excel o CSV.

    Genera un archivo con la tabla resumen de todos los análisis,
    incluyendo datos de la cuenca y parámetros.
    """
    manager = get_session_manager()
    session = manager.get_session(session_id)

    if session is None:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.")
        raise typer.Exit(1)

    # Determinar nombre de salida
    if output is None:
        output = session.name.lower().replace(" ", "_")

    # Agregar extensión si no tiene
    if not output.endswith(f".{format}"):
        output = f"{output}.{format}"

    output_path = Path(output)

    if format == "xlsx":
        _export_to_excel(session, output_path)
    elif format == "csv":
        _export_to_csv(session, output_path)
    else:
        typer.echo(f"Error: Formato '{format}' no soportado. Use 'xlsx' o 'csv'.")
        raise typer.Exit(1)

    typer.echo(f"Exportado: {output_path.absolute()}")


def _export_to_excel(session: Session, output_path: Path) -> None:
    """Exporta sesión a Excel con múltiples hojas."""
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Hoja 1: Datos de la cuenca
        cuenca_data = _get_cuenca_dataframe(session)
        cuenca_data.to_excel(writer, sheet_name="Cuenca", index=False)

        # Hoja 2: Resultados de Tc
        if session.tc_results:
            tc_data = _get_tc_dataframe(session)
            tc_data.to_excel(writer, sheet_name="Tiempo Concentracion", index=False)

        # Hoja 3: Resumen de análisis
        if session.analyses:
            summary_data = _get_summary_dataframe(session)
            summary_data.to_excel(writer, sheet_name="Resumen Analisis", index=False)

            # Hoja 4: Detalle por período de retorno
            pivot_data = _get_pivot_dataframe(session)
            if pivot_data is not None:
                pivot_data.to_excel(writer, sheet_name="Por Periodo Retorno", index=True)

        # Hoja 5: Notas (si hay)
        notes_data = _get_notes_dataframe(session)
        if notes_data is not None:
            notes_data.to_excel(writer, sheet_name="Notas", index=False)


def _export_to_csv(session: Session, output_path: Path) -> None:
    """Exporta sesión a CSV (solo resumen de análisis)."""
    if not session.analyses:
        typer.echo("La sesión no tiene análisis para exportar.")
        raise typer.Exit(1)

    summary_data = _get_summary_dataframe(session)
    summary_data.to_csv(output_path, index=False)


def _get_cuenca_dataframe(session: Session) -> pd.DataFrame:
    """Genera DataFrame con datos de la cuenca."""
    cuenca = session.cuenca
    data = {
        "Parámetro": [
            "Nombre sesión",
            "Nombre cuenca",
            "Área (ha)",
            "Área (km²)",
            "Pendiente (%)",
            "P3,10 (mm)",
            "Coeficiente C",
            "Curve Number CN",
            "Longitud cauce (m)",
        ],
        "Valor": [
            session.name,
            cuenca.nombre,
            cuenca.area_ha,
            cuenca.area_ha / 100,
            cuenca.slope_pct,
            cuenca.p3_10,
            cuenca.c if cuenca.c else "-",
            cuenca.cn if cuenca.cn else "-",
            cuenca.length_m if cuenca.length_m else "-",
        ],
    }

    # Agregar notas de sesión si existen
    if session.notes:
        data["Parámetro"].append("Notas")
        data["Valor"].append(session.notes)

    return pd.DataFrame(data)


def _get_tc_dataframe(session: Session) -> pd.DataFrame:
    """Genera DataFrame con resultados de Tc."""
    rows = []
    for tc in session.tc_results:
        row = {
            "Método": tc.method.capitalize(),
            "Tc (hr)": round(tc.tc_hr, 3),
            "Tc (min)": round(tc.tc_min, 1),
        }
        # Agregar parámetros relevantes si existen
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


def _get_summary_dataframe(session: Session) -> pd.DataFrame:
    """Genera DataFrame con resumen de todos los análisis."""
    rows = []
    for a in session.analyses:
        row = {
            "ID": a.id,
            "Método Tc": a.tc.method.capitalize(),
            "Tc (min)": round(a.tc.tc_min, 1),
            "Tormenta": a.storm.type.upper(),
            "Tr (años)": a.storm.return_period,
            "Duración (hr)": round(a.storm.duration_hr, 2),
            "P total (mm)": round(a.storm.total_depth_mm, 1),
            "i pico (mm/hr)": round(a.storm.peak_intensity_mmhr, 1),
            "Escorrentía (mm)": round(a.hydrograph.runoff_mm, 1),
            "Q pico (m³/s)": round(a.hydrograph.peak_flow_m3s, 3),
            "t pico (min)": round(a.hydrograph.time_to_peak_min, 1),
            "Volumen (m³)": round(a.hydrograph.volume_m3, 0),
        }

        # Agregar C si el método de Tc depende de C (desbordes, faa)
        if a.tc.parameters and "c" in a.tc.parameters:
            row["C"] = round(a.tc.parameters["c"], 3)

        # Agregar t0 si existe (para desbordes)
        if a.tc.parameters and "t0_min" in a.tc.parameters:
            row["t0 (min)"] = a.tc.parameters["t0_min"]

        # Agregar parámetros SCS-CN si existen
        if a.tc.parameters:
            if "cn_adjusted" in a.tc.parameters:
                row["CN ajustado"] = a.tc.parameters["cn_adjusted"]
            if "amc" in a.tc.parameters:
                row["AMC"] = a.tc.parameters["amc"]
            if "lambda" in a.tc.parameters:
                row["λ"] = a.tc.parameters["lambda"]

        # Agregar X factor si existe
        if a.hydrograph.x_factor:
            row["Factor X"] = a.hydrograph.x_factor

        # Agregar nota si existe
        if a.note:
            row["Nota"] = a.note

        rows.append(row)

    return pd.DataFrame(rows)


def _get_pivot_dataframe(session: Session) -> Optional[pd.DataFrame]:
    """Genera tabla pivote de Q pico por Tr y método."""
    if not session.analyses:
        return None

    rows = []
    for a in session.analyses:
        rows.append({
            "Método": f"{a.tc.method} X={a.hydrograph.x_factor:.2f}" if a.hydrograph.x_factor else a.tc.method,
            "Tr": a.storm.return_period,
            "Q pico (m³/s)": round(a.hydrograph.peak_flow_m3s, 3),
        })

    df = pd.DataFrame(rows)

    # Crear pivot si hay suficientes datos
    if len(df["Tr"].unique()) > 1 or len(df["Método"].unique()) > 1:
        pivot = df.pivot_table(
            index="Método",
            columns="Tr",
            values="Q pico (m³/s)",
            aggfunc="first",
        )
        # Renombrar columnas para claridad
        pivot.columns = [f"Tr={tr}" for tr in pivot.columns]
        return pivot

    return None


def _get_notes_dataframe(session: Session) -> Optional[pd.DataFrame]:
    """Genera DataFrame con notas de sesión y análisis."""
    rows = []

    # Nota de sesión
    if session.notes:
        rows.append({
            "Tipo": "Sesión",
            "ID": session.id,
            "Descripción": session.name,
            "Nota": session.notes,
        })

    # Notas de análisis
    for a in session.analyses:
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


def compare_sessions(
    session_ids: Annotated[list[str], typer.Argument(help="IDs de sesiones a comparar (mínimo 2)")],
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Archivo Excel de salida")] = None,
    tr: Annotated[Optional[int], typer.Option("--tr", help="Filtrar por período de retorno")] = None,
) -> None:
    """
    Compara resultados de múltiples sesiones lado a lado.

    Genera una tabla comparativa con los caudales pico de cada cuenca
    para los mismos períodos de retorno.
    """
    if len(session_ids) < 2:
        typer.echo("Error: Necesitas al menos 2 sesiones para comparar.")
        raise typer.Exit(1)

    manager = get_session_manager()
    sessions = []

    for sid in session_ids:
        session = manager.get_session(sid)
        if session is None:
            typer.echo(f"Error: Sesión '{sid}' no encontrada.")
            raise typer.Exit(1)
        if not session.analyses:
            typer.echo(f"Advertencia: Sesión '{sid}' no tiene análisis.")
        sessions.append(session)

    # Generar comparación
    comparison_df = _generate_comparison(sessions, tr)

    if comparison_df is None or comparison_df.empty:
        typer.echo("No hay datos comparables entre las sesiones.")
        raise typer.Exit(1)

    # Mostrar en consola
    typer.echo("\n" + "=" * 70)
    typer.echo("  COMPARACIÓN DE CUENCAS")
    typer.echo("=" * 70 + "\n")

    # Info de cada cuenca
    for s in sessions:
        typer.echo(f"  [{s.id}] {s.name}")
        typer.echo(f"         Área: {s.cuenca.area_ha} ha, Pendiente: {s.cuenca.slope_pct}%")

    typer.echo("\n" + "-" * 70)
    typer.echo(comparison_df.to_string(index=False))
    typer.echo("-" * 70)

    # Exportar si se especifica
    if output:
        if not output.endswith(".xlsx"):
            output = f"{output}.xlsx"

        output_path = Path(output)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # Hoja 1: Comparación
            comparison_df.to_excel(writer, sheet_name="Comparacion", index=False)

            # Hoja 2: Datos de cuencas
            cuencas_data = []
            for s in sessions:
                cuencas_data.append({
                    "ID Sesión": s.id,
                    "Nombre": s.name,
                    "Cuenca": s.cuenca.nombre,
                    "Área (ha)": s.cuenca.area_ha,
                    "Pendiente (%)": s.cuenca.slope_pct,
                    "P3,10 (mm)": s.cuenca.p3_10,
                    "C": s.cuenca.c if s.cuenca.c else "-",
                    "CN": s.cuenca.cn if s.cuenca.cn else "-",
                    "Longitud (m)": s.cuenca.length_m if s.cuenca.length_m else "-",
                })
            pd.DataFrame(cuencas_data).to_excel(writer, sheet_name="Datos Cuencas", index=False)

        typer.echo(f"\nExportado: {output_path.absolute()}")


def _generate_comparison(sessions: list[Session], tr_filter: Optional[int] = None) -> Optional[pd.DataFrame]:
    """Genera DataFrame comparativo de múltiples sesiones."""
    # Recolectar todos los Tr disponibles
    all_trs = set()
    for s in sessions:
        for a in s.analyses:
            if tr_filter is None or a.storm.return_period == tr_filter:
                all_trs.add(a.storm.return_period)

    if not all_trs:
        return None

    rows = []
    for tr in sorted(all_trs):
        row = {"Tr (años)": tr}

        for s in sessions:
            # Buscar el análisis con mayor Q para este Tr
            max_q = None
            for a in s.analyses:
                if a.storm.return_period == tr:
                    if max_q is None or a.hydrograph.peak_flow_m3s > max_q:
                        max_q = a.hydrograph.peak_flow_m3s

            col_name = f"{s.name[:20]} (m³/s)"
            row[col_name] = round(max_q, 3) if max_q else "-"

        rows.append(row)

    return pd.DataFrame(rows)
