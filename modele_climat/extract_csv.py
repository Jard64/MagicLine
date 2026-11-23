"""
Chargement des CSV produits par extract_climate.py dans un DataFrame pandas.

Objectif : séries temporelles (journalières ou mensuelles) de température
maximale, pression et masse volumique, pour plusieurs aéroports, scénarios
et modèles climatiques, dans un seul tableau facile à filtrer.

Un fichier CSV = un modèle. Le nom du modèle est lu dans le nom du fichier :
    climat_aeroports_[day_|Amon_]AAAA-AAAA_<MODELE>.csv
(ou dans une colonne 'modele' si le CSV en contient une).

Tableau obtenu (format « long », une ligne par aéroport/scénario/modèle/date) :
    modele, scenario, aeroport, pas ('jour' ou 'mois'),
    date_str : date telle qu'écrite dans le CSV (AAAA-MM-JJ ou AAAA-MM),
    date     : datetime pandas (NaT pour les dates impossibles des calendriers
               de 360 jours, ex. 30 février ; la ligne est gardée),
    annee, mois, jour : entiers (jour vide pour les données mensuelles),
    tasmax_C, psl_hPa, ps_hPa, rho_kgm3 : grandeurs présentes dans le CSV,
    lat, lon, altitude_m : coordonnées de l'aéroport (airports_data.py).

Usage :
    from extract_csv import charger_donnees, filtrer
    df = charger_donnees()                                   # tous les CSV de Donnees CMIP/CSV/
    cdg = filtrer(df, aeroports='CDG', scenarios='ssp585', debut='2050', fin='2059')
    cdg.groupby('modele')['tasmax_C'].max()

À voir : autres facteurs limitants (vent fort, tempêtes...) si on les ajoute
dans extract_climate.py.
"""

import re
from pathlib import Path

import pandas as pd

import sys

# airports_data.py et les CSV restent dans MagicLine/Donnees CMIP/
DOSSIER_CMIP = Path(__file__).resolve().parent.parent / 'Donnees CMIP'
sys.path.insert(0, str(DOSSIER_CMIP))
from CMIP.airports_data import AIRPORTS

DOSSIER_CSV = DOSSIER_CMIP / 'CSV'
MOTIF = 'climat_aeroports_*.csv'

# climat_aeroports_day_2026-2100_CNRM-CM6-1.csv (préfixe de table facultatif)
NOM_FICHIER = re.compile(r'climat_aeroports_(?:(?P<table>[A-Za-z]+)_)?\d{4}-\d{4}_(?P<modele>.+)\.csv$')

COLONNES_ID = ['modele', 'scenario', 'aeroport', 'pas', 'date_str', 'date', 'annee', 'mois', 'jour']


def _modele_depuis_nom(chemin):
    m = NOM_FICHIER.match(chemin.name)
    return m.group('modele') if m else chemin.stem


def charger_csv(chemin):
    """Lit un CSV d'extract_climate.py et renvoie un DataFrame normalisé."""
    chemin = Path(chemin)
    df = pd.read_csv(chemin, dtype={'aeroport': str, 'scenario': str})

    # Anciens fichiers : colonne 'mois' (AAAA-MM) au lieu de 'date'
    if 'date' not in df.columns:
        if 'mois' not in df.columns:
            raise ValueError(f"{chemin.name} : ni colonne 'date' ni colonne 'mois'")
        df = df.rename(columns={'mois': 'date'})
    df = df.rename(columns={'date': 'date_str'})
    df['date_str'] = df['date_str'].astype(str)

    if 'modele' not in df.columns:
        df['modele'] = _modele_depuis_nom(chemin)

    # Découpage texte de la date : fonctionne aussi pour le 30 février
    morceaux = df['date_str'].str.split('-', expand=True)
    df['annee'] = morceaux[0].astype(int)
    df['mois'] = morceaux[1].astype(int)
    journalier = morceaux.shape[1] > 2
    df['jour'] = morceaux[2].astype('Int64') if journalier else pd.array([pd.NA] * len(df), dtype='Int64')
    df['pas'] = 'jour' if journalier else 'mois'
    df['date'] = pd.to_datetime(df['date_str'], format='%Y-%m-%d' if journalier else '%Y-%m',
                                errors='coerce')

    # Coordonnées et altitude de l'aéroport
    infos = pd.DataFrame.from_dict(AIRPORTS, orient='index')[['lat', 'lon', 'altitude_m']]
    df = df.join(infos, on='aeroport')

    grandeurs = [c for c in df.columns if c not in COLONNES_ID + ['lat', 'lon', 'altitude_m']]
    return df[COLONNES_ID + grandeurs + ['lat', 'lon', 'altitude_m']]


