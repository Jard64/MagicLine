from modele_climatique import take_off_performance,dTOFL_dT,thermal_threshold,flex_capability,inoperable_days,flex_metrics,flex_impact_scores, Aircraft
from modele_climatique import MAGIC_LINE_QUAD,MAGIC_LINE_TWIN,MAGIC_LINE_UNIFIED
from extract_csv import filter_scenario,charger_donnees
import pandas as pd
import json

# Entrée: données avions, choix aéroport, séries temporelles aéroport pression, température 
# Inoperable day, flex metrics 

NAME_AVION = "Boeing-787"



def create_avion(name_avion):
    objet_avion = Aircraft()

    with open("../Avions/aircraf_performance.json") as f:
        dict_avion = json.load(f)[name_avion]

    name: str = "B737-800"
    # Geometry and aerodynamics
    dict_aero = dict_avion["geometric_aerodynamic"]
    objet_avion.S = dict_aero["wing_reference_area"]["value"]
    objet_avion.C_L_max = dict_aero["C_L_max"]["value"]
    objet_avion.C_D0 = dict_aero["CD0"]["value"]
    objet_avion.K = dict_aero["K"]["value"]

    # Propulsion
    dict_propulsion = dict_avion["propulsion"]
    objet_avion.n_engines = dict_propulsion["number_of_engines"]["value"]
    objet_avion.F_to_base = dict_propulsion["F_TO_base"]["value"]
    objet_avion.F_climb_base = dict_propulsion["F_climb_base"]["value"]
    objet_avion.T_flat = dict_propulsion["T_flat"]["takeoff"]["value"]
    k_derate_to = dict_propulsion["k_derate_TO"]["value"]
    objet_avion.k_derate_climb = dict_propulsion["k_derate_clim"]["value"]
    # Weights and runway
    dict_operational = dict_avion["operational"]
    objet_avion.OEW = dict_operational["operating_empty_weight"]["value"]
    objet_avion.MTOW = dict_operational["max_takeoff_weight"]["value"]
    objet_avion.mu_r = dict_operational["rolling_friction_coefficient"]["value"]
    # Magic Line coefficients (TOFL = alpha * F_TOL + beta)
    if objet_avion.n_engines == 2:
        MAGIC_LINE = MAGIC_LINE_TWIN
    elif objet_avion.n_engines == 4:
        MAGIC_LINE = MAGIC_LINE_QUAD
    else:
        MAGIC_LINE=MAGIC_LINE_UNIFIED

    objet_avion.alpha = MAGIC_LINE[0]
    objet_avion.beta = MAGIC_LINE[1]
    return objet_avion


objet_avion = create_avion(NAME_AVION)










