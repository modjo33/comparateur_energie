import requests
import re
import json
from datetime import datetime

FOURNISSEURS = {
    "Ohm Énergie": [
        "https://www.ohm-energie.com/content/dam/ohm-public/pdf/",
        "https://www.ohm-energie.com/fileadmin/Digital/Groupe/PDF/Documents_contractuels/Particuliers/Tarifs_Ohm/fr/",
    ],
    "EDF": [
        "https://particulier.edf.fr/content/dam/edf-fr/particuliers/docs/pdf/",
        "https://particulier.edf.fr/content/dam/edf-fr/particuliers/docs/pdf/tarif-bleu/",
    ],
    "Ekwateur": [
        "https://cdn.ekwateur.com/contract/",
        "https://www.ekwateur.fr/assets/files/",
    ],
    "TotalEnergies": [
        "https://totalenergies.fr/sites/g/files/nytnzq621/files/atoms/files/",
    ],
}

STATE_FILE = "etat_tarifs_web.json"


def charger_etat():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def sauvegarder_etat(etat):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(etat, f, indent=2, ensure_ascii=False)


def lister_pdfs(base_url):
    r = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    liens = re.findall(r'href="([^"]+\.pdf)"', r.text, flags=re.IGNORECASE)
    result = {}
    for lien in liens:
        if not lien.lower().startswith("http"):
            lien = base_url + lien
        try:
            head = requests.head(lien, headers={"User-Agent": "Mozilla/5.0"})
            taille = head.headers.get("Content-Length", "0")
            result[lien] = int(taille)
        except Exception:
            continue
    return result


def main():
    print("🌐 Surveillance multi-fournisseurs de grilles tarifaires\n")
    ancien = charger_etat()
    actuel = {}

    for fournisseur, urls in FOURNISSEURS.items():
        print(f"🔍 {fournisseur}...")
        trouve = False
        for url in urls:
            try:
                pdfs = lister_pdfs(url)
                if pdfs:
                    trouve = True
                    print(f"   ✅ {len(pdfs)} fichiers trouvés sur {url}")
                    for lien, taille in pdfs.items():
                        actuel[lien] = {"taille": taille, "fournisseur": fournisseur}
                    break
            except requests.HTTPError as e:
                print(f"   ⚠️  HTTP {e.response.status_code} sur {url}")
            except Exception as e:
                print(f"   ⚠️  Erreur : {e}")
        if not trouve:
            print(f"   ❌ Aucun PDF trouvé pour {fournisseur}")

    nouveaux = [l for l in actuel if l not in ancien]
    modifies = [l for l, v in actuel.items() if l in ancien and v["taille"] != ancien[l]["taille"]]

    print("\n📢 Résumé :")
    if not nouveaux and not modifies:
        print("😴 Aucune nouvelle grille détectée.")
    else:
        if nouveaux:
            print("🆕 Nouveaux fichiers :")
            for lien in nouveaux:
                print(f"  ➕ {lien} ({actuel[lien]['fournisseur']})")
        if modifies:
            print("✏️ Fichiers modifiés :")
            for lien in modifies:
                print(f"  ✏ {lien} ({actuel[lien]['fournisseur']})")

    sauvegarder_etat(actuel)
    print(f"\n💾 État sauvegardé ({len(actuel)} fichiers suivis).")


if __name__ == "__main__":
    main()
