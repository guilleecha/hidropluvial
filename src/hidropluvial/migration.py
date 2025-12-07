"""
Script de migración de JSON a SQLite.

Convierte los datos existentes en formato JSON a la nueva base de datos SQLite.
"""

import json
from pathlib import Path
from typing import Optional

from hidropluvial.database import Database, get_database
from hidropluvial.session import (
    Session,
    TcResult,
    StormResult,
    HydrographResult,
    AnalysisRun,
)


def migrate_json_to_sqlite(
    data_dir: Optional[Path] = None,
    db: Optional[Database] = None,
    delete_json: bool = False,
    verbose: bool = True,
) -> dict:
    """
    Migra todos los datos JSON existentes a SQLite.

    Args:
        data_dir: Directorio de datos (default: ~/.hidropluvial/)
        db: Instancia de Database (default: global)
        delete_json: Si True, elimina archivos JSON después de migrar
        verbose: Si True, imprime progreso

    Returns:
        Dict con estadísticas de la migración
    """
    if data_dir is None:
        data_dir = Path.home() / ".hidropluvial"

    if db is None:
        db = get_database()

    stats = {
        "projects_migrated": 0,
        "basins_migrated": 0,
        "analyses_migrated": 0,
        "sessions_migrated": 0,
        "errors": [],
    }

    projects_dir = data_dir / "projects"
    sessions_dir = data_dir / "sessions"

    # Migrar proyectos existentes
    if projects_dir.exists():
        for json_path in projects_dir.glob("*.json"):
            try:
                result = _migrate_project_file(json_path, db, verbose)
                stats["projects_migrated"] += result["projects"]
                stats["basins_migrated"] += result["basins"]
                stats["analyses_migrated"] += result["analyses"]

                if delete_json:
                    json_path.unlink()

            except Exception as e:
                error_msg = f"Error migrando {json_path.name}: {e}"
                stats["errors"].append(error_msg)
                if verbose:
                    print(f"  ERROR: {error_msg}")

    # Migrar sesiones legacy (crear proyecto "Sesiones Migradas")
    if sessions_dir.exists():
        session_files = list(sessions_dir.glob("*.json"))
        if session_files:
            try:
                result = _migrate_sessions(session_files, db, verbose, delete_json)
                stats["sessions_migrated"] = result["sessions"]
                stats["basins_migrated"] += result["basins"]
                stats["analyses_migrated"] += result["analyses"]

            except Exception as e:
                error_msg = f"Error migrando sesiones: {e}"
                stats["errors"].append(error_msg)
                if verbose:
                    print(f"  ERROR: {error_msg}")

    return stats


def _migrate_project_file(
    json_path: Path,
    db: Database,
    verbose: bool,
) -> dict:
    """Migra un archivo de proyecto JSON."""
    result = {"projects": 0, "basins": 0, "analyses": 0}

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if verbose:
        print(f"Migrando proyecto: {data.get('name', json_path.stem)}")

    # Crear proyecto en SQLite
    project = db.create_project(
        name=data["name"],
        description=data.get("description", ""),
        author=data.get("author", ""),
        location=data.get("location", ""),
        notes=data.get("notes"),
        tags=data.get("tags", []),
    )
    result["projects"] = 1

    # Migrar cuencas
    for basin_data in data.get("basins", []):
        basin = db.create_basin(
            project_id=project["id"],
            name=basin_data["name"],
            area_ha=basin_data["area_ha"],
            slope_pct=basin_data["slope_pct"],
            p3_10=basin_data["p3_10"],
            c=basin_data.get("c"),
            cn=basin_data.get("cn"),
            length_m=basin_data.get("length_m"),
            notes=basin_data.get("notes"),
        )
        result["basins"] += 1

        # Actualizar coeficientes ponderados si existen
        if basin_data.get("c_weighted") or basin_data.get("cn_weighted"):
            db.update_basin(
                basin_id=basin["id"],
                c_weighted=basin_data.get("c_weighted"),
                cn_weighted=basin_data.get("cn_weighted"),
            )

        # Migrar resultados de Tc
        for tc_data in basin_data.get("tc_results", []):
            db.add_tc_result(
                basin_id=basin["id"],
                method=tc_data["method"],
                tc_hr=tc_data["tc_hr"],
                parameters=tc_data.get("parameters", {}),
            )

        # Migrar análisis
        for analysis_data in basin_data.get("analyses", []):
            tc = TcResult(**analysis_data["tc"])
            storm = StormResult(**analysis_data["storm"])
            hydrograph = HydrographResult(**analysis_data["hydrograph"])

            db.add_analysis(
                basin_id=basin["id"],
                tc=tc,
                storm=storm,
                hydrograph=hydrograph,
                note=analysis_data.get("note"),
            )
            result["analyses"] += 1

    if verbose:
        print(f"  -> {result['basins']} cuencas, {result['analyses']} análisis")

    return result


