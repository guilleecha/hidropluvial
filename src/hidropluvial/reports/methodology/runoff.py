"""
Textos metodológicos para métodos de escorrentía.
"""

from typing import Optional


def get_runoff_methodology_latex(
    methods_used: Optional[list[str]] = None,
    include_cn_tables: bool = False,
) -> str:
    """
    Genera texto LaTeX explicativo sobre métodos de escorrentía.

    Args:
        methods_used: Lista de métodos utilizados (scs-cn, racional).
                     Si es None, incluye todos los métodos.
        include_cn_tables: Si True, incluye tablas de CN por tipo de suelo.

    Returns:
        Contenido LaTeX con marco teórico y formulaciones.
    """
    content = r"""
\subsection{Marco Teórico: Precipitación Efectiva y Escorrentía}

La precipitación efectiva ($P_e$) es la porción de la precipitación total que
se convierte en escorrentía superficial directa. La diferencia entre la precipitación
total y la efectiva corresponde a las pérdidas por:

\begin{itemize}
    \item Intercepción por vegetación
    \item Almacenamiento en depresiones
    \item Infiltración en el suelo
    \item Evapotranspiración (menor importancia en eventos cortos)
\end{itemize}

Los dos métodos más utilizados para estimar la precipitación efectiva son el
\textbf{Método Racional} (coeficiente C) y el \textbf{Método SCS Curve Number} (CN).

"""

    # Determinar qué métodos incluir
    all_methods = ["scs-cn", "racional"]
    if methods_used:
        methods_to_include = [m.lower() for m in methods_used]
    else:
        methods_to_include = all_methods

    # Agregar secciones por método
    if "racional" in methods_to_include or "c" in methods_to_include:
        content += _get_racional_section()

    if "scs-cn" in methods_to_include or "cn" in methods_to_include:
        content += _get_scs_cn_section(include_cn_tables)

    # Comparación si ambos métodos están presentes
    if len(methods_to_include) >= 2:
        content += _get_comparison_section()

    # Referencias
    content += _get_runoff_references(methods_to_include)

    return content


def _get_racional_section() -> str:
    """Sección del método Racional."""
    return r"""
\subsubsection{Método Racional}

El método racional es una fórmula empírica desarrollada a mediados del siglo XIX,
ampliamente utilizada para estimar caudales pico en cuencas pequeñas.

\textbf{Formulación del caudal pico:}
\begin{equation}
Q_p = 0.278 \times C \times i \times A
\label{eq:racional}
\end{equation}

Donde:
\begin{itemize}
    \item $Q_p$ = Caudal pico (m$^3$/s)
    \item $C$ = Coeficiente de escorrentía (adimensional, 0-1)
    \item $i$ = Intensidad de lluvia (mm/hr) para duración igual a $T_c$
    \item $A$ = Área de la cuenca (km$^2$)
\end{itemize}

\textbf{Precipitación efectiva:}
\begin{equation}
P_e = C \times P
\label{eq:pe_racional}
\end{equation}

El coeficiente $C$ representa la fracción de la lluvia que se convierte en escorrentía.
Sus valores dependen de:
\begin{itemize}
    \item Tipo de superficie (impermeable, permeable)
    \item Uso del suelo (urbano, agrícola, forestal)
    \item Pendiente del terreno
    \item Período de retorno (para eventos extremos)
\end{itemize}

\textbf{Valores típicos del coeficiente C:}

\begin{table}[H]
\centering
\small
\begin{tabular}{lcc}
\toprule
Uso de Suelo & $C_{min}$ & $C_{max}$ \\
\midrule
Comercial centro ciudad & 0.70 & 0.95 \\
Comercial barrio & 0.50 & 0.70 \\
Residencial unifamiliar & 0.30 & 0.50 \\
Residencial multifamiliar & 0.40 & 0.60 \\
Industrial liviano & 0.50 & 0.80 \\
Industrial pesado & 0.60 & 0.90 \\
Parques y jardines & 0.10 & 0.25 \\
Asfalto/concreto & 0.70 & 0.95 \\
Techos & 0.75 & 0.95 \\
Césped arenoso plano & 0.05 & 0.10 \\
Césped arcilloso plano & 0.13 & 0.17 \\
\bottomrule
\end{tabular}
\caption{Coeficientes de escorrentía típicos (HEC-22)}
\label{tab:coef_c}
\end{table}

\textbf{Hipótesis del método:}
\begin{enumerate}
    \item La intensidad de lluvia es uniforme sobre toda la cuenca
    \item La intensidad es constante durante la duración de la tormenta
    \item El caudal pico ocurre cuando toda la cuenca contribuye (duración = $T_c$)
    \item El coeficiente $C$ es constante durante el evento
\end{enumerate}

\textbf{Rango de aplicación:}
\begin{itemize}
    \item Cuencas pequeñas: $A < 80$ ha (preferentemente $< 25$ ha)
    \item Cuencas urbanas y semiurbanas
    \item Diseño preliminar de obras de drenaje
\end{itemize}

"""


