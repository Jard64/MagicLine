r"""
Remplit le catalogue d'avions (catalogue.csv) à partir des bases publiques.

Pour chaque avion demandé (code OACI + moteur), on récupère :
    OpenAP (TU Delft)        géométrie, masses, polaire lisse, volets, montage moteur
    ICAO Emissions Databank  poussée de décollage certifiée et taux de dilution (BPR),
                             via le fichier engines.csv d'OpenAP
    EUROCONTROL APD          V2 (IAS), distance de décollage et masse associée

Utilisation :
    python import_catalogue.py                      # reconstruit le catalogue par défaut
    python import_catalogue.py B739 E190 A332       # ajoute / met à jour des types
    python import_catalogue.py A20N:PW1127G-JM      # impose le moteur

Les lignes existantes du catalogue sont mises à jour (clé : nom), les autres conservées :
on peut donc corriger ou compléter le CSV à la main sans perdre ces corrections, tant
qu'on ne réimporte pas le même avion.
"""

import csv
import html
import io
import math
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGUE = os.path.join(HERE, "catalogue.csv")

OPENAP_RAW = "https://raw.githubusercontent.com/junzis/openap/master/openap/data"
APD_URL = "https://learningzone.eurocontrol.int/ilp/customs/ATCPFDB/details.aspx?ICAO={}"

COLUMNS = [
    "nom", "icao", "moteur", "moteur_icao_eedb", "n_moteurs", "montage_moteur",
    "S_m2", "envergure_m", "MTOW_kg", "OEW_kg",
    "cd0_lisse", "k_lisse", "polaire_openap", "lambda_f", "cf_c", "Sf_S", "volets_TO_deg",
    "F_TO_N", "bpr", "diam_soufflante_m",
    "masse_ref_kg", "V2_kt", "dist_TO_ref_m",
    "magic_line", "notes",
]

""" Diamètre de soufflante (m) par famille de moteur - traînée de moulinet en panne """

FAN_DIAMETER = {
    "CFM56-5B": 68.3 * 0.0254, # Aircraft Commerce n°145 (2023)
    "CFM56-7B": 61.0 * 0.0254,
    "LEAP-1A": 78.0 * 0.0254,
    "LEAP-1B": 69.4 * 0.0254,
    "PW1100G": 81.0 * 0.0254, # valeur constructeur couramment citée, non vérifiée
}

""" Braquage des volets au décollage (°) : Boeing volets 5, Airbus CONF 1+F """

TAKEOFF_FLAP_DEG = {"default": 10, "b737": 5, "b738": 5, "b739": 5, "b37m": 5, "b38m": 5, "b39m": 5}

""" Catalogue par défaut : (code OACI, moteur, nom) """

DEFAULT_FLEET = [
    ("B738", "CFM56-7B26", "B737-800"),
    ("B737", "CFM56-7B24", "B737-700"),
    ("B739", "CFM56-7B27", "B737-900ER"),
    ("B38M", "LEAP-1B27", "B737 MAX 8"),
    ("A319", "CFM56-5B6/P", "A319ceo"),
    ("A320", "CFM56-5B4/P", "A320ceo"),
    ("A20N", "LEAP-1A26", "A320neo"),
    ("A20N", "PW1127G-JM", "A320neo"),
    ("A321", "CFM56-5B3/P", "A321ceo"),
    ("A21N", "LEAP-1A33", "A321neo"),
    ("A21N", "PW1133G-JM", "A321neo"),
    ("E190", None, "E190"),
    ("E195", None, "E195"),
    ("A332", None, "A330-200"),
    ("B788", None, "B787-8"),
]


