"""
Les 20 aéroports les plus fréquentés du monde en 2025 (passagers),
d'après le classement définitif d'ACI World publié en juillet 2026.

Coordonnées approximatives (au centième de degré), largement suffisantes
pour choisir un point de grille CMIP6 (mailles d'environ 100 à 250 km).

altitude_m : altitude de référence de l'aéroport, en mètres au-dessus du niveau
de la mer (arrondie au mètre). Elle sert à calculer la pression au sol à partir
de la pression au niveau de la mer (psl).

pistes : liste des pistes en service (nom, longueur_m, cap_deg), de la plus
longue à la plus courte. Détails et source dans le tableau PISTES plus bas.

Usage dans le script CMIP6 :
    from airports_data import AIRPORTS
    lat, lon = AIRPORTS['CDG']['lat'], AIRPORTS['CDG']['lon']
    altitude = AIRPORTS['CDG']['altitude_m']

Usage avec le modèle (modele_climatique.py) :
    pistes = AIRPORTS['CDG']['pistes']
    longueurs = [p['longueur_m'] for p in pistes]      # pour aggregate_runways
    inoperable_days(..., runway_length=pistes[0]['longueur_m'],
                    runway_heading=pistes[0]['cap_deg'], ...)
"""

AIRPORTS = {
    'ATL': {'rang': 1,  'ville': 'Atlanta',           'pays': 'États-Unis',          'passagers_2025': 106_302_208, 'lat': 33.64, 'lon': -84.43,  'altitude_m':  313},
    'DXB': {'rang': 2,  'ville': 'Dubaï',             'pays': 'Émirats arabes unis', 'passagers_2025': 95_192_160,  'lat': 25.25, 'lon': 55.36,   'altitude_m':   19},
    'HND': {'rang': 3,  'ville': 'Tokyo Haneda',      'pays': 'Japon',               'passagers_2025': 91_679_814,  'lat': 35.55, 'lon': 139.78,  'altitude_m':    6},
    'DFW': {'rang': 4,  'ville': 'Dallas/Fort Worth', 'pays': 'États-Unis',          'passagers_2025': 85_660_127,  'lat': 32.90, 'lon': -97.04,  'altitude_m':  185},
    'PVG': {'rang': 5,  'ville': 'Shanghai Pudong',   'pays': 'Chine',               'passagers_2025': 84_994_548,  'lat': 31.14, 'lon': 121.81,  'altitude_m':    4},
    'ORD': {'rang': 6,  'ville': 'Chicago O\'Hare',   'pays': 'États-Unis',          'passagers_2025': 84_856_018,  'lat': 41.98, 'lon': -87.90,  'altitude_m':  205},
    'LHR': {'rang': 7,  'ville': 'Londres Heathrow',  'pays': 'Royaume-Uni',         'passagers_2025': 84_482_126,  'lat': 51.47, 'lon': -0.45,   'altitude_m':   25},
    'IST': {'rang': 8,  'ville': 'Istanbul',          'pays': 'Turquie',             'passagers_2025': 84_437_710,  'lat': 41.26, 'lon': 28.74,   'altitude_m':   99},
    'CAN': {'rang': 9,  'ville': 'Canton',            'pays': 'Chine',               'passagers_2025': 83_582_952,  'lat': 23.39, 'lon': 113.30,  'altitude_m':   15},
    'DEN': {'rang': 10, 'ville': 'Denver',            'pays': 'États-Unis',          'passagers_2025': 82_427_962,  'lat': 39.86, 'lon': -104.67, 'altitude_m': 1656},
    'DEL': {'rang': 11, 'ville': 'New Delhi',         'pays': 'Inde',                'passagers_2025': 78_148_081,  'lat': 28.56, 'lon': 77.10,   'altitude_m':  237},
    'ICN': {'rang': 12, 'ville': 'Séoul Incheon',     'pays': 'Corée du Sud',        'passagers_2025': 74_126_912,  'lat': 37.46, 'lon': 126.44,  'altitude_m':    7},
    'LAX': {'rang': 13, 'ville': 'Los Angeles',       'pays': 'États-Unis',          'passagers_2025': 73_709_594,  'lat': 33.94, 'lon': -118.41, 'altitude_m':   39},
    'CDG': {'rang': 14, 'ville': 'Paris-CDG',         'pays': 'France',              'passagers_2025': 72_029_407,  'lat': 49.01, 'lon': 2.55,    'altitude_m':  119},
    'PEK': {'rang': 15, 'ville': 'Pékin Capitale',    'pays': 'Chine',               'passagers_2025': 70_742_712,  'lat': 40.08, 'lon': 116.58,  'altitude_m':   35},
    'SIN': {'rang': 16, 'ville': 'Singapour Changi',  'pays': 'Singapour',           'passagers_2025': 69_982_000,  'lat': 1.36,  'lon': 103.99,  'altitude_m':    7},
    'AMS': {'rang': 17, 'ville': 'Amsterdam',         'pays': 'Pays-Bas',            'passagers_2025': 68_771_592,  'lat': 52.31, 'lon': 4.76,    'altitude_m':   -3},
    'MAD': {'rang': 18, 'ville': 'Madrid',            'pays': 'Espagne',             'passagers_2025': 68_118_754,  'lat': 40.47, 'lon': -3.56,   'altitude_m':  610},
    'SZX': {'rang': 19, 'ville': 'Shenzhen',          'pays': 'Chine',               'passagers_2025': 66_485_213,  'lat': 22.64, 'lon': 113.81,  'altitude_m':    4},
    'KUL': {'rang': 20, 'ville': 'Kuala Lumpur',      'pays': 'Malaisie',            'passagers_2025': 63_409_501,  'lat': 2.75,  'lon': 101.71,  'altitude_m':   21},
}

