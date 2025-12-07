"""
Textos metodológicos para Tiempo de Concentración.
"""

from typing import Optional


def get_tc_methodology_latex(methods_used: Optional[list[str]] = None) -> str:
    """
    Genera texto LaTeX explicativo sobre métodos de tiempo de concentración.

    Args:
        methods_used: Lista de métodos utilizados (kirpich, temez, desbordes, nrcs).
                     Si es None, incluye todos los métodos.

    Returns:
        Contenido LaTeX con marco teórico y formulaciones.
    """
    content = r"""
\subsection{Marco Teórico: Tiempo de Concentración}

El tiempo de concentración ($T_c$) es el tiempo que tarda el agua en viajar desde
el punto hidráulicamente más alejado de la cuenca hasta el punto de salida o de interés.
Este parámetro es fundamental en el diseño hidrológico ya que:

\begin{itemize}
    \item Determina la duración crítica de la tormenta de diseño
    \item Influye directamente en la forma del hidrograma de crecida
    \item Condiciona el caudal pico calculado
\end{itemize}

Existen múltiples fórmulas empíricas para estimar $T_c$, cada una desarrollada
para condiciones específicas de cuenca. La selección del método apropiado depende
del tipo de cuenca, su tamaño, y la disponibilidad de datos.

"""

    # Determinar qué métodos incluir
    all_methods = ["kirpich", "temez", "desbordes", "nrcs"]
    if methods_used:
        methods_to_include = [m.lower() for m in methods_used if m.lower() in all_methods]
    else:
        methods_to_include = all_methods

    # Agregar secciones por método
    if "kirpich" in methods_to_include:
        content += _get_kirpich_section()

    if "temez" in methods_to_include:
        content += _get_temez_section()

    if "desbordes" in methods_to_include:
        content += _get_desbordes_section()

    if "nrcs" in methods_to_include:
        content += _get_nrcs_section()

    # Referencias
    content += _get_tc_references(methods_to_include)

    return content


def _get_kirpich_section() -> str:
    """Sección del método Kirpich."""
    return r"""
\subsubsection{Método de Kirpich (1940)}

Desarrollado por Kirpich para pequeñas cuencas agrícolas en Tennessee, Estados Unidos.
Es uno de los métodos más utilizados por su simplicidad y amplia validación.

\textbf{Formulación:}
\begin{equation}
T_c = 0.0195 \times L^{0.77} \times S^{-0.385}
\label{eq:kirpich}
\end{equation}

Donde:
\begin{itemize}
    \item $T_c$ = Tiempo de concentración (minutos)
    \item $L$ = Longitud del cauce principal (metros)
    \item $S$ = Pendiente media del cauce (m/m)
\end{itemize}

\textbf{Factores de ajuste por superficie:}

\begin{table}[H]
\centering
\small
\begin{tabular}{lc}
\toprule
Tipo de Superficie & Factor \\
\midrule
Natural (sin tratamiento) & 1.0 \\
Con pasto (grassy) & 2.0 \\
Concreto/asfalto & 0.4 \\
Canal de concreto & 0.2 \\
\bottomrule
\end{tabular}
\caption{Factores de ajuste para método Kirpich}
\end{table}

\textbf{Rango de aplicación:}
\begin{itemize}
    \item Cuencas rurales pequeñas: $A < 80$ ha
    \item Pendientes: 3\% a 10\%
    \item Cauces naturales bien definidos
\end{itemize}

"""


def _get_temez_section() -> str:
    """Sección del método Témez."""
    return r"""
\subsubsection{Método de Témez (1978)}

Fórmula desarrollada por José Ramón Témez para cuencas naturales en España.
Ampliamente utilizada en Latinoamérica por su adaptabilidad a diversas condiciones.

\textbf{Formulación:}
\begin{equation}
T_c = 0.3 \times \left( \frac{L}{S^{0.25}} \right)^{0.76}
\label{eq:temez}
\end{equation}

Donde:
\begin{itemize}
    \item $T_c$ = Tiempo de concentración (horas)
    \item $L$ = Longitud del cauce principal (km)
    \item $S$ = Pendiente media del cauce (m/m)
\end{itemize}

\textbf{Rango de aplicación:}
\begin{itemize}
    \item Cuencas naturales: 1 a 3000 km²
    \item Pendientes moderadas a altas
    \item Ampliamente validado en cuencas iberoamericanas
\end{itemize}

\textbf{Observaciones:}
El método Témez tiende a dar valores de $T_c$ mayores que Kirpich para cuencas
pequeñas, lo que resulta en caudales pico menores. Se recomienda para estudios
de planificación donde se requiere un enfoque conservador.

"""