def _migrate_sessions(
    session_files: list[Path],
    db: Database,
    verbose: bool,
    delete_json: bool,
) -> dict:
    """Migra sesiones legacy a un nuevo proyecto."""
    result = {"sessions": 0, "basins": 0, "analyses": 0}

    if verbose:
        print(f"Migrando {len(session_files)} sesiones legacy...")

    # Crear proyecto contenedor
    project = db.create_project(
        name="Sesiones Migradas",
        description="Proyecto creado automáticamente para sesiones legacy",
    )

    for json_path in session_files:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            session = Session.model_validate(data)

            # Crear cuenca desde sesión
            basin = db.create_basin(
                project_id=project["id"],
                name=session.cuenca.nombre or session.name,
                area_ha=session.cuenca.area_ha,
                slope_pct=session.cuenca.slope_pct,
                p3_10=session.cuenca.p3_10,
                c=session.cuenca.c,
                cn=session.cuenca.cn,
                length_m=session.cuenca.length_m,
                notes=session.notes,
            )
            result["sessions"] += 1
            result["basins"] += 1

            # Actualizar coeficientes ponderados
            if session.cuenca.c_weighted or session.cuenca.cn_weighted:
                db.update_basin(
                    basin_id=basin["id"],
                    c_weighted=session.cuenca.c_weighted.model_dump() if session.cuenca.c_weighted else None,
                    cn_weighted=session.cuenca.cn_weighted.model_dump() if session.cuenca.cn_weighted else None,
                )

            # Migrar resultados de Tc
            for tc_result in session.tc_results:
                db.add_tc_result(
                    basin_id=basin["id"],
                    method=tc_result.method,
                    tc_hr=tc_result.tc_hr,
                    parameters=tc_result.parameters,
                )

            # Migrar análisis
            for analysis in session.analyses:
                db.add_analysis(
                    basin_id=basin["id"],
                    tc=analysis.tc,
                    storm=analysis.storm,
                    hydrograph=analysis.hydrograph,
                    note=analysis.note,
                )
                result["analyses"] += 1

            if delete_json:
                json_path.unlink()

        except Exception as e:
            if verbose:
                print(f"  Error con {json_path.name}: {e}")

    if verbose:
        print(f"  -> {result['basins']} cuencas, {result['analyses']} análisis")

    return result


def check_migration_needed(data_dir: Optional[Path] = None) -> dict:
    """
    Verifica si hay datos JSON que necesitan migración.

    Returns:
        Dict con conteos de archivos pendientes
    """
    if data_dir is None:
        data_dir = Path.home() / ".hidropluvial"

    result = {
        "projects_json": 0,
        "sessions_json": 0,
        "migration_needed": False,
    }

    projects_dir = data_dir / "projects"
    sessions_dir = data_dir / "sessions"

    if projects_dir.exists():
        result["projects_json"] = len(list(projects_dir.glob("*.json")))

    if sessions_dir.exists():
        result["sessions_json"] = len(list(sessions_dir.glob("*.json")))

    result["migration_needed"] = (
        result["projects_json"] > 0 or result["sessions_json"] > 0
    )

    return result


def backup_json_data(
    data_dir: Optional[Path] = None,
    backup_dir: Optional[Path] = None,
) -> Path:
    """
    Crea backup de todos los archivos JSON.

    Returns:
        Path del directorio de backup
    """
    import shutil
    from datetime import datetime

    if data_dir is None:
        data_dir = Path.home() / ".hidropluvial"

    if backup_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = data_dir / f"backup_{timestamp}"

    backup_dir.mkdir(parents=True, exist_ok=True)

    # Copiar proyectos
    projects_dir = data_dir / "projects"
    if projects_dir.exists():
        backup_projects = backup_dir / "projects"
        shutil.copytree(projects_dir, backup_projects)

    # Copiar sesiones
    sessions_dir = data_dir / "sessions"
    if sessions_dir.exists():
        backup_sessions = backup_dir / "sessions"
        shutil.copytree(sessions_dir, backup_sessions)

    return backup_dir


if __name__ == "__main__":
    import sys

    # Verificar si hay migración pendiente
    status = check_migration_needed()

    if not status["migration_needed"]:
        print("No hay datos JSON para migrar.")
        sys.exit(0)

    print(f"Encontrados: {status['projects_json']} proyectos, {status['sessions_json']} sesiones")
    print()

    # Crear backup
    print("Creando backup...")
    backup_path = backup_json_data()
    print(f"Backup creado en: {backup_path}")
    print()

    # Ejecutar migración
    print("Iniciando migración a SQLite...")
    stats = migrate_json_to_sqlite(verbose=True)
    print()

    # Resumen
    print("=== Migración completada ===")
    print(f"Proyectos: {stats['projects_migrated']}")
    print(f"Cuencas: {stats['basins_migrated']}")
    print(f"Análisis: {stats['analyses_migrated']}")
    print(f"Sesiones legacy: {stats['sessions_migrated']}")

    if stats["errors"]:
        print(f"\nErrores ({len(stats['errors'])}):")
        for error in stats["errors"]:
            print(f"  - {error}")
