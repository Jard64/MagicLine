# Sources des paramètres avions (`avions.py`)

Ce fichier donne l'origine de chaque paramètre des avions ajoutés au modèle Magic Line
(`MelvinxClaudine.py`), la façon dont il a été obtenu, et le niveau de confiance.
Consulté le 2 novembre 2026.

## 1. Sources utilisées

| # | Source | Ce qu'on en tire | Lien |
|---|--------|------------------|------|
| [1] | Salles, S. (2025), *Vulnerability of aviation to climate change*, thèse, méthode Magic Line | Paramètres B737-800 de référence (5.5.1), méthode (5.18), corrélation bimoteur (5.19) | (thèse, non en ligne dans le dépôt) |
| [2] | OpenAP, Open Aircraft Performance Model, TU Delft (J. Sun), fichiers `aircraft/<code>.yml` | Surface alaire, envergure, MTOW, OEW, motorisations | https://github.com/junzis/openap/tree/master/openap/data/aircraft |
| [3] | OpenAP, fichiers `dragpolar/<code>.yml` | Polaire lisse (C_D0, K), géométrie volets (λ_f, c_f/c, S_f/S) | https://github.com/junzis/openap/tree/master/openap/data/dragpolar |
| [4] | OpenAP, `drag.py` (`Drag.nonclean`) | Formules d'incrément de traînée volets / train, effet des volets sur K | https://github.com/junzis/openap/blob/master/openap/drag.py |
| [5] | ICAO Aircraft Engine Emissions Databank, repris dans OpenAP `engines.csv` (colonne `max_thrust` = poussée certifiée au décollage) | Poussée de décollage par moteur | https://github.com/junzis/openap/blob/master/openap/data/engine/engines.csv · https://www.easa.europa.eu/en/domains/environment/icao-aircraft-engine-emissions-databank |
| [6] | EUROCONTROL Aircraft Performance Database | V2 (IAS), distance de décollage, masse associée | https://learningzone.eurocontrol.int/ilp/customs/ATCPFDB/ (pages `details.aspx?ICAO=A319`, `A320`, `A20N`, `A321`, `A21N`, `B38M`, `B738`) |
| [7] | JCAB, TADS No. 778 (LEAP-1A) | Température de flat-rating au décollage du LEAP-1A : 86 °F (30 °C) | https://asims.cab.mlit.go.jp/fsdb/a_katashiki.nsf/8344a61f244404e6492574eb003898d6/6204c93856eaded3492584860025d5ef/%24FILE/TADS_No.778_%28LEAP-1A%29.pdf |