def _get_desbordes_section() -> str:
    """Sección del método de los Desbordes (DINAGUA)."""
    return r"""
\subsubsection{Método de los Desbordes (DINAGUA Uruguay)}

Método recomendado por la Dirección Nacional de Aguas (DINAGUA) de Uruguay
para cuencas urbanas. Especialmente útil para diseño de sistemas de drenaje pluvial.

\textbf{Formulación:}
\begin{equation}
T_c = T_0 + 6.625 \times A^{0.3} \times P^{-0.39} \times C^{-0.45}
\label{eq:desbordes}
\end{equation}

Donde:
\begin{itemize}
    \item $T_c$ = Tiempo de concentración (minutos)
    \item $T_0$ = Tiempo de entrada inicial (típicamente 5 min)
    \item $A$ = Área de la cuenca (hectáreas)
    \item $P$ = Pendiente media de la cuenca (\%)
    \item $C$ = Coeficiente de escorrentía (0-1)
\end{itemize}

\textbf{Valores típicos de $T_0$:}
\begin{itemize}
    \item Áreas residenciales: 5 minutos
    \item Áreas comerciales/industriales: 3-5 minutos
    \item Áreas con techos conectados directamente: 2-3 minutos
\end{itemize}

\textbf{Rango de aplicación:}
\begin{itemize}
    \item Cuencas urbanas: $A < 500$ ha
    \item Zonas con desarrollo urbano consolidado
    \item Sistemas de drenaje pluvial en Uruguay
\end{itemize}

\textbf{Referencia normativa:}
Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas, DINAGUA-MVOTMA.

"""


def _get_nrcs_section() -> str:
    """Sección del método NRCS (TR-55)."""
    return r"""
\subsubsection{Método NRCS (TR-55)}

El método del Natural Resources Conservation Service (antes SCS) divide el
trayecto del agua en tres tipos de flujo, calculando el tiempo de viaje para cada uno.

\textbf{Componentes del tiempo de concentración:}
\begin{equation}
T_c = T_{laminar} + T_{concentrado} + T_{canal}
\label{eq:nrcs}
\end{equation}

\paragraph{Flujo Laminar (Sheet Flow)}

Ocurre en los primeros metros del recorrido (máximo 100 m):
\begin{equation}
T_t = \frac{0.007 \times (n \times L)^{0.8}}{P_2^{0.5} \times S^{0.4}}
\end{equation}

Donde:
\begin{itemize}
    \item $T_t$ = Tiempo de viaje (horas)
    \item $n$ = Coeficiente de rugosidad de Manning
    \item $L$ = Longitud del flujo (pies), máximo $\approx$ 100 m
    \item $P_2$ = Precipitación de 2 años, 24 horas (pulgadas)
    \item $S$ = Pendiente (m/m)
\end{itemize}

\begin{table}[H]
\centering
\small
\begin{tabular}{lc}
\toprule
Superficie & $n$ \\
\midrule
Lisa (smooth) & 0.011 \\
Barbecho (fallow) & 0.05 \\
Pasto corto & 0.15 \\
Pasto denso & 0.24 \\
Bosque ligero & 0.40 \\
Bosque denso & 0.80 \\
\bottomrule
\end{tabular}
\caption{Coeficientes de Manning para flujo laminar}
\end{table}

\paragraph{Flujo Concentrado Superficial (Shallow Flow)}

Flujo que se concentra después del flujo laminar:
\begin{equation}
V = k \times S^{0.5} \quad ; \quad T_t = \frac{L}{V \times 3600}
\end{equation}

\begin{table}[H]
\centering
\small
\begin{tabular}{lc}
\toprule
Superficie & $k$ (m/s) \\
\midrule
Pavimentada & 6.196 \\
Sin pavimentar & 4.918 \\
Con pasto & 4.572 \\
Pasto corto & 2.134 \\
\bottomrule
\end{tabular}
\caption{Coeficientes $k$ para flujo concentrado superficial}
\end{table}

\paragraph{Flujo en Canal}

Utiliza la ecuación de Manning:
\begin{equation}
V = \frac{1}{n} \times R^{2/3} \times S^{1/2}
\end{equation}

Donde $R$ es el radio hidráulico del canal.

\textbf{Rango de aplicación:}
\begin{itemize}
    \item Cuencas mixtas con diferentes tipos de flujo
    \item Requiere caracterización detallada del trayecto del agua
    \item Especialmente útil cuando hay tramos diferenciados (rural-urbano)
\end{itemize}

"""


def _get_tc_references(methods: list[str]) -> str:
    """Genera sección de referencias bibliográficas."""
    refs = r"""
\subsubsection{Referencias Bibliográficas}

\begin{itemize}
"""
    if "kirpich" in methods:
        refs += r"    \item Kirpich, Z.P. (1940). ``Time of Concentration of Small Agricultural Watersheds''. Civil Engineering, Vol. 10, No. 6." + "\n"

    if "temez" in methods:
        refs += r"    \item Témez, J.R. (1978). ``Cálculo Hidrometeorológico de Caudales Máximos en Pequeñas Cuencas Naturales''. MOPU, España." + "\n"

    if "desbordes" in methods:
        refs += r"    \item DINAGUA. ``Manual de Diseño para Sistemas de Drenaje de Aguas Pluviales Urbanas''. MVOTMA, Uruguay." + "\n"

    if "nrcs" in methods:
        refs += r"    \item NRCS (1986). ``Urban Hydrology for Small Watersheds''. Technical Release 55 (TR-55)." + "\n"

    refs += r"""\end{itemize}

"""
    return refs
