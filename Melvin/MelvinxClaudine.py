r"""
Modèle mathématique et physique complet de la thèse de Suzanne Salles (2025)
"Vulnerability of aviation to climate change" -- méthode "Magic Line".

Organisation (numéros de section / équation = ceux de la thèse) :

    PARTIE A - Climat (chap. 3 & 4)
        A1. Densité et altitude-densité ............................ (3.1), (3.2)
        A2. Vent projeté sur la piste ................................ (3.3), (3.10), (5.49)
        A3. Agrégation journalière ERA5 ............................... (3.5)-(3.7)
        A4. Sélection du point de grille (masque terre/mer) ........... Fig. 3.3
        A5. Correction de biais CDF-t ................................. (3.8), (3.9)
        A6. Moyenne d'ensemble "un modèle, une voix" .................. (3.4)
        A7. Seuil thermique opérationnel .............................. (4.1), (4.2)

    PARTIE B - Performance au décollage (chap. 5)
        B1. Paramètres Boeing 737-800 / CFM56-7B24 .................... 5.5.1
        B2. Atmosphère ISA ............................................ (5.25)-(5.27)
        B3. Poussée : flat-rating, derate, correction altitude ....... (5.21), (5.28)-(5.34)
        B4. Physique du roulage (Newton, polaire, distance exacte) ... (5.5)-(5.13)
        B5. Contrainte de 2e segment (pente de montée OEI) ........... (5.14), (5.35)-(5.43)
        B6. Paramètre Magic Line et longueur de piste ................ (5.15)-(5.19), (5.44), (5.45)
        B7. Effet du vent ............................................ (5.46)-(5.52)
        B8. Sensibilités analytiques à la température ................ (5.20), (5.22)
        B9. Longueur certifiée (BFL) .................................. (5.4)
        B10. Modèle complet (Fig. 5.3) ................................

    PARTIE C - Vulnérabilité des aéroports (chap. 7)
        C1. Jour inopérable, défaillance opérationnelle .............. 7.1.2
        C2. Agrégation multi-pistes .................................. 7.1.1
        C3. Décollage "flex" (poussée réduite) ....................... 7.2.4

Conventions d'unités (SI) : m, kg, N, s, K (les écarts ISA en °C = K).
Dans F_TOL, W est la MASSE en kg (=> F_TOL en s², cf. Fig. 5.2 : valeurs 60-140 s²) ;
dans la pente de montée, W est le POIDS en N (m·g).

/!\ Points où la thèse est ambiguë ou contient une coquille, et choix faits ici :
  - (5.26) : T0 doit être en Kelvin (288.15 K), l'exposant vaut g0/(R·L) = 5.256
    (et non g0/(R·L) - 1, qui est l'exposant de la densité, 4.256).
  - (3.3) et (5.49) donnent deux formules différentes pour le vent de face. Avec la
    convention météo (u vers l'est, v vers le nord) et ψ cap piste depuis le nord
    (sens horaire), la direction de l'avion est (sin ψ, cos ψ) et le vent de face
    est  -(u·sin ψ + v·cos ψ). C'est cette formule qui est codée.
  - (3.9) est mal retranscrite dans le PDF ; on code la CDF-t standard de
    Michelangeli et al. (2009).
  - Le critère "flex" (7.2.4) n'est pas formalisé : on cherche la plus grande
    réduction de poussée (≤ 25 %) telle que TOFL ≤ longueur de piste et S2 respecté.
"""

from dataclasses import dataclass, replace
import math
import warnings

import numpy as np


###############################################################################
################## PARTIE B1 - Paramètres (Boeing 737-800) (5.5.1) ###########
###############################################################################

""" Constantes atmosphériques """

T0 = 288.15 # sea-level standard temperature - K
L = 0.0065 # temperature lapse rate - K/m
P0 = 101325 # sea-level standard pressure - Pa
G0 = 9.80665 # standard gravitational acceleration - m/s^2
R = 287.05 # specific gas constant for air - J/(kg·K)
RHO_0 = 1.225 # sea-level standard density - kg/m^3
C_RHO = 0.985 # empirical humidity correction factor - (5.27)
H_TROPOPAUSE = 11000 # validity limit of the tropospheric model - m
KELVIN = 273.15

GAMMA_RHO = 27.6 / 1000 # effective density-altitude lapse rate - °C/m (3.2)

""" Contraintes réglementaires (CS-25 / FAR 25) """

K_VS1G_MIN = 1.13 # minimum speed margin above stall (V2 = 1.13 Vs1g)
TOL_AEO_FACTOR = 1.15 # safety factor on all-engines take-off length (5.4)
GAMMA_S2_MIN = {2: 0.024, 3: 0.027, 4: 0.030} # min 2nd segment gradient by engine count (5.3.4)

""" Corrélation Magic Line (5.19) et calibrations """