# ---------------------------------------------------------------------------
# Pistes de chaque aéroport
# ---------------------------------------------------------------------------
# Une entrée par piste physique (les deux sens de décollage), de la plus longue
# à la plus courte :
#   nom        : désignation des deux sens, ex. '08L/26R'
#   longueur_m : longueur physique de la piste (m)
#   cap_deg    : cap vrai (degrés depuis le nord géographique, sens horaire)
#                du sens de décollage cité en premier ; l'autre sens vaut
#                cap_deg + 180. C'est le ψ de la thèse pour le vent de face.
#
# Source : base OurAirports (domaine public, téléchargée le 23/11/2026),
# caps recalculés à partir des coordonnées des seuils. Pistes fermées et
# bandes en herbe exclues. Corrections et remarques en commentaire.
#
# Attention : c'est la longueur physique, pas la distance déclarée TORA de
# l'AIP (souvent identique, parfois plus courte d'un sens). Pour une étude
# fine d'un aéroport, vérifier dans son AIP.
PISTES = {
    'ATL': [
        {'nom': '09L/27R', 'longueur_m': 3776, 'cap_deg': 90},
        {'nom': '08R/26L', 'longueur_m': 3048, 'cap_deg': 90},
        {'nom': '08L/26R', 'longueur_m': 2743, 'cap_deg': 90},
        {'nom': '09R/27L', 'longueur_m': 2743, 'cap_deg': 90},
        {'nom': '10/28', 'longueur_m': 2743, 'cap_deg': 90},
    ],
    'DXB': [
        {'nom': '12R/30L', 'longueur_m': 4447, 'cap_deg': 122},
        {'nom': '12L/30R', 'longueur_m': 4351, 'cap_deg': 122},
    ],
    'HND': [
        {'nom': '16L/34R', 'longueur_m': 3360, 'cap_deg': 150},
        {'nom': '16R/34L', 'longueur_m': 3000, 'cap_deg': 150},
        {'nom': '04/22', 'longueur_m': 2500, 'cap_deg': 35},
        {'nom': '05/23', 'longueur_m': 2500, 'cap_deg': 42},
    ],
    'DFW': [
        {'nom': '18L/36R', 'longueur_m': 4085, 'cap_deg': 180},
        {'nom': '17C/35C', 'longueur_m': 4084, 'cap_deg': 180},
        {'nom': '17R/35L', 'longueur_m': 4084, 'cap_deg': 180},
        {'nom': '18R/36L', 'longueur_m': 4084, 'cap_deg': 180},
        {'nom': '13R/31L', 'longueur_m': 2835, 'cap_deg': 139},
        {'nom': '13L/31R', 'longueur_m': 2743, 'cap_deg': 135},
        {'nom': '17L/35R', 'longueur_m': 2591, 'cap_deg': 180},
    ],
    'PVG': [
        {'nom': '17L/35R', 'longueur_m': 4000, 'cap_deg': 162},
        {'nom': '16L/34R', 'longueur_m': 3800, 'cap_deg': 162},
        {'nom': '16R/34L', 'longueur_m': 3800, 'cap_deg': 163},
        {'nom': '15/33', 'longueur_m': 3400, 'cap_deg': 150},   # statut incertain (peut-être hors service), cap déduit du nom
        {'nom': '17R/35L', 'longueur_m': 3400, 'cap_deg': 162},
    ],
    'ORD': [
        {'nom': '10L/28R', 'longueur_m': 3962, 'cap_deg': 90},
        {'nom': '09R/27L', 'longueur_m': 3432, 'cap_deg': 90},
        {'nom': '09C/27C', 'longueur_m': 3427, 'cap_deg': 90},
        {'nom': '10C/28C', 'longueur_m': 3292, 'cap_deg': 90},
        {'nom': '04R/22L', 'longueur_m': 2461, 'cap_deg': 41},
        {'nom': '04L/22R', 'longueur_m': 2286, 'cap_deg': 39},
        {'nom': '09L/27R', 'longueur_m': 2286, 'cap_deg': 90},
        {'nom': '10R/28L', 'longueur_m': 2286, 'cap_deg': 90},
    ],
    'LHR': [
        {'nom': '09L/27R', 'longueur_m': 3901, 'cap_deg': 90},
        {'nom': '09R/27L', 'longueur_m': 3658, 'cap_deg': 90},
    ],
    'IST': [
        {'nom': '17L/35R', 'longueur_m': 4100, 'cap_deg': 179},
        {'nom': '17R/35L', 'longueur_m': 4100, 'cap_deg': 179},
        {'nom': '16L/34R', 'longueur_m': 3750, 'cap_deg': 179},
        {'nom': '16R/34L', 'longueur_m': 3750, 'cap_deg': 179},
        {'nom': '18/36', 'longueur_m': 3060, 'cap_deg': 179},
        {'nom': '09/27', 'longueur_m': 2819, 'cap_deg': 89},
    ],
    'CAN': [
        {'nom': '02L/20R', 'longueur_m': 3800, 'cap_deg': 14},
        {'nom': '02R/20L', 'longueur_m': 3800, 'cap_deg': 14},
        {'nom': '01R/19L', 'longueur_m': 3600, 'cap_deg': 13},
        {'nom': '03/21', 'longueur_m': 3600, 'cap_deg': 14},
        {'nom': '01L/19R', 'longueur_m': 3400, 'cap_deg': 14},
    ],
    'DEN': [
        {'nom': '16R/34L', 'longueur_m': 4877, 'cap_deg': 181},
        {'nom': '07/25', 'longueur_m': 3658, 'cap_deg': 90},
        {'nom': '08/26', 'longueur_m': 3658, 'cap_deg': 91},
        {'nom': '16L/34R', 'longueur_m': 3658, 'cap_deg': 180},
        {'nom': '17L/35R', 'longueur_m': 3658, 'cap_deg': 181},
        {'nom': '17R/35L', 'longueur_m': 3658, 'cap_deg': 181},
    ],
    'DEL': [
        {'nom': '11R/29L', 'longueur_m': 4430, 'cap_deg': 104},
        {'nom': '11L/29R', 'longueur_m': 4400, 'cap_deg': 104},   # 4e piste (2023), longueur officielle du ministère indien
        {'nom': '10/28', 'longueur_m': 3813, 'cap_deg': 105},
        {'nom': '09/27', 'longueur_m': 2816, 'cap_deg': 92},
    ],
    'ICN': [
        {'nom': '16L/34R', 'longueur_m': 4000, 'cap_deg': 145},
        {'nom': '15L/33R', 'longueur_m': 3750, 'cap_deg': 144},
        {'nom': '15R/33L', 'longueur_m': 3750, 'cap_deg': 144},
        {'nom': '16R/34L', 'longueur_m': 3750, 'cap_deg': 145},
    ],
    'LAX': [
        {'nom': '07L/25R', 'longueur_m': 3930, 'cap_deg': 83},
        {'nom': '07R/25L', 'longueur_m': 3382, 'cap_deg': 83},
        {'nom': '06R/24L', 'longueur_m': 3310, 'cap_deg': 83},
        {'nom': '06L/24R', 'longueur_m': 2721, 'cap_deg': 83},
    ],
    'CDG': [
        {'nom': '08L/26R', 'longueur_m': 4215, 'cap_deg': 85},
        {'nom': '09R/27L', 'longueur_m': 4200, 'cap_deg': 85},
        {'nom': '08R/26L', 'longueur_m': 2700, 'cap_deg': 85},
        {'nom': '09L/27R', 'longueur_m': 2700, 'cap_deg': 85},
    ],
    'PEK': [
        {'nom': '01/19', 'longueur_m': 3800, 'cap_deg': 353},
        {'nom': '18L/36R', 'longueur_m': 3800, 'cap_deg': 173},
        {'nom': '18R/36L', 'longueur_m': 3200, 'cap_deg': 173},
    ],
    'SIN': [
        {'nom': '02C/20C', 'longueur_m': 4000, 'cap_deg': 23},
        {'nom': '02L/20R', 'longueur_m': 4000, 'cap_deg': 23},
        {'nom': '02R/20L', 'longueur_m': 4000, 'cap_deg': 23},   # usage militaire : non disponible au civil d'après l'AIP récent
    ],
    'AMS': [
        {'nom': '18R/36L', 'longueur_m': 3800, 'cap_deg': 183},
        {'nom': '09/27', 'longueur_m': 3453, 'cap_deg': 87},
        {'nom': '06/24', 'longueur_m': 3439, 'cap_deg': 58},
        {'nom': '18L/36R', 'longueur_m': 3400, 'cap_deg': 183},
        {'nom': '18C/36C', 'longueur_m': 3300, 'cap_deg': 183},
        {'nom': '04/22', 'longueur_m': 2020, 'cap_deg': 41},
    ],
    'MAD': [
        {'nom': '18R/36L', 'longueur_m': 4350, 'cap_deg': 180},
        {'nom': '14R/32L', 'longueur_m': 3988, 'cap_deg': 142},   # longueur Aena (certaines sources : 4100 m)
        {'nom': '14L/32R', 'longueur_m': 3500, 'cap_deg': 142},
        {'nom': '18L/36R', 'longueur_m': 3500, 'cap_deg': 180},
    ],
    'SZX': [
        {'nom': '16L/34R', 'longueur_m': 3800, 'cap_deg': 153},
        {'nom': '16R/34L', 'longueur_m': 3600, 'cap_deg': 153},
        {'nom': '15/33', 'longueur_m': 3400, 'cap_deg': 153},
    ],
    'KUL': [
        {'nom': '14L/32R', 'longueur_m': 4124, 'cap_deg': 147},
        {'nom': '14R/32L', 'longueur_m': 4050, 'cap_deg': 147},
        {'nom': '15/33', 'longueur_m': 3960, 'cap_deg': 146},
    ],
}

for _code, _pistes in PISTES.items():
    AIRPORTS[_code]['pistes'] = _pistes
