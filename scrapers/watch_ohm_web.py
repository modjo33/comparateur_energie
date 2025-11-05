import requests
import re
import json
from datetime import datetime

URL_CDN = "https://www.ohm-energie.com/content/dam/ohm-public/pdf/"
STATE_FILE = "etat_web_ohm.json"

def charger_etat():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def sauvegarder_etat(etat):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(etat, f, indent=2)

def lister_pdfs():
    print(f"🔍 Vérification sur {URL_CDN}")
    r = requests.get(URL_CDN, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    # On cherche tous les liens PDF dans le HTML
    pdfs = re.findall(r'href="([^"]+\.pdf)"', r.text, flags=re.IGNORECASE)
    fichiers = {}
    for lien in pdfs:
        if not lien.lower().startswith("http"):
            lien = URL_CDN + lien
        head = requests.head(lien, headers={"User-Agent": "Mozilla/5.0"})
        taille = head.headers.get("Content-Length", "0")
        fichiers[lien] = int(taille)
    return fichiers

def main():
    ancien = charger_etat()
    try:
        actuel = lister_pdfs()
    except Exception as e:
        print("❌ Erreur :", e)
        return

    nouveaux = []
    modifies = []

    for lien, taille in actuel.items():
        if lien not in ancien:
            nouveaux.append(lien)
        elif ancien[lien] != taille:
            modifies.append(lien)

    if not nouveaux and not modifies:
        print("😴 Aucune nouvelle grille sur le web.")
    else:
        if nouveaux:
            print("🆕 Nouvelles grilles détectées :")
            for lien in nouveaux:
                print(f"  ➕ {lien}")
        if modifies:
            print("✏️ Grilles modifiées :")
            for lien in modifies:
                print(f"  ✏ {lien}")

    sauvegarder_etat(actuel)
    print(f"\n💾 État mis à jour ({len(actuel)} fichiers suivis).")

if __name__ == "__main__":
    main()
