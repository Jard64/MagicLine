"""
Extraction des projections climatiques CMIP6 (table Amon) au-dessus d'un aéroport,
de l'année en cours jusqu'en 2100.

D'après le tutoriel "Importation of data from the Google Cloud CMIP6 Public Data".
Les données sont lues directement dans le cloud de Google (accès anonyme).

Grandeurs extraites (moyennes mensuelles) :
    - tasmax : température maximale près de la surface, moyenne des maxima journaliers (°C)
    - psl    : pression ramenée au niveau de la mer (hPa)
    - rho    : masse volumique de l'air en surface (kg/m³)

CMIP6 ne fournit pas directement la masse volumique de l'air. Elle est calculée
avec la loi des gaz parfaits pour l'air humide :
    rho = ps / (Rd * Tv)   avec   Tv = tas * (1 + 0.608 * huss)
où ps est la pression en surface (et non psl), tas la température moyenne près
de la surface et huss l'humidité spécifique. Si huss n'est pas disponible,
le calcul se fait pour de l'air sec (écart de l'ordre de 1 %).

Installation :
    pip install xarray zarr gcsfs dask pandas matplotlib

Sorties :
    - un fichier CSV avec les valeurs mensuelles par scénario
    - un graphique avec l'évolution mensuelle des trois grandeurs
"""

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
SCENARIOS = ['ssp245'] #, 'ssp585']   # scénario intermédiaire et scénario fort
TABLE = 'Amon'                     # mensuel

AIRPORT = 'CDG'
LAT, LON = AIRPORTS[AIRPORT]['lat'], AIRPORTS[AIRPORT]['lon']
START, END = str(date.today().year), '2100'

# Variables à télécharger : tasmax et psl sont tracées telles quelles,
# ps, tas et huss servent au calcul de la masse volumique.
VARIABLES = ['tasmax', 'psl', 'ps', 'tas', 'huss']

RD = 287.05   # constante spécifique de l'air sec, J kg-1 K-1

CATALOG_URL = 'https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv'
OUT_CSV = f'climat_{AIRPORT}_{START}-{END}_{MODEL}.csv'
OUT_PNG = f'climat_{AIRPORT}_{START}-{END}_{MODEL}.png'

# Grandeurs tracées : colonne du tableau, titre, unité
GRANDEURS = [
    ('tasmax_C', 'Température maximale près de la surface', '°C'),
    ('psl_hPa', 'Pression au niveau de la mer', 'hPa'),
    ('rho_kgm3', "Masse volumique de l'air en surface", 'kg/m³'),
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


def extract_point(zstore, variable):
    """Ouvre le jeu de données, garde le point de grille le plus proche de
    l'aéroport et la période voulue. Renvoie une série pandas indexée par mois."""
    ds = xr.open_zarr(zstore, consolidated=True, storage_options={'token': 'anon'})
    da = (
        ds[variable]
        .sel(lat=LAT, lon=LON % 360, method='nearest')   # longitudes de 0 à 360
        .sel(time=slice(START, END))
    )
    print(f'    point de grille : lat {float(da.lat):.2f}, lon {float(da.lon):.2f}')
    da = da.load()                                        # téléchargement ici seulement
    # Index au format AAAA-MM : fonctionne aussi avec les calendriers
    # particuliers (365 jours, 360 jours) utilisés par certains modèles.
    mois = [str(t)[:7] for t in da.time.values]
    return pd.Series(da.values, index=pd.Index(mois, name='mois'), name=variable)


def extract_scenario(catalog, scenario):
    """Télécharge toutes les variables d'un scénario et calcule les grandeurs finales."""
    brut = {}
    for var in VARIABLES:
        zstore = find_store(catalog, scenario, var)
        if zstore is None:
            print(f'  {var} : introuvable dans le catalogue, ignorée.')
            continue
        print(f'  {var} : {zstore}')
        brut[var] = extract_point(zstore, var)

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
            print('  huss absente : masse volumique calculée pour de l\'air sec.')
            tv = df['tasmax']
        out['rho_kgm3'] = df['ps'] / (RD * tv)
    else:
        print('  ps ou tasmax absente : masse volumique non calculée.')

    out.insert(0, 'scenario', scenario)
    return out


def trace(resultats):
    """Un graphique par grandeur : valeurs mensuelles en trait fin,
    moyenne glissante sur 12 mois en trait épais."""
    presentes = [g for g in GRANDEURS if g[0] in resultats.columns]
    fig, axes = plt.subplots(len(presentes), 1, figsize=(13, 3.6 * len(presentes)),
                             sharex=True, squeeze=False)
    couleurs = plt.rcParams['axes.prop_cycle'].by_key()['color']

    for ax, (col, titre, unite) in zip(axes[:, 0], presentes):
        for i, (scenario, df) in enumerate(resultats.groupby('scenario', sort=False)):
            serie = df[col].dropna()
            x = pd.to_datetime(serie.index, format='%Y-%m')
            c = couleurs[i % len(couleurs)]
            ax.plot(x, serie.values, color=c, lw=0.6, alpha=0.35)
            ax.plot(x, serie.rolling(12, center=True).mean().values, color=c, lw=2,
                    label=f'{scenario} (moyenne glissante 12 mois)')
        ax.set_title(titre)
        ax.set_ylabel(unite)
        ax.grid(alpha=0.3)
        ax.legend(loc='upper left', fontsize=9)

    nom = AIRPORTS[AIRPORT]['ville']
    fig.suptitle(f'{nom} ({AIRPORT}), {START}-{END}, modèle {MODEL}, valeurs mensuelles',
                 fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)
    print(f'Graphique enregistré dans {OUT_PNG}')
    plt.show()


def resume(resultats):
    """Compare la première et la dernière décennie de la période."""
    debut = (int(START), int(START) + 9)
    fin = (int(END) - 9, int(END))
    print(f'\nMoyennes {debut[0]}-{debut[1]} puis {fin[0]}-{fin[1]} :')
    annee = resultats.index.str[:4].astype(int)
    for scenario in resultats['scenario'].unique():
        print(f'  {scenario}')
        for col, titre, unite in GRANDEURS:
            if col not in resultats:
                continue
            s = resultats.loc[resultats['scenario'] == scenario, col]
            a = annee[resultats['scenario'] == scenario]
            m1 = s[(a >= debut[0]) & (a <= debut[1])].mean()
            m2 = s[(a >= fin[0]) & (a <= fin[1])].mean()
            prec = 3 if unite == 'kg/m³' else 2
            print(f'    {titre:<40} {m1:.{prec}f} -> {m2:.{prec}f} {unite} '
                  f'({m2 - m1:+.{prec}f})')


def main():
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

    resultats = pd.concat(morceaux)
    resultats.to_csv(OUT_CSV, float_format='%.4f')
    print(f'\nDonnées enregistrées dans {OUT_CSV} ({len(resultats)} lignes)')

    resume(resultats)
    trace(resultats)


if __name__ == '__main__':
    main()