def _get_scs_cn_section(include_tables: bool = False) -> str:
    """Sección del método SCS Curve Number."""
    content = r"""
\subsubsection{Método SCS Curve Number (CN)}

El método del Número de Curva fue desarrollado por el Soil Conservation Service
(ahora NRCS) de Estados Unidos. Es el método más utilizado mundialmente para
estimar volúmenes de escorrentía.

\textbf{Retención potencial máxima:}
\begin{equation}
S = \frac{25400}{CN} - 254 \quad \text{[mm]}
\label{eq:retention}
\end{equation}

\textbf{Abstracción inicial:}
\begin{equation}
I_a = \lambda \times S
\label{eq:ia}
\end{equation}

Donde $\lambda$ es típicamente:
\begin{itemize}
    \item $\lambda = 0.20$ (valor tradicional SCS)
    \item $\lambda = 0.05$ (valor recomendado por Hawkins et al., 2002)
\end{itemize}

\textbf{Precipitación efectiva (escorrentía directa):}
\begin{equation}
P_e = \begin{cases}
\dfrac{(P - I_a)^2}{P - I_a + S} & \text{si } P > I_a \\[2ex]
0 & \text{si } P \leq I_a
\end{cases}
\label{eq:pe_scs}
\end{equation}

Donde:
\begin{itemize}
    \item $P_e$ = Precipitación efectiva o escorrentía directa (mm)
    \item $P$ = Precipitación total (mm)
    \item $I_a$ = Abstracción inicial (mm)
    \item $S$ = Retención potencial máxima (mm)
\end{itemize}

\textbf{Número de Curva (CN):}

El CN varía entre 30 y 100:
\begin{itemize}
    \item CN = 100: Superficie totalmente impermeable (toda la lluvia escurre)
    \item CN = 30: Superficie muy permeable con alta infiltración
\end{itemize}

El CN depende de:
\begin{enumerate}
    \item \textbf{Grupo hidrológico del suelo} (A, B, C, D)
    \item \textbf{Uso y cobertura del suelo}
    \item \textbf{Condición hidrológica} (buena, regular, mala)
    \item \textbf{Condición antecedente de humedad} (AMC I, II, III)
\end{enumerate}

\textbf{Grupos hidrológicos de suelo:}

\begin{table}[H]
\centering
\small
\begin{tabular}{clc}
\toprule
Grupo & Descripción & Tasa infiltración \\
\midrule
A & Arena profunda, loess, limos agregados & Alta ($> 7.6$ mm/h) \\
B & Limo arenoso, franco arenoso & Moderada (3.8-7.6 mm/h) \\
C & Franco arcilloso, franco limoso & Baja (1.3-3.8 mm/h) \\
D & Arcillas, suelos con nivel freático alto & Muy baja ($< 1.3$ mm/h) \\
\bottomrule
\end{tabular}
\caption{Grupos hidrológicos de suelo (NRCS)}
\label{tab:soil_groups}
\end{table}

\textbf{Ajuste por Condición Antecedente de Humedad (AMC):}

La condición de humedad del suelo antes del evento afecta significativamente
la escorrentía. El CN se ajusta según:

\begin{itemize}
    \item \textbf{AMC I} (seco): Suelos secos, mínima humedad
    \begin{equation}
    CN_I = \frac{CN_{II}}{2.281 - 0.01281 \times CN_{II}}
    \end{equation}

    \item \textbf{AMC II} (normal): Condición promedio (valor de tablas)

    \item \textbf{AMC III} (húmedo): Suelos saturados o lluvias previas
    \begin{equation}
    CN_{III} = \frac{CN_{II}}{0.427 + 0.00573 \times CN_{II}}
    \end{equation}
\end{itemize}

\textbf{Rango de aplicación:}
\begin{itemize}
    \item Cuencas de cualquier tamaño
    \item Eventos de lluvia con $P > I_a$
    \item Especialmente útil para cuencas rurales y mixtas
    \item Requiere caracterización del suelo y cobertura
\end{itemize}

"""

    if include_tables:
        content += _get_cn_tables()

    return content


