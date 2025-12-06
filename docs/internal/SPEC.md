# SPEC.md — Python Hydrological Calculation Tool with LaTeX Report Generation

**Version 1.0** | December 2025

---

## Executive Summary

This specification defines a Python-based hydrological calculation toolkit (`hydro-calc`) that implements industry-standard methodologies from FHWA, NRCS, and recognized academic sources. The tool generates professional LaTeX reports with publication-quality figures and tables. Key capabilities include IDF curve analysis, design storm hyetograph generation, time of concentration calculation, runoff estimation via Rational and SCS Curve Number methods, and synthetic unit hydrograph development.

---

## 1. System Architecture

### 1.1 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| CLI Framework | **Typer** | Type hints integration, minimal boilerplate, automatic help generation |
| Configuration | **TOML + Pydantic v2** | Python 3.11+ stdlib support, validation, type safety |
| Numerical | **NumPy**, **SciPy** | Industry-standard scientific computing |
| Data | **Pandas** | DataFrame operations, LaTeX table export |
| Plotting | **Matplotlib (PGF backend)** | Native LaTeX font integration, vector graphics |
| Report Generation | **Jinja2** | Flexible LaTeX templating with custom delimiters |
| Testing | **pytest + Hypothesis** | Property-based testing for engineering calculations |

### 1.2 Project Structure (src Layout)

```
hydro-calc/
├── pyproject.toml
├── README.md
├── SPEC.md
├── src/
│   └── hydro_calc/
│       ├── __init__.py
│       ├── cli.py                    # Typer CLI entry point
│       ├── config.py                 # Pydantic settings/models
│       ├── core/
│       │   ├── __init__.py
│       │   ├── idf.py                # IDF curve methods
│       │   ├── temporal.py           # Rainfall distributions
│       │   ├── tc.py                 # Time of concentration
│       │   ├── runoff.py             # Rational, CN methods
│       │   └── hydrograph.py         # Unit hydrograph methods
│       ├── reports/
│       │   ├── __init__.py
│       │   ├── generator.py          # LaTeX report generator
│       │   ├── plotting.py           # Matplotlib PGF figures
│       │   └── templates/
│       │       ├── report_base.tex
│       │       ├── hyetograph.tex
│       │       └── hydrograph.tex
│       └── data/
│           ├── scs_distributions.json
│           ├── huff_curves.json
│           └── cn_tables.json
├── tests/
│   ├── conftest.py
│   ├── test_idf.py
│   ├── test_temporal.py
│   ├── test_hydrograph.py
│   └── data/validation_cases.json
└── docs/
```

---

## 2. IDF Curves Module (`core/idf.py`)

### 2.1 Supported Equation Forms

#### 2.1.1 Sherman Equation (1931)
```
i = a / (t + b)^n
```
**With return period:**
```
i = (k × T^m) / (t + c)^n
```
Where:
- `i` = rainfall intensity (mm/hr)
- `t` = duration (minutes)
- `T` = return period (years)
- `k, m, c, n` = regional coefficients

**Parameter ranges:** c: 0–30 min, n: 0.5–1.0, m: 0.1–0.5

#### 2.1.2 Bernard Equation (Power Law)
```
i = a × T^m / t^n
```
Typical values: n: 0.5–0.9, m: 0.15–0.35

#### 2.1.3 Koutsoyiannis Method (1998)
Theoretically rigorous formulation with Gumbel distribution:
```
I(T,d) = a(T) / (d + θ)^η
```
Where:
```
a(T) = μ + σ × {0.5772 + ln[ln(T/(T-1))]}
μ = mean - 0.5772 × σ
σ = (√6/π) × std_dev ≈ 0.7797 × std_dev
```

#### 2.1.4 Chen's Method (1983)
Uses three base rainfall depths (P₁¹⁰, P₂₄¹⁰, P₁¹⁰⁰):
```
R = P₁¹⁰ / P₂₄¹⁰  (hour-to-day ratio)
S = P₁¹⁰⁰ / P₁¹⁰  (frequency ratio)
f(T) = [ln(T/(T-1)) + 0.5772] / [ln(10/9) + 0.5772]
```

### 2.2 Uruguay/DINAGUA Methods

