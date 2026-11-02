r"""
Étude d'une flotte d'avions avec le modèle Magic Line.

Pour chaque avion du catalogue (ou une sélection) :
  - TOFL Magic Line en fonction de l'écart ISA, à une altitude et une masse données ;
  - écart ISA à partir duquel le 2e segment devient limitant ;
  - température maximale d'exploitation sur une piste de longueur donnée ;
  - TOFL estimée par une méthode indépendante (Torenbeek, longueur de piste
    équilibrée), pour contrôler la Magic Line ;
  - distance de décollage EUROCONTROL, pour mémoire.

Utilisation :
    python flotte.py                                  # tout le catalogue, niveau de la mer, piste 3000 m
    python flotte.py A320 B737 --altitude 1600 --piste 3500
    python flotte.py --methode echelle --masse 0.9    # 90 % de la MTOW
Les figures sont écrites dans figures/.
"""

import argparse
import math
import os
import warnings

import numpy as np

from avions import CATALOGUE, charger_catalogue, flotte
from MelvinxClaudine import (Aircraft, G0, KELVIN, RHO_0, K_VS1G_MIN, density, delta_isa,
                             engine_thrust, climb_gradient_s2, temperature_isa,
                             take_off_performance, is_inoperable)

HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.join(HERE, "figures")

H_SCREEN = 10.7 # hauteur de passage d'obstacle 35 ft - m

""" Palette catégorielle de référence (ordre fixe) et encres """

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


###############################################################################
################## Méthode indépendante : Torenbeek ###########################
###############################################################################

def tofl_torenbeek(ac: Aircraft, mass, T_celsius, h=0.0, bpr=5.0, alt_correction="none"):
    """Longueur de piste équilibrée (BFL), formule semi-empirique de Torenbeek (1982).

    BFL = 0.863/(1 + 2.3 Δγ2) · (W/S / (ρ g C_L2) + h_35) · (1/(T̄/W − μ') + 2.7) + 655/√σ

      C_L2 = C_L,max / 1.13²        (V2 = 1.13 V_S1g ≈ 1.2 V_S de l'ancienne réglementation)
      Δγ2  = γ2 − γ2,min            pente OEI à V2 avec la poussée décollage
      T̄    = 0.75 · N F · (5+λ)/(4+λ)  poussée moyenne au roulage, λ = taux de dilution
      μ'   = 0.02 + 0.01 C_L,max     frottement / freinage équivalent
    Indépendante de la Magic Line : pas de régression sur F_TOL, perte de poussée avec la
    vitesse prise en compte par λ. Retourne inf si le 2e segment n'est pas tenu.
    """
    dT = delta_isa(h, T_celsius)
    rho = density(h, T_celsius + KELVIN)
    F = engine_thrust(ac, dT, h, "takeoff", alt_correction)
    W = mass * G0
    C_L2 = ac.C_L_max / K_VS1G_MIN ** 2
    d_gamma = climb_gradient_s2(ac, mass, F, C_L2) - ac.gamma_s2_min
    if d_gamma < 0:
        return math.inf
    T_mean = 0.75 * ac.n_engines * F * (5 + bpr) / (4 + bpr)
    mu = 0.02 + 0.01 * ac.C_L_max
    if T_mean / W <= mu:
        return math.inf
    return (0.863 / (1 + 2.3 * d_gamma) * (W / ac.S / (rho * G0 * C_L2) + H_SCREEN)
            * (1 / (T_mean / W - mu) + 2.7) + 655 / math.sqrt(rho / RHO_0))


###############################################################################
################## Grandeurs étudiées #########################################
###############################################################################

def tofl(ac, mass, delta_T_isa, h=0.0, **kwargs):
    """TOFL Magic Line (m) à l'écart ISA donné ; inf si infaisable."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return take_off_performance(mass, temperature_isa(h) - KELVIN + delta_T_isa, h,
                                    ac=ac, **kwargs).TOFL


def delta_isa_s2(ac, mass, h=0.0, dmax=60.0, step=0.5, **kwargs):
    """Plus petit écart ISA (°C) où le 2e segment devient limitant (ou infaisable) ; None sinon."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for d in np.arange(-20, dmax + 1e-9, step):
            r = take_off_performance(mass, temperature_isa(h) - KELVIN + d, h, ac=ac, **kwargs)
            if r.s2_status != "not-binding":
                return float(d)
    return None


