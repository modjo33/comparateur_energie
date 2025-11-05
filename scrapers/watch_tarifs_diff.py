# scrapers/watch_tarifs_diff.py
import hashlib
import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright

STATE_FILE = "etat_tarifs_diff.json"

FOURNISSEURS = {
    "Ohm Énergie": "https://www.ohm-energie.com/electricite/offres",
    "EDF": "https://www.edf.fr/particuliers/offres-d-electricite",
    "Ekwateur": "https://ekwateur.com/energie/",
    "TotalEnergies": "https://www.totalenergies.fr/particuliers/electricite-gaz",
    "Mint Energie": "https://www.mint-energie.com/offres",
    "Ilek": "https://www.ilek.fr/offres-electricite",
    "Enercoop": "https://www.enercoop.fr/particuliers/offres/",
    "Elmy": "https://www.elmy.fr/offres",
    "Alpiq": "https://www.alpiq.fr/offres-electricite-particuliers",
    "Happ-e": "https://www.happ-e.fr/offres",
}

def hash_html(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def clean_html(html: str) -> str:
    # Supprime les parties volatiles (dates, tracking, etc.)
    lines = [
        l for l in html.splitlines()
        if not any(x in l.lower() for x in ["cookie", "tracking", "analytics", "csrf", "gtm"])
    ]
    return "\n".join(lines)

def main():
    print("🌐 Surveillance des pages fournisseurs (diff HTML)\n")

    state = load_state()
    updated = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(ignore_https_errors=True)

        for fournisseur, url in FOURNISSEURS.items():
            print(f"🔎 {fournisseur} → {url}")
            try:
                page = context.new_page()
                page.goto(url, timeout=60000)
                page.wait_for_timeout(6000)
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(3000)

                html = clean_html(page.content())
                new_hash = hash_html(html)
                old_hash = state.get(fournisseur, {}).get("hash")

                if not old_hash:
                    print("   📥 Première sauvegarde du contenu.")
                elif old_hash != new_hash:
                    print("   ⚠️  Changement détecté sur la page !")
                    updated[fournisseur] = url
                else:
                    print("   ✅ Aucun changement.")

                state[fournisseur] = {
                    "hash": new_hash,
                    "last_check": datetime.now().isoformat(timespec="seconds"),
                }

            except Exception as e:
                print(f"   ❌ Erreur : {e}")

        browser.close()

    print("\n📢 Résumé :")
    if updated:
        for f, u in updated.items():
            print(f"🆕 {f} a mis à jour sa page : {u}")
    else:
        print("😴 Aucune évolution détectée.")

    save_state(state)
    print(f"\n💾 État sauvegardé ({len(state)} fournisseurs suivis).")

if __name__ == "__main__":
    main()