MAGIC_LINE_UNIFIED = (29.41, -10.50) # (alpha, beta) 29 aircraft, R²=0.77, σ=185 m
MAGIC_LINE_TWIN = (32.44, -347.40) # twin-engine fit
MAGIC_LINE_QUAD = (1.87, 2911.80) # four-engine fit
MAGIC_LINE_B738 = (30.34, -323.0) # B737-800 specific (RMSE 377 m), used for validation

""" Algorithme S2 (5.5.4) """

S2_TOLERANCE = 1e-4
S2_MAX_ITER = 50
S2_ALPHA_STEP = 0.5

""" Paramètres opérationnels """

THRUST_FLOOR = 0.35 # minimum thrust fraction (5.34)
FLEX_MAX_REDUCTION = 0.25 # flex thrust >= 75 % of rated (7.2.4.1)


@dataclass(frozen=True)
class Aircraft:
    """Paramètres avion (5.5.1). Valeurs par défaut : Boeing 737-800, CFM56-7B24, volets 5°."""

    name: str = "B737-800"
    # Geometry and aerodynamics
    S: float = 124.6 # reference surface - m^2
    C_L_max: float = 2.10 # max lift coefficient in take-off configuration
    C_D0: float = 0.0780 # zero-lift drag coefficient
    K: float = 0.0366 # induced drag factor
    # Propulsion
    n_engines: int = 2
    F_to_base: float = 117000 # take-off thrust per engine - N
    F_climb_base: float = 112000 # climb thrust per engine - N
    T_flat: float = 15.0 # flat-rating limit, as ISA deviation - °C
    k_derate_to: float = 900 # take-off thrust derate rate - N/°C/engine
    k_derate_climb: float = 850 # climb thrust derate rate - N/°C/engine
    # Weights and runway
    OEW: float = 41400 # operating empty weight - kg
    MTOW: float = 79000 # maximum take-off weight - kg
    mu_r: float = 0.02 # rolling friction coefficient (dry runway)
    # Magic Line coefficients (TOFL = alpha * F_TOL + beta)
    alpha: float = MAGIC_LINE_B738[0]
    beta: float = MAGIC_LINE_B738[1]

    @property
    def gamma_s2_min(self):
        return GAMMA_S2_MIN[self.n_engines]


B738 = Aircraft()
# Variantes de volets (7.1.3.2) - seuls C_L_max et C_D0 sont donnés dans la thèse
B738_FLAPS_1 = replace(B738, name="B737-800 flaps 1", C_L_max=2.125, C_D0=0.073)
B738_FLAPS_5 = B738
B738_FLAPS_15 = replace(B738, name="B737-800 flaps 15", C_L_max=2.875, C_D0=0.092)


###############################################################################
################## PARTIE B2 - Atmosphère ISA (5.5.2) #########################
###############################################################################

def _check_altitude(h):
    if np.any(np.asarray(h) > H_TROPOPAUSE):
        raise ValueError("ISA tropospheric model only valid below 11 000 m")


def temperature_isa(h):
    """Température ISA en K à l'altitude h (m) - (5.25) / (4.2)."""
    _check_altitude(h)
    return T0 - L * h


def temperature_actual(h, delta_T_isa):
    """Température réelle en K : T = T_ISA(h) + ΔT_ISA."""
    return temperature_isa(h) + delta_T_isa


def delta_isa(h, T_celsius):
    """Écart ISA (°C) d'une température mesurée T (°C) à l'altitude h."""
    return T_celsius + KELVIN - temperature_isa(h)


def pressure(h):
    """Pression en Pa, équilibre hydrostatique à gradient constant - (5.26).

    p/p0 = (1 - L·h/T0)^(g0/(R·L)) = (1 - h/44330.8)^5.256
    """
    _check_altitude(h)
    return P0 * (1 - L * h / T0) ** (G0 / (R * L))


def density(h, T_kelvin, humidity_correction=True):
    """Masse volumique de l'air en kg/m³ - (5.27).

    ρ = ρ0 · (p/p0) · (T_ISA(0)/T) · c_ρ
    """
    c = C_RHO if humidity_correction else 1.0
    return RHO_0 * (pressure(h) / P0) * (T0 / T_kelvin) * c


###############################################################################
################## PARTIE A1 - Gaz parfait et altitude-densité (3.2.1) ########
###############################################################################

def density_ideal_gas(p, T_kelvin):
    """Loi des gaz parfaits ρ = p / (R·T) - (3.1)."""
    return p / (R * T_kelvin)


def density_altitude(h, T_celsius):
    """Altitude-densité en m - (3.2) : h_ρ = h + (T - T_ISA(h)) / Γ_ρ, Γ_ρ ≈ 27.6 °C/km."""
    return h + delta_isa(h, T_celsius) / GAMMA_RHO


###############################################################################
################## PARTIE B3 - Poussée (5.4.3, 5.5.3) #########################
###############################################################################

