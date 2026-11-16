"""
Extraction des projections climatiques CMIP6 (table Amon) au-dessus d'une liste
d'aéroports, de l'année en cours jusqu'en 2100.

D'après le tutoriel "Importation of data from the Google Cloud CMIP6 Public Data".
Les données sont lues directement dans le cloud de Google (accès anonyme).

Grandeurs extraites (moyennes mensuelles) :
    - tasmax : température maximale près de la surface, moyenne des maxima journaliers (°C)
    - psl    : pression ramenée au niveau de la mer (hPa)
    - rho    : masse volumique de l'air en surface aux heures chaudes (kg/m³)

CMIP6 ne fournit pas directement la masse volumique de l'air. Elle est calculée
avec la loi des gaz parfaits pour l'air humide :
    rho = ps / (Rd * Tv)   avec   Tv = tasmax * (1 + 0.608 * huss)
où ps est la pression en surface (et non psl), tasmax la température maximale
près de la surface et huss l'humidité spécifique. Si huss n'est pas disponible,
le calcul se fait pour de l'air sec (écart de l'ordre de 1 %).

Installation :
    pip install xarray zarr gcsfs dask pandas matplotlib

Sorties :
    - un fichier CSV avec les valeurs mensuelles par aéroport et par scénario
    - un graphique par aéroport avec l'évolution mensuelle des trois grandeurs
"""

import os
import sys
from datetime import date

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
TABLE = 'Amon'                     # mensuel

# Codes des aéroports à traiter (voir airports_data.py).
# Pour les 20 aéroports : AEROPORTS = list(AIRPORTS)
AEROPORTS = ['CDG', 'LHR', 'AMS', 'MAD', 'DXB']

START, END = str(date.today().year), '2100'
AFFICHER = False   # True pour ouvrir chaque graphique à l'écran en plus de l'enregistrer

# Variables à télécharger : tasmax et psl sont tracées telles quelles,
# ps et huss servent, avec tasmax, au calcul de la masse volumique.
VARIABLES = ['tasmax', 'psl', 'ps', 'huss']

RD = 287.05   # constante spécifique de l'air sec, J kg-1 K-1

CATALOG_URL = 'https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv'
OUT_CSV = f'climat_aeroports_{START}-{END}_{MODEL}.csv'
OUT_PNG = 'climat_{code}_' + f'{START}-{END}_{MODEL}.png'

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
    Renvoie une série pandas indexée par (aéroport, mois)."""
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
    # Mois au format AAAA-MM : fonctionne aussi avec les calendriers
    # particuliers (365 jours, 360 jours) utilisés par certains modèles.
    mois = [str(t)[:7] for t in da.time.values]
    valeurs = da.transpose('aeroport', 'time').values
    index = pd.MultiIndex.from_product([AEROPORTS, mois], names=['aeroport', 'mois'])
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
    if {'ps', 'tasmax'} <= set(df):
        if 'huss' in df:
            tv = df['tasmax'] * (1 + 0.608 * df['huss'])
        else:
            print("  huss absente : masse volumique calculée pour de l'air sec.")
            tv = df['tasmax']
        out['rho_kgm3'] = df['ps'] / (RD * tv)
    else:
        print('  ps ou tasmax absente : masse volumique non calculée.')

    out.insert(0, 'scenario', scenario)
    return out.reset_index()


def trace(resultats, code):
    """Graphique d'un aéroport, un panneau par grandeur : valeurs mensuelles
    en trait fin, moyenne glissante sur 12 mois en trait épais."""
    data = resultats[resultats['aeroport'] == code]
    presentes = [g for g in GRANDEURS if g[0] in data.columns]
    fig, axes = plt.subplots(len(presentes), 1, figsize=(13, 3.6 * len(presentes)),
                             sharex=True, squeeze=False)
    couleurs = plt.rcParams['axes.prop_cycle'].by_key()['color']

    for ax, (col, titre, unite) in zip(axes[:, 0], presentes):
        for i, (scenario, df) in enumerate(data.groupby('scenario', sort=False)):
            df = df.dropna(subset=[col])
            x = pd.to_datetime(df['mois'], format='%Y-%m')
            c = couleurs[i % len(couleurs)]
            ax.plot(x, df[col].values, color=c, lw=0.6, alpha=0.35)
            ax.plot(x, df[col].rolling(12, center=True).mean().values, color=c, lw=2,
                    label=f'{scenario} (moyenne glissante 12 mois)')
        ax.set_title(titre)
        ax.set_ylabel(unite)
        ax.grid(alpha=0.3)
        ax.legend(loc='upper left', fontsize=9)

    nom = AIRPORTS[code]['ville']
    fig.suptitle(f'{nom} ({code}), {START}-{END}, modèle {MODEL}, valeurs mensuelles',
                 fontsize=13)
    fig.tight_layout()
    chemin = "Donnees CMIP/Graphes/"+ OUT_PNG.format(code=code)
    fig.savefig(chemin, dpi=150)
    print(f'  {chemin}')
    if AFFICHER:
        plt.show()
    plt.close(fig)


def resume(resultats):
    """Compare la première et la dernière décennie de la période, par aéroport."""
    debut = (int(START), int(START) + 9)
    fin = (int(END) - 9, int(END))
    annee = resultats['mois'].str[:4].astype(int)
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
    resultats = resultats[['aeroport', 'scenario', 'mois']
                          + [c for c in resultats.columns
                             if c not in ('aeroport', 'scenario', 'mois')]]
    resultats.to_csv("Donnees CMIP/CSV/" + OUT_CSV, index=False, float_format='%.4f')
    print(f'\nDonnées enregistrées dans {OUT_CSV} ({len(resultats)} lignes)')

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