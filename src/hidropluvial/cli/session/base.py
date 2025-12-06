"""
Comandos básicos de sesión: create, list, show, tc, summary, delete.
"""

from typing import Annotated, Optional

import typer

from hidropluvial.session import SessionManager
from hidropluvial.cli.theme import print_header, print_field, print_separator, print_subheader

# Instancia global del gestor de sesiones
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Obtiene o crea el gestor de sesiones."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def session_create(
    name: Annotated[str, typer.Argument(help="Nombre de la sesión")],
    area_ha: Annotated[float, typer.Option("--area", "-a", help="Área en hectáreas")],
    slope_pct: Annotated[float, typer.Option("--slope", "-s", help="Pendiente media en %")],
    p3_10: Annotated[float, typer.Option("--p3_10", "-p", help="P3,10 en mm")],
    c: Annotated[Optional[float], typer.Option("--c", help="Coef. escorrentía (0-1)")] = None,
    cn: Annotated[Optional[int], typer.Option("--cn", help="Curve Number (30-100)")] = None,
    length_m: Annotated[Optional[float], typer.Option("--length", "-l", help="Longitud cauce en m")] = None,
    cuenca_nombre: Annotated[str, typer.Option("--cuenca", help="Nombre de la cuenca")] = "",
):
    """
    Crea una nueva sesión de análisis.

    Ejemplo:
        hidropluvial session create "Proyecto Norte" --area 62 --slope 3.41 --p3_10 83 --c 0.62 --cn 81
    """
    manager = get_session_manager()

    session = manager.create(
        name=name,
        area_ha=area_ha,
        slope_pct=slope_pct,
        p3_10=p3_10,
        c=c,
        cn=cn,
        length_m=length_m,
        cuenca_nombre=cuenca_nombre,
    )

    print_header("SESION CREADA")
    print_field("ID", session.id)
    print_field("Nombre", session.name)
    print_field("Cuenca", session.cuenca.nombre)
    print_subheader("")
    print_field("Area", f"{session.cuenca.area_ha:.2f}", "ha")
    print_field("Pendiente", f"{session.cuenca.slope_pct:.2f}", "%")
    print_field("P3,10", f"{session.cuenca.p3_10:.1f}", "mm")
    if session.cuenca.c:
        print_field("Coef. C", f"{session.cuenca.c:.2f}")
    if session.cuenca.cn:
        print_field("CN", f"{session.cuenca.cn}")
    if session.cuenca.length_m:
        print_field("Longitud cauce", f"{session.cuenca.length_m:.0f}", "m")
    print_separator()
    typer.echo(f"\n  Usa 'session tc {session.id}' para calcular Tc")
    typer.echo(f"  Usa 'session analyze {session.id}' para analisis completo\n")


def session_list():
    """Lista todas las sesiones disponibles."""
    manager = get_session_manager()
    sessions = manager.list_sessions()

    if not sessions:
        typer.echo("\nNo hay sesiones guardadas.")
        typer.echo("Usa 'session create' para crear una nueva.\n")
        return

    from hidropluvial.cli.theme import print_sessions_table
    print_sessions_table(sessions)


def session_show(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
):
    """Muestra detalles de una sesión."""
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    print_header(f"SESION: {session.name}")
    print_field("ID", session.id)
    print_field("Creada", session.created_at[:19].replace('T', ' '))
    print_field("Actualizada", session.updated_at[:19].replace('T', ' '))

    print_subheader(f"CUENCA: {session.cuenca.nombre}")
    print_field("Area", f"{session.cuenca.area_ha:.2f}", "ha")
    print_field("Pendiente", f"{session.cuenca.slope_pct:.2f}", "%")
    print_field("P3,10", f"{session.cuenca.p3_10:.1f}", "mm")
    if session.cuenca.c:
        print_field("Coef. C", f"{session.cuenca.c:.2f}")
    if session.cuenca.cn:
        print_field("CN", f"{session.cuenca.cn}")
    if session.cuenca.length_m:
        print_field("Longitud cauce", f"{session.cuenca.length_m:.0f}", "m")

    # Mostrar Tc calculados
    if session.tc_results:
        print_subheader("TIEMPOS DE CONCENTRACION")
        for tc in session.tc_results:
            typer.echo(f"  {tc.method:15} Tc = {tc.tc_min:>8.1f} min ({tc.tc_hr:.2f} hr)")

    # Mostrar análisis
    if session.analyses:
        print_subheader(f"ANALISIS REALIZADOS: {len(session.analyses)}")
        for a in session.analyses:
            x_str = f"X={a.hydrograph.x_factor:.2f}" if a.hydrograph.x_factor else ""
            typer.echo(f"  [{a.id}] {a.tc.method} + {a.storm.type} Tr{a.storm.return_period} {x_str}")
            typer.echo(f"          Qp = {a.hydrograph.peak_flow_m3s:.3f} m3/s, Tp = {a.hydrograph.time_to_peak_min:.1f} min")

    print_separator()


