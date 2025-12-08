"""
Script para migrar proyectos desde archivos JSON a la base de datos SQLite.

Uso:
    python -m hidropluvial.cli.migrate_json

Este script:
1. Busca archivos JSON en ~/.hidropluvial/projects/
2. Importa cada proyecto a la base de datos SQLite
3. Opcionalmente elimina los archivos JSON después de migrar
"""

import json
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from hidropluvial.database import get_database
from hidropluvial.models import (
    TcResult,
    StormResult,
    HydrographResult,
    WeightedCoefficient,
    CoverageItem,
)


def migrate_json_to_sqlite(
    projects_dir: Optional[Path] = None,
    delete_after: bool = False,
) -> tuple[int, int]:
    """
    Migra proyectos desde JSON a SQLite.

    Args:
        projects_dir: Directorio con archivos JSON. Default: ~/.hidropluvial/projects/
        delete_after: Si True, elimina los archivos JSON después de migrar

    Returns:
        Tupla (proyectos_migrados, errores)
    """
    if projects_dir is None:
        projects_dir = Path.home() / ".hidropluvial" / "projects"

    if not projects_dir.exists():
        return 0, 0

    db = get_database()
    console = Console()

    json_files = list(projects_dir.glob("*.json"))
    if not json_files:
        console.print("[yellow]No hay archivos JSON para migrar.[/yellow]")
        return 0, 0

    migrated = 0
    errors = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Migrando proyectos...", total=len(json_files))

        for json_file in json_files:
            try:
                progress.update(task, description=f"Migrando {json_file.name}...")

                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Verificar si el proyecto ya existe en la DB
                existing = db.get_project(data["id"])
                if existing:
                    console.print(f"  [dim]Proyecto {data['id']} ya existe, omitiendo[/dim]")
                    progress.advance(task)
                    continue

                # Crear proyecto en la DB
                project_dict = db.create_project(
                    name=data["name"],
                    description=data.get("description", ""),
                    author=data.get("author", ""),
                    location=data.get("location", ""),
                    notes=data.get("notes"),
                    tags=data.get("tags", []),
                )

                # Actualizar el ID para mantener el original
                with db.connection() as conn:
                    conn.execute(
                        "UPDATE projects SET id = ?, created_at = ?, updated_at = ? WHERE id = ?",
                        (data["id"], data.get("created_at"), data.get("updated_at"), project_dict["id"])
                    )

                project_id = data["id"]

                # Migrar cuencas
                for basin_data in data.get("basins", []):
                    _migrate_basin(db, project_id, basin_data)

                migrated += 1

                if delete_after:
                    json_file.unlink()
                    console.print(f"  [green]✓[/green] Migrado y eliminado: {json_file.name}")
                else:
                    console.print(f"  [green]✓[/green] Migrado: {json_file.name}")

            except Exception as e:
                errors += 1
                console.print(f"  [red]✗[/red] Error en {json_file.name}: {e}")

            progress.advance(task)

    return migrated, errors


