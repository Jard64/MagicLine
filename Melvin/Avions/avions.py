r"""
Autres modèles d'avion pour le modèle Magic Line (MelvinxClaudine.py).

La thèse ne paramètre que le Boeing 737-800 (5.5.1). Ce fichier construit des
instances `Aircraft` pour d'autres monocouloirs bimoteurs, à partir de données
publiques sourcées (voir SOURCES.md), en gardant le B737-800 de la thèse comme
référence de calibration pour les grandeurs qui ne sont pas publiées.

    Avion             Moteur (défaut)     Variante
    A319ceo           CFM56-5B6/P         -
    A320ceo           CFM56-5B4/P         -
    A320neo           LEAP-1A26           A320neo PW1127G-JM
    A321ceo           CFM56-5B3/P         -
    A321neo           LEAP-1A33           A321neo PW1133G-JM
    B737 MAX 8        LEAP-1B27           -

Méthode de construction de chaque paramètre :

  S, OEW, MTOW         OpenAP (TU Delft), fichiers aircraft/<code>.yml
  F_to_base            poussée certifiée au décollage, ICAO Engine Emissions
                       Databank (reprise dans OpenAP engines.csv)
  F_climb_base         F_to_base × (112 000 / 117 000)      (ratio B737-800 thèse)
  k_derate_to/_climb   k_B738 × F_base / F_base,B738        (même pente relative)
  T_flat               ISA+15 °C, comme la thèse (confirmé pour le LEAP-1A : 30 °C)
  C_L_max              reconstruit par (5.18) à partir de V2 et de la masse
                       EUROCONTROL APD :  C_L,max = 2 m g / (ρ0 S (V2/1.13)²)
  C_D0, K              transfert par similitude depuis le B737-800 de la thèse :
                       X_avion = X_B738,thèse × X_OpenAP(avion) / X_OpenAP(B738)
                       avec X_OpenAP la polaire OpenAP en configuration décollage
                       (lisse + volets + train, formules de openap/drag.py)
  alpha, beta          corrélation bimoteur de la thèse MAGIC_LINE_TWIN (5.19)

Contrôles faits sur le B737-800 (même chaîne appliquée à la référence) :
  - (5.18) + EUROCONTROL donne C_L,max = 2.08, la thèse prend 2.10 ;
  - ICAO donne 116.99 kN pour le CFM56-7B26, la thèse prend 117 kN.

Remarque : seul le produit S·C_L,max entre dans V_LOF et F_TOL. Comme C_L,max est
reconstruit avec le même S, le choix de la surface de référence (124 m² OpenAP ou
122.6 m² Airbus pour l'A320) n'a pas d'effet sur la TOFL.
"""

from dataclasses import replace
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from MelvinxClaudine import (Aircraft, B738, G0, RHO_0, K_VS1G_MIN, MAGIC_LINE_TWIN,
                             take_off_performance)


KT = 0.514444 # knot -> m/s


###############################################################################
################## Données sources brutes (cf. SOURCES.md) ####################
###############################################################################

""" OpenAP - géométrie, masses, polaire lisse, volets (aircraft/*.yml, dragpolar/*.yml) """

OPENAP = {
    #        S      span   MTOW    OEW    cd0    k      lambda_f cf/c   Sf/S
    "B738": (124.6, 34.32, 79000, 41400, 0.019, 0.042, 0.900, 0.150, 0.150),
    "A319": (124.0, 35.80, 75500, 40800, 0.020, 0.039, 0.900, 0.176, 0.170),
    "A320": (124.0, 35.80, 78000, 42600, 0.018, 0.039, 0.900, 0.176, 0.170),
    "A20N": (124.0, 35.80, 79000, 44300, 0.017, 0.038, 0.900, 0.176, 0.170),
    "A321": (128.0, 35.80, 93500, 48500, 0.020, 0.041, 0.900, 0.176, 0.165),
    "A21N": (128.0, 35.80, 97000, 50000, 0.017, 0.038, 0.900, 0.176, 0.170), # polaire = A20N (pas de fichier a21n)
    "B38M": (124.6, 34.32, 82000, 45000, 0.020, 0.042, 0.900, 0.150, 0.150),
}

""" Braquage volets au décollage retenu (°) - B737 : volets 5 (thèse) ; Airbus : CONF 1+F """