Références citées par OpenAP pour les formules de [4] : McCormick (1994), *Aerodynamics,
Aeronautics and Flight Mechanics*, p. 109 (traînée des volets) ; Mair & Birdsall (1996),
*Aircraft Performance*, éq. 6.1 (traînée du train) ; Obert (2009), *Aerodynamic Design of
Transport Aircraft*, fig. 27.39 (effet des volets sur le facteur d'Oswald).

## 2. Données brutes retenues

### Géométrie, masses, polaire lisse : OpenAP [2], [3]

| Code | Avion | S (m²) | Envergure (m) | MTOW (kg) | OEW (kg) | C_D0 lisse | K lisse | c_f/c | S_f/S |
|------|-------|-------:|--------------:|----------:|---------:|-----------:|--------:|------:|------:|
| B738 | B737-800 (contrôle) | 124.6 | 34.32 | 79 000 | 41 400 | 0.019 | 0.042 | 0.150 | 0.150 |
| A319 | A319ceo | 124.0 | 35.80 | 75 500 | 40 800 | 0.020 | 0.039 | 0.176 | 0.170 |
| A320 | A320ceo | 124.0 | 35.80 | 78 000 | 42 600 | 0.018 | 0.039 | 0.176 | 0.170 |
| A20N | A320neo | 124.0 | 35.80 | 79 000 | 44 300 | 0.017 | 0.038 | 0.176 | 0.170 |
| A321 | A321ceo | 128.0 | 35.80 | 93 500 | 48 500 | 0.020 | 0.041 | 0.176 | 0.165 |
| A21N | A321neo | 128.0 | 35.80 | 97 000 | 50 000 | 0.017* | 0.038* | 0.176 | 0.170 |
| B38M | B737 MAX 8 | 124.6 | 34.32 | 82 000 | 45 000 | 0.020 | 0.042 | 0.150 | 0.150 |

\* OpenAP n'a pas de fichier `dragpolar/a21n.yml` : le fichier avion A321neo reprend la polaire A320neo (annotée `#a20n`).
λ_f = 0.900 pour tous les avions.

### Poussée de décollage certifiée : ICAO EEDB [5]

| Avion | Moteur | Entrée ICAO | Poussée (N) |
|-------|--------|-------------|------------:|
| B737-800 (contrôle) | CFM56-7B26 | 8CM051 | 116 990 |
| A319ceo | CFM56-5B6/P | 3CM028 | 104 530 |
| A320ceo | CFM56-5B4/P | 2CM014 (CFM56-5B4) | 117 900 |
| A320neo | LEAP-1A26 | 20CM089 (LEAP-1A26/26E1) | 120 600 |
| A320neo (variante) | PW1127G-JM | 18PW122 | 120 430 |
| A321ceo | CFM56-5B3/P | 3CM025 | 142 350 |
| A321neo | LEAP-1A33 | 20CM090 (LEAP-1A35A/33/33B2/32/30, entrée groupée) | 143 100 |
| A321neo (variante) | PW1133G-JM | 18PW126 | 147 280 |
| B737 MAX 8 | LEAP-1B27 | 20CM098 | 124 700 |

Moteurs par défaut : ceux d'OpenAP pour l'A320ceo (A320-214) et l'A320neo/A321neo
(LEAP-1A) ; CFM56-5B6 (A319-112) et CFM56-5B3 (A321-211) pour l'A319 et l'A321ceo, plutôt
que les IAE V2500 donnés par défaut dans OpenAP, pour rester sur des moteurs CFM comme le
B737-800 de la thèse.

### Données de décollage : EUROCONTROL APD [6]

| Code | Masse (kg) | V2 (kt IAS) | Distance de décollage (m) |
|------|-----------:|------------:|--------------------------:|
| B738 | 70 530 | 145 | 2 300 |
| A319 | 64 000 | 135 | 1 750 |
| A320 | 73 900 | 145 | 2 190 |
| A20N | 79 000 | 145 | 1 951 |
| A321 | 83 000 | 145 | 2 210 |
| A21N | 97 000 | 145 | 2 150 |
| B38M | 82 600 | 145 | 2 500 |

EUROCONTROL précise : *« All data presented is only indicative and should not be used
operationally. »* Les conditions (température, altitude, volets) ne sont pas indiquées.

## 3. Paramètres dérivés et méthode

| Paramètre `Aircraft` | Méthode | Confiance |
|----------------------|---------|-----------|
| `S`, `OEW`, `MTOW` | OpenAP [2], tels quels | Bonne |
| `F_to_base` | ICAO EEDB [5], tel quel | Bonne (valeur certifiée) |
| `F_climb_base` | `F_to_base × 112 000 / 117 000` (ratio du B737-800 de la thèse [1]) | Moyenne (hypothèse) |
| `k_derate_to`, `k_derate_climb` | `k_B738 × F_base / 117 000` : même pente relative (≈ 0.77 %/°C) que la thèse | Moyenne (hypothèse) |
| `T_flat` | 15 °C (ISA+15), comme la thèse ; confirmé pour le LEAP-1A (30 °C au niveau de la mer [7]) | Bonne pour LEAP-1A, hypothèse pour les autres |
| `C_L_max` | Méthode de la thèse (5.18) : `C_L,max = 2 m g / (ρ0 S (V2/1.13)²)` avec m et V2 d'EUROCONTROL [6] | Faible à moyenne (V2 arrondis à 135/145 kt) |
| `C_D0`, `K` | Similitude avec le B737-800 de la thèse : `X = X_B738,thèse × X_OpenAP(avion) / X_OpenAP(B738)`, avec X_OpenAP la polaire de décollage calculée par les formules de [4] (volets 5° pour les Boeing, 10° = CONF 1+F pour les Airbus, train sorti) | Moyenne |
| `mu_r` | 0.02, comme la thèse | Bonne (piste sèche) |
| `alpha`, `beta` | Corrélation bimoteur de la thèse `MAGIC_LINE_TWIN = (32.44, −347.40)` [1] | Voir § 4 |

Valeurs obtenues (sortie de `python avions.py`) :

| Avion | C_L,max | C_D0 | K | F_to (kN) | k_derate,TO (N/°C) |
|-------|--------:|-----:|--:|----------:|-------------------:|
| A319ceo (CFM56-5B6/P) | 2.188 | 0.0798 | 0.0334 | 104.5 | 804 |
| A320ceo (CFM56-5B4/P) | 2.190 | 0.0764 | 0.0334 | 117.9 | 907 |
| A320neo (LEAP-1A26) | 2.341 | 0.0746 | 0.0326 | 120.6 | 928 |
| A320neo (PW1127G-JM) | 2.341 | 0.0746 | 0.0326 | 120.4 | 926 |
| A321ceo (CFM56-5B3/P) | 2.382 | 0.0850 | 0.0351 | 142.3 | 1095 |
| A321neo (LEAP-1A33) | 2.784 | 0.0798 | 0.0326 | 143.1 | 1101 |
| A321neo (PW1133G-JM) | 2.784 | 0.0798 | 0.0326 | 147.3 | 1133 |
| B737 MAX 8 (LEAP-1B27) | 2.436 | 0.0812 | 0.0366 | 124.7 | 959 |

### Pourquoi la surface alaire importe peu

Seul le produit S·C_L,max intervient dans V_LOF et F_TOL. Comme C_L,max est reconstruit par
(5.18) avec le même S, prendre 124 m² (OpenAP) ou 122.6 m² (valeur souvent citée par Airbus
pour l'A320) donne la même TOFL.

## 4. Validation et limites

**Contrôle de la méthode sur le B737-800.** La même chaîne appliquée au B737-800 redonne
les valeurs de la thèse :
- C_L,max = 2.08 par (5.18) + EUROCONTROL, contre 2.10 dans la thèse ;
- poussée ICAO du CFM56-7B26 = 116.99 kN, contre 117 kN dans la thèse ;
- TOFL modèle à 70.5 t, ISA, niveau de la mer = 2 311 m, contre 2 300 m chez EUROCONTROL (+0.5 %).

**Comparaison aux distances EUROCONTROL (ISA, niveau de la mer, vent nul).**

| Avion | Masse (t) | TOFL modèle (m) | EUROCONTROL (m) | Écart |
|-------|----------:|----------------:|----------------:|------:|
| A319ceo | 64.0 | 2 132 | 1 750 | +21.8 % |
| A320ceo | 73.9 | 2 581 | 2 190 | +17.8 % |
| A320neo | 79.0 | 2 713 | 1 951 | +39.0 % |
| A321ceo | 83.0 | 2 377 | 2 210 | +7.5 % |
| A321neo | 97.0 | 2 819 | 2 150 | +31.1 % |
| B737 MAX 8 | 82.6 | 2 747 | 2 500 | +9.9 % |

Le modèle surestime la longueur de décollage des Airbus, surtout des neo. Causes probables :
1. **Corrélation générique.** La droite bimoteur de la thèse (σ = 185 m sur 29 avions) n'est
   pas calée sur chaque type ; le B737-800 a sa propre droite (30.34, −323).
2. **V2 EUROCONTROL arrondis.** Tous les avions sauf l'A319 ont V2 = 145 kt, quelle que soit la
   masse, ce qui rend le C_L,max reconstruit peu fiable (2.78 pour l'A321neo paraît élevé).
3. **Conditions EUROCONTROL inconnues.** On ne sait pas si la distance est donnée à la MTOW, à
   ISA, au niveau de la mer, ni avec quels volets.

**Recalage proposé.** `calibrate_beta(ac, masse, tofl_ref)` recale β (α gardé) sur une TOFL de
référence dont les conditions sont connues. Les meilleures références sont les abaques
« take-off weight / field length » (ISA et ISA+15, niveau de la mer) des documents Airbus
*Aircraft Characteristics – Airport and Maintenance Planning* (AC A319, A320, A321) :
https://aircraft.airbus.com/en/customer-care/fleet-wide-care/airport-operations-and-aircraft-characteristics/aircraft-characteristics
Ces abaques sont des graphiques vectoriels : leurs valeurs n'ont pas pu être extraites
automatiquement et doivent être lues à la main.

**Sources consultées mais non exploitées.**
- Fiches de certification EASA (TCDS E.067 CFM56-5, E.110 LEAP-1A) : les liens trouvés
  pointaient vers d'autres documents (Special Condition TOTHAT) ou n'étaient pas lisibles.
  La poussée certifiée vient donc de la base ICAO, qui reprend les valeurs certifiées.
- Documents Boeing *Airplane Characteristics for Airport Planning* (737 NG / 737 MAX) :
  liens morts (HTTP 404).
- Tableaux de caractéristiques sur des sites agrégateurs (Skybrary, aerocorner, etc.) :
  valeurs de distance de décollage contradictoires et sans conditions, donc écartés.