def altitude_correction_factor(h, method="none", T_kelvin=None):
    """Facteur de correction de poussée avec l'altitude f_alt (5.5.3, step 2).

    method :
        "none"    -> 1.0 (configuration validée, 6.2.2)
        "density" -> ρ(h)/ρ0
        "linear25"-> 1 - 0.025·h/1000  (pénalité réduite)
        "linear6" -> 1 - 0.06·h/1000   (règle traditionnelle)
    """
    if method == "none":
        return 1.0
    if method == "density":
        T = temperature_isa(h) if T_kelvin is None else T_kelvin
        return density(h, T) / RHO_0
    if method == "linear25":
        return 1 - 0.025 * (h / 1000)
    if method == "linear6":
        return 1 - 0.06 * (h / 1000)
    raise ValueError(f"unknown altitude correction method: {method}")


def thrust_regime(ac: Aircraft, delta_T_isa):
    """Régime moteur : 'flat-rating' si ΔT_ISA ≤ T_flat, sinon 'derate'."""
    return "flat-rating" if delta_T_isa <= ac.T_flat else "derate"


def engine_thrust(ac: Aircraft, delta_T_isa, h=0.0, rating="takeoff", alt_correction="none"):
    """Poussée par moteur en N (5.28)-(5.34).

    1. flat-rating : F = F_base                                (5.28), (5.29)
       derate      : F = F_base - k_derate·(ΔT_ISA - T_flat)   (5.30), (5.31) / (5.21)
    2. F_corr = F · f_alt                                      (5.32), (5.33)
    3. F_final = max(F_corr, 0.35·F_base)                      (5.34)
    """
    if rating == "takeoff":
        F_base, k = ac.F_to_base, ac.k_derate_to
    elif rating == "climb":
        F_base, k = ac.F_climb_base, ac.k_derate_climb
    else:
        raise ValueError("rating must be 'takeoff' or 'climb'")

    F = F_base
    if delta_T_isa > ac.T_flat:
        F = F_base - k * (delta_T_isa - ac.T_flat)
    F *= altitude_correction_factor(h, alt_correction, temperature_actual(h, delta_T_isa))
    return max(F, THRUST_FLOOR * F_base)


###############################################################################
################## PARTIE B4 - Physique du roulage (5.3.3) ####################
###############################################################################

def drag_coefficient(ac: Aircraft, C_L):
    """Polaire parabolique C_D = C_D0 + K·C_L² - (5.7) / (5.39)."""
    return ac.C_D0 + ac.K * C_L ** 2


def lift_to_drag(ac: Aircraft, C_L):
    """Finesse L/D = C_L / C_D - (5.40)."""
    return C_L / drag_coefficient(ac, C_L)


def C_L_optimal(ac: Aircraft):
    """C_L de finesse maximale, sqrt(C_D0/K) - (6.3). Plafond de l'optimisation S2 (6.6.1)."""
    return math.sqrt(ac.C_D0 / ac.K)


def take_off_lift_coefficient(ac: Aircraft, K_vs1g=K_VS1G_MIN):
    """C_L,TO = C_L,max / K_VS1g² - (5.12) / (5.35)."""
    return ac.C_L_max / K_vs1g ** 2


def stall_speed(ac: Aircraft, mass, rho):
    """V_S1g = sqrt(2W / (ρ S C_L,max)) - (5.11)."""
    return math.sqrt(2 * mass * G0 / (rho * ac.S * ac.C_L_max))


def lift_off_speed(ac: Aircraft, mass, rho, C_L_TO):
    """Vitesse air de décollage (= V2 dans le modèle) - (5.12) / (5.37) : V² = 2W / (ρ S C_L,TO)."""
    return math.sqrt(2 * mass * G0 / (rho * ac.S * C_L_TO))


def acceleration(ac: Aircraft, V, mass, rho, thrust_total, C_L):
    """Accélération au roulage, 2e loi de Newton - (5.5), (5.6).

    m dV/dt = T - D(V) - μ_r (W - L(V))
    """
    q = 0.5 * rho * V ** 2
    lift = q * ac.S * C_L
    drag = q * ac.S * drag_coefficient(ac, C_L)
    return (thrust_total - drag - ac.mu_r * (mass * G0 - lift)) / mass


def ground_roll_exact(ac: Aircraft, mass, rho, thrust_total, C_L, V_LOF):
    """Distance de roulage exacte (intégrale (5.9), solution logarithmique).

    s_g = (W/g) ∫ V dV / (A - B V²),  A = T - μ_r W,  B = ½ ρ S (C_D - μ_r C_L)
        = m / (2B) · ln(A / (A - B V_LOF²))
    (poussée supposée constante avec la vitesse)
    """
    W = mass * G0
    A = thrust_total - ac.mu_r * W
    B = 0.5 * rho * ac.S * (drag_coefficient(ac, C_L) - ac.mu_r * C_L)
    if A <= 0 or A - B * V_LOF ** 2 <= 0:
        return math.inf
    if abs(B) < 1e-12:
        return mass * V_LOF ** 2 / (2 * A)
    return mass / (2 * B) * math.log(A / (A - B * V_LOF ** 2))