def session_tc(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
    methods: Annotated[str, typer.Option("--methods", "-m", help="Métodos: kirpich,temez,desbordes")] = "desbordes",
):
    """
    Calcula tiempo de concentración con múltiples métodos.

    Ejemplo:
        hidropluvial session tc abc123 --methods "kirpich,desbordes"
    """
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    from hidropluvial.core import desbordes, kirpich, temez

    method_list = [m.strip().lower() for m in methods.split(",")]

    print_header("CALCULO DE TIEMPOS DE CONCENTRACION")
    typer.echo(f"  Sesion: {session.name} [{session.id}]")
    print_subheader("")

    for method in method_list:
        tc_hr = None
        params = {}

        if method == "kirpich":
            if not session.cuenca.length_m:
                typer.echo(f"  {method}: ERROR - Requiere longitud de cauce", err=True)
                continue
            slope_mm = session.cuenca.slope_pct / 100
            tc_hr = kirpich(session.cuenca.length_m, slope_mm)
            params = {"length_m": session.cuenca.length_m, "slope_mm": slope_mm}

        elif method == "temez":
            if not session.cuenca.length_m:
                typer.echo(f"  {method}: ERROR - Requiere longitud de cauce", err=True)
                continue
            slope_mm = session.cuenca.slope_pct / 100
            length_km = session.cuenca.length_m / 1000
            tc_hr = temez(length_km, slope_mm)
            params = {"length_km": length_km, "slope_mm": slope_mm}

        elif method == "desbordes":
            if not session.cuenca.c:
                typer.echo(f"  {method}: ERROR - Requiere coeficiente C", err=True)
                continue
            tc_hr = desbordes(
                session.cuenca.area_ha,
                session.cuenca.slope_pct,
                session.cuenca.c,
            )
            params = {
                "area_ha": session.cuenca.area_ha,
                "slope_pct": session.cuenca.slope_pct,
                "c": session.cuenca.c,
            }

        else:
            typer.echo(f"  {method}: ERROR - Método desconocido", err=True)
            continue

        if tc_hr:
            result = manager.add_tc_result(session, method, tc_hr, **params)
            typer.echo(f"  {method:15} Tc = {result.tc_min:>8.1f} min ({result.tc_hr:.2f} hr)")

    print_separator()


def session_summary(
    session_id: Annotated[str, typer.Argument(help="ID o nombre de la sesión")],
):
    """
    Muestra tabla comparativa de todos los análisis.

    Ejemplo:
        hidropluvial session summary abc123
    """
    manager = get_session_manager()

    try:
        session = manager.find(session_id)
    except FileNotFoundError:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    if not session.analyses:
        typer.echo(f"\nNo hay análisis en la sesión '{session.name}'.")
        typer.echo("Usa 'session analyze' para ejecutar análisis.\n")
        return

    from hidropluvial.cli.formatters import format_flow, format_volume_hm3
    from hidropluvial.cli.theme import print_summary_table

    rows = manager.get_summary_table(session)

    print_summary_table(session.name, rows)

    # Mostrar máximos/mínimos
    if len(rows) > 1:
        max_q = max(rows, key=lambda x: x['qpeak_m3s'])
        min_q = min(rows, key=lambda x: x['qpeak_m3s'])

        typer.echo(f"  Caudal maximo: {format_flow(max_q['qpeak_m3s'])} m3/s ({max_q['tc_method']} + {max_q['storm']} Tr{max_q['tr']})")
        typer.echo(f"  Caudal minimo: {format_flow(min_q['qpeak_m3s'])} m3/s ({min_q['tc_method']} + {min_q['storm']} Tr{min_q['tr']})")
        typer.echo(f"  Variacion: {(max_q['qpeak_m3s'] - min_q['qpeak_m3s']) / min_q['qpeak_m3s'] * 100:.1f}%\n")