def temperature_limite(ac, mass, runway_length, h=0.0, headwind=0.0, tmin=-30.0, tmax=65.0, **kwargs):
    """Température maximale (°C) pour laquelle le décollage tient dans la piste (bissection).

    Retourne tmin si l'avion ne décolle jamais, tmax s'il décolle toujours dans la plage.
    """
    def ok(T):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return not is_inoperable(take_off_performance(mass, T, h, headwind, ac, **kwargs),
                                     runway_length)
    if not ok(tmin):
        return tmin
    if ok(tmax):
        return tmax
    lo, hi = tmin, tmax
    while hi - lo > 0.1:
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return lo


def etude_flotte(avions, masse=1.0, h=0.0, piste=3000.0, delta_isa=(0, 15, 25, 35), catalogue=None,
                 **kwargs):
    """Tableau d'étude : une ligne par avion.

    masse : fraction de la MTOW (≤ 1.5) ou masse en kg.
    """
    catalogue = catalogue or charger_catalogue(CATALOGUE)
    rows = []
    for name, ac in avions.items():
        r = catalogue.get(name, {})
        m = ac.MTOW * masse if masse <= 1.5 else masse
        bpr = r.get("bpr") if isinstance(r.get("bpr"), float) else 5.0
        rows.append({
            "avion": name,
            "masse_kg": m,
            "tofl": {d: tofl(ac, m, d, h, **kwargs) for d in delta_isa},
            "torenbeek_isa": tofl_torenbeek(ac, m, temperature_isa(h) - KELVIN, h, bpr),
            "disa_s2": delta_isa_s2(ac, m, h, **kwargs),
            "T_lim": temperature_limite(ac, m, piste, h, **kwargs),
            "apd": (r.get("dist_TO_ref_m"), r.get("masse_ref_kg")),
        })
    return rows


def afficher(rows, h, piste, delta_isa=(0, 15, 25, 35)):
    print(f"Altitude {h:.0f} m, piste {piste:.0f} m (T_ISA = {temperature_isa(h) - KELVIN:.1f} °C)")
    head = (f"{'avion':28s} {'masse':>6s} " + " ".join(f"ISA+{d:<3d}" for d in delta_isa)
            + f" {'Toren.':>7s} {'S2 dès':>7s} {'T_lim':>6s}")
    print(head)
    print("-" * len(head))
    for r in rows:
        cells = " ".join(f"{v:7.0f}" if math.isfinite(v) else "    inf" for v in r["tofl"].values())
        tor = f"{r['torenbeek_isa']:7.0f}" if math.isfinite(r["torenbeek_isa"]) else "    inf"
        s2 = f"ISA+{r['disa_s2']:<3.0f}" if r["disa_s2"] is not None else "  jamais"
        print(f"{r['avion']:28s} {r['masse_kg'] / 1000:5.1f}t {cells} {tor} {s2:>7s} "
              f"{_label_tlim(r['T_lim'])}")
    print("TOFL en m (Magic Line) ; Toren. = BFL Torenbeek à ISA ; S2 dès = écart ISA où le 2e segment"
          " limite ; T_lim = température max d'exploitation sur la piste.")


###############################################################################
################## Figures ####################################################
###############################################################################