def charger_donnees(dossier=DOSSIER_CSV, motif=MOTIF, pas='jour'):
    """Charge et empile tous les CSV du dossier (un par modèle et par pas de temps).

    pas : 'jour' (défaut) ou 'mois' pour ne garder qu'un type de données,
          None pour tout garder. Attention avec None : si un même modèle existe
          en journalier et en mensuel, les deux sont empilés et un max() ou un
          mean() sans grouper par 'pas' mélange les deux.
    """
    fichiers = sorted(Path(dossier).glob(motif))
    if not fichiers:
        raise FileNotFoundError(f'Aucun fichier {motif} dans {dossier}')

    df = pd.concat([charger_csv(f) for f in fichiers], ignore_index=True)
    # Grandeurs climatiques avant les coordonnées, même si les fichiers diffèrent
    coords = ['lat', 'lon', 'altitude_m']
    df = df[[c for c in df.columns if c not in coords] + coords]
    if pas is not None:
        df = df[df['pas'] == pas]

    for col in ['modele', 'scenario', 'aeroport', 'pas']:
        df[col] = df[col].astype('category')
    return df.sort_values(['modele', 'scenario', 'aeroport', 'date_str'], ignore_index=True)


def _liste(x):
    return [x] if isinstance(x, str) else list(x)


def filtrer(df, aeroports=None, scenarios=None, modeles=None, debut=None, fin=None):
    """Sélection par aéroport(s), scénario(s), modèle(s) et période.

    aeroports / scenarios / modeles : une chaîne ou une liste (None = tout).
    debut / fin : bornes incluses, sous forme 'AAAA', 'AAAA-MM' ou 'AAAA-MM-JJ'
                  (ou entier pour une année). fin='2059' garde toute l'année 2059.
    """
    masque = pd.Series(True, index=df.index)
    if aeroports is not None:
        masque &= df['aeroport'].isin(_liste(aeroports))
    if scenarios is not None:
        masque &= df['scenario'].isin(_liste(scenarios))
    if modeles is not None:
        masque &= df['modele'].isin(_liste(modeles))
    # Comparaison sur le texte ISO : marche aussi pour les dates de 360 jours
    if debut is not None:
        debut = str(debut)
        masque &= df['date_str'].str[:len(debut)] >= debut
    if fin is not None:
        fin = str(fin)
        masque &= df['date_str'].str[:len(fin)] <= fin
    return df[masque]


if __name__ == '__main__':
    df = charger_donnees()
    print(f'{len(df)} lignes')
    print('Modèles   :', list(df['modele'].cat.categories))
    print('Scénarios :', list(df['scenario'].cat.categories))
    print('Aéroports :', list(df['aeroport'].cat.categories))
    print('Pas       :', list(df['pas'].cat.categories))
    print(df.head())

    sel = filtrer(df, aeroports='CDG', debut=2090, fin=2100)
    print('\nCDG 2090-2100, tasmax maximale par modèle et scénario :')
    print(sel.groupby(['modele', 'scenario'], observed=True)['tasmax_C'].max())
