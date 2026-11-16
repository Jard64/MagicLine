"""
Extraction des projections climatiques CMIP6 pour Paris, de 2030 à 2060.

D'après le tutoriel "Importation of data from the Google Cloud CMIP6 Public Data".
Les données sont lues directement dans le cloud de Google (accès anonyme).

Installation :
    pip install xarray zarr gcsfs dask pandas matplotlib

Sorties :
    - un fichier CSV avec la température journalière (°C) par scénario
    - un graphique des moyennes annuelles
"""

import pandas as pd
import xarray as xr
from matplotlib import pyplot as plt

# ---------------------------------------------------------------------------
# Paramètres
# ---------------------------------------------------------------------------
MODEL = 'CNRM-CM6-1'
MEMBER = 'r1i1p1f2'
SCENARIOS = ['ssp245'] #, 'ssp585']   # scénario intermédiaire et scénario fort
VARIABLE = 'tas'                   # température de l'air près de la surface (K)
TABLE = 'Amon'                      # 'day' = journalier, 'Amon' = mensuel (plus léger)

LAT, LON = 48.85, 2.35             # Paris
START, END = '2030', '2060'

CATALOG_URL = 'https://storage.googleapis.com/cmip6/cmip6-zarr-consolidated-stores.csv'
OUT_CSV = f'{VARIABLE}_paris_{START}-{END}_{MODEL}.csv'
OUT_PNG = f'{VARIABLE}_paris_{START}-{END}_{MODEL}.png'


def find_store(catalog, scenario):
    """Renvoie l'adresse zarr du jeu de données demandé, ou None s'il n'existe pas."""
    sel = catalog.query(
        "activity_id == 'ScenarioMIP' "
        f"& source_id == '{MODEL}' & table_id == '{TABLE}' "
        f"& variable_id == '{VARIABLE}' & experiment_id == '{scenario}' "
        f"& member_id == '{MEMBER}'"
    )
    if sel.empty:
        return None
    # Si plusieurs versions existent, on garde la plus récente
    return sel.sort_values('version').zstore.values[-1]


def extract_point(zstore):
    """Ouvre le jeu de données, garde le point de grille le plus proche de Paris
    et la période voulue, puis convertit en °C."""
    ds = xr.open_zarr(zstore, consolidated=True, storage_options={'token': 'anon'})
    serie = (
        ds[VARIABLE]
        .sel(lat=LAT, lon=LON % 360, method='nearest')   # longitudes de 0 à 360
        .sel(time=slice(START, END))
    )
    print(f'  point de grille retenu : lat {float(serie.lat):.2f}, lon {float(serie.lon):.2f}')
    serie = serie.load()                                  # téléchargement ici seulement
    if VARIABLE in ('tas', 'tasmin', 'tasmax'):
        serie = serie - 273.15
    return serie


def main():
    print('Lecture du catalogue CMIP6...')
    catalog = pd.read_csv(CATALOG_URL)

    colonnes = {}
    series = {}
    for scenario in SCENARIOS:
        print(f'\nScénario {scenario}')
        zstore = find_store(catalog, scenario)
        if zstore is None:
            print('  introuvable dans le catalogue pour ce modèle/membre, ignoré.')
            continue
        print(f'  {zstore}')
        serie = extract_point(zstore)
        series[scenario] = serie
        # Les dates sont converties en texte pour gérer aussi les calendriers
        # particuliers (365 jours, 360 jours) utilisés par certains modèles.
        dates = [str(t)[:10] for t in serie.time.values]
        colonnes[scenario] = pd.Series(serie.values, index=dates)

    if not colonnes:
        raise SystemExit('Aucune donnée trouvée : change de modèle, de membre ou de TABLE.')

    table = pd.DataFrame(colonnes)
    table.index.name = 'date'
    table.to_csv(OUT_CSV, float_format='%.2f')
    print(f'\nDonnées enregistrées dans {OUT_CSV} ({len(table)} lignes)')

    # Moyennes annuelles
    print('\nMoyenne annuelle sur la période (°C) :')
    for scenario, serie in series.items():
        annuel = serie.groupby('time.year').mean()
        annuel.plot(label=scenario)
        print(f'  {scenario} : {float(annuel.mean()):.2f}')

    plt.title(f'Température moyenne annuelle à Paris, {START}-{END} ({MODEL})')
    plt.xlabel('Année')
    plt.ylabel('°C')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUT_PNG, dpi=150)
    print(f'Graphique enregistré dans {OUT_PNG}')
    plt.show()


if __name__ == '__main__':
    main()