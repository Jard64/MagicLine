r"""
Étude indépendante du B737-800 et comparaison avec la modélisation de la thèse.

Trois jeux de paramètres :
  "Thèse"            B738 de MelvinxClaudine.py (5.5.1), droite Magic Line B737-800
  "Direct"           paramètres reconstruits depuis les sources publiques (avions.py,
                     methode="direct"), même droite Magic Line B737-800
  "Direct + bimot."  idem, droite bimoteur générique de la thèse (celle de la flotte)
et une méthode de contrôle indépendante de la Magic Line : Torenbeek (flotte.py).

    python etude_b738.py      -> tableaux dans le terminal, figures dans figures/
"""

from dataclasses import replace
import math
import os
import warnings

import numpy as np

from avions import charger_catalogue, construire_avion
from flotte import (FIGURES, SERIES, INK, INK_2, SURFACE, _style, tofl, tofl_torenbeek,
                    delta_isa_s2)
from MelvinxClaudine import (B738, MAGIC_LINE_B738, KELVIN, K_VS1G_MIN, temperature_isa,
                             take_off_performance)

cat = charger_catalogue()
ROW = cat["B737-800 (CFM56-7B26)"]
BPR = ROW["bpr"]

THESE = B738
DIRECT = replace(construire_avion(ROW, "direct"), name="Direct", alpha=MAGIC_LINE_B738[0],
                 beta=MAGIC_LINE_B738[1])
DIRECT_TWIN = replace(construire_avion(ROW, "direct"), name="Direct + bimot.")


def ld(ac):
    C_L = ac.C_L_max / K_VS1G_MIN ** 2
    return C_L / (ac.C_D0 + ac.K * C_L ** 2)


def fmt(v, w=6):
    return f"{v:{w}.0f}" if math.isfinite(v) else " " * (w - 3) + "inf"


def table_parametres():
    print("## 1. Paramètres\n")
    print(f"{'paramètre':16s} {'thèse':>10s} {'direct':>10s} {'écart':>8s}")
    for f in ("S", "C_L_max", "C_D0", "K", "F_to_base", "F_climb_base", "T_flat",
              "k_derate_to", "OEW", "MTOW", "mu_r"):
        a, b = getattr(THESE, f), getattr(DIRECT, f)
        print(f"{f:16s} {a:10.4g} {b:10.4g} {100 * (b / a - 1):+7.1f}%")
    print(f"{'C_L,TO':16s} {THESE.C_L_max / K_VS1G_MIN ** 2:10.4g} {DIRECT.C_L_max / K_VS1G_MIN ** 2:10.4g}")
    print(f"{'L/D (C_L,TO)':16s} {ld(THESE):10.4g} {ld(DIRECT):10.4g} {100 * (ld(DIRECT) / ld(THESE) - 1):+7.1f}%")
    print()


def table_tofl():
    print("## 2. TOFL (m) au niveau de la mer, vent nul\n")
    cases = [("Thèse", lambda m, d: tofl(THESE, m, d)),
             ("Direct", lambda m, d: tofl(DIRECT, m, d)),
             ("Direct + bimot.", lambda m, d: tofl(DIRECT_TWIN, m, d)),
             ("Torenbeek (direct)", lambda m, d: tofl_torenbeek(DIRECT, m, 15 + d, 0, BPR)),
             ("Torenbeek (thèse)", lambda m, d: tofl_torenbeek(THESE, m, 15 + d, 0, BPR))]
    temps = (0, 15, 25, 35)
    for mass in (70530, 75000, 79000):
        print(f"masse {mass / 1000:.1f} t" + (" (masse EUROCONTROL, distance 2300 m)" if mass == 70530 else ""))
        print(f"  {'':20s} " + " ".join(f"ISA+{d:<2d}" for d in temps))
        for name, f in cases:
            print(f"  {name:20s} " + " ".join(fmt(f(mass, d)) for d in temps))
    print()


def table_s2():
    print("## 3. Écart ISA (°C) à partir duquel le 2e segment limite\n")
    alts = (0, 500, 1000, 1500, 2000, 2500)
    print(f"  {'':30s} " + " ".join(f"{h:>6d}" for h in alts) + "   (altitude m)")
    for mass in (75000, 79000):
        for s2 in ("takeoff", "climb"):
            for ac in (THESE, DIRECT):
                vals = [delta_isa_s2(ac, mass, h, s2_thrust=s2) for h in alts]
                print(f"  {ac.name[:8]:8s} {mass / 1000:.0f} t, S2 {s2:7s}       "
                      + " ".join(f"{v:6.1f}" if v is not None else "    -" for v in vals))
    print("  S2 'takeoff' = configuration validée de la thèse (poussée décollage), 'climb' = chap. 5\n")


