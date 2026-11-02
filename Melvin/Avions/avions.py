r"""
Construction des avions du modèle Magic Line (MelvinxClaudine.py) à partir du catalogue.

Le catalogue (catalogue.csv, rempli par import_catalogue.py) contient les données
brutes sourcées de chaque avion : OpenAP, ICAO Engine Emissions Databank, EUROCONTROL
APD (voir SOURCES.md). Ce module en tire les paramètres `Aircraft`, selon deux méthodes :

  methode="direct"  (par défaut) - chaque avion est traité de la même façon, sans
                    utiliser les valeurs du B737-800 de la thèse :
      C_L_max   (5.18) : 2 m g / (ρ0 S (V2/1.13)²), m et V2 EUROCONTROL
      C_D0      configuration 2e segment (train rentré, volets décollage, un moteur
                en panne) : C_D0,lisse + ΔC_D0,volets + ΔC_D0,moulinet
                  ΔC_D0,volets   = λ_f (c_f/c)^1.38 (S_f/S) sin²δ      (McCormick, via OpenAP)
                  ΔC_D0,moulinet = 0.3 · (π D_fan²/4) / S              (Raymer, ordre de grandeur)
      K         1 / (1/K_lisse + π A Δe),  Δe = 0.0026 δ (moteurs sous l'aile, Obert via OpenAP)

  methode="echelle" - méthode de la première version : C_D0 et K du B737-800 de la
                    thèse, multipliés par le rapport des polaires OpenAP (avion / B737-800).
                    Garde le niveau de traînée de la thèse (validée sur le B737-800).

Communs aux deux méthodes :
  S, OEW, MTOW         OpenAP
  F_to_base            ICAO EEDB (poussée certifiée)
  F_climb_base         F_to_base × 112/117                  (rapport de la thèse)
  k_derate             F_base × 0.77 %/°C (TO), 0.76 %/°C (montée) (pente relative de la thèse)
  T_flat               15 °C (ISA+15)
  alpha, beta          corrélation Magic Line de la thèse choisie dans la colonne `magic_line`

Toute colonne du catalogue portant le nom d'un champ `Aircraft` (C_L_max, C_D0, K,
T_flat, alpha, beta, ...) et non vide remplace la valeur calculée : c'est le moyen de
forcer une donnée constructeur connue.
"""

import csv
from dataclasses import fields, replace
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from MelvinxClaudine import (Aircraft, B738, G0, RHO_0, K_VS1G_MIN, MAGIC_LINE_TWIN,
                             MAGIC_LINE_UNIFIED, MAGIC_LINE_QUAD, MAGIC_LINE_B738,
                             take_off_performance)

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGUE = os.path.join(HERE, "catalogue.csv")

KT = 0.514444 # knot -> m/s

""" Rapports repris du B737-800 de la thèse (5.5.1), appliqués à tous les avions """

CLIMB_TO_RATIO = B738.F_climb_base / B738.F_to_base # 112/117
DERATE_REL_TO = B738.k_derate_to / B738.F_to_base # 0.77 %/°C
DERATE_REL_CLIMB = B738.k_derate_climb / B738.F_climb_base # 0.76 %/°C

""" Traînée de moulinet du moteur en panne """

WINDMILL_COEF = 0.3 # D/q = 0.3 · aire de la soufflante (Raymer)
DEFAULT_DCD_WINDMILL = 0.005 # si le diamètre de soufflante n'est pas connu

MAGIC_LINES = {"twin": MAGIC_LINE_TWIN, "unified": MAGIC_LINE_UNIFIED,
               "quad": MAGIC_LINE_QUAD, "b738": MAGIC_LINE_B738}

""" Référence OpenAP du B737-800 pour la méthode 'echelle' (dragpolar/b738.yml, volets 5°) """

B738_OPENAP = dict(S_m2=124.6, envergure_m=34.32, MTOW_kg=79000, cd0_lisse=0.019, k_lisse=0.042,
                   lambda_f=0.9, cf_c=0.15, Sf_S=0.15, volets_TO_deg=5, montage_moteur="wing")


###############################################################################
################## Lecture du catalogue #######################################
###############################################################################

def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def charger_catalogue(path=CATALOGUE):
    """Lignes du catalogue, valeurs numériques converties. {nom: ligne}"""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        out[r["nom"]] = {k: (_num(v) if _num(v) is not None else v) for k, v in r.items()}
    return out


###############################################################################
################## Polaires ###################################################
###############################################################################

def delta_cd0_flaps(r):
    """ΔC_D0 volets (McCormick 1994, formule OpenAP)."""
    return (r["lambda_f"] * r["cf_c"] ** 1.38 * r["Sf_S"]
            * math.sin(math.radians(r["volets_TO_deg"])) ** 2)


def delta_cd0_gear(r):
    """ΔC_D0 train sorti (Mair & Birdsall 1996, formule OpenAP)."""
    m = r["MTOW_kg"]
    return m * G0 / r["S_m2"] * 3.16e-5 * m ** (-0.215)


def delta_cd0_windmill(r):
    """ΔC_D0 du moteur en panne (moulinet) : 0.3 · aire soufflante / S."""
    d = r.get("diam_soufflante_m")
    if not isinstance(d, float):
        return DEFAULT_DCD_WINDMILL
    return WINDMILL_COEF * math.pi * d ** 2 / 4 / r["S_m2"]


def k_flaps(r):
    """K avec volets : 1 / (1/K + π A Δe), Δe = 0.0026 δ (0.0046 δ si moteurs à l'arrière)."""
    de = (0.0046 if r.get("montage_moteur") == "rear" else 0.0026) * r["volets_TO_deg"]
    aspect_ratio = r["envergure_m"] ** 2 / r["S_m2"]
    return 1 / (1 / r["k_lisse"] + math.pi * aspect_ratio * de)


