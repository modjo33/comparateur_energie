import os
import json
from datetime import datetime

# Dossier où tu ranges les grilles OHM
DOSSIERS_OHM = [
    "/mnt/c/Users/johan/OneDrive/Documents/ELECTRICITE PARTICULIER/OHM ENERGIE/",
]

# Fichier qui mémorise l'état précédent
STATE_FILE = "etat_grilles_ohm.json"


def scanner_pdfs():
    """Retourne un dict {chemin_pdf: timestamp_modif}."""
    result = {}
    for base in DOSSIERS_OHM:
        if not os.path.isdir(base):
            print(f"⚠️ Dossier introuvable : {base}")
            continue

        for root, dirs, files in os.walk(base):
            for name in files:
                if name.lower().endswith(".pdf"):
                    full = os.path.join(root, name)
                    try:
                        mtime = os.path.getmtime(full)
                        result[full] = mtime
                    except OSError:
                        print(f"⚠️ Impossible de lire : {full}")
    return result


def charger_etat():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def sauvegarder_etat(etat):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(etat, f, indent=2)


def format_date(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def main():
    print("🔍 Scan des grilles OHM locales...")

    ancien = charger_etat()
    actuel = scanner_pdfs()

    nouveaux = []
    modifies = []

    for chemin, ts in actuel.items():
        ts_old = ancien.get(chemin)
        if ts_old is None:
            nouveaux.append((chemin, ts))
        elif ts > ts_old + 1:
            modifies.append((chemin, ts))

    disparus = [c for c in ancien.keys() if c not in actuel]

    if not nouveaux and not modifies:
        print("😴 Aucune nouvelle grille détectée.")
    else:
        if nouveaux:
            print("🆕 Nouvelles grilles détectées :")
            for chemin, ts in sorted(nouveaux, key=lambda x: x[1]):
                print(f"  ➕ {chemin}")
                print(f"     ajoutée le {format_date(ts)}")
        if modifies:
            print("✏️ Grilles modifiées :")
            for chemin, ts in sorted(modifies, key=lambda x: x[1]):
                print(f"  ✏ {chemin}")
                print(f"     modifiée le {format_date(ts)}")

    if disparus:
        print("🗑️ Grilles supprimées depuis le dernier scan :")
        for c in disparus:
            print(f"  ❌ {c}")

    sauvegarder_etat(actuel)
    print("\n💾 État mis à jour dans", STATE_FILE)


if __name__ == "__main__":
    main()

