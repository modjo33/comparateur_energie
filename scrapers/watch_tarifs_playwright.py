import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

FOURNISSEURS = {
    "Ohm Énergie": "https://www.ohm-energie.com/electricite/offres",
    "EDF": "https://www.edf.fr/particuliers/offres-d-electricite",
    "TotalEnergies": "https://www.totalenergies.fr/particuliers/electricite-gaz",
    "Ekwateur": "https://ekwateur.com/energie/",
    "Alpiq": "https://www.alpiq.fr/offres-electricite-particuliers",
    "Alterna": "https://www.alterna.fr/offres",
    "Dyneff": "https://www.dyneff.com/particuliers/offres",
    "Elecocite": "https://www.elecocite.fr/offres",
    "Elmy": "https://www.elmy.fr/offres",
    "Enercoop": "https://www.enercoop.fr/particuliers/offres/",
    "Gedia": "https://www.gedia.fr/offres",
    "GEG": "https://www.geg.fr/particuliers/offres",
    "Happ-e": "https://www.happ-e.fr/offres",
    "La Belle Énergie": "https://www.labelleenergie.fr/offres",
    "Ilek": "https://www.ilek.fr/offres-electricite",
    "Mint Energie": "https://www.mint-energie.com/offres",
    "Octopus Energy": "https://octopus.energy/fr/offres",
    "Ohm Énergie (CGV)": "https://www.ohm-energie.com/cgv",
    "Alpiq (PDF direct fallback)": "https://particuliers.alpiq.fr/grille-tarifaire/particuliers/gtr_elec_part.pdf",
}

STATE_FILE = "etat_tarifs_playwright.json"


def charger_etat():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def sauvegarder_etat(etat):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(etat, f, indent=2, ensure_ascii=False)


def extraire_pdfs(page_html, base_url):
    soup = BeautifulSoup(page_html, "html.parser")
    liens = []
    for a in soup.find_all("a", href=True):
        if ".pdf" in a["href"].lower():
            lien = a["href"]
            if not lien.startswith("http"):
                base = "/".join(base_url.split("/")[:3])
                lien = base + lien
            liens.append(lien)
    return list(set(liens))


def main():
    print("🌐 Surveillance multi-fournisseurs (mode navigateur)")

    ancien = charger_etat()
    actuel = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for fournisseur, url in FOURNISSEURS.items():
            print(f"\n🔎 {fournisseur} → {url}")
            try:
                page.goto(url, timeout=40000)
                page.wait_for_timeout(5000)
                html = page.content()
                pdfs = extraire_pdfs(html, url)
                if not pdfs:
                    print("   ⚠️ Aucun PDF trouvé.")
                else:
                    print(f"   ✅ {len(pdfs)} PDF trouvés.")
                    for lien in pdfs:
                        actuel[lien] = {
                            "fournisseur": fournisseur,
                            "date": str(datetime.now())
                        }
            except Exception as e:
                print(f"   ❌ Erreur : {e}")

        browser.close()

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