def _migrate_basin(db, project_id: str, basin_data: dict) -> None:
    """Migra una cuenca y sus análisis."""
    # Crear cuenca
    basin_dict = db.create_basin(
        project_id=project_id,
        name=basin_data["name"],
        area_ha=basin_data["area_ha"],
        slope_pct=basin_data["slope_pct"],
        p3_10=basin_data["p3_10"],
        c=basin_data.get("c"),
        cn=basin_data.get("cn"),
        length_m=basin_data.get("length_m"),
        notes=basin_data.get("notes"),
    )

    # Actualizar ID para mantener el original
    with db.connection() as conn:
        conn.execute(
            "UPDATE basins SET id = ?, created_at = ?, updated_at = ? WHERE id = ?",
            (basin_data["id"], basin_data.get("created_at"), basin_data.get("updated_at"), basin_dict["id"])
        )

    basin_id = basin_data["id"]

    # Migrar weighted coefficients si existen
    if basin_data.get("c_weighted"):
        cw = basin_data["c_weighted"]
        items = [CoverageItem(**item) for item in cw.get("items", [])]
        c_weighted = WeightedCoefficient(
            type=cw.get("type", "c"),
            table_used=cw.get("table_used"),
            weighted_value=cw.get("weighted_value"),
            items=items,
            base_tr=cw.get("base_tr"),
        )
        db.update_basin(basin_id, c_weighted=c_weighted)

    if basin_data.get("cn_weighted"):
        cnw = basin_data["cn_weighted"]
        items = [CoverageItem(**item) for item in cnw.get("items", [])]
        cn_weighted = WeightedCoefficient(
            type=cnw.get("type", "cn"),
            table_used=cnw.get("table_used"),
            weighted_value=cnw.get("weighted_value"),
            items=items,
            base_tr=cnw.get("base_tr"),
        )
        db.update_basin(basin_id, cn_weighted=cn_weighted)

    # Migrar resultados de Tc
    for tc_data in basin_data.get("tc_results", []):
        db.add_tc_result(
            basin_id=basin_id,
            method=tc_data["method"],
            tc_hr=tc_data["tc_hr"],
            parameters=tc_data.get("parameters", {}),
        )

    # Migrar análisis
    for analysis_data in basin_data.get("analyses", []):
        tc = TcResult(
            method=analysis_data["tc"]["method"],
            tc_hr=analysis_data["tc"]["tc_hr"],
            tc_min=analysis_data["tc"]["tc_min"],
            parameters=analysis_data["tc"].get("parameters", {}),
        )

        storm_data = analysis_data["storm"]
        storm = StormResult(
            type=storm_data["type"],
            return_period=storm_data["return_period"],
            duration_hr=storm_data["duration_hr"],
            total_depth_mm=storm_data["total_depth_mm"],
            peak_intensity_mmhr=storm_data["peak_intensity_mmhr"],
            n_intervals=storm_data["n_intervals"],
            time_min=storm_data.get("time_min", []),
            intensity_mmhr=storm_data.get("intensity_mmhr", []),
        )

        hydro_data = analysis_data["hydrograph"]
        hydrograph = HydrographResult(
            tc_method=hydro_data["tc_method"],
            tc_min=hydro_data["tc_min"],
            storm_type=hydro_data["storm_type"],
            return_period=hydro_data["return_period"],
            x_factor=hydro_data.get("x_factor"),
            peak_flow_m3s=hydro_data["peak_flow_m3s"],
            time_to_peak_hr=hydro_data["time_to_peak_hr"],
            time_to_peak_min=hydro_data["time_to_peak_min"],
            tp_unit_hr=hydro_data.get("tp_unit_hr"),
            tp_unit_min=hydro_data.get("tp_unit_min"),
            tb_hr=hydro_data.get("tb_hr"),
            tb_min=hydro_data.get("tb_min"),
            volume_m3=hydro_data["volume_m3"],
            total_depth_mm=hydro_data["total_depth_mm"],
            runoff_mm=hydro_data["runoff_mm"],
            time_hr=hydro_data.get("time_hr", []),
            flow_m3s=hydro_data.get("flow_m3s", []),
        )

        analysis_dict = db.add_analysis(
            basin_id=basin_id,
            tc=tc,
            storm=storm,
            hydrograph=hydrograph,
            note=analysis_data.get("note"),
        )

        # Actualizar ID para mantener el original
        with db.connection() as conn:
            conn.execute(
                "UPDATE analyses SET id = ?, timestamp = ? WHERE id = ?",
                (analysis_data["id"], analysis_data.get("timestamp"), analysis_dict["id"])
            )


def main():
    """Punto de entrada principal."""
    console = Console()

    console.print("\n[bold]Migración de proyectos JSON a SQLite[/bold]\n")

    # Verificar si hay archivos JSON
    projects_dir = Path.home() / ".hidropluvial" / "projects"
    if not projects_dir.exists():
        console.print("[yellow]No existe el directorio de proyectos JSON.[/yellow]")
        return

    json_files = list(projects_dir.glob("*.json"))
    if not json_files:
        console.print("[yellow]No hay archivos JSON para migrar.[/yellow]")
        return

    console.print(f"Encontrados {len(json_files)} archivos JSON para migrar.\n")

    # Preguntar si eliminar después
    from questionary import confirm
    delete_after = confirm(
        "¿Eliminar archivos JSON después de migrar?",
        default=False,
    ).ask()

    if delete_after is None:
        console.print("[yellow]Migración cancelada.[/yellow]")
        return

    migrated, errors = migrate_json_to_sqlite(delete_after=delete_after)

    console.print(f"\n[bold]Resultado:[/bold]")
    console.print(f"  Proyectos migrados: [green]{migrated}[/green]")
    if errors:
        console.print(f"  Errores: [red]{errors}[/red]")

    if not delete_after and migrated > 0:
        console.print(f"\n[dim]Los archivos JSON originales se mantienen en {projects_dir}[/dim]")


if __name__ == "__main__":
    main()