###############################################################################
################## Téléchargement et lecture ##################################
###############################################################################

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "MagicLine-PIE/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_simple_yaml(text):
    """Lecteur YAML minimal suffisant pour les fichiers OpenAP (dictionnaires imbriqués, listes '- x')."""
    root = {}
    stack = [(-1, root, None, None)] # (indentation, conteneur, parent, clé dans le parent)
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        while stack[-1][0] >= indent:
            stack.pop()
        _, container, parent, key_in_parent = stack[-1]
        item = line.strip()
        if item.startswith("- "):
            if isinstance(container, dict) and not container and parent is not None:
                container = parent[key_in_parent] = [] # 'clé:' suivie de '- x' : c'est une liste
                stack[-1] = (stack[-1][0], container, parent, key_in_parent)
            container.append(_scalar(item[2:]))
            continue
        key, _, value = item.partition(":")
        key, value = key.strip(), value.strip()
        if value == "":
            container[key] = {}
            stack.append((indent, container[key], container, key))
        else:
            container[key] = _scalar(value)
    return root


def _scalar(v):
    v = v.strip()
    if v in ("null", "~", ""):
        return None
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def openap_aircraft(code):
    return parse_simple_yaml(fetch(f"{OPENAP_RAW}/aircraft/{code}.yml"))


def openap_dragpolar(code):
    """Polaire OpenAP ; si absente, synonyme officiel (_synonym.csv). Retourne (polaire, code utilisé)."""
    try:
        return parse_simple_yaml(fetch(f"{OPENAP_RAW}/dragpolar/{code}.yml")), code
    except Exception:
        syn = dict(csv.reader(io.StringIO(fetch(f"{OPENAP_RAW}/dragpolar/_synonym.csv"))))
        if code in syn:
            return parse_simple_yaml(fetch(f"{OPENAP_RAW}/dragpolar/{syn[code]}.yml")), syn[code]
        raise


_ENGINES = None


def icao_engines():
    global _ENGINES
    if _ENGINES is None:
        _ENGINES = list(csv.DictReader(io.StringIO(fetch(f"{OPENAP_RAW}/engine/engines.csv"))))
    return _ENGINES


def _engine_aliases(name):
    """Noms couverts par une entrée ICAO groupée, ex. 'LEAP-1A35A/33/32' -> LEAP-1A35A, LEAP-1A33, LEAP-1A32."""
    parts = name.upper().split("/")
    aliases = {name.upper(), parts[0]}
    m = re.match(r"(.*?-\d*[A-Z]+)", parts[0])
    if m:
        aliases |= {m.group(1) + p for p in parts[1:]}
    return aliases


def find_engine(query):
    """Entrée ICAO EEDB correspondant au moteur demandé (nom exact, puis variantes /P, /3, entrées groupées).

    Si plusieurs entrées conviennent (ex. 'LEAP-1B'), on prend la plus poussante.
    """
    q = query.upper()
    rows = icao_engines()
    exact = [r for r in rows if r["name"].upper() == q]
    if exact:
        return exact[0]
    cands = [r for r in rows if q in _engine_aliases(r["name"])
             or r["name"].upper().startswith(q + "/") or r["name"].upper().startswith(q)]
    if not cands:
        raise KeyError(f"moteur introuvable dans la base ICAO : {query}")
    return max(cands, key=lambda r: float(r["max_thrust"]))


def engine_family(name):
    """Famille de moteur pour FAN_DIAMETER (ex. 'PW1127G-JM' -> 'PW1100G'), ou None."""
    n = re.sub(r"^PW11\d\dG", "PW1100G", name.upper())
    return next((f for f in FAN_DIAMETER if n.startswith(f)), None)


def eurocontrol_apd(code):
    """(MTOW kg, V2 kt, distance m) de la base EUROCONTROL APD, ou (None, None, None)."""
    try:
        t = fetch(APD_URL.format(code.upper()))
    except Exception:
        return None, None, None
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    txt = html.unescape(re.sub(r"<[^>]+>", "|", t))
    txt = re.sub(r"\s*\|\s*(\|\s*)*", " | ", txt)
    m = re.search(r"Take-off \| V2 \(IAS\) \| (\d+) \| kts \| Distance \| (\d+) \| m .*?MTOW \| (\d+) \| kg", txt)
    if not m:
        return None, None, None
    v2, dist, mtow = (int(g) for g in m.groups())
    return mtow, v2, dist


