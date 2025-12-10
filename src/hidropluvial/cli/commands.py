"""
Comando 'commands' - Lista todos los comandos disponibles.
"""

import typer


def show_commands():
    """
    Muestra todos los comandos disponibles con ejemplos.
    """
    typer.echo("""
+-------------------------------------------------------------+
|              HIDROPLUVIAL - Comandos Disponibles            |
+-------------------------------------------------------------+

USO: hp <comando> [opciones]

MODO INTERACTIVO (RECOMENDADO)
--------------------------------------------------------------
  wizard                   Asistente guiado paso a paso

PROYECTOS
--------------------------------------------------------------
  project create <nombre>     Crear proyecto hidrologico
  project list                Listar proyectos disponibles
  project show <id>           Ver detalles del proyecto
  project edit <id>           Editar metadatos
  project delete <id>         Eliminar proyecto
  project basin-add <id>      Agregar cuenca al proyecto
  project basin-list <id>     Listar cuencas del proyecto
  project basin-show <id>     Ver detalles de cuenca

CUENCAS
--------------------------------------------------------------
  basin list [project_id]     Listar cuencas (todas o de proyecto)
  basin show <id>             Ver detalles de cuenca
  basin export <id>           Exportar a Excel/CSV
  basin report <id>           Generar reporte LaTeX
  basin preview <id>          Ver hidrogramas en terminal
  basin compare <id1> <id2>   Comparar cuencas

CURVAS IDF
--------------------------------------------------------------
  idf departamentos           Ver P3,10 por departamento
  idf uruguay <p3_10> <d>     Calcular intensidad

TIEMPO DE CONCENTRACION
--------------------------------------------------------------
  tc kirpich <L> <S>          Metodo Kirpich (L en m, S en m/m)
  tc desbordes <A> <S> <C>    Metodo Desbordes (A en ha, S en %)
  tc temez <L> <S>            Metodo Temez (L en km, S en m/m)

ESCORRENTIA
--------------------------------------------------------------
  runoff cn <P> <CN>          Escorrentia metodo SCS-CN
  runoff cn-table             Ver tablas de CN

TORMENTAS DE DISENO
--------------------------------------------------------------
  storm blocks <p3_10> <dur>  Tormenta bloques alternantes
  storm gz <p3_10>            Tormenta metodologia GZ (6h)
  storm bimodal-uy <p3_10>    Tormenta bimodal Uruguay

EJEMPLO RAPIDO
--------------------------------------------------------------
  # Iniciar wizard (recomendado)
  hp wizard

  # Crear proyecto y agregar cuenca
  hp project create "Estudio Arroyo XYZ" --desc "Drenaje zona norte"
  hp project basin-add abc123 "Cuenca A" --area 50 --slope 2.5 --p310 80

  # Ver cuencas
  hp basin list
  hp basin show abc123

  # Exportar y reportes
  hp basin export abc123 --format xlsx
  hp basin report abc123 --pdf

  # Ver hidrogramas interactivamente
  hp basin preview abc123

  # Calculos directos
  hp tc kirpich 800 0.034
  hp idf uruguay 78 3 --tr 25

Usa 'hp <comando> --help' para ver opciones detalladas.
""")
