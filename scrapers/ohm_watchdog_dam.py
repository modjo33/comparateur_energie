#!/usr/bin/env python3
# coding: utf-8

import os
import re
import json
import requests
from datetime import datetime
from urllib.parse import urljoin

BASE_URL = "https://www.ohm-energie.com/content/dam/ohm-public/pdf/"
CACHE_FILE = "ohm_dam_cache.json"
TIMEOUT = 20
DOWNLOAD_DIR = "ohm_dam_pdfs"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36",
    "Accept": "*/*",
}

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
    return path

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("files", {})
        except Exception:
            return {}
    return {}

def save_cache(data):
    payload = {"timestamp": datetime.now().isoformat(), "files": data}
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

def fetch_listing():
    try:
        r = requests.get(BASE_URL, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text
        pdfs = re.findall(r'href="([^"]+\.pdf)"', html, flags=re.IGNORECASE)
        if not pdfs:
            print("⚠️ Aucun lien PDF trouvé dans la page (peut-être index bloqué).")
        return sorted(set(urljoin(BASE_URL, p) for p in pdfs))
    except Exception as e:
        print("❌ Erreur accès CDN:", e)
        return []

def check_last_modified(url):
    try:
        r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and "Last-Modified" in r.headers:
            return r.headers["Last-Modified"]
        return None
    except Exception:
        return None

def download_pdf(url):
    fname = os.path.basename(url)
    dest = os.path.join(DOWNLOAD_DIR, fname)
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            with open(dest, "wb") as f:
                f.write(r.content)
            print(f"📥 Téléchargé : {fname}")
        else:
            print(f"⚠️ Échec téléchargement {fname} ({r.status_code})")
    except Exception as e:
        print("Erreur téléchargement:", e)

def main():
    print(f"🔍 Vérification des grilles Ohm (DAM CDN): {BASE_URL}")
    ensure_dir(DOWNLOAD_DIR)

    cache = load_cache()
    updated = {}
    pdfs = fetch_listing()
    if not pdfs:
        # fallback heuristique
        guess = [
            "grille_tarifaire_elec_modulo_01082025.pdf",
            "grille_tarifaire_elec_fixe_2ans_01082025.pdf",
            "grille_tarifaire_elec_swe_01082025.pdf",
            "grille_tarifaire_elec_extraeco_01082025.pdf",
            "grille_tarifaire_elec_classique_01082025.pdf",
        ]
        pdfs = [urljoin(BASE_URL, g) for g in guess]

    for url in pdfs:
        if not any(x in url.lower() for x in ["grille", "tarif", "elec"]):
            continue
        lm = check_last_modified(url)
        updated[url] = lm or "unknown"

    new_files = [f for f in updated if f not in cache]
    changed = [f for f in updated if f in cache and cache[f] != updated[f]]

    if new_files or changed:
        print("🚨 Nouveaux ou modifiés détectés :")
        for f in new_files:
            print(" ➕ Nouveau :", f)
            download_pdf(f)
        for f in changed:
            print(" ♻️ Modifié :", f)
            download_pdf(f)
        save_cache(updated)
    else:
        print("✅ Aucune nouvelle grille depuis la dernière vérification.")

if __name__ == "__main__":
    main()