def ground_roll_constant_accel(ac: Aircraft, mass, rho, thrust_total, C_L, V_LOF, frac=0.85):
    """Approximation à accélération constante - (5.10), (5.13).

    s_g ≈ W V_LOF² / (2 g Γ W),  Γ = (T - D• - μ_r (W - L•)) / W  évalué à frac·V_LOF
    """
    V = frac * V_LOF
    gamma = acceleration(ac, V, mass, rho, thrust_total, C_L) / G0
    return V_LOF ** 2 / (2 * G0 * gamma)


###############################################################################
################## PARTIE B5 - Contrainte de 2e segment (5.3.4, 5.5.4) ########
###############################################################################

def climb_gradient_s2(ac: Aircraft, mass, F_climb, C_L):
    """Pente de montée moteur en panne - (5.14) / (5.41).

    γ_S2 = (N-1)·F / W - 1/(L/D)
    """
    return (ac.n_engines - 1) * F_climb / (mass * G0) - 1 / lift_to_drag(ac, C_L)


@dataclass
class S2Result:
    K_vs1g: float
    C_L_TO: float
    gamma_s2: float
    status: str # "not-binding" | "converged" | "max-iter" | "infeasible"
    iterations: int


def solve_second_segment(ac: Aircraft, mass, F_climb,
                         tol=S2_TOLERANCE, max_iter=S2_MAX_ITER, alpha_step=S2_ALPHA_STEP):
    """Algorithme itératif de la thèse (5.5.4) : augmente K_VS1g jusqu'à γ_S2 ≥ γ_min.

    K^(n+1) = K^(n) + α_step·|Δγ|   (5.43)

    Comme C_L,climb = C_L,TO (5.38), γ_S2 ne dépend pas de ρ : seule la poussée
    transmet l'effet de la température (origine du biais d'altitude, 6.6 / 6.8.2).
    Si C_L,TO passe sous sqrt(C_D0/K), augmenter K dégrade L/D : opération infaisable.
    """
    gamma_min = ac.gamma_s2_min
    C_L_opt = C_L_optimal(ac)
    K = K_VS1G_MIN
    previous = []

    for n in range(1, max_iter + 1):
        C_L = take_off_lift_coefficient(ac, K) # Step 1 (5.35)
        gamma = climb_gradient_s2(ac, mass, F_climb, C_L) # Steps 2-6 (5.36)-(5.41)
        d_gamma = gamma - gamma_min # Step 7 (5.42)
        previous.append(d_gamma)

        if abs(d_gamma) < tol:
            return S2Result(K, C_L, gamma, "converged" if n > 1 else "not-binding", n)
        if d_gamma > tol:
            return S2Result(K, C_L, gamma, "not-binding" if n == 1 else "converged", n)
        if C_L <= C_L_opt:
            # L/D ceiling reached (6.6.1): no aerodynamic fix left
            return S2Result(K, C_L, gamma, "infeasible", n)
        K = K + alpha_step * abs(d_gamma)

    monotonic = all(b >= a for a, b in zip(previous, previous[1:]))
    warnings.warn("S2 iteration did not converge"
                  + (" (monotonic, keeping last K)" if monotonic else " (oscillating)"))
    return S2Result(K, C_L, gamma, "max-iter", max_iter)


###############################################################################
################## PARTIE B6 - Paramètre Magic Line (5.4) #####################
###############################################################################

def magic_line_parameter(ac: Aircraft, mass, rho, C_L_TO, F_to):
    """F_TOL = W² / (ρ S C_L,TO N F_TO)  - (5.16) / (5.44), W en kg -> F_TOL en s²."""
    return mass ** 2 / (rho * ac.S * C_L_TO * ac.n_engines * F_to)


def take_off_field_length(F_TOL, alpha=MAGIC_LINE_B738[0], beta=MAGIC_LINE_B738[1]):
    """TOFL = α F_TOL + β - (5.17) / (5.45)."""
    return alpha * F_TOL + beta


def fit_magic_line(F_TOL_values, TOFL_values):
    """Régression linéaire TOFL = α F_TOL + β sur une base d'avions (5.4.2.2).

    Retourne (alpha, beta, R², sigma).
    """
    x, y = np.asarray(F_TOL_values, float), np.asarray(TOFL_values, float)
    alpha, beta = np.polyfit(x, y, 1)
    residuals = y - (alpha * x + beta)
    r2 = 1 - np.sum(residuals ** 2) / np.sum((y - y.mean()) ** 2)
    sigma = np.sqrt(np.sum(residuals ** 2) / (len(x) - 2))
    return alpha, beta, r2, sigma


