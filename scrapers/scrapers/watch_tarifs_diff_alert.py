cat > scrapers/watch_tarifs_diff_v2.py <<'PY'
#!/usr/bin/env python3
# scrapers/watch_tarifs_diff_v2.py
"""
Surveille les pages d'offres fournisseurs : calcule un hash du HTML rendu et
détecte les changements. Sauvegarde l'état et conserve snapshots + diffs.
Mode debug (navigateur visible) : SHOW_BROWSER=1 python scrapers/watch_tarifs_diff_v2.py
"""

import os
import json
import hashlib
import difflib
import random
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

STATE_FILE = "etat_tarifs_diff_v2.json"
SNAPSHOT_DIR = Path("snapshots_v2")
DIFF_DIR = Path("diffs_v2")

# Liste étendue (ajoute/modifie selon tes besoins)
FOURNISSEURS = {
    "Ohm Énergie": "https://www.ohm-energie.com/electricite/offres",
    "Ohm Énergie (CGV)": "https://www.ohm-energie.com/cgv",
    "EDF": "https://www.edf.fr/particuliers/offres-d-electricite",
    "TotalEnergies": "https://www.totalenergies.fr/particuliers/electricite-gaz",
    "Ekwateur": "https://ekwateur.com/energie/",
    "Alpiq": "https://www.alpiq.fr/offres-electricite-particuliers",
    "Alterna": "https://www.alterna.fr/offres",
    "Dyneff": "https://www.dyneff.fr/particuliers/offres",
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
    "Engie": "https://particuliers.engie.fr/electricite/offres-electricite.html",
    "Vattenfall": "https://www.vattenfall.fr/particuliers/offres-electricite",
    "Plüm Energie": "https://www.plumenergie.fr/offres",
    "Sowee": "https://www.sowee.fr/offres/electricite",
    "Mega Energie": "https://www.mega-energie.fr/offres-electricite/",
    "Proxelia": "https://www.proxelia.fr/nos-offres-electricite",
    "Planète Oui": "https://www.planete-oui.fr/offres",
    "Iberdrola": "https://www.iberdrola.fr/particuliers/offres-electricite",
    "Joemia": "https://www.joemia.fr/offres-electricite/",
    "Urban Solar Energy": "https://www.urbansolarenergy.fr/offres-electricite/",
}

def ensure_dirs():
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    DIFF_DIR.mkdir(parents=True, exist_ok=True)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def hash_html(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()

def clean_html(html: str) -> str:
    # retire les scripts, les balises meta volatiles et lignes évidentes de tracking
    # (ne prétend pas être parfait, mais réduit le bruit)
    lines = []
    for line in html.splitlines():
        low = line.lower()
        if any(x in low for x in ["cookie", "analytics", "gtm", "google-analytics", "csrf", "token"]):
            continue
        if "<script" in low or "</script" in low:
            continue
        if "<style" in low or "</style" in low:
            continue
        lines.append(line.strip())
    # remove consecutive empty lines
    out = "\n".join(l for l in lines if l)
    return out

def save_snapshot(fournisseur, stamp, html):
    name = f"{stamp}_{safe_name(fournisseur)}.html"
    path = SNAPSHOT_DIR / name
    path.write_text(html, encoding="utf-8")
    return str(path)

def write_diff(fournisseur, stamp, old_html, new_html):
    old_lines = old_html.splitlines()
    new_lines = new_html.splitlines()
    diff = difflib.unified_diff(old_lines, new_lines, fromfile="old", tofile="new", lineterm="")
    name = f"{stamp}_{safe_name(fournisseur)}.diff.txt"
    path = DIFF_DIR / name
    path.write_text("\n".join(diff), encoding="utf-8")
    return str(path)

def safe_name(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s)[:120]

def visit_page(page, url):
    # essais de navigation avec quelques tactiques simples
    attempts = 3
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            page.goto(url, timeout=45000, wait_until="load")
            # petits comportements humains simulés
            page.wait_for_timeout(1500 + random.randint(0, 1500))
            page.mouse.wheel(0, 1000 + random.randint(0, 1500))
            page.wait_for_timeout(800 + random.randint(0, 1200))
            # parfois forcer un scroll plus long
            if random.random() < 0.4:
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(1200 + random.randint(0, 1200))
            return page.content()
        except PWTimeout as e:
            last_exc = e
            time.sleep(1 + attempt)
        except Exception as e:
            last_exc = e
            time.sleep(1 + attempt)
    raise last_exc

def main():
    print("🌐 Surveillance multi-fournisseurs (diff HTML) — v2\n")
    ensure_dirs()
    state = load_state()
    updated = {}

    show_browser = bool(os.environ.get("SHOW_BROWSER"))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not show_browser)
        context = browser.new_context(ignore_https_errors=True)
        # user-agent moins robotique
        context.set_default_navigation_timeout(60000)

        for fournisseur, url in FOURNISSEURS.items():
            print(f"🔎 {fournisseur} → {url}")
            page = None
            try:
                page = context.new_page()
                html_raw = visit_page(page, url)
                html = clean_html(html_raw)
                new_hash = hash_html(html)
                old = state.get(fournisseur)
                old_hash = old.get("hash") if old else None

                stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                snapshot_path = save_snapshot(fournisseur, stamp, html)

                if old_hash is None:
                    print("   📥 Première sauvegarde du contenu.")
                elif old_hash != new_hash:
                    print("   ⚠️  Changement détecté sur la page !")
                    # write diff between previous snapshot (if exists) and current
                    prev_snapshot = None
                    if old and old.get("snapshot"):
                        prev_snapshot = old.get("snapshot")
                        try:
                            old_html = Path(prev_snapshot).read_text(encoding="utf-8")
                        except Exception:
                            old_html = ""
                        diff_path = write_diff(fournisseur, stamp, old_html, html)
                        print(f"     → diff enregistré: {diff_path}")
                    updated[fournisseur] = {
                        "url": url,
                        "snapshot": snapshot_path,
                        "diff": diff_path if old_hash is not None else None,
                    }
                else:
                    print("   ✅ Aucun changement.")

                state[fournisseur] = {
                    "hash": new_hash,
                    "last_check": datetime.utcnow().isoformat(timespec="seconds"),
                    "snapshot": snapshot_path,
                    "url": url,
                }

            except Exception as e:
                print(f"   ❌ Erreur : {repr(e)}")
            finally:
                if page:
                    try:
                        page.close()
                    except Exception:
                        pass

        browser.close()

    # résumé
    print("\n📢 Résumé :")
    if updated:
        for k, v in updated.items():
            print(f"🆕 {k} a modifié sa page → {v['url']}")
    else:
        print("😴 Aucune évolution détectée.")

    save_state(state)
    print(f"\n💾 État sauvegardé ({len(state)} fournisseurs suivis).")

if __name__ == "__main__":
    main()
PY
