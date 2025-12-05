"""
Comando 'commands' - Lista todos los comandos disponibles.
"""

import typer

from hidropluvial.cli.formatters import fmt


def show_commands():
    """
    Muestra todos los comandos disponibles con ejemplos.
    """
    typer.echo("""
+-------------------------------------------------------------+
|              HIDROPLUVIAL - Comandos Disponibles            |
+-------------------------------------------------------------+

USO: hp <comando> [opciones]

PROYECTOS (estructura multi-cuenca)
--------------------------------------------------------------
  project create <nombre>     Crear proyecto hidrologico
  project list                Listar proyectos disponibles
  project show <id>           Ver detalles del proyecto
  project edit <id>           Editar metadatos
  project delete <id>         Eliminar proyecto
  project basin-add <id>      Agregar cuenca al proyecto
  project basin-list <id>     Listar cuencas del proyecto
  project basin-show <id>     Ver detalles de cuenca
  project migrate             Migrar sesiones a proyecto

SESIONES (legacy, cuenca individual)
--------------------------------------------------------------
  session create <nombre>     Crear sesion de analisis
  session list                Listar sesiones guardadas
  session tc <id>             Calcular tiempo de concentracion
  session analyze <id>        Ejecutar analisis hidrologico
  session summary <id>        Ver tabla resumen
  session preview <id>        Ver hidrogramas en terminal
  session report <id>         Generar reporte LaTeX
  session export <id>         Exportar a Excel/CSV
  session batch <yaml>        Analisis batch desde archivo
  session delete <id>         Eliminar sesion

CURVAS IDF
--------------------------------------------------------------
  idf tabla-uy <estacion>     Tabla IDF para estacion Uruguay
  idf intensidad <est> <d>    Intensidad para duracion especifica

TORMENTAS DE DISENO
--------------------------------------------------------------
  storm blocks <p3_10> <dur>  Tormenta bloques alternantes
  storm gz <p3_10>            Tormenta metodologia GZ (6h)
  storm bimodal-uy <p3_10>    Tormenta bimodal Uruguay

TIEMPO DE CONCENTRACION
--------------------------------------------------------------
  tc kirpich <L> <S>          Metodo Kirpich (L en m, S en m/m)
  tc desbordes <A> <S> <C>    Metodo Desbordes (A en ha, S en %)

ESCORRENTIA
--------------------------------------------------------------
  runoff cn <P> <CN>          Escorrentia metodo SCS-CN

HIDROGRAMAS
--------------------------------------------------------------
  hydrograph scs              Hidrograma unitario SCS
  hydrograph gz               Hidrograma metodologia GZ

EXPORTACION
--------------------------------------------------------------
  export idf-csv <est>        Exportar tabla IDF a CSV
  report idf <est>            Generar reporte IDF en LaTeX

EJEMPLO RAPIDO (proyecto)
--------------------------------------------------------------
  # Crear proyecto
  hp project create "Estudio Arroyo XYZ" --desc "Drenaje zona norte"

  # Agregar cuenca al proyecto
  hp project basin-add abc123 "Subcuenca Norte" --area 50 --slope 2.5 --p3_10 80 --c 0.55

  # Migrar sesiones existentes a proyecto
  hp project migrate --name "Mis Analisis"

EJEMPLO RAPIDO (sesion legacy)
--------------------------------------------------------------
  # Crear sesion con datos de cuenca
  hp session create "Mi Cuenca" --area 50 --slope 2.5 --p3_10 80 --c 0.55

  # Calcular tiempo de concentracion
  hp session tc abc123 --methods "kirpich,desbordes"

  # Ejecutar analisis
  hp session analyze abc123 --tc desbordes --storm gz --tr 10

  # Ver hidrogramas en terminal
  hp session preview abc123 --interactive          # Navegar con flechas
  hp session preview abc123 --compare              # Comparar todos
  hp session preview abc123 --compare --select 0,2 # Comparar indices
  hp session preview abc123 --compare --tr 10      # Filtrar por Tr
  hp session preview abc123 -i 0                   # Ver hidrograma #0
  hp session preview abc123 -i 0 --hyeto           # Ver hietograma #0

  # Generar reporte
  hp session report abc123 -o mi_reporte

MODO INTERACTIVO
--------------------------------------------------------------
  hp wizard                   Asistente guiado paso a paso

Usa 'hp <comando> --help' para ver opciones detalladas.
""")
