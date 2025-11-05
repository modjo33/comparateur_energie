import requests
import re
import json
from datetime import datetime
from bs4 import BeautifulSoup

FOURNISSEURS = {
    "Ohm Énergie": "https://www.ohm-energie.com/electricite/offres",
    "EDF": "https://www.edf.fr/particuliers/offres-d-electricite",
    "Ekwateur": "https://ekwateur.com/energie/",
    "TotalEnergies": "https://www.totalenergies.fr/particuliers/electricite-gaz",
}

STATE_FILE = "etat_tarifs_webpages.json"


def charger_etat():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def sauvegarder_etat(etat):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(etat, f, indent=2, ensure_ascii=False)


def extraire_pdfs(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    liens = []
    for a in soup.find_all("a", href=True):
        if ".pdf" in a["href"].lower():
            lien = a["href"]
            if not lien.startswith("http"):
                base = "/".join(url.split("/")[:3])
                lien = base + lien
            liens.append(lien)
    return list(set(liens))


def main():
    print("🌍 Surveillance multi-fournisseurs des pages d’offres\n")
    ancien = charger_etat()
    actuel = {}

    for fournisseur, page in FOURNISSEURS.items():
        print(f"🔎 {fournisseur} → {page}")
        try:
            pdfs = extraire_pdfs(page)
            if not pdfs:
                print("   ⚠️ Aucun PDF trouvé sur cette page.")
            else:
                print(f"   ✅ {len(pdfs)} PDF trouvés.")
                for lien in pdfs:
                    actuel[lien] = {"fournisseur": fournisseur, "date": str(datetime.now())}
        except requests.HTTPError as e:
            print(f"   ❌ HTTP {e.response.status_code}")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")

    nouveaux = [l for l in actuel if l not in ancien]
    supprimes = [l for l in ancien if l not in actuel]

    print("\n📢 Résumé :")
    if not nouveaux and not supprimes:
        print("😴 Aucune évolution détectée.")
    else:
        if nouveaux:
            print("🆕 Nouveaux PDF :")
            for lien in nouveaux:
                print(f"  ➕ {lien} ({actuel[lien]['fournisseur']})")
        if supprimes:
            print("🗑️ Fichiers disparus :")
            for lien in supprimes:
                print(f"  ❌ {lien} ({ancien[lien]['fournisseur']})")

    sauvegarder_etat(actuel)
    print(f"\n💾 État sauvegardé ({len(actuel)} fichiers suivis).")


if __name__ == "__main__":
    main()