def polaire_directe(r):
    """(C_D0, K) en configuration 2e segment, construits sans référence à la thèse."""
    return r["cd0_lisse"] + delta_cd0_flaps(r) + delta_cd0_windmill(r), k_flaps(r)


def _polaire_openap_decollage(r):
    return r["cd0_lisse"] + delta_cd0_flaps(r) + delta_cd0_gear(r), k_flaps(r)


def polaire_echelle(r):
    """(C_D0, K) du B737-800 de la thèse × rapport des polaires OpenAP de décollage (avion / B737-800)."""
    cd0_ref, k_ref = _polaire_openap_decollage(B738_OPENAP)
    cd0, k = _polaire_openap_decollage(r)
    return B738.C_D0 * cd0 / cd0_ref, B738.K * k / k_ref


###############################################################################
################## Construction des avions ####################################
###############################################################################

def C_L_max_depuis_V2(masse, V2_kt, S):
    """(5.18) : V_stall = V2 / 1.13, V2 IAS ≈ EAS au niveau de la mer (ρ0)."""
    V_stall = V2_kt * KT / K_VS1G_MIN
    return 2 * masse * G0 / (RHO_0 * V_stall ** 2 * S)


def construire_avion(r, methode="direct"):
    """`Aircraft` à partir d'une ligne du catalogue."""
    if methode == "direct":
        C_D0, K = polaire_directe(r)
    elif methode == "echelle":
        C_D0, K = polaire_echelle(r)
    else:
        raise ValueError("methode doit valoir 'direct' ou 'echelle'")

    if isinstance(r.get("V2_kt"), float) and isinstance(r.get("masse_ref_kg"), float):
        C_L_max = C_L_max_depuis_V2(r["masse_ref_kg"], r["V2_kt"], r["S_m2"])
    elif isinstance(r.get("C_L_max"), float):
        C_L_max = r["C_L_max"]
    else:
        raise ValueError(f"{r['nom']} : ni V2 ni C_L_max dans le catalogue")

    F_to = r["F_TO_N"]
    F_climb = F_to * CLIMB_TO_RATIO
    ml = str(r.get("magic_line") or "twin")
    alpha, beta = MAGIC_LINES[ml] if ml in MAGIC_LINES else map(float, ml.split(";"))

    ac = Aircraft(
        name=r["nom"],
        S=r["S_m2"],
        C_L_max=C_L_max,
        C_D0=C_D0,
        K=K,
        n_engines=int(r["n_moteurs"]),
        F_to_base=F_to,
        F_climb_base=F_climb,
        T_flat=B738.T_flat,
        k_derate_to=F_to * DERATE_REL_TO,
        k_derate_climb=F_climb * DERATE_REL_CLIMB,
        OEW=r["OEW_kg"],
        MTOW=r["MTOW_kg"],
        mu_r=B738.mu_r,
        alpha=alpha,
        beta=beta,
    )
    overrides = {f.name: r[f.name] for f in fields(Aircraft)
                 if f.name != "name" and isinstance(r.get(f.name), float)}
    return replace(ac, **overrides)


def flotte(noms=None, methode="direct", path=CATALOGUE):
    """{nom: Aircraft} pour tout le catalogue, ou pour les noms donnés (recherche partielle acceptée)."""
    cat = charger_catalogue(path)
    if noms is not None:
        choisis = [n for n in cat if any(q.lower() in n.lower() for q in noms)]
        cat = {n: cat[n] for n in choisis}
    return {n: construire_avion(r, methode) for n, r in cat.items()}


def calibrate_beta(ac: Aircraft, mass, tofl_ref, T_celsius=15.0, h=0.0):
    """Recale β (α gardé) pour que le modèle donne tofl_ref dans une condition connue.

    À utiliser avec une TOFL constructeur dont les conditions sont connues (ex. abaque
    "take-off weight / field length" des documents Airbus AC, ISA, niveau de la mer).
    TOFL = α F_TOL + β  =>  β = tofl_ref - α F_TOL
    """
    r = take_off_performance(mass, T_celsius, h, ac=ac)
    return replace(ac, beta=tofl_ref - ac.alpha * r.F_TOL)


###############################################################################
################## Raccourcis (première version) ##############################
###############################################################################

AIRCRAFT = flotte()


def _get(prefix):
    return next(ac for n, ac in AIRCRAFT.items() if n.startswith(prefix))


A319CEO = _get("A319ceo")
A320CEO = _get("A320ceo")
A320NEO = _get("A320neo (LEAP")
A320NEO_PW = _get("A320neo (PW")
A321CEO = _get("A321ceo")
A321NEO = _get("A321neo (LEAP")
A321NEO_PW = _get("A321neo (PW")
B38M = _get("B737 MAX 8")


if __name__ == "__main__":
    for methode in ("direct", "echelle"):
        print(f"=== Paramètres, méthode '{methode}' ===")
        print(f"{'avion':28s} {'S':>6s} {'CLmax':>6s} {'CD0':>7s} {'K':>7s} {'L/D_TO':>6s} "
              f"{'F_to':>7s} {'MTOW':>7s}")
        for ac in (B738, *flotte(methode=methode).values()):
            C_L = ac.C_L_max / K_VS1G_MIN ** 2
            ld = C_L / (ac.C_D0 + ac.K * C_L ** 2)
            print(f"{ac.name:28s} {ac.S:6.1f} {ac.C_L_max:6.3f} {ac.C_D0:7.4f} {ac.K:7.4f} "
                  f"{ld:6.2f} {ac.F_to_base / 1000:6.1f}k {ac.MTOW:7.0f}")
        print()