###############################################################################
################## Construction d'une ligne du catalogue ######################
###############################################################################

def build_row(icao, engine=None, name=None):
    code = icao.lower()
    ac = openap_aircraft(code)
    polar, polar_code = openap_dragpolar(code)

    eng = ac["engine"]
    engine = engine or eng.get("default")
    e = find_engine(engine)
    family = engine_family(e["name"])

    m_ref, v2, dist = eurocontrol_apd(icao)
    notes = []
    if polar_code != code:
        notes.append(f"polaire OpenAP de {polar_code.upper()} (synonyme)")
    if family is None:
        notes.append("diamètre soufflante inconnu : traînée de moulinet par défaut")
    if v2 is None:
        notes.append("V2 EUROCONTROL absent : C_L,max à renseigner")

    clean = polar["clean"]
    flaps = polar["flaps"]
    return {
        "nom": f"{name or ac['aircraft']} ({engine})",
        "icao": icao.upper(),
        "moteur": engine,
        "moteur_icao_eedb": f"{e['name']} [{e['uid']}]",
        "n_moteurs": eng["number"],
        "montage_moteur": eng.get("mount", "wing"),
        "S_m2": ac["wing"]["area"],
        "envergure_m": ac["wing"]["span"],
        "MTOW_kg": ac["mtow"],
        "OEW_kg": ac["oew"],
        "cd0_lisse": clean["cd0"],
        "k_lisse": clean["k"],
        "polaire_openap": polar_code.upper(),
        "lambda_f": flaps["lambda_f"],
        "cf_c": flaps["cf/c"],
        "Sf_S": flaps["Sf/S"],
        "volets_TO_deg": TAKEOFF_FLAP_DEG.get(code, TAKEOFF_FLAP_DEG["default"]),
        "F_TO_N": float(e["max_thrust"]),
        "bpr": float(e["bpr"]),
        "diam_soufflante_m": round(FAN_DIAMETER[family], 3) if family else "",
        "masse_ref_kg": m_ref or "",
        "V2_kt": v2 or "",
        "dist_TO_ref_m": dist or "",
        "magic_line": "twin" if eng["number"] == 2 else ("quad" if eng["number"] == 4 else "unified"),
        "notes": " ; ".join(notes),
    }


def read_catalogue(path=CATALOGUE):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_catalogue(rows, path=CATALOGUE):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})


def update_catalogue(requests, path=CATALOGUE):
    """requests : liste de (icao, moteur ou None, nom ou None). Met à jour / ajoute les lignes."""
    rows = read_catalogue(path)
    index = {r["nom"]: i for i, r in enumerate(rows)}
    for icao, engine, name in requests:
        if name is None: # avion déjà au catalogue : on garde son nom
            same = [r for r in rows if r["icao"] == icao.upper() and (engine is None or r["moteur"] == engine)]
            if same:
                name, engine = same[0]["nom"].rsplit(" (", 1)[0], same[0]["moteur"]
        try:
            row = build_row(icao, engine, name)
        except Exception as exc:
            print(f"  [échec] {icao} {engine or ''} : {exc}")
            continue
        if row["nom"] in index:
            rows[index[row["nom"]]] = row
        else:
            index[row["nom"]] = len(rows)
            rows.append(row)
        print(f"  [ok] {row['nom']:28s} F={row['F_TO_N'] / 1000:6.1f} kN  V2={row['V2_kt'] or '-':>4} kt"
              f"  {row['notes']}")
    write_catalogue(rows, path)
    return rows


if __name__ == "__main__":
    args = sys.argv[1:]
    if args:
        reqs = [(a.split(":")[0], a.split(":")[1] if ":" in a else None, None) for a in args]
    else:
        reqs = DEFAULT_FLEET
    update_catalogue(reqs)
    print(f"Catalogue écrit : {CATALOGUE}")