def C_L_max_from_V2(mass, V2, S, rho=RHO_0):
    """C_L,max reconstruit depuis V2 = 1.13 V_stall - (5.18)."""
    V_stall = V2 / K_VS1G_MIN
    return 2 * mass * G0 / (rho * V_stall ** 2 * S)


###############################################################################
################## PARTIE A2 / B7 - Vent (3.2.2.1, 5.5.5) #####################
###############################################################################

def wind_components(u, v, runway_heading_deg):
    """Composantes vent de face / travers pour un cap de piste ψ (° depuis le nord, horaire).

    u : vent vers l'est (m/s), v : vent vers le nord (m/s).
    headwind  = -(u sin ψ + v cos ψ)  (> 0 : vent de face)
    crosswind =   u cos ψ - v sin ψ   (> 0 : vent venant de la gauche)
    (cf. remarque en tête de fichier sur (3.3) / (5.49) / (5.50))
    """
    psi = np.radians(runway_heading_deg)
    headwind = -(u * np.sin(psi) + v * np.cos(psi))
    crosswind = u * np.cos(psi) - v * np.sin(psi)
    return headwind, crosswind


def optimal_runway_heading(u_hist, v_hist, candidate_headings):
    """Cap retenu pour une piste : celui qui maximise le vent de face moyen historique
    (1980-2010), puis figé pour les scénarios futurs (3.2.2.1)."""
    means = [np.mean(wind_components(u_hist, v_hist, h)[0]) for h in candidate_headings]
    return candidate_headings[int(np.argmax(means))]


def wind_factor(V_LOF, headwind):
    """TOFL_vent / TOFL_sans_vent = ((V_LOF - V_hw) / V_LOF)² - (5.48), (5.52).

    La vitesse air de décollage est fixe, c'est la vitesse sol (donc l'énergie
    cinétique à fournir) qui change : V_air = V_sol + V_hw (5.47).
    """
    return ((V_LOF - headwind) / V_LOF) ** 2


def lift_off_speed_scaled(V_LOF_ref, mass, mass_ref, rho, rho_ref=RHO_0):
    """V_LOF = V_LOF,ref · sqrt(W/W_ref) · sqrt(ρ_SL/ρ) - (5.51)."""
    return V_LOF_ref * math.sqrt(mass / mass_ref) * math.sqrt(rho_ref / rho)


###############################################################################
################## PARTIE B8 / B9 - Sensibilités et BFL #######################
###############################################################################

def dTOFL_dT(ac: Aircraft, F_TOL, T_kelvin, delta_T_isa, F_to):
    """Sensibilité analytique de la TOFL à la température (m/°C).

    flat-rating (5.20) : α F_TOL / T
    derate      (5.22) : α F_TOL (1/T + k_derate / F_total)   (k par moteur ramené au total)
    Le signe '-' de la thèse vient de la dérivée par rapport à ρ ; ici la TOFL
    augmente avec T, on renvoie donc une valeur positive.
    """
    s = 1 / T_kelvin
    if delta_T_isa > ac.T_flat:
        s += ac.k_derate_to / F_to
    return ac.alpha * F_TOL * s


def certified_take_off_length(tol_aeo, tol_oei_bfl):
    """TOL = max(1.15 TOL_AEO, TOL_OEI,BFL) - (5.4)."""
    return max(TOL_AEO_FACTOR * tol_aeo, tol_oei_bfl)


###############################################################################
################## PARTIE B10 - Modèle complet (Fig. 5.3) #####################
###############################################################################

@dataclass
class TakeOffResult:
    TOFL: float # take-off field length incl. wind - m (inf if infeasible)
    TOFL_no_wind: float
    F_TOL: float # Magic Line parameter - s²
    rho: float
    delta_T_isa: float
    regime: str # "flat-rating" | "derate" | "S2-limited"
    K_vs1g: float
    C_L_TO: float
    V_LOF: float # lift-off airspeed - m/s
    gamma_s2: float
    F_to: float # take-off thrust per engine - N
    F_climb: float
    s2_status: str
    feasible: bool