TAKEOFF_FLAP_DEG = {"B738": 5, "B38M": 5, "A319": 10, "A320": 10, "A20N": 10, "A321": 10, "A21N": 10}

""" ICAO Engine Emissions Databank - poussée de décollage certifiée (N) """

ENGINE_THRUST = {
    "CFM56-7B26": 116990, # contrôle B737-800
    "CFM56-5B6/P": 104530,
    "CFM56-5B4/P": 117900,
    "CFM56-5B3/P": 142350,
    "LEAP-1A26": 120600,
    "PW1127G-JM": 120430,
    "LEAP-1A33": 143100, # entrée ICAO groupée LEAP-1A35A/33/33B2/32/30
    "PW1133G-JM": 147280,
    "LEAP-1B27": 124700,
}

""" EUROCONTROL Aircraft Performance Database - (masse kg, V2 kt IAS, distance décollage m) """

EUROCONTROL_APD = {
    "B738": (70530, 145, 2300),
    "A319": (64000, 135, 1750),
    "A320": (73900, 145, 2190),
    "A20N": (79000, 145, 1951),
    "A321": (83000, 145, 2210),
    "A21N": (97000, 145, 2150),
    "B38M": (82600, 145, 2500),
}


###############################################################################
################## Dérivation des paramètres ##################################
###############################################################################

def openap_takeoff_polar(code):
    """(C_D0, K) OpenAP en configuration décollage (openap/drag.py, Drag.nonclean).

    ΔC_D0,volets = λ_f (c_f/c)^1.38 (S_f/S) sin²δ          (McCormick 1994)
    ΔC_D0,train  = (W/S) · 3.16e-5 · MTOW^-0.215          (Mair & Birdsall 1996)
    K            = 1 / (1/K_lisse + π A Δe),  Δe = 0.0026 δ (Obert 2009, moteurs sous l'aile)
    """
    S, span, mtow, _, cd0, k, lambda_f, cfc, sfs = OPENAP[code]
    delta = TAKEOFF_FLAP_DEG[code]
    d_cd_flap = lambda_f * cfc ** 1.38 * sfs * math.sin(math.radians(delta)) ** 2
    d_cd_gear = mtow * G0 / S * 3.16e-5 * mtow ** (-0.215)
    aspect_ratio = span ** 2 / S
    k_to = 1 / (1 / k + math.pi * aspect_ratio * 0.0026 * delta)
    return cd0 + d_cd_flap + d_cd_gear, k_to


def scaled_polar(code):
    """(C_D0, K) transférés depuis le B737-800 de la thèse par le rapport des polaires OpenAP."""
    cd0_ref, k_ref = openap_takeoff_polar("B738")
    cd0, k = openap_takeoff_polar(code)
    return B738.C_D0 * cd0 / cd0_ref, B738.K * k / k_ref


def C_L_max_from_apd(code, S):
    """C_L,max par (5.18) : V_stall = V2 / 1.13, V2 IAS ≈ EAS au niveau de la mer (ρ0)."""
    mass, V2_kt, _ = EUROCONTROL_APD[code]
    V_stall = V2_kt * KT / K_VS1G_MIN
    return 2 * mass * G0 / (RHO_0 * V_stall ** 2 * S)


def make_aircraft(name, code, engine):
    """Construit un `Aircraft` à partir des données sources et des ratios B737-800 de la thèse."""
    S, _, mtow, oew, *_ = OPENAP[code]
    F_to = ENGINE_THRUST[engine]
    scale = F_to / B738.F_to_base
    C_D0, K = scaled_polar(code)
    return Aircraft(
        name=f"{name} ({engine})",
        S=S,
        C_L_max=C_L_max_from_apd(code, S),
        C_D0=C_D0,
        K=K,
        n_engines=2,
        F_to_base=F_to,
        F_climb_base=B738.F_climb_base * scale,
        T_flat=B738.T_flat,
        k_derate_to=B738.k_derate_to * scale,
        k_derate_climb=B738.k_derate_climb * scale,
        OEW=oew,
        MTOW=mtow,
        mu_r=B738.mu_r,
        alpha=MAGIC_LINE_TWIN[0],
        beta=MAGIC_LINE_TWIN[1],
    )


###############################################################################
################## Avions disponibles #########################################
###############################################################################

