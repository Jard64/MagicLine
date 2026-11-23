"""
Extraction des projections climatiques CMIP6 au-dessus d'une liste d'aéroports,
de l'année en cours jusqu'en 2100.

D'après le tutoriel "Importation of data from the Google Cloud CMIP6 Public Data".
Les données sont lues directement dans le cloud de Google (accès anonyme).

Grandeurs extraites :
    - tasmax : température maximale près de la surface (°C)
    - psl    : pression ramenée au niveau de la mer (hPa)
    - ps     : pression au sol à l'altitude de l'aéroport, reconstituée à partir de psl (hPa)
    - rho    : masse volumique de l'air en surface aux heures chaudes (kg/m³)

Seules tasmax, psl et huss sont téléchargées. Ces trois variables existent dans
la table Amon (mensuelle) comme dans la table day (journalière), donc le script
fonctionne avec l'une ou l'autre (paramètre TABLE).

Pression au sol : on refait en sens inverse la réduction au niveau de la mer,
avec l'altitude réelle de l'aéroport (airports_data.py) :
    ps = psl * exp(-g * h / (Rd * Tm))
où h est l'altitude de l'aéroport et Tm la température virtuelle moyenne de la
couche d'air entre le niveau de la mer et l'aéroport, estimée à partir de
tasmax avec un gradient de 6,5 K/km : Tm = Tv + 0.0065 * h / 2.

Masse volumique : loi des gaz parfaits pour l'air humide,
    rho = ps / (Rd * Tv)   avec   Tv = tasmax * (1 + 0.608 * huss)
Si huss n'est pas disponible, le calcul se fait pour de l'air sec (écart de
l'ordre de 1 %).

Installation :
    pip install xarray zarr gcsfs dask pandas matplotlib

Sorties :
    - un fichier CSV avec les valeurs par aéroport et par scénario
    - un graphique par aéroport avec l'évolution des trois grandeurs
"""

import os
import sys
from datetime import date

import numpy as np
import pandas as pd
import xarray as xr
from matplotlib import pyplot as plt

from airports_data import AIRPORTS

# ---------------------------------------------------------------------------
# Paramètres
# ---------------------------------------------------------------------------
MODEL = 'CNRM-CM6-1'
MEMBER = 'r1i1p1f2'
SCENARIOS = ['ssp245', 'ssp585']   # scénario intermédiaire et scénario fort

# 'Amon' = valeurs mensuelles (tasmax = moyenne des maxima journaliers du mois)
# 'day'  = valeurs journalières : environ 30 fois plus de données à télécharger
TABLE = 'Amon'

# Codes des aéroports à traiter (voir airports_data.py).
# Pour les 20 aéroports : AEROPORTS = list(AIRPORTS)
AEROPORTS = ['CDG', 'LHR', 'AMS', 'MAD', 'DXB']

START, END = str(date.today().year), '2100'
AFFICHER = False   # True pour ouvrir chaque graphique à l'écran en plus de l'enregistrer

DOSSIER_CSV = 'Donnees CMIP/CSV'
DOSSIER_GRAPHES = 'Donnees CMIP/Graphes'

# Variables à télécharger : tasmax et psl sont tracées, huss sert au calcul
# de la température virtuelle (pression au sol et masse volumique).
VARIABLES = ['tasmax', 'psl', 'huss']

RD = 287.05       # constante spécifique de l'air sec, J kg-1 K-1
G = 9.80665       # accélération de la pesanteur, m s-2
GRADIENT = 0.0065 # décroissance de la température avec l'altitude, K/m

JOURNALIER = TABLE == 'day'
PAS = 'journalières' if JOURNALIER else 'mensuelles'
FENETRE = 365 if JOURNALIER else 12          # moyenne glissante sur un an
LONGUEUR_DATE = 10 if JOURNALIER else 7      # AAAA-MM-JJ ou AAAA-MM

CATALOG_URL = 'https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv'
OUT_CSV = f'climat_aeroports_{TABLE}_{START}-{END}_{MODEL}.csv'
OUT_PNG = 'climat_{code}_' + f'{TABLE}_{START}-{END}_{MODEL}.png'

# Grandeurs tracées : colonne du tableau, titre, unité
GRANDEURS = [
    ('tasmax_C', 'Température maximale près de la surface', '°C'),
    ('psl_hPa', 'Pression au niveau de la mer', 'hPa'),
    ('rho_kgm3', "Masse volumique de l'air en surface (heures chaudes)", 'kg/m³'),
]


