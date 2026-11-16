"""
Les 20 aéroports les plus fréquentés du monde en 2025 (passagers),
d'après le classement définitif d'ACI World publié en juillet 2026.

Coordonnées approximatives (au centième de degré), largement suffisantes
pour choisir un point de grille CMIP6 (mailles d'environ 100 à 250 km).

Usage dans le script CMIP6 :
    from airports_data import AIRPORTS
    lat, lon = AIRPORTS['CDG']['lat'], AIRPORTS['CDG']['lon']
"""

AIRPORTS = {
    'ATL': {'rang': 1,  'ville': 'Atlanta',           'pays': 'États-Unis',          'passagers_2025': 106_302_208, 'lat': 33.64, 'lon': -84.43},
    'DXB': {'rang': 2,  'ville': 'Dubaï',             'pays': 'Émirats arabes unis', 'passagers_2025': 95_192_160,  'lat': 25.25, 'lon': 55.36},
    'HND': {'rang': 3,  'ville': 'Tokyo Haneda',      'pays': 'Japon',               'passagers_2025': 91_679_814,  'lat': 35.55, 'lon': 139.78},
    'DFW': {'rang': 4,  'ville': 'Dallas/Fort Worth', 'pays': 'États-Unis',          'passagers_2025': 85_660_127,  'lat': 32.90, 'lon': -97.04},
    'PVG': {'rang': 5,  'ville': 'Shanghai Pudong',   'pays': 'Chine',               'passagers_2025': 84_994_548,  'lat': 31.14, 'lon': 121.81},
    'ORD': {'rang': 6,  'ville': 'Chicago O\'Hare',   'pays': 'États-Unis',          'passagers_2025': 84_856_018,  'lat': 41.98, 'lon': -87.90},
    'LHR': {'rang': 7,  'ville': 'Londres Heathrow',  'pays': 'Royaume-Uni',         'passagers_2025': 84_482_126,  'lat': 51.47, 'lon': -0.45},
    'IST': {'rang': 8,  'ville': 'Istanbul',          'pays': 'Turquie',             'passagers_2025': 84_437_710,  'lat': 41.26, 'lon': 28.74},
    'CAN': {'rang': 9,  'ville': 'Canton',            'pays': 'Chine',               'passagers_2025': 83_582_952,  'lat': 23.39, 'lon': 113.30},
    'DEN': {'rang': 10, 'ville': 'Denver',            'pays': 'États-Unis',          'passagers_2025': 82_427_962,  'lat': 39.86, 'lon': -104.67},
    'DEL': {'rang': 11, 'ville': 'New Delhi',         'pays': 'Inde',                'passagers_2025': 78_148_081,  'lat': 28.56, 'lon': 77.10},
    'ICN': {'rang': 12, 'ville': 'Séoul Incheon',     'pays': 'Corée du Sud',        'passagers_2025': 74_126_912,  'lat': 37.46, 'lon': 126.44},
    'LAX': {'rang': 13, 'ville': 'Los Angeles',       'pays': 'États-Unis',          'passagers_2025': 73_709_594,  'lat': 33.94, 'lon': -118.41},
    'CDG': {'rang': 14, 'ville': 'Paris-CDG',         'pays': 'France',              'passagers_2025': 72_029_407,  'lat': 49.01, 'lon': 2.55},
    'PEK': {'rang': 15, 'ville': 'Pékin Capitale',    'pays': 'Chine',               'passagers_2025': 70_742_712,  'lat': 40.08, 'lon': 116.58},
    'SIN': {'rang': 16, 'ville': 'Singapour Changi',  'pays': 'Singapour',           'passagers_2025': 69_982_000,  'lat': 1.36,  'lon': 103.99},
    'AMS': {'rang': 17, 'ville': 'Amsterdam',         'pays': 'Pays-Bas',            'passagers_2025': 68_771_592,  'lat': 52.31, 'lon': 4.76},
    'MAD': {'rang': 18, 'ville': 'Madrid',            'pays': 'Espagne',             'passagers_2025': 68_118_754,  'lat': 40.47, 'lon': -3.56},
    'SZX': {'rang': 19, 'ville': 'Shenzhen',          'pays': 'Chine',               'passagers_2025': 66_485_213,  'lat': 22.64, 'lon': 113.81},
    'KUL': {'rang': 20, 'ville': 'Kuala Lumpur',      'pays': 'Malaisie',            'passagers_2025': 63_409_501,  'lat': 2.75,  'lon': 101.71},
}