def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=8)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def tracer_tofl(avions, masse=1.0, h=0.0, piste=None, path=None, **kwargs):
    """TOFL en fonction de l'écart ISA. ≤ 8 avions : un graphique ; au-delà : petits multiples."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = np.arange(-10, 46, 1.0)
    curves = {}
    for name, ac in avions.items():
        m = ac.MTOW * masse if masse <= 1.5 else masse
        curves[name] = np.array([tofl(ac, m, x, h, **kwargs) for x in d])
    finite = np.concatenate([c[np.isfinite(c)] for c in curves.values()])
    ymax = 1.05 * max(finite.max(), piste or 0)

    n = len(curves)
    if n <= len(SERIES):
        fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
        _style(ax)
        for i, (name, c) in enumerate(curves.items()):
            ax.plot(d, c, color=SERIES[i], linewidth=2, label=name)
            last = np.where(np.isfinite(c))[0][-1]
            if n <= 4:
                ax.annotate(name, (d[last], c[last]), xytext=(4, 0), textcoords="offset points",
                            fontsize=8, color=INK, va="center")
        if piste:
            ax.axhline(piste, color=INK_2, linewidth=1, linestyle="--")
            ax.annotate(f"piste {piste:.0f} m", (d[0], piste), xytext=(2, 3),
                        textcoords="offset points", fontsize=8, color=INK_2)
        ax.set_ylim(0, ymax)
        ax.legend(frameon=False, fontsize=8, labelcolor=INK)
        ax.set_xlabel("Écart ISA (°C)", color=INK_2)
        ax.set_ylabel("TOFL (m)", color=INK_2)
    else:
        cols = 4
        rows = math.ceil(n / cols)
        fig, axes = plt.subplots(rows, cols, figsize=(3.2 * cols, 2.4 * rows), sharex=True, sharey=True,
                                 facecolor=SURFACE)
        for ax, (name, c) in zip(axes.flat, curves.items()):
            _style(ax)
            for other in curves.values():
                ax.plot(d, other, color=GRID, linewidth=1)
            ax.plot(d, c, color=SERIES[0], linewidth=2)
            if piste:
                ax.axhline(piste, color=INK_2, linewidth=0.8, linestyle="--")
            ax.set_title(name, fontsize=8, color=INK, loc="left")
            ax.set_ylim(0, ymax)
        for ax in list(axes.flat)[n:]:
            ax.set_visible(False)
        fig.supxlabel("Écart ISA (°C)", color=INK_2, fontsize=9)
        fig.supylabel("TOFL (m)", color=INK_2, fontsize=9)
    fig.suptitle(f"TOFL Magic Line, altitude {h:.0f} m, masse "
                 + (f"{masse:.0%} MTOW" if masse <= 1.5 else f"{masse / 1000:.0f} t"),
                 color=INK, fontsize=10, x=0.01, ha="left")
    fig.tight_layout()
    if path:
        fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def _label_tlim(T, tmin=-30.0, tmax=65.0):
    if T <= tmin:
        return "ne décolle pas"
    if T >= tmax:
        return f"> {tmax:.0f} °C"
    return f"{T:.0f} °C"


def tracer_temperature_limite(rows, h, piste, path, tmin=-30.0, tmax=65.0):
    """Points : température max d'exploitation de chaque avion sur la piste (pas de barres :
    une température n'a pas de zéro naturel)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = sorted(rows, key=lambda r: r["T_lim"])
    fig, ax = plt.subplots(figsize=(8, 0.35 * len(rows) + 1.2), facecolor=SURFACE)
    _style(ax)
    ax.grid(axis="y", visible=False)
    y = np.arange(len(rows))
    ok = [tmin < r["T_lim"] < tmax for r in rows]
    ax.scatter([r["T_lim"] for r, k in zip(rows, ok) if k], [yi for yi, k in zip(y, ok) if k],
               s=60, color=SERIES[0], zorder=3, edgecolors=SURFACE, linewidths=2)
    x_text = min([r["T_lim"] for r, k in zip(rows, ok) if k] or [0])
    for yi, r, k in zip(y, rows, ok):
        ax.annotate(_label_tlim(r["T_lim"], tmin, tmax), (r["T_lim"] if k else x_text, yi),
                    xytext=(7 if k else 0, 0), textcoords="offset points", fontsize=8,
                    color=INK_2, va="center")
    ax.set_yticks(y, [r["avion"] for r in rows], fontsize=8, color=INK)
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.axvline(temperature_isa(h) - KELVIN + 35, color=INK_2, linewidth=1, linestyle="--")
    ax.annotate("seuil thèse ISA+35", (temperature_isa(h) - KELVIN + 35, len(rows) - 0.5),
                xytext=(3, 0), textcoords="offset points", fontsize=8, color=INK_2)
    ax.set_xlabel("Température maximale d'exploitation (°C)", color=INK_2)
    ax.set_title(f"Piste {piste:.0f} m, altitude {h:.0f} m", color=INK, fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


###############################################################################
################## Ligne de commande ##########################################
###############################################################################

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Étude d'une flotte avec le modèle Magic Line")
    p.add_argument("noms", nargs="*", help="avions à étudier (recherche partielle), tous par défaut")
    p.add_argument("--methode", default="direct", choices=["direct", "echelle"])
    p.add_argument("--altitude", type=float, default=0.0, help="altitude terrain (m)")
    p.add_argument("--piste", type=float, default=3000.0, help="longueur de piste (m)")
    p.add_argument("--masse", type=float, default=1.0, help="fraction de MTOW (≤ 1.5) ou masse en kg")
    a = p.parse_args()

    avions = flotte(a.noms or None, methode=a.methode)
    rows = etude_flotte(avions, a.masse, a.altitude, a.piste)
    afficher(rows, a.altitude, a.piste)

    os.makedirs(FIGURES, exist_ok=True)
    tag = f"{a.methode}_h{a.altitude:.0f}_L{a.piste:.0f}"
    tracer_tofl(avions, a.masse, a.altitude, a.piste, os.path.join(FIGURES, f"flotte_tofl_{tag}.png"))
    tracer_temperature_limite(rows, a.altitude, a.piste, os.path.join(FIGURES, f"flotte_Tlim_{tag}.png"))
    print(f"Figures : {FIGURES}")