def session_delete(
    session_id: Annotated[str, typer.Argument(help="ID de la sesión a eliminar")],
    force: Annotated[bool, typer.Option("--force", "-f", help="No pedir confirmación")] = False,
):
    """Elimina una sesión."""
    manager = get_session_manager()

    if not force:
        confirm = typer.confirm(f"¿Eliminar sesión '{session_id}'?")
        if not confirm:
            typer.echo("Cancelado.")
            raise typer.Exit(0)

    if manager.delete(session_id):
        typer.echo(f"Sesión '{session_id}' eliminada.")
    else:
        typer.echo(f"Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)


def session_edit(
    session_id: Annotated[str, typer.Argument(help="ID de la sesión a editar")],
    area_ha: Annotated[Optional[float], typer.Option("--area", "-a", help="Nueva área (ha)")] = None,
    slope_pct: Annotated[Optional[float], typer.Option("--slope", "-s", help="Nueva pendiente (%)")] = None,
    p3_10: Annotated[Optional[float], typer.Option("--p3_10", "-p", help="Nuevo P3,10 (mm)")] = None,
    c: Annotated[Optional[float], typer.Option("--c", help="Nuevo coef. C")] = None,
    cn: Annotated[Optional[int], typer.Option("--cn", help="Nuevo CN")] = None,
    length_m: Annotated[Optional[float], typer.Option("--length", "-l", help="Nueva longitud (m)")] = None,
    clone: Annotated[bool, typer.Option("--clone", help="Crear nueva sesión en vez de modificar")] = False,
    new_name: Annotated[Optional[str], typer.Option("--name", "-n", help="Nombre para la sesión clonada")] = None,
):
    """
    Edita los parámetros de una cuenca en una sesión existente.

    ADVERTENCIA: Los análisis existentes fueron calculados con los datos
    originales. Al modificar parámetros:
    - Los análisis existentes se ELIMINAN (opción por defecto)
    - O se crea una NUEVA sesión con los cambios (--clone)

    Ejemplos:
        # Corregir el área (elimina análisis existentes)
        hp session edit abc123 --area 65

        # Crear nueva sesión con área corregida (preserva original)
        hp session edit abc123 --area 65 --clone

        # Modificar varios parámetros
        hp session edit abc123 --area 65 --slope 3.0 --c 0.58
    """
    manager = get_session_manager()

    session = manager.get_session(session_id)
    if session is None:
        typer.echo(f"Error: Sesión '{session_id}' no encontrada.", err=True)
        raise typer.Exit(1)

    # Verificar que hay algo que cambiar
    if all(v is None for v in [area_ha, slope_pct, p3_10, c, cn, length_m]):
        typer.echo("Error: Debes especificar al menos un parámetro a modificar.")
        typer.echo("\nUso: hp session edit <id> --area VALOR --slope VALOR ...")
        raise typer.Exit(1)

    # Mostrar valores actuales y propuestos
    print_header(f"EDITAR SESION: {session.name} [{session.id}]")

    cuenca = session.cuenca
    typer.echo(f"\n  {'Parametro':<20} {'Actual':>12} {'Nuevo':>12}")
    typer.echo(f"  {'-'*44}")

    if area_ha is not None:
        typer.echo(f"  {'Área (ha)':<20} {cuenca.area_ha:>12.2f} {area_ha:>12.2f}")
    if slope_pct is not None:
        typer.echo(f"  {'Pendiente (%)':<20} {cuenca.slope_pct:>12.2f} {slope_pct:>12.2f}")
    if p3_10 is not None:
        typer.echo(f"  {'P3,10 (mm)':<20} {cuenca.p3_10:>12.1f} {p3_10:>12.1f}")
    if c is not None:
        c_actual = cuenca.c if cuenca.c else 0
        typer.echo(f"  {'Coef. C':<20} {c_actual:>12.2f} {c:>12.2f}")
    if cn is not None:
        cn_actual = cuenca.cn if cuenca.cn else 0
        typer.echo(f"  {'CN':<20} {cn_actual:>12} {cn:>12}")
    if length_m is not None:
        length_actual = cuenca.length_m if cuenca.length_m else 0
        typer.echo(f"  {'Longitud (m)':<20} {length_actual:>12.0f} {length_m:>12.0f}")

    # Advertencia sobre análisis existentes
    n_analyses = len(session.analyses)
    n_tc = len(session.tc_results)

    if n_analyses > 0 or n_tc > 0:
        typer.echo(f"\n  ⚠️  ADVERTENCIA:")
        if n_tc > 0:
            typer.echo(f"      - {n_tc} cálculos de Tc serán ELIMINADOS")
        if n_analyses > 0:
            typer.echo(f"      - {n_analyses} análisis serán ELIMINADOS")
        typer.echo(f"      (fueron calculados con los datos anteriores)")

    if clone:
        typer.echo(f"\n  Modo: CLONAR (se creara nueva sesion, la original no cambia)")
    else:
        typer.echo(f"\n  Modo: MODIFICAR (se actualizara la sesion existente)")

    print_separator()

    # Confirmar
    if not typer.confirm("\n¿Continuar con los cambios?"):
        typer.echo("Cancelado.")
        raise typer.Exit(0)

    if clone:
        # Crear nueva sesión clonada
        new_session, changes = manager.clone_with_modified_cuenca(
            session,
            new_name=new_name,
            area_ha=area_ha,
            slope_pct=slope_pct,
            p3_10=p3_10,
            c=c,
            cn=cn,
            length_m=length_m,
        )

        typer.echo(f"\n  ✓ Nueva sesión creada: {new_session.id}")
        typer.echo(f"    Nombre: {new_session.name}")
        if changes:
            typer.echo(f"\n  Cambios aplicados:")
            for change in changes:
                typer.echo(f"    - {change}")

        typer.echo(f"\n  Sesión original '{session.id}' sin modificar.")
        typer.echo(f"  Usa 'hp session tc {new_session.id}' para calcular Tc\n")

    else:
        # Modificar en el lugar
        changes = manager.update_cuenca_in_place(
            session,
            area_ha=area_ha,
            slope_pct=slope_pct,
            p3_10=p3_10,
            c=c,
            cn=cn,
            length_m=length_m,
            clear_analyses=True,
        )

        if changes:
            typer.echo(f"\n  ✓ Sesión '{session.id}' actualizada.")
            typer.echo(f"\n  Cambios aplicados:")
            for change in changes:
                typer.echo(f"    - {change}")

            typer.echo(f"\n  Usa 'hp session tc {session.id}' para recalcular Tc")
            typer.echo(f"  Usa 'hp session analyze {session.id}' para nuevos análisis\n")
        else:
            typer.echo("\n  No se realizaron cambios (valores iguales).\n")


def session_clean(
    pattern: Annotated[Optional[str], typer.Option("--pattern", "-p", help="Patrón en nombre (ej: 'test')")] = None,
    empty: Annotated[bool, typer.Option("--empty", "-e", help="Eliminar sesiones sin análisis")] = False,
    force: Annotated[bool, typer.Option("--force", "-f", help="No pedir confirmación")] = False,
):
    """
    Limpia sesiones según criterios.

    Ejemplos:
        # Eliminar sesiones con "test" en el nombre
        hp session clean --pattern test

        # Eliminar sesiones vacías (sin análisis)
        hp session clean --empty

        # Combinar criterios (OR)
        hp session clean --pattern prueba --empty
    """
    manager = get_session_manager()
    sessions = manager.list_sessions()

    to_delete = []

    for s in sessions:
        should_delete = False

        if pattern and pattern.lower() in s["name"].lower():
            should_delete = True

        if empty and s["n_analyses"] == 0:
            should_delete = True

        if should_delete:
            to_delete.append(s)

    if not to_delete:
        typer.echo("No hay sesiones que coincidan con los criterios.")
        return

    typer.echo(f"\nSesiones a eliminar ({len(to_delete)}):")
    typer.echo(f"  {'ID':8} | {'Nombre':25} | {'Análisis':>8}")
    typer.echo(f"  {'-'*50}")
    for s in to_delete[:15]:
        typer.echo(f"  {s['id']:8} | {s['name'][:25]:25} | {s['n_analyses']:>8}")
    if len(to_delete) > 15:
        typer.echo(f"  ... y {len(to_delete) - 15} más")

    if not force:
        confirm = typer.confirm(f"\n¿Eliminar {len(to_delete)} sesiones?")
        if not confirm:
            typer.echo("Cancelado.")
            raise typer.Exit(0)

    deleted = 0
    for s in to_delete:
        if manager.delete(s["id"]):
            deleted += 1

    typer.echo(f"\n{deleted} sesiones eliminadas.")


def session_rename(
    session_id: Annotated[str, typer.Argument(help="ID de sesión")],
    new_name: Annotated[str, typer.Argument(help="Nuevo nombre")],
):
    """Renombra una sesión."""
    manager = get_session_manager()
    session = manager.get_session(session_id)

    if not session:
        typer.echo(f"Sesión no encontrada: {session_id}", err=True)
        raise typer.Exit(1)

    old_name = session.name
    session.name = new_name
    manager.save(session)

    typer.echo(f"Sesión renombrada: '{old_name}' -> '{new_name}'")