def _get_cn_tables() -> str:
    """Tablas de CN por uso de suelo."""
    return r"""
\textbf{Valores de CN para áreas urbanas:}

\begin{table}[H]
\centering
\footnotesize
\begin{tabular}{lcccc}
\toprule
Descripción de cobertura & \multicolumn{4}{c}{CN por grupo de suelo} \\
 & A & B & C & D \\
\midrule
\textit{Áreas urbanas desarrolladas:} & & & & \\
Espacios abiertos (césped, parques): & & & & \\
\quad Condición pobre ($<$ 50\% cobertura) & 68 & 79 & 86 & 89 \\
\quad Condición regular (50-75\% cobertura) & 49 & 69 & 79 & 84 \\
\quad Condición buena ($>$ 75\% cobertura) & 39 & 61 & 74 & 80 \\
Áreas impermeables: & & & & \\
\quad Pavimento, techos, etc. & 98 & 98 & 98 & 98 \\
Calles y carreteras: & & & & \\
\quad Pavimentadas con cunetas & 98 & 98 & 98 & 98 \\
\quad Grava & 76 & 85 & 89 & 91 \\
\quad Tierra & 72 & 82 & 87 & 89 \\
\midrule
\textit{Distritos urbanos:} & & & & \\
Comercial y negocios (85\% imp.) & 89 & 92 & 94 & 95 \\
Industrial (72\% imp.) & 81 & 88 & 91 & 93 \\
\midrule
\textit{Residencial:} & & & & \\
1/8 acre o menos (65\% imp.) & 77 & 85 & 90 & 92 \\
1/4 acre (38\% imp.) & 61 & 75 & 83 & 87 \\
1/3 acre (30\% imp.) & 57 & 72 & 81 & 86 \\
1/2 acre (25\% imp.) & 54 & 70 & 80 & 85 \\
1 acre (20\% imp.) & 51 & 68 & 79 & 84 \\
\bottomrule
\end{tabular}
\caption{Números de curva para áreas urbanas (TR-55)}
\label{tab:cn_urbano}
\end{table}

"""


def _get_comparison_section() -> str:
    """Sección de comparación entre métodos."""
    return r"""
\subsubsection{Comparación de Métodos}

\begin{table}[H]
\centering
\small
\begin{tabular}{p{3cm}p{5.5cm}p{5.5cm}}
\toprule
Aspecto & Método Racional (C) & Método SCS-CN \\
\midrule
Relación P-Pe & Lineal ($P_e = C \times P$) & No lineal (considera abstracciones) \\
Parámetro principal & Coeficiente C (0-1) & Número de Curva CN (30-100) \\
Abstracción inicial & Implícita en C & Explícita ($I_a = \lambda S$) \\
Resultado directo & Caudal pico $Q_p$ & Volumen de escorrentía $P_e$ \\
Distribución temporal & No considera & Permite distribución temporal \\
Tamaño de cuenca & $<$ 80 ha & Cualquier tamaño \\
Complejidad & Baja & Media \\
Datos requeridos & C, i, A & CN, P (serie temporal) \\
\bottomrule
\end{tabular}
\caption{Comparación entre métodos de escorrentía}
\label{tab:comp_metodos}
\end{table}

\textbf{Criterios de selección:}
\begin{itemize}
    \item \textbf{Método Racional}: Preferir para cuencas pequeñas urbanas ($<$ 25 ha),
          diseño preliminar, cuando solo se requiere el caudal pico.
    \item \textbf{Método SCS-CN}: Preferir cuando se requiere el volumen de escorrentía,
          para cuencas rurales o mixtas, cuando se necesita generar hidrogramas,
          o para análisis más detallados.
\end{itemize}

"""


def _get_runoff_references(methods: list[str]) -> str:
    """Genera sección de referencias bibliográficas."""
    refs = r"""
\subsubsection{Referencias Bibliográficas}

\begin{itemize}
"""
    if "racional" in methods or "c" in methods:
        refs += r"    \item Chow, V.T., Maidment, D.R., Mays, L.W. (1988). ``Applied Hydrology''. McGraw-Hill." + "\n"
        refs += r"    \item HEC-22 (2013). ``Urban Drainage Design Manual''. FHWA." + "\n"

    if "scs-cn" in methods or "cn" in methods:
        refs += r"    \item NRCS (1986). ``Urban Hydrology for Small Watersheds''. Technical Release 55 (TR-55)." + "\n"
        refs += r"    \item Hawkins, R.H. et al. (2002). ``Curve Number Hydrology: State of the Practice''. ASCE." + "\n"

    refs += r"    \item HHA-FING UdelaR (2019). ``Hidrología e Hidráulica Aplicadas''. Facultad de Ingeniería, Uruguay." + "\n"

    refs += r"""\end{itemize}

"""
    return refs