def take_off_performance(mass, T_celsius, h=0.0, headwind=0.0, ac: Aircraft = B738,
                         thrust_factor=1.0, s2_thrust="takeoff", alt_correction="none"):
    """Modèle Magic Line complet pour une condition (masse kg, T °C, altitude m, vent m/s).

    s2_thrust : poussée utilisée pour le 2e segment. "takeoff" = configuration
                validée (6.2.2), "climb" = formulation du chap. 5.
    thrust_factor : < 1 pour un décollage flex (poussée réduite).
    """
    # 1. Atmosphere
    T_K = T_celsius + KELVIN
    dT = delta_isa(h, T_celsius)
    rho = density(h, T_K)

    # 2. Thrust regime + altitude correction + floor
    F_to = thrust_factor * engine_thrust(ac, dT, h, "takeoff", alt_correction)
    F_climb = thrust_factor * engine_thrust(ac, dT, h, s2_thrust, alt_correction)

    # 3. Second segment iteration
    s2 = solve_second_segment(ac, mass, F_climb)
    feasible = s2.status in ("not-binding", "converged")

    # 4. Magic Line
    F_TOL = magic_line_parameter(ac, mass, rho, s2.C_L_TO, F_to)
    tofl0 = take_off_field_length(F_TOL, ac.alpha, ac.beta)

    # 5. Wind
    V_LOF = lift_off_speed(ac, mass, rho, s2.C_L_TO)
    tofl = tofl0 * wind_factor(V_LOF, headwind)

    regime = "S2-limited" if s2.status == "converged" else thrust_regime(ac, dT)
    return TakeOffResult(
        TOFL=tofl if feasible else math.inf, TOFL_no_wind=tofl0, F_TOL=F_TOL, rho=rho,
        delta_T_isa=dT, regime=regime, K_vs1g=s2.K_vs1g, C_L_TO=s2.C_L_TO, V_LOF=V_LOF,
        gamma_s2=s2.gamma_s2, F_to=F_to, F_climb=F_climb, s2_status=s2.status,
        feasible=feasible)


###############################################################################
################## PARTIE A3 / A4 - Données climat (3.5) ######################
###############################################################################

def daily_aggregates(T2m_hourly, u10_hourly, v10_hourly):
    """Agrégation journalière des champs horaires ERA5 - (3.5)-(3.7).

    Entrées : tableaux (n_jours, 24). Sorties : T_max, ū, v̄ par jour.
    """
    return (np.max(T2m_hourly, axis=1), np.mean(u10_hourly, axis=1), np.mean(v10_hourly, axis=1))


def select_grid_point(lat_grid, lon_grid, land_fraction, lat, lon,
                      threshold=0.5, search_radius=4):
    """Sélection automatique du point de grille d'un aéroport (Fig. 3.3).

    lat_grid, lon_grid : coordonnées 1D ; land_fraction : tableau (n_lat, n_lon) dans [0, 1].
    Retourne (i_lat, i_lon, flag) avec flag ∈ {"nearest", "land-optimised", "quality-flag"}.
    """
    lon_diff = (np.asarray(lon_grid) - lon + 180) % 360 - 180
    i0 = int(np.argmin(np.abs(np.asarray(lat_grid) - lat)))
    j0 = int(np.argmin(np.abs(lon_diff)))
    if land_fraction[i0, j0] >= threshold:
        return i0, j0, "nearest"

    n_lat, n_lon = land_fraction.shape
    best, best_frac = None, -1.0
    for i in range(max(0, i0 - search_radius), min(n_lat, i0 + search_radius + 1)):
        for dj in range(-search_radius, search_radius + 1):
            j = (j0 + dj) % n_lon
            if land_fraction[i, j] > best_frac:
                best, best_frac = (i, j), land_fraction[i, j]
    if best_frac >= threshold:
        return best[0], best[1], "land-optimised"
    return i0, j0, "quality-flag"


###############################################################################
################## PARTIE A5 - Correction de biais CDF-t (3.6) ################
###############################################################################

def _ecdf(sample, x):
    s = np.sort(sample)
    return np.searchsorted(s, x, side="right") / len(s)


def _quantile(sample, p):
    return np.quantile(sample, np.clip(p, 0, 1))


def quantile_mapping(obs_hist, mod_hist, mod_values):
    """Quantile mapping simple T(x) = F_o,hist⁻¹(F_m,hist(x)) - (3.8)."""
    return _quantile(obs_hist, _ecdf(mod_hist, mod_values))


def cdft(obs_hist, mod_hist, mod_fut, n_points=1000):
    """CDF-transform (Michelangeli et al., 2009) - (3.9).

    On construit la CDF observée future :
        F_o,fut(x) = F_o,hist( F_m,hist⁻¹( F_m,fut(x) ) )
    puis on corrige chaque valeur future par quantile mapping :
        x_corr = F_o,fut⁻¹( F_m,fut(x) )
    ce qui conserve le signal de changement climatique du modèle.
    """
    obs_hist, mod_hist, mod_fut = (np.asarray(a, float) for a in (obs_hist, mod_hist, mod_fut))
    # common support, widened by the mean shift so future extremes are representable
    shift = mod_fut.mean() - mod_hist.mean()
    lo = min(obs_hist.min(), mod_hist.min(), mod_fut.min()) - abs(shift)
    hi = max(obs_hist.max(), mod_hist.max(), mod_fut.max()) + abs(shift)
    x = np.linspace(lo, hi, n_points)

    F_o_fut = _ecdf(obs_hist, _quantile(mod_hist, _ecdf(mod_fut, x)))
    F_o_fut = np.maximum.accumulate(F_o_fut)

    p = _ecdf(mod_fut, mod_fut)
    # invert F_o,fut on the grid
    return np.interp(p, F_o_fut, x, left=x[0], right=x[-1])