def find_store(catalog, scenario, variable):
    """Renvoie l'adresse zarr du jeu de données demandé, ou None s'il n'existe pas."""
    sel = catalog.query(
        "activity_id == 'ScenarioMIP' "
        f"& source_id == '{MODEL}' & table_id == '{TABLE}' "
        f"& variable_id == '{variable}' & experiment_id == '{scenario}' "
        f"& member_id == '{MEMBER}'"
    )
    if sel.empty:
        return None
    # Si plusieurs versions existent, on garde la plus récente
    return sel.sort_values('version').zstore.values[-1]


def extract_points(zstore, variable, premier_passage):
    """Ouvre le jeu de données une seule fois et extrait d'un coup le point de
    grille le plus proche de chaque aéroport, sur la période voulue.
    Renvoie une série pandas indexée par (aéroport, date)."""
    ds = xr.open_zarr(zstore, consolidated=True, storage_options={'token': 'anon'})
    lats = xr.DataArray([AIRPORTS[c]['lat'] for c in AEROPORTS], dims='aeroport')
    lons = xr.DataArray([AIRPORTS[c]['lon'] % 360 for c in AEROPORTS], dims='aeroport')  # 0 à 360
    da = (
        ds[variable]
        .sel(lat=lats, lon=lons, method='nearest')
        .sel(time=slice(START, END))
    )
    if premier_passage:
        for code, la, lo in zip(AEROPORTS, da.lat.values, da.lon.values):
            print(f'    {code} : point de grille lat {la:.2f}, lon {lo:.2f}')
    da = da.load()                                        # téléchargement ici seulement
    # Dates en texte (AAAA-MM ou AAAA-MM-JJ) : fonctionne aussi avec les
    # calendriers particuliers (365 jours, 360 jours) utilisés par certains modèles.
    dates = [str(t)[:LONGUEUR_DATE] for t in da.time.values]
    valeurs = da.transpose('aeroport', 'time').values
    index = pd.MultiIndex.from_product([AEROPORTS, dates], names=['aeroport', 'date'])
    return pd.Series(valeurs.ravel(), index=index, name=variable)


def extract_scenario(catalog, scenario):
    """Télécharge toutes les variables d'un scénario et calcule les grandeurs finales."""
    brut = {}
    for var in VARIABLES:
        zstore = find_store(catalog, scenario, var)
        if zstore is None:
            print(f'  {var} : introuvable dans le catalogue, ignorée.')
            continue
        print(f'  {var} : {zstore}')
        brut[var] = extract_points(zstore, var, premier_passage=not brut)

    if not brut:
        return None
    df = pd.DataFrame(brut)

    out = pd.DataFrame(index=df.index)
    if 'tasmax' in df:
        out['tasmax_C'] = df['tasmax'] - 273.15
    if 'psl' in df:
        out['psl_hPa'] = df['psl'] / 100

    if {'psl', 'tasmax'} <= set(df):
        if 'huss' in df:
            tv = df['tasmax'] * (1 + 0.608 * df['huss'])
        else:
            print("  huss absente : calcul fait pour de l'air sec.")
            tv = df['tasmax']
        # Altitude de l'aéroport pour chaque ligne du tableau
        h = df.index.get_level_values('aeroport').map(
            lambda c: AIRPORTS[c]['altitude_m']).to_numpy(dtype=float)
        tv_couche = tv + GRADIENT * h / 2
        ps = df['psl'] * np.exp(-G * h / (RD * tv_couche))
        out['ps_hPa'] = ps / 100
        out['rho_kgm3'] = ps / (RD * tv)
    else:
        print('  psl ou tasmax absente : pression au sol et masse volumique non calculées.')

    out.insert(0, 'scenario', scenario)
    return out.reset_index()


