# Avions du modèle Magic Line : organisation et sources

Consulté le 2 novembre 2026.

## 1. Fichiers du dossier

| Fichier | Rôle |
|---------|------|
| `catalogue.csv` | Catalogue d'avions : données brutes sourcées, une ligne par avion × moteur |
| `import_catalogue.py` | Remplit ou met à jour le catalogue depuis OpenAP, ICAO EEDB et EUROCONTROL |
| `avions.py` | Construit les objets `Aircraft` à partir du catalogue (méthode `direct` ou `echelle`) |
| `flotte.py` | Étude d'une flotte : TOFL, début de limitation 2e segment, température limite, figures |
| `etude_b738.py`, `ETUDE_B737-800.md` | Étude indépendante du B737-800 et comparaison avec la thèse |
| `figures/` | Figures générées |

## 2. Ajouter des avions

```bash
python import_catalogue.py B739 E190 A332        # types OpenAP, moteur par défaut
python import_catalogue.py A20N:PW1127G-JM        # moteur imposé
python flotte.py A320 B737 --altitude 1600 --piste 3500 --masse 0.95
```

Types disponibles dans OpenAP (38) : A19N, A20N, A21N, A318, A319, A320, A321, A332, A333,
A343, A359, A388, B37M, B38M, B39M, B3XM, B734, B737, B738, B739, B744, B748, B752, B763,
B772, B773, B77W, B788, B789, C550, CRJ9, E145, E170, E190, E195, E75L, GLF6.
Ceux qui n'ont pas de polaire reprennent celle d'un type proche (fichier `_synonym.csv`
d'OpenAP, signalé dans la colonne `notes`).

Pour **forcer une valeur connue** (donnée constructeur), ajouter au CSV une colonne portant
le nom du champ `Aircraft` (`C_L_max`, `C_D0`, `K`, `T_flat`, `alpha`, `beta`, ...) : elle
remplace la valeur calculée. La colonne `magic_line` accepte `twin`, `unified`, `quad`,
`b738` ou `alpha;beta`.

## 3. Sources

| # | Source | Ce qu'on en tire | Lien |
|---|--------|------------------|------|
| [1] | Salles, S. (2025), *Vulnerability of aviation to climate change*, thèse | B737-800 de référence (5.5.1), méthode (5.18), droites Magic Line (5.19), rapports de poussée | – |
| [2] | OpenAP, TU Delft (J. Sun), `aircraft/<code>.yml` | S, envergure, MTOW, OEW, moteurs, montage | https://github.com/junzis/openap/tree/master/openap/data/aircraft |
| [3] | OpenAP, `dragpolar/<code>.yml` et `_synonym.csv` | C_D0 et K lisses, géométrie des volets | https://github.com/junzis/openap/tree/master/openap/data/dragpolar |
| [4] | OpenAP, `drag.py` (`Drag.nonclean`) | Formules volets (McCormick 1994), train (Mair & Birdsall 1996), effet des volets sur K (Obert 2009) | https://github.com/junzis/openap/blob/master/openap/drag.py |
| [5] | ICAO Aircraft Engine Emissions Databank, via OpenAP `engines.csv` | Poussée certifiée au décollage (`max_thrust`), taux de dilution (`bpr`) | https://github.com/junzis/openap/blob/master/openap/data/engine/engines.csv · https://www.easa.europa.eu/en/domains/environment/icao-aircraft-engine-emissions-databank |
| [6] | EUROCONTROL Aircraft Performance Database | V2 (IAS), distance de décollage, masse associée | https://learningzone.eurocontrol.int/ilp/customs/ATCPFDB/details.aspx?ICAO=A320 (remplacer le code) |
| [7] | JCAB, TADS No. 778 (LEAP-1A) | Flat-rating décollage du LEAP-1A : 30 °C | https://asims.cab.mlit.go.jp/fsdb/a_katashiki.nsf/8344a61f244404e6492574eb003898d6/6204c93856eaded3492584860025d5ef/%24FILE/TADS_No.778_%28LEAP-1A%29.pdf |
| [8] | Aircraft Commerce n° 145 (2023), article maintenance | Diamètres de soufflante CFM56-5B (68.3 in), CFM56-7B (61 in), LEAP-1A (78 in), LEAP-1B (69.4 in) | https://aircraft-commerce.com/wp-content/uploads/aircraft-commerce-docs/General%20Articles/2023/145_MTCE_A.pdf |
| [9] | Torenbeek, E. (1982), *Synthesis of Subsonic Airplane Design*, Delft University Press | Formule semi-empirique de longueur de piste équilibrée (contrôle indépendant) | – |
| [10] | Raymer, D. (2018), *Aircraft Design: A Conceptual Approach*, AIAA | Traînée de moulinet d'un moteur en panne, D/q ≈ 0.3 × aire de la soufflante (ordre de grandeur) | – |

Le diamètre de soufflante du PW1100G (81 in) est une valeur constructeur couramment citée,
non vérifiée sur une source primaire. Pour les autres moteurs (CF34, Trent), le diamètre
n'est pas renseigné et une traînée de moulinet par défaut (ΔC_D0 = 0.005) est utilisée.

## 4. Construction des paramètres

| Paramètre `Aircraft` | Méthode `direct` (défaut) | Méthode `echelle` | Confiance |
|----------------------|---------------------------|-------------------|-----------|
| `S`, `OEW`, `MTOW` | OpenAP [2] | idem | Bonne |
| `F_to_base` | ICAO EEDB [5] | idem | Bonne (valeur certifiée) |
| `C_L_max` | (5.18) : 2 m g / (ρ0 S (V2/1.13)²), m et V2 EUROCONTROL [6] | idem | Faible à moyenne (V2 arrondis) |
| `C_D0` | 2e segment : lisse + volets + moteur en panne [3][4][10] | C_D0 thèse × rapport OpenAP (avion / B737-800) | Moyenne / reprend la thèse |
| `K` | K lisse corrigé des volets [3][4] | K thèse × rapport OpenAP | Moyenne |
| `F_climb_base` | F_to × 112/117 [1] | idem | Hypothèse |
| `k_derate_to`, `k_derate_climb` | F × 0.77 %/°C (TO) et 0.76 %/°C (montée) [1] | idem | Hypothèse, sensible (voir étude) |
| `T_flat` | ISA+15 [1], confirmé pour le LEAP-1A [7] | idem | Hypothèse sauf LEAP-1A |
| `mu_r` | 0.02 [1] | idem | Bonne (piste sèche) |
| `alpha`, `beta` | droite de la colonne `magic_line`, par défaut bimoteur (32.44, −347.40) [1] | idem | Voir ci-dessous |

Seul le produit S·C_L,max entre dans V_LOF et F_TOL. Comme C_L,max est reconstruit avec le
même S, le choix de la surface de référence n'a pas d'effet sur la TOFL.

## 5. Limites connues

- **V2 EUROCONTROL.** Valeurs indicatives (« should not be used operationally »), arrondies
  (145 kt pour presque tous les monocouloirs, quelle que soit la masse), sans conditions
  indiquées. Le C_L,max reconstruit est la donnée la plus fragile. Exemple : le B787-8 sort à
  C_L,max = 1.72 et à une TOFL irréaliste (4 800 m à la MTOW).
- **Droite Magic Line.** La droite bimoteur générique (σ = 185 m sur 29 avions) n'est calée sur
  aucun type. `calibrate_beta(ac, masse, tofl_ref)` (dans `avions.py`) recale β sur une TOFL
  constructeur dont les conditions sont connues. Les références à utiliser sont les abaques
  « take-off weight / field length » des documents Airbus *Aircraft Characteristics – Airport
  and Maintenance Planning* et Boeing *Airplane Characteristics for Airport Planning* :
  https://aircraft.airbus.com/en/customer-care/fleet-wide-care/airport-operations-and-aircraft-characteristics/aircraft-characteristics
- **Sources consultées non exploitées.** Fiches de certification EASA (liens incorrects ou PDF
  illisibles), documents Boeing d'aéroport (HTTP 404), sites agrégateurs (valeurs
  contradictoires, sans conditions).