def cdft_seasonal(obs_hist, mod_hist, mod_fut, doy_obs, doy_hist, doy_fut, window=31):
    """CDF-t par fenêtres de 31 jours (calibration saisonnière, 3.6.2.2).

    doy_* : jour de l'année (1-366) associé à chaque valeur.
    """
    out = np.empty_like(np.asarray(mod_fut, float))
    for start in range(1, 367, window):
        sel = lambda d: (np.asarray(d) >= start) & (np.asarray(d) < start + window)
        m_o, m_h, m_f = sel(doy_obs), sel(doy_hist), sel(doy_fut)
        if m_f.any():
            out[m_f] = cdft(np.asarray(obs_hist)[m_o], np.asarray(mod_hist)[m_h],
                            np.asarray(mod_fut)[m_f])
    return out


def validation_stats(reference, values):
    """Statistiques de validation de la correction (Tab. 3.3)."""
    reference, values = np.asarray(reference), np.asarray(values)
    return {
        "mean": values.mean(), "std": values.std(),
        "p95": np.percentile(values, 95), "p5": np.percentile(values, 5),
        "rmse": np.sqrt(np.mean((values - reference) ** 2)),
        "mbe": np.mean(values - reference),
        "r": np.corrcoef(reference, values)[0, 1],
    }


###############################################################################
################## PARTIE A6 / A7 - Ensemble et seuil (3.3.4, 4.1.1) ##########
###############################################################################

def ensemble_mean(results_by_model):
    """Moyenne 'un modèle, une voix' - (3.4).

    results_by_model : {modèle: [membre_1, membre_2, ...]} (scalaires ou tableaux)
    X_ens = 1/N_models Σ_i ( 1/N_members,i Σ_j X_ij )
    """
    return np.mean([np.mean(np.asarray(members, float), axis=0)
                    for members in results_by_model.values()], axis=0)


def ensemble_weights(results_by_model):
    """Poids par membre (1 / (N_models · N_members,i)) pour statistiques pondérées (percentiles...)."""
    n_models = len(results_by_model)
    return {model: [1 / (n_models * len(members))] * len(members)
            for model, members in results_by_model.items()}


def thermal_threshold(h):
    """Seuil thermique opérationnel T_lim = T_ISA(h) + 35 °C, en °C - (4.1)."""
    return temperature_isa(h) - KELVIN + 35.0


def exceedance_days(T_max_celsius, h):
    """Nombre de jours où T_max dépasse T_lim."""
    return int(np.sum(np.asarray(T_max_celsius) > thermal_threshold(h)))


# Percentiles "extrême annuel" et "extrême décennal" (4.1.2)
P_ANNUAL_EXTREME = 100 * (1 - 1 / 365.25) # 99.726
P_DECADAL_EXTREME = 100 * (1 - 1 / 3652.5) # 99.9726


###############################################################################
################## PARTIE C - Vulnérabilité des aéroports (chap. 7) ###########
###############################################################################

def is_inoperable(result: TakeOffResult, runway_length):
    """Jour inopérable : TOFL > piste disponible ou γ_S2 < minimum (7.1.2)."""
    return (not result.feasible) or result.TOFL > runway_length


def inoperable_days(T_max_celsius, u, v, runway_length, runway_heading, h,
                    mass=75000, ac: Aircraft = B738, **kwargs):
    """Compte les jours inopérables d'une piste sur une série journalière."""
    count = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore") # non-convergence = infeasible day, already counted
        for T, uu, vv in zip(T_max_celsius, u, v):
            hw, _ = wind_components(uu, vv, runway_heading)
            r = take_off_performance(mass, T, h, hw, ac, **kwargs)
            count += is_inoperable(r, runway_length)
    return count


def is_operational_failure(inoperable_days_per_year):
    """Défaillance opérationnelle : 365 jours inopérables / an (7.1.2)."""
    return inoperable_days_per_year >= 365


def aggregate_runways(values_by_runway, runway_lengths, method="best"):
    """Agrégation multi-pistes (7.1.1) : 'best' = piste la plus longue,
    'worst' = piste la plus courte, 'mean' = moyenne des pistes (7.1.3.1)."""
    values = np.asarray(values_by_runway, float)
    if method == "best":
        return values[int(np.argmax(runway_lengths))]
    if method == "worst":
        return values[int(np.argmin(runway_lengths))]
    if method == "mean":
        return values.mean(axis=0)
    raise ValueError("method must be 'best', 'worst' or 'mean'")


