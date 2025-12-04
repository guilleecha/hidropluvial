"""Módulos de cálculo hidrológico."""

from hidropluvial.core.idf import (
    # Uruguay/DINAGUA - Método principal
    dinagua_intensity,
    dinagua_intensity_simple,
    dinagua_depth,
    dinagua_ct,
    dinagua_ca,
    generate_dinagua_idf_table,
    get_p3_10,
    P3_10_URUGUAY,
    UruguayIDFResult,
    # Métodos internacionales
    sherman_intensity,
    bernard_intensity,
    koutsoyiannis_intensity,
    depth_from_intensity,
    intensity_from_depth,
    generate_idf_table,
    get_intensity,
    get_depth,
)

from hidropluvial.core.temporal import (
    alternating_blocks,
    alternating_blocks_dinagua,
    chicago_storm,
    scs_distribution,
    huff_distribution,
    bimodal_storm,
    bimodal_chicago,
    generate_hyetograph,
    generate_hyetograph_dinagua,
)

from hidropluvial.core.tc import (
    kirpich,
    nrcs_velocity_method,
    temez,
    california_culverts,
    faa_formula,
    kinematic_wave,
    desbordes,
    calculate_tc,
)

from hidropluvial.core.runoff import (
    scs_runoff,
    scs_potential_retention,
    scs_initial_abstraction,
    adjust_cn_for_amc,
    composite_cn,
    calculate_scs_runoff,
    rainfall_excess_series,
    rational_peak_flow,
    composite_c,
)

from hidropluvial.core.hydrograph import (
    scs_lag_time,
    scs_time_to_peak,
    scs_triangular_uh,
    scs_curvilinear_uh,
    triangular_uh_x,
    snyder_uh,
    clark_uh,
    convolve_uh,
    generate_unit_hydrograph,
    generate_hydrograph,
)

__all__ = [
    # IDF - Uruguay/DINAGUA (método principal)
    "dinagua_intensity",
    "dinagua_intensity_simple",
    "dinagua_depth",
    "dinagua_ct",
    "dinagua_ca",
    "generate_dinagua_idf_table",
    "get_p3_10",
    "P3_10_URUGUAY",
    "UruguayIDFResult",
    # IDF - Métodos internacionales
    "sherman_intensity",
    "bernard_intensity",
    "koutsoyiannis_intensity",
    "depth_from_intensity",
    "intensity_from_depth",
    "generate_idf_table",
    "get_intensity",
    "get_depth",
    # Temporal
    "alternating_blocks",
    "alternating_blocks_dinagua",
    "chicago_storm",
    "scs_distribution",
    "huff_distribution",
    "bimodal_storm",
    "bimodal_chicago",
    "generate_hyetograph",
    "generate_hyetograph_dinagua",
    # Time of concentration
    "kirpich",
    "nrcs_velocity_method",
    "temez",
    "california_culverts",
    "faa_formula",
    "kinematic_wave",
    "desbordes",
    "calculate_tc",
    # Runoff
    "scs_runoff",
    "scs_potential_retention",
    "scs_initial_abstraction",
    "adjust_cn_for_amc",
    "composite_cn",
    "calculate_scs_runoff",
    "rainfall_excess_series",
    "rational_peak_flow",
    "composite_c",
    # Hydrograph
    "scs_lag_time",
    "scs_time_to_peak",
    "scs_triangular_uh",
    "scs_curvilinear_uh",
    "triangular_uh_x",
    "snyder_uh",
    "clark_uh",
    "convolve_uh",
    "generate_unit_hydrograph",
    "generate_hydrograph",
]