A319CEO = make_aircraft("A319ceo", "A319", "CFM56-5B6/P")
A320CEO = make_aircraft("A320ceo", "A320", "CFM56-5B4/P")
A320NEO = make_aircraft("A320neo", "A20N", "LEAP-1A26")
A320NEO_PW = make_aircraft("A320neo", "A20N", "PW1127G-JM")
A321CEO = make_aircraft("A321ceo", "A321", "CFM56-5B3/P")
A321NEO = make_aircraft("A321neo", "A21N", "LEAP-1A33")
A321NEO_PW = make_aircraft("A321neo", "A21N", "PW1133G-JM")
B38M = make_aircraft("B737 MAX 8", "B38M", "LEAP-1B27")

# B737-800 reconstruit avec la même chaîne, uniquement pour contrôler la méthode
B738_CHECK = replace(make_aircraft("B737-800", "B738", "CFM56-7B26"),
                     alpha=B738.alpha, beta=B738.beta)

AIRCRAFT = {ac.name: ac for ac in (A319CEO, A320CEO, A320NEO, A320NEO_PW,
                                   A321CEO, A321NEO, A321NEO_PW, B38M)}


def calibrate_beta(ac: Aircraft, mass, tofl_ref, T_celsius=15.0, h=0.0):
    """Recale β (α gardé) pour que le modèle donne tofl_ref dans une condition connue.

    À utiliser avec une TOFL constructeur dont les conditions sont connues (ex. abaque
    "take-off weight / field length" des documents Airbus AC, ISA, niveau de la mer).
    TOFL = α F_TOL + β  =>  β = tofl_ref - α F_TOL
    """
    r = take_off_performance(mass, T_celsius, h, ac=ac)
    return replace(ac, beta=tofl_ref - ac.alpha * r.F_TOL)


###############################################################################
################## Démonstration ##############################################
###############################################################################

if __name__ == "__main__":
    import warnings
    warnings.simplefilter("ignore") # non-convergence S2 = jour infaisable, affiché "inf"

    print("=== Paramètres dérivés ===")
    print(f"{'avion':32s} {'S':>6s} {'CLmax':>6s} {'CD0':>7s} {'K':>7s} {'F_to':>7s} "
          f"{'k_der':>6s} {'OEW':>6s} {'MTOW':>6s}")
    for ac in (B738, B738_CHECK, *AIRCRAFT.values()):
        print(f"{ac.name:32s} {ac.S:6.1f} {ac.C_L_max:6.3f} {ac.C_D0:7.4f} {ac.K:7.4f} "
              f"{ac.F_to_base / 1000:6.1f}k {ac.k_derate_to:6.0f} {ac.OEW:6.0f} {ac.MTOW:6.0f}")

    print("\n=== Contrôle : TOFL modèle vs distance EUROCONTROL (ISA, niveau de la mer, vent nul) ===")
    print("    (les conditions EUROCONTROL ne sont pas publiées : ordre de grandeur seulement)")
    codes = {B738_CHECK.name: "B738", A319CEO.name: "A319", A320CEO.name: "A320",
             A320NEO.name: "A20N", A321CEO.name: "A321", A321NEO.name: "A21N", B38M.name: "B38M"}
    for name, code in codes.items():
        ac = B738_CHECK if code == "B738" else AIRCRAFT[name]
        mass, _, tod = EUROCONTROL_APD[code]
        r = take_off_performance(mass, 15.0, ac=ac)
        print(f"  {name:32s} m={mass / 1000:5.1f} t : TOFL={r.TOFL:6.0f} m  (APD {tod} m, "
              f"écart {100 * (r.TOFL / tod - 1):+5.1f} %)  {r.regime}, S2={r.s2_status}")

    print("\n=== TOFL (m) à la MTOW, niveau de la mer, vent nul ===")
    temps_isa = [0, 15, 25, 35]
    print(f"{'avion':32s} " + " ".join(f"ISA+{d:<3d}" for d in temps_isa))
    for ac in AIRCRAFT.values():
        row = []
        for d in temps_isa:
            r = take_off_performance(ac.MTOW, 15 + d, ac=ac)
            row.append(f"{r.TOFL:7.0f}" if r.feasible else "    inf")
        print(f"{ac.name:32s} " + " ".join(row))