**Rodríguez Fontal (1980):** National IDF curves for 8 subregions
```
Pₜ(Tr,r) = εₜ + Kₜ × ln(Tr)
```
Based on Gumbel distribution parameters (εₜ, Kₜ) by region and duration.

**Silveira et al. (2014) - Montevideo Updated:**
Koutsoyiannis methodology applied to 1906-2005 data for durations 1-24 hours.

### 2.3 NOAA Atlas 14 Integration

- **Data Source:** PFDS (https://hdsc.nws.noaa.gov/pfds/)
- **Output format:** Point precipitation frequency estimates with 90% confidence intervals
- **Durations:** 5, 10, 15, 30, 60 min; 2, 3, 6, 12, 24 hr; 2-60 days
- **Return periods:** 1, 2, 5, 10, 25, 50, 100, 200, 500, 1000 years
- **Implementation:** Parse CSV/XML output from PFDS for local calibration

### 2.4 L-Moments Regionalization

**L-Moment Definitions:**
```
λ₁ = β₀ (mean)
λ₂ = 2β₁ - β₀
λ₃ = 6β₂ - 6β₁ + β₀
λ₄ = 20β₃ - 30β₂ + 12β₁ - β₀
```

**L-Moment Ratios:**
```
τ = λ₂/λ₁ (L-CV)
τ₃ = λ₃/λ₂ (L-Skewness)
τ₄ = λ₄/λ₂ (L-Kurtosis)
```

**Heterogeneity Measure H:**
- H < 1: Acceptably homogeneous
- 1 ≤ H < 2: Possibly heterogeneous
- H ≥ 2: Definitely heterogeneous

**Distribution Selection:** GEV, GPA, GLO, LN3, PE3 via L-moment ratio diagram (τ₃ vs τ₄)

---

## 3. Temporal Rainfall Distributions (`core/temporal.py`)

### 3.1 Alternating Block Method

**Algorithm:**
1. Calculate cumulative depths from IDF: `P(d) = i(d) × d`
2. Compute incremental depths: `ΔPₙ = P(n×Δt) - P((n-1)×Δt)`
3. Sort increments descending
4. Place alternating around peak position (center default)

**Peak positioning options:** center, front-loaded, custom fraction (0-1)

### 3.2 Chicago Design Storm (Keifer & Chu 1957)

**Base IDF:** `i_avg = a / (t + b)^c`

**Before peak** (t_b measured backward):
```
i_b = a[(1-c)×(t_b/r) + b] / [(t_b/r) + b]^(c+1)
```

**After peak** (t_a measured forward):
```
i_a = a[(1-c)×(t_a/(1-r)) + b] / [(t_a/(1-r)) + b]^(c+1)
```

**Advancement coefficient r:** typical 0.3-0.5 (commonly r = 0.375)

### 3.3 NRCS/SCS 24-Hour Distributions

| Type | Geographic Application | Peak Position |
|------|------------------------|---------------|
| I | Pacific Coast, Alaska, Hawaii | ~10 hr |
| IA | Pacific Northwest coastal | ~8 hr |
| II | Most continental US | ~12 hr (50%) |
| III | Gulf/Atlantic coastal | ~12 hr |

**Type II Dimensionless Ratios (P/P₂₄ vs t/24):**
```json
{
  "time_hr": [0, 1, 2, 3, 4, 5, 6, 7, 7.5, 8, 8.5, 9, 9.5, 9.75, 10, 10.5, 11, 11.5, 11.75, 12, 12.5, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
  "ratio": [0.000, 0.011, 0.022, 0.035, 0.048, 0.063, 0.080, 0.099, 0.109, 0.120, 0.133, 0.147, 0.163, 0.172, 0.181, 0.204, 0.235, 0.283, 0.357, 0.663, 0.772, 0.820, 0.880, 0.910, 0.934, 0.953, 0.967, 0.978, 0.986, 0.992, 0.996, 0.998, 1.000]
}
```

### 3.4 Huff Curves (1967)

**Classification by quartile of heaviest rainfall:**
- **Q1:** 37% of storms, typically ≤6 hr duration
- **Q2:** 27% of storms, 6-12 hr duration
- **Q3:** 21% of storms, 12-24 hr duration
- **Q4:** 15% of storms, >24 hr duration

**Probability levels:** 10% (intense), 50% (median), 90% (uniform)

**Median Q2 Distribution (50% probability):**
```json
{
  "time_pct": [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100],
  "rain_pct": [0, 3, 8, 12, 16, 22, 29, 39, 51, 62, 70, 76, 81, 85, 88, 91, 93, 95, 97, 98, 100]
}
```

### 3.5 Bimodal/Double-Peak Storms

**Applications:** Urban catchments with mixed imperviousness, coastal tropical regions, long-duration frontal storms.

**Implementation:** Superposition of two Chicago storms or parametric double-triangular peaks with configurable timing and volume split.

---

## 4. Time of Concentration Methods (`core/tc.py`)

### 4.1 Kirpich Formula (1940)

```
tc = 0.0078 × L^0.77 × S^(-0.385)   [tc: min, L: ft, S: ft/ft]
tc = 0.0195 × L^0.77 × S^(-0.385)   [tc: min, L: m]
```

**Adjustment factors:**
- Grassy channels: ×2.0
- Concrete/asphalt: ×0.4
- Concrete channels: ×0.2

### 4.2 NRCS Velocity Method (TR-55)

**Total:** `tc = Tt_sheet + Tt_shallow + Tt_channel`

**Sheet Flow:**
```
Tt = 0.007 × (n × L)^0.8 / (P₂^0.5 × S^0.4)   [Tt: hr, L: ft, P₂: in]
```
Maximum L = 100-300 ft

**Manning's n for Sheet Flow:**
| Surface | n |
|---------|---|
| Smooth surfaces | 0.011 |
| Fallow (no residue) | 0.05 |
| Short grass prairie | 0.15 |
| Dense grass | 0.24 |
| Woods (light underbrush) | 0.40 |
| Woods (dense underbrush) | 0.80 |

**Shallow Concentrated Flow:**
```
V = k × S^0.5   [V: ft/s, S: ft/ft]
```
| Surface | k |
|---------|---|
| Paved | 20.3 |
| Unpaved | 16.1 |
| Grassed waterway | 15.0 |
| Short grass pasture | 7.0 |

**Channel Flow (Manning):**
```
V = (1.49/n) × R^(2/3) × S^(1/2)   [English]
```

### 4.3 Témez Formula (Spain/Latin America)

```
tc = 0.3 × (L / S^0.25)^0.76   [tc: hr, L: km, S: m/m]
```
Valid for basins 1-3000 km²

### 4.4 California Culverts Practice

```
tc = 60 × (11.9 × L³ / H)^0.385   [tc: min, L: mi, H: ft]
```

### 4.5 FAA Formula

```
tc = 1.8 × (1.1 - C) × L^0.5 / S^0.333   [tc: min, L: ft, S: %]
```

### 4.6 Kinematic Wave (Iterative)

```
tc = 0.94 × (L × n)^0.6 / (i^0.4 × S^0.3)   [tc: min, L: ft, i: in/hr]
```

---

## 5. Runoff Methods (`core/runoff.py`)

### 5.1 Rational Method

**Peak Discharge:**
```
Q = Cf × C × i × A   [Q: cfs, i: in/hr, A: acres]
Q = 0.00278 × C × i × A   [Q: m³/s, i: mm/hr, A: ha]
```

**Return Period Adjustment Factors (Cf):**
| Return Period | Cf |
|--------------|-----|
| < 25 years | 1.00 |
| 25 years | 1.10 |
| 50 years | 1.20 |
| 100 years | 1.25 |

**Note:** Cf × C ≤ 1.0

**Runoff Coefficients by Land Use (HEC-22):**
| Land Use | C Range |
|----------|---------|
| Downtown commercial | 0.70-0.95 |
| Residential single-family | 0.30-0.50 |
| Industrial light | 0.50-0.80 |
| Asphalt/concrete | 0.70-0.95 |
| Parks/open space | 0.10-0.25 |

**Composite C:**
```
C_composite = Σ(Cᵢ × Aᵢ) / Σ(Aᵢ)
```

### 5.2 SCS Curve Number Method

**Runoff Equation:**
```
Q = (P - Ia)² / (P - Ia + S)   for P > Ia
Q = 0                          for P ≤ Ia
```

**Potential Maximum Retention:**
```
S = (1000/CN) - 10   [inches]
S = (25400/CN) - 254 [mm]
```

**Initial Abstraction:**
```
Ia = λ × S
λ = 0.20 (traditional)
λ = 0.05 (Hawkins et al. 2002 update)
```

**Curve Number Tables (TR-55 Table 2-2):**

| Cover Description | HSG A | HSG B | HSG C | HSG D |
|-------------------|-------|-------|-------|-------|
| **Open Space (good)** | 39 | 61 | 74 | 80 |
| **Impervious areas** | 98 | 98 | 98 | 98 |
| **Residential 1/4 acre** | 61 | 75 | 83 | 87 |
| **Commercial (85% imp)** | 89 | 92 | 94 | 95 |
| **Pasture (good)** | 39 | 61 | 74 | 80 |
| **Woods (good)** | 30 | 55 | 70 | 77 |

**Antecedent Moisture Condition Adjustments:**

```
CN_I = CN_II / (2.281 - 0.01281 × CN_II)    [AMC II → I]
CN_III = CN_II / (0.427 + 0.00573 × CN_II)  [AMC II → III]
```

**5-Day Antecedent Precipitation Thresholds:**
| AMC | Dormant | Growing |
|-----|---------|---------|
| I (Dry) | < 0.5 in | < 1.4 in |
| II (Avg) | 0.5-1.1 in | 1.4-2.1 in |
| III (Wet) | > 1.1 in | > 2.1 in |

---

## 6. Unit Hydrograph Methods (`core/hydrograph.py`)

### 6.1 SCS Triangular Unit Hydrograph

**Peak Discharge:**
```
qp = 484 × A × Q / Tp   [qp: cfs, A: mi², Q: in, Tp: hr]
qp = 2.08 × A × Q / Tp  [qp: m³/s, A: km², Q: mm, Tp: hr]
```

**Temporal Parameters:**
```
tlag = 0.6 × Tc
Tp = ΔD/2 + tlag
Tr = 1.67 × Tp
Tb = 2.67 × Tp
```

**Unit Duration:** `ΔD ≤ 0.25 × Tp` (recommended: ΔD = 0.133 × Tc)

### 6.2 NRCS Curvilinear (Dimensionless) Unit Hydrograph

**Standard DUH Coordinates (PRF=484):**
```json
{
  "t_Tp": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0, 4.5, 5.0],
  "q_qp": [0.000, 0.030, 0.100, 0.190, 0.310, 0.470, 0.660, 0.820, 0.930, 0.990, 1.000, 0.990, 0.930, 0.860, 0.780, 0.680, 0.560, 0.460, 0.390, 0.330, 0.280, 0.207, 0.147, 0.107, 0.077, 0.055, 0.040, 0.029, 0.021, 0.015, 0.011, 0.005, 0.000]
}
```

**Gamma Equation for Variable PRF:**
```
q/qp = e^m × (t/Tp)^m × e^(-m × t/Tp)
```

| m | PRF |
|---|-----|
| 1.0 | 238 |
| 3.0 | 433 |
| 3.7 | 484 |
| 5.0 | 566 |

### 6.3 Snyder Synthetic Unit Hydrograph (1938)

**Lag Time:**
```
tp = Ct × (L × Lc)^0.3   [tp: hr, L/Lc: mi]
```

**Peak Discharge:**
```
Qp = 640 × Cp × A / tp   [Qp: cfs, A: mi²]
```

**Coefficients:**
| Terrain | Ct | Cp |
|---------|----|----|
| Mountainous | 0.4-1.0 | 0.6-0.8 |
| Standard (Appalachian) | 1.8-2.2 | 0.4-0.8 |
| Flat/Gulf regions | 3.0-8.0 | 0.3-0.4 |

**Width Equations (USACE):**
```
W50 = 770 × (Qp/A)^(-1.08)   [hr]
W75 = 440 × (Qp/A)^(-1.08)   [hr]
```
Distribution: 1/3 before peak, 2/3 after peak

**Non-Standard Duration Adjustment:**
```
tr_std = tp / 5.5
tp_adj = tp + 0.25 × (tR - tr_std)
```

### 6.4 Clark Unit Hydrograph

**Key Parameters:**
- Tc: Time of concentration (translation)
- R: Storage coefficient (attenuation)

**Default Time-Area Relationship:**
```
A(t) = 1.414 × (t/Tc)^1.5           for t/Tc ≤ 0.5
A(t) = 1 - 1.414 × (1 - t/Tc)^1.5   for t/Tc > 0.5
```

**Linear Reservoir Routing Coefficients:**
```
C₀ = Δt / (2R + Δt)
C₁ = Δt / (2R + Δt)
C₂ = (2R - Δt) / (2R + Δt)
```

**Kc Ratio (R/Tc) Guidelines:**
| Watershed Type | R/Tc |
|----------------|------|
| Developed urban | 1.1-2.1 |
| Rural | 1.5-2.8 |
| Forested | 8-12 |

### 6.5 Convolution Algorithm

**Discrete Convolution:**
```
Qn = Σ(m=1 to M) [Pm × U(n-m+1)]   for m ≤ n
```

**Python Implementation:**
```python
import numpy as np

def convolve_uh(rainfall_excess: np.ndarray, unit_hydrograph: np.ndarray) -> np.ndarray:
    """Discrete convolution of rainfall excess with unit hydrograph."""
    return np.convolve(rainfall_excess, unit_hydrograph, mode='full')
```

---

## 7. LaTeX Report Generation (`reports/`)

### 7.1 Jinja2 Configuration for LaTeX

**Custom Delimiters (avoid LaTeX conflicts):**
```python
env = jinja2.Environment(
    block_start_string=r'\BLOCK{',
    block_end_string='}',
    variable_start_string=r'\VAR{',
    variable_end_string='}',
    comment_start_string=r'\#{',
    comment_end_string='}',
    line_statement_prefix='%%',
    trim_blocks=True,
    autoescape=False,
    loader=jinja2.FileSystemLoader(template_dir)
)
```

**LaTeX Character Escaping:**
```python
LATEX_SPECIAL = {'&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', 
                  '_': r'\_', '{': r'\{', '}': r'\}'}
```

### 7.2 Report Template Structure

```latex
\documentclass[11pt]{article}
\usepackage{booktabs, siunitx, graphicx, pgf, amsmath}
\usepackage[margin=1in]{geometry}

\title{\VAR{project_name | escape_latex}}
\author{Generated by hydro-calc v\VAR{version}}
\date{\VAR{date}}

\begin{document}
\maketitle

\section{Project Summary}
\input{tables/catchment_summary.tex}

\section{Design Storm}
\subsection{IDF Analysis}
\input{figures/idf_curves.pgf}

\subsection{Hyetograph}
\input{figures/hyetograph.pgf}
\input{tables/hyetograph_data.tex}

\section{Hydrograph Analysis}
\BLOCK{for catchment in catchments}
\subsection{\VAR{catchment.name | escape_latex}}
\input{figures/\VAR{catchment.id}_hydrograph.pgf}
\BLOCK{endfor}

\section{Results Summary}
\input{tables/results_summary.tex}

\end{document}
```

### 7.3 Matplotlib PGF Configuration

```python
import matplotlib as mpl
mpl.use('pgf')
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "text.usetex": True,
    "pgf.rcfonts": False,
    "pgf.texsystem": "pdflatex",
    "pgf.preamble": r"\usepackage{siunitx}"
})

def set_figure_size(width_pt=345, fraction=1.0):
    """Calculate figure dimensions matching LaTeX document width."""
    inches_per_pt = 1 / 72.27
    golden_ratio = (5**0.5 - 1) / 2
    width = width_pt * fraction * inches_per_pt
    height = width * golden_ratio
    return (width, height)
```

### 7.4 Pandas to LaTeX Tables

```python
def df_to_latex(df, caption, label, output_path):
    latex = df.style.format(precision=3).to_latex(
        hrules=True,
        caption=caption,
        label=label,
        position='htbp',
        column_format='l' + 'r' * len(df.columns)
    )
    Path(output_path).write_text(latex)
```

---

## 8. CLI Interface (`cli.py`)

### 8.1 Command Structure

```
hydro-calc
├── idf                    # IDF curve analysis
│   ├── fit               # Fit parameters from data
│   ├── generate          # Generate curves
│   └── export            # Export tables
├── storm                  # Design storm generation
│   ├── chicago           # Chicago method
│   ├── scs               # SCS Type I/IA/II/III
│   ├── huff              # Huff curves
│   └── blocks            # Alternating blocks
├── tc                     # Time of concentration
│   ├── kirpich
│   ├── nrcs
│   ├── temez
│   └── composite
├── runoff                 # Runoff calculation
│   ├── rational
│   └── cn                # SCS Curve Number
├── hydrograph             # Hydrograph generation
│   ├── scs               # SCS triangular/curvilinear
│   ├── snyder
│   └── clark
├── report                 # Report generation
│   └── generate          # Full LaTeX report
└── config                 # Configuration
    ├── init              # Create config file
    └── validate          # Validate config
```

### 8.2 Configuration Schema (TOML)

```toml
[project]
name = "Example Project"
location = "Montevideo, Uruguay"
engineer = "J. Smith"
date = "2025-12-03"

[units]
system = "SI"  # or "US"

[idf]
method = "sherman"  # sherman, bernard, koutsoyiannis
coefficients = {k = 2150.0, m = 0.22, c = 15.0, n = 0.75}

[storm]
method = "scs_type_ii"
duration_hr = 24
return_period_yr = 100
total_depth_mm = 150

[catchment]
name = "Basin A"
area_km2 = 25.5
cn = 75
tc_method = "nrcs"
slope = 0.02

[[catchment.tc_segments]]
type = "sheet"
length_m = 50
n = 0.24
slope = 0.02

[[catchment.tc_segments]]
type = "shallow"
length_m = 300
surface = "unpaved"
slope = 0.015

[[catchment.tc_segments]]
type = "channel"
length_m = 1500
n = 0.035
slope = 0.008
hydraulic_radius_m = 0.5

[hydrograph]
method = "scs_curvilinear"
prf = 484
dt_hr = 0.1

[report]
template = "standard"
output_format = "pdf"  # pdf, tex
include_figures = true
include_tables = true
```

---

## 9. Data Structures (Pydantic Models)

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional
from enum import Enum

class UnitSystem(str, Enum):
    SI = "SI"
    US = "US"

class TCSegmentType(str, Enum):
    SHEET = "sheet"
    SHALLOW = "shallow"
    CHANNEL = "channel"

class HydrographMethod(str, Enum):
    SCS_TRIANGULAR = "scs_triangular"
    SCS_CURVILINEAR = "scs_curvilinear"
    SNYDER = "snyder"
    CLARK = "clark"

class TCSegment(BaseModel):
    type: TCSegmentType
    length_m: float = Field(..., gt=0)
    slope: float = Field(..., gt=0, lt=1)
    n: Optional[float] = Field(None, gt=0)
    surface: Optional[str] = None
    hydraulic_radius_m: Optional[float] = None

class Catchment(BaseModel):
    name: str = Field(..., min_length=1)
    area_km2: float = Field(..., gt=0, le=10000)
    cn: int = Field(..., ge=30, le=100)
    tc_hours: Optional[float] = Field(None, gt=0)
    tc_segments: Optional[list[TCSegment]] = None
    slope: float = Field(..., gt=0, lt=1)
    
    @field_validator('cn')
    @classmethod
    def validate_cn(cls, v):
        if not 30 <= v <= 100:
            raise ValueError("CN must be between 30 and 100")
        return v

class StormEvent(BaseModel):
    method: str
    duration_hr: float = Field(..., gt=0)
    return_period_yr: int = Field(..., ge=1)
    total_depth_mm: float = Field(..., gt=0)

class HydrographResult(BaseModel):
    time: list[float]
    flow: list[float]
    peak_flow: float
    time_to_peak: float
    volume: float
    method: str
```

---

## 10. Testing Strategy

### 10.1 Validation Against Published Examples

| Source | Example | Method | Expected |
|--------|---------|--------|----------|
| TR-55 Example 2-1 | Urban watershed | CN runoff | Q = 3.4 in |
| TR-55 Example 3-1 | Travel time | NRCS Tc | Tc = 1.5 hr |
| HEC-HMS Manual | SCS UH | Peak flow | Match ±5% |
| Chow et al. Ch.7 | Snyder UH | Parameters | Match tables |

### 10.2 Property-Based Testing

```python
from hypothesis import given, strategies as st

@given(
    area=st.floats(0.1, 1000),
    cn=st.integers(30, 100),
    rainfall=st.floats(1, 500)
)
def test_runoff_less_than_rainfall(area, cn, rainfall):
    """Runoff depth must never exceed rainfall."""
    result = scs_runoff(rainfall, cn)
    assert result <= rainfall

@given(cn=st.integers(30, 100))
def test_higher_cn_more_runoff(cn):
    """Higher CN should produce more runoff."""
    rainfall = 100  # mm
    q1 = scs_runoff(rainfall, cn)
    q2 = scs_runoff(rainfall, min(cn + 10, 100))
    assert q2 >= q1
```

---

## 11. Key References

### 11.1 Official Documents

| Document | Edition | Year | Primary Use |
|----------|---------|------|-------------|
| **FHWA HDS-2** "Highway Hydrology" | 3rd | 2023 | Comprehensive highway drainage |
| **FHWA HEC-22** "Urban Drainage Design Manual" | 4th | 2024 | Storm drain design, inlets |
| **NRCS NEH Part 630** "Hydrology" | Amend. 90 | 2020 | CN method, unit hydrographs |
| **TR-55** "Urban Hydrology for Small Watersheds" | 2nd | 1986 | Peak discharge, tabular method |

### 11.2 Textbooks

- **Chow, V.T., Maidment, D.R., Mays, L.W. (1988/2013)** *Applied Hydrology*, McGraw-Hill. ISBN: 978-0071743914

### 11.3 Original Papers

- **Sherman, C.W. (1931)** "Frequency and Intensity of Excessive Rainfall at Boston" *Trans. ASCE*, 95:951-960
- **Keifer, C.J. & Chu, H.H. (1957)** "Synthetic Storm Pattern for Drainage Design" *J. Hydraulics Div. ASCE*, 83(HY4):1-25
- **Huff, F.A. (1967)** "Time Distribution of Rainfall in Heavy Storms" *Water Resources Research*, 3(4):1007-1019
- **Hosking, J.R.M. & Wallis, J.R. (1997)** *Regional Frequency Analysis: An Approach Based on L-moments*, Cambridge University Press
- **Koutsoyiannis, D. et al. (1998)** "A mathematical framework for studying rainfall IDF relationships" *J. Hydrology*, 206:118-135

---

## 12. Output Report Structure

### 12.1 Minimum Required Sections

1. **Cover Page**: Project name, location, date, engineer
2. **Table of Contents**
3. **Executive Summary**: Key results, peak flows, critical durations
4. **Methodology**: Methods used with justification
5. **Input Data**: Catchment parameters, soil data, land use
6. **IDF Analysis**: Curves, equations, source data
7. **Design Storm**: Hyetograph with tabular data
8. **Runoff Analysis**: CN or C values, abstractions
9. **Hydrograph Results**: Time series, peak flows, volumes
10. **Summary Tables**: All catchments, all return periods
11. **Appendices**: Detailed calculations, data sources

### 12.2 Standard Tables

**Catchment Summary Table:**
| Catchment | Area (km²) | CN | Tc (hr) | Slope (%) |
|-----------|------------|----|---------|-----------| 

**Results Summary Table:**
| Catchment | Return Period | Peak Q (m³/s) | Time to Peak (hr) | Volume (m³) |
|-----------|--------------|---------------|-------------------|-------------|

**Hyetograph Data Table:**
| Time (hr) | Intensity (mm/hr) | Cumulative (mm) |
|-----------|-------------------|-----------------|

---

## 13. Implementation Priorities

### Phase 1: Core Calculations
1. IDF module (Sherman, Koutsoyiannis)
2. Temporal distributions (SCS Types, Chicago, Alternating Blocks)
3. Time of concentration (Kirpich, NRCS, Témez)
4. SCS Curve Number runoff
5. SCS Unit Hydrograph (triangular, curvilinear)

### Phase 2: Extended Methods
1. Huff curves
2. Snyder UH
3. Clark UH
4. Rational method with Cf
5. Bimodal storms

### Phase 3: Report Generation
1. Jinja2 LaTeX templates
2. Matplotlib PGF figures
3. Pandas booktabs tables
4. PDF compilation

### Phase 4: CLI and Integration
1. Typer CLI structure
2. TOML configuration
3. Batch processing
4. Validation against published examples

---

*End of Specification Document*