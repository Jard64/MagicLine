from MelvinxClaudine import take_off_performance,dTOFL_dT,thermal_threshold,flex_capability,inoperable_days,flex_metrics,flex_impact_scores, Aircraft
from extract_csv import filter_scenario,charger_donnees
import pandas as pd
import json

# Entrée: données avions, choix aéroport, séries temporelles aéroport pression, température 
# Inoperable day, flex metrics 

NAME_AVION = "Boeing-787"

with open("../Avions/avions.json") as f:
    dict_avion = json.load(f)[NAME_AVION]




