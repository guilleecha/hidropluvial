"""
Tablas de coeficiente de escorrentía C.

Fuentes:
- FHWA HEC-22 (Federal Highway Administration)
- Ven Te Chow - Applied Hydrology (Table 5.5.2)
"""

from .types import ChowCEntry, FHWACEntry


# Tabla FHWA HEC-22 (Urban Drainage Design Manual)
# C base para Tr = 2-10 anos, usar get_c(tr) para ajustar
FHWA_C_TABLE = [
    # Zonas desarrolladas
    FHWACEntry("Comercial", "Centro comercial/negocios", 0.85),
    FHWACEntry("Comercial", "Vecindario comercial", 0.60),
    FHWACEntry("Industrial", "Industria liviana", 0.65),
    FHWACEntry("Industrial", "Industria pesada", 0.75),
    # Residencial
    FHWACEntry("Residencial", "Unifamiliar (lotes >1000 m2)", 0.40),
    FHWACEntry("Residencial", "Unifamiliar (lotes 500-1000 m2)", 0.50),
    FHWACEntry("Residencial", "Unifamiliar (lotes <500 m2)", 0.60),
    FHWACEntry("Residencial", "Multifamiliar/Apartamentos", 0.70),
    FHWACEntry("Residencial", "Condominios/Townhouse", 0.60),
    # Superficies
    FHWACEntry("Superficies", "Asfalto/Concreto", 0.85),
    FHWACEntry("Superficies", "Adoquin/Ladrillo", 0.78),
    FHWACEntry("Superficies", "Techos", 0.85),
    FHWACEntry("Superficies", "Grava/Ripio", 0.32),
    # Areas verdes (suelo arenoso)
    FHWACEntry("Cesped arenoso", "Pendiente plana <2%", 0.08),
    FHWACEntry("Cesped arenoso", "Pendiente media 2-7%", 0.12),
    FHWACEntry("Cesped arenoso", "Pendiente alta >7%", 0.18),
    # Areas verdes (suelo arcilloso)
    FHWACEntry("Cesped arcilloso", "Pendiente plana <2%", 0.15),
    FHWACEntry("Cesped arcilloso", "Pendiente media 2-7%", 0.20),
    FHWACEntry("Cesped arcilloso", "Pendiente alta >7%", 0.28),
]

# Tabla Ven Te Chow - Applied Hydrology (Table 5.5.2)
# Valores de C para diferentes periodos de retorno
#                                                    Tr2   Tr5   Tr10  Tr25  Tr50  Tr100
VEN_TE_CHOW_C_TABLE = [
    # Zonas desarrolladas
    ChowCEntry("Comercial", "Centro comercial denso",    0.75, 0.80, 0.85, 0.88, 0.90, 0.95),
    ChowCEntry("Comercial", "Vecindario comercial",      0.50, 0.55, 0.60, 0.65, 0.70, 0.75),
    ChowCEntry("Residencial", "Unifamiliar",             0.25, 0.30, 0.35, 0.40, 0.45, 0.50),
    ChowCEntry("Residencial", "Multifamiliar separado",  0.35, 0.40, 0.45, 0.50, 0.55, 0.60),
    ChowCEntry("Residencial", "Multifamiliar adosado",   0.45, 0.50, 0.55, 0.60, 0.65, 0.70),
    ChowCEntry("Residencial", "Suburbano",               0.20, 0.25, 0.30, 0.35, 0.40, 0.45),
    ChowCEntry("Residencial", "Apartamentos",            0.50, 0.55, 0.60, 0.65, 0.70, 0.75),
    ChowCEntry("Industrial", "Liviana",                  0.50, 0.55, 0.60, 0.65, 0.70, 0.80),
    ChowCEntry("Industrial", "Pesada",                   0.60, 0.65, 0.70, 0.75, 0.80, 0.85),
    # Superficies
    ChowCEntry("Superficies", "Pavimento asfaltico",     0.70, 0.75, 0.80, 0.85, 0.90, 0.95),
    ChowCEntry("Superficies", "Pavimento concreto",      0.75, 0.80, 0.85, 0.90, 0.92, 0.95),
    ChowCEntry("Superficies", "Techos",                  0.75, 0.80, 0.85, 0.90, 0.92, 0.95),
    ChowCEntry("Superficies", "Adoquin con juntas",      0.50, 0.55, 0.60, 0.65, 0.70, 0.75),
    ChowCEntry("Superficies", "Grava/Macadam",           0.25, 0.30, 0.35, 0.40, 0.45, 0.50),
    # Cesped suelo arenoso
    ChowCEntry("Cesped arenoso", "Plano (<2%)",          0.05, 0.08, 0.10, 0.13, 0.15, 0.18),
    ChowCEntry("Cesped arenoso", "Medio (2-7%)",         0.10, 0.13, 0.16, 0.19, 0.22, 0.25),
    ChowCEntry("Cesped arenoso", "Fuerte (>7%)",         0.15, 0.18, 0.21, 0.25, 0.29, 0.32),
    # Cesped suelo arcilloso pesado
    ChowCEntry("Cesped arcilloso", "Plano (<2%)",        0.13, 0.16, 0.19, 0.23, 0.26, 0.29),
    ChowCEntry("Cesped arcilloso", "Medio (2-7%)",       0.18, 0.21, 0.25, 0.29, 0.34, 0.37),
    ChowCEntry("Cesped arcilloso", "Fuerte (>7%)",       0.25, 0.29, 0.34, 0.40, 0.44, 0.50),
]


# Diccionario de tablas disponibles
C_TABLES = {
    "fhwa": ("FHWA HEC-22 (Federal Highway Administration)", FHWA_C_TABLE),
    "chow": ("Ven Te Chow - Applied Hydrology", VEN_TE_CHOW_C_TABLE),
}