def trace(resultats, code):
    """Graphique d'un aéroport, un panneau par grandeur : valeurs brutes
    en trait fin, moyenne glissante sur un an en trait épais."""
    data = resultats[resultats['aeroport'] == code]
    presentes = [g for g in GRANDEURS if g[0] in data.columns]
    fig, axes = plt.subplots(len(presentes), 1, figsize=(13, 3.6 * len(presentes)),
                             sharex=True, squeeze=False)
    couleurs = plt.rcParams['axes.prop_cycle'].by_key()['color']
    fmt = '%Y-%m-%d' if JOURNALIER else '%Y-%m'

    for ax, (col, titre, unite) in zip(axes[:, 0], presentes):
        for i, (scenario, df) in enumerate(data.groupby('scenario', sort=False)):
            df = df.dropna(subset=[col])
            # errors='coerce' : les dates impossibles des calendriers de 360 jours
            # (30 février...) ne sont pas tracées, mais restent dans le CSV
            x = pd.to_datetime(df['date'], format=fmt, errors='coerce')
            ok = x.notna().to_numpy()
            c = couleurs[i % len(couleurs)]
            ax.plot(x[ok], df[col].to_numpy()[ok], color=c, lw=0.5, alpha=0.3)
            lisse = df[col].rolling(FENETRE, center=True).mean().to_numpy()
            ax.plot(x[ok], lisse[ok], color=c, lw=2,
                    label=f'{scenario} (moyenne glissante sur un an)')
        ax.set_title(titre)
        ax.set_ylabel(unite)
        ax.grid(alpha=0.3)
        ax.legend(loc='upper left', fontsize=9)

    info = AIRPORTS[code]
    fig.suptitle(f"{info['ville']} ({code}, {info['altitude_m']} m), {START}-{END}, "
                 f'modèle {MODEL}, valeurs {PAS}', fontsize=13)
    fig.tight_layout()
    chemin = os.path.join(DOSSIER_GRAPHES, OUT_PNG.format(code=code))
    fig.savefig(chemin, dpi=150)
    print(f'  {chemin}')
    if AFFICHER:
        plt.show()
    plt.close(fig)


def resume(resultats):
    """Compare la première et la dernière décennie de la période, par aéroport."""
    debut = (int(START), int(START) + 9)
    fin = (int(END) - 9, int(END))
    annee = resultats['date'].str[:4].astype(int)
    d1 = resultats[(annee >= debut[0]) & (annee <= debut[1])]
    d2 = resultats[(annee >= fin[0]) & (annee <= fin[1])]
    cols = [g[0] for g in GRANDEURS if g[0] in resultats]
    m1 = d1.groupby(['aeroport', 'scenario'], sort=False)[cols].mean()
    m2 = d2.groupby(['aeroport', 'scenario'], sort=False)[cols].mean()

    print(f'\nMoyennes {debut[0]}-{debut[1]} puis {fin[0]}-{fin[1]} :')
    for (code, scenario) in m1.index:
        print(f'  {code} {scenario}')
        for col, titre, unite in GRANDEURS:
            if col not in cols:
                continue
            a, b = m1.loc[(code, scenario), col], m2.loc[(code, scenario), col]
            prec = 3 if unite == 'kg/m³' else 2
            print(f'    {titre:<52} {a:.{prec}f} -> {b:.{prec}f} {unite} ({b - a:+.{prec}f})')


def main():
    inconnus = [c for c in AEROPORTS if c not in AIRPORTS]
    if inconnus:
        raise SystemExit(f'Codes absents de airports_data.py : {", ".join(inconnus)}')
    sans_altitude = [c for c in AEROPORTS if 'altitude_m' not in AIRPORTS[c]]
    if sans_altitude:
        raise SystemExit(f'Altitude manquante dans airports_data.py : {", ".join(sans_altitude)}')

    os.makedirs(DOSSIER_CSV, exist_ok=True)
    os.makedirs(DOSSIER_GRAPHES, exist_ok=True)

    print('Lecture du catalogue CMIP6...')
    catalog = pd.read_csv(CATALOG_URL)

    morceaux = []
    for scenario in SCENARIOS:
        print(f'\nScénario {scenario}')
        df = extract_scenario(catalog, scenario)
        if df is not None:
            morceaux.append(df)

    if not morceaux:
        raise SystemExit('Aucune donnée trouvée : change de modèle ou de membre.')

    resultats = pd.concat(morceaux, ignore_index=True)
    resultats = resultats[['aeroport', 'scenario', 'date']
                          + [c for c in resultats.columns
                             if c not in ('aeroport', 'scenario', 'date')]]
    chemin_csv = os.path.join(DOSSIER_CSV, OUT_CSV)
    resultats.to_csv(chemin_csv, index=False, float_format='%.4f')
    print(f'\nDonnées enregistrées dans {chemin_csv} ({len(resultats)} lignes)')

    resume(resultats)

    print('\nGraphiques :')
    for code in AEROPORTS:
        trace(resultats, code)


if __name__ == '__main__':
    main()
    # gcsfs/fsspec (accès au cloud Google) laisse tourner des fils d'exécution
    # réseau en arrière-plan qui peuvent empêcher Python de se fermer, surtout
    # sous Windows. À ce stade, le CSV et les graphiques sont déjà écrits et
    # fermés : on quitte directement sans attendre ces fils.
    print('\nTerminé.')
    sys.stdout.flush()
    sys.stderr.flush()
    if 'IPython' not in sys.modules:   # ne pas fermer la console Spyder ou Jupyter
        os._exit(0)