def flex_capability(mass, T_celsius, h, headwind, runway_length, ac: Aircraft = B738,
                    max_reduction=FLEX_MAX_REDUCTION, step=0.005, **kwargs):
    """Réduction de poussée flex maximale (%) admissible ce jour-là (7.2.4).

    Interprétation : plus grande réduction r ∈ [0, max_reduction] telle que la
    TOFL à poussée (1-r) tienne dans la piste et que le 2e segment soit respecté.
    Retourne 0 si le flex n'est pas possible (jour de "flex loss").
    """
    best = 0.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for r in np.arange(step, max_reduction + 1e-9, step):
            res = take_off_performance(mass, T_celsius, h, headwind, ac, thrust_factor=1 - r, **kwargs)
            if is_inoperable(res, runway_length):
                break
            best = r
    return 100 * best


def flex_metrics(capabilities_percent):
    """Métriques flex (7.2.4.2) sur une série journalière de capacités (%).

    availability (%) = part des jours où le flex est possible
    capability (%)   = réduction moyenne quand le flex est possible
    effective (%)    = availability × capability / 100
    """
    c = np.asarray(capabilities_percent, float)
    available = c > 0
    availability = 100 * available.mean()
    capability = c[available].mean() if available.any() else 0.0
    return {"availability": availability, "capability": capability,
            "effective": availability * capability / 100,
            "flex_loss_days": int((~available).sum())}


def flex_impact_scores(baseline, future, days_per_year=365):
    """Scores d'impact (7.2.4.2) entre deux périodes (dicts issus de flex_metrics).

    composite = 0.7·perte de disponibilité + 0.3·perte de capacité
    economic  = jours perdus + 0.5·dégradation de capacité
    """
    availability_loss = baseline["availability"] - future["availability"]
    capability_loss = baseline["capability"] - future["capability"]
    days_lost = availability_loss / 100 * days_per_year
    return {"composite": 0.7 * availability_loss + 0.3 * capability_loss,
            "economic": days_lost + 0.5 * capability_loss}


###############################################################################
################## Démonstration ##############################################
###############################################################################

if __name__ == "__main__":
    print("=== B737-800, TOFL (m) vs masse et écart ISA, niveau de la mer, vent nul ===")
    temps_isa = [0, 15, 25, 35]
    print("masse (t) | " + " | ".join(f"ISA+{d:<2d}" for d in temps_isa))
    for mass in range(66000, 80000, 2000):
        row = []
        for d in temps_isa:
            r = take_off_performance(mass, 15 + d)
            row.append(f"{r.TOFL:6.0f}" if r.feasible else "  inf ")
        print(f"   {mass / 1000:4.0f}   | " + " | ".join(row))

    print("\n=== Détail à 75 t, Delhi (237 m), 45 °C, 5 m/s de vent de face ===")
    r = take_off_performance(75000, 45.0, h=237, headwind=5.0)
    for k, v in r.__dict__.items():
        print(f"  {k:12s} = {v:.4g}" if isinstance(v, float) else f"  {k:12s} = {v}")
    print(f"  dTOFL/dT    = {dTOFL_dT(B738, r.F_TOL, 45 + KELVIN, r.delta_T_isa, r.F_to):.1f} m/°C")
    print(f"  T_lim       = {thermal_threshold(237):.1f} °C")
    print(f"  flex        = {flex_capability(75000, 45.0, 237, 5.0, 4430):.1f} % de réduction")

    print("\n=== Volets 1 / 5 / 15 à 75 t, ISA+25 ===")
    for ac in (B738_FLAPS_1, B738_FLAPS_5, B738_FLAPS_15):
        for h in (0, 1000, 2000):
            r = take_off_performance(75000, temperature_isa(h) - KELVIN + 25, h, ac=ac)
            print(f"  {ac.name:18s} h={h:4d} m : TOFL={r.TOFL:7.0f} m, K_VS1g={r.K_vs1g:.3f}, "
                  f"{r.regime}, S2={r.s2_status}")

    print("\n=== Roulage : solution exacte (5.9) vs accélération constante (5.13) ===")
    rho = density(0, T0)
    F = 2 * B738.F_to_base
    V = lift_off_speed(B738, 75000, rho, take_off_lift_coefficient(B738))
    C_L_ground = 0.8 # ground-roll attitude C_L (illustrative)
    print(f"  V_LOF={V:.1f} m/s, exact={ground_roll_exact(B738, 75000, rho, F, C_L_ground, V):.0f} m, "
          f"approx={ground_roll_constant_accel(B738, 75000, rho, F, C_L_ground, V):.0f} m")

    print("\n=== CDF-t sur données synthétiques ===")
    rng = np.random.default_rng(0)
    obs = rng.normal(30, 5, 5000)
    mod_h = rng.normal(32, 7, 5000)
    mod_f = rng.normal(35, 7, 5000)
    corr = cdft(obs, mod_h, mod_f)
    print(f"  obs={obs.mean():.2f}, mod_hist={mod_h.mean():.2f}, mod_fut={mod_f.mean():.2f}"
          f" -> corrigé={corr.mean():.2f} (attendu ≈ 33, σ ≈ 5 : {corr.std():.2f})")