def table_sensibilites():
    print("## 4. Sensibilités (thèse, 75 t, niveau de la mer)\n")
    m = 75000

    def run(ac, d):
        return tofl(ac, m, d)
    base35 = run(THESE, 35)
    print(f"  référence : TOFL(ISA+35) = {base35:.0f} m")
    for rel in (0.005, 0.01):
        ac = replace(THESE, k_derate_to=THESE.F_to_base * rel, k_derate_climb=THESE.F_climb_base * rel)
        print(f"  pente de derate {100 * rel:.1f} %/°C (thèse 0.77) : TOFL(ISA+35) = {fmt(run(ac, 35))} m")
    for tf in (10, 20):
        ac = replace(THESE, T_flat=tf)
        print(f"  T_flat = ISA+{tf} (thèse 15)        : TOFL(ISA+35) = {fmt(run(ac, 35))} m")
    for f in (0.95, 1.05):
        ac = replace(THESE, C_L_max=THESE.C_L_max * f)
        print(f"  C_L,max × {f:.2f}                   : TOFL(ISA+35) = {fmt(run(ac, 35))} m")
    print("  C_D0 -> premier écart ISA où S2 limite (79 t, niveau de la mer) :")
    for cd0 in (0.024, 0.04, 0.06, 0.078):
        ac = replace(THESE, C_D0=cd0)
        v = delta_isa_s2(ac, 79000, 0)
        print(f"     C_D0 = {cd0:.3f} (L/D = {ld(ac):5.2f}) : ISA+{v:.1f}" if v is not None
              else f"     C_D0 = {cd0:.3f} : jamais")
    print()


def figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(FIGURES, exist_ok=True)

    # Figure 1 : TOFL vs écart ISA à 75 t
    d = np.arange(-10, 46, 1.0)
    m = 75000
    series = [("Thèse (Magic Line B737-800)", [tofl(THESE, m, x) for x in d]),
              ("Direct (Magic Line B737-800)", [tofl(DIRECT, m, x) for x in d]),
              ("Direct (Magic Line bimoteur)", [tofl(DIRECT_TWIN, m, x) for x in d]),
              ("Torenbeek (paramètres directs)", [tofl_torenbeek(DIRECT, m, 15 + x, 0, BPR) for x in d])]
    fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
    _style(ax)
    for i, (name, y) in enumerate(series):
        ax.plot(d, y, color=SERIES[i], linewidth=2, label=name)
    ax.axvline(THESE.T_flat, color=INK_2, linewidth=0.8, linestyle=":")
    ax.annotate("fin du flat-rating", (THESE.T_flat, ax.get_ylim()[0]), xytext=(3, 6),
                textcoords="offset points", fontsize=8, color=INK_2)
    ax.set_xlabel("Écart ISA (°C)", color=INK_2)
    ax.set_ylabel("TOFL (m)", color=INK_2)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    ax.set_title("B737-800, 75 t, niveau de la mer, vent nul", color=INK, fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "b738_tofl_vs_isa.png"), dpi=150, facecolor=SURFACE)
    plt.close(fig)

    # Figure 2 : écart ISA où S2 devient limitant vs altitude
    alts = np.arange(0, 3001, 250)
    fig, ax = plt.subplots(figsize=(8, 5), facecolor=SURFACE)
    _style(ax)
    i = 0
    for ac, label in ((THESE, "Thèse (C_D0 = 0.078)"), (DIRECT, "Direct (C_D0 = 0.024)")):
        for mass, ls in ((79000, "-"), (75000, "--")):
            y = [delta_isa_s2(ac, mass, h) for h in alts]
            y = [v if v is not None else np.nan for v in y]
            ax.plot(alts, y, color=SERIES[i], linewidth=2, linestyle=ls, label=f"{label}, {mass / 1000:.0f} t")
        i += 1
    ax.axhline(35, color=INK_2, linewidth=0.8, linestyle=":")
    ax.annotate("seuil opérationnel ISA+35 (4.1)", (alts[-1], 35), xytext=(-4, 4), textcoords="offset points",
                fontsize=8, color=INK_2, ha="right")
    ax.set_xlabel("Altitude terrain (m)", color=INK_2)
    ax.set_ylabel("Écart ISA où le 2e segment limite (°C)", color=INK_2)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
    ax.set_title("B737-800 : début de la limitation 2e segment (poussée décollage)", color=INK,
                 fontsize=10, loc="left")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES, "b738_s2_vs_altitude.png"), dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"Figures : {FIGURES}")


if __name__ == "__main__":
    warnings.simplefilter("ignore")
    table_parametres()
    table_tofl()
    table_s2()
    table_sensibilites()
    figures()
