#!/usr/bin/env python3
# coding: utf-8
"""
ohm_watchdog_cdn.py
Surveille le CDN d'Ohm Énergie pour détecter de nouvelles grilles tarifaires.
Plus fiable que la page /cgv, car les PDFs sont hébergés directement sur leur fileadmin.
"""

import os
import re
import json
import requests
from datetime import datetime
from urllib.parse import urljoin, urlparse

# === CONFIGURATION ===
BASE_URL = "https://www.ohm-energie.com/fileadmin/Digital/Groupe/PDF/Documents_contractuels/Particuliers/Tarifs_Ohm/fr/"
CACHE_FILENAME = "ohm_cdn_cache.json"
TIMEOUT = 20
DOWNLOAD_DIR = "ohm_pdfs"  # Dossier local où stocker les fichiers téléchargés

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}


class OhmCDNWatchdog:
    def __init__(self):
        self.base_url = BASE_URL
        base = os.path.dirname(os.path.abspath(__file__))
        self.cache_path = os.path.join(base, CACHE_FILENAME)
        os.makedirs(os.path.join(base, DOWNLOAD_DIR), exist_ok=True)

    def list_pdfs(self):
        """Tente de lister les PDF dans le répertoire CDN (en supposant un index public ou une page générée)."""
        try:
            r = requests.get(self.base_url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
        except Exception as e:
            print(f"❌ Erreur accès CDN: {e}")
            return []

        # Extraire tous les liens PDF du HTML (si directory listing activé)
        pdfs = re.findall(r'href="([^"]+\.pdf)"', r.text, flags=re.IGNORECASE)
        pdfs = [urljoin(self.base_url, p) for p in pdfs]
        pdfs = sorted(set(pdfs))
        if not pdfs:
            print("⚠️ Aucun PDF listé directement, tentative de scan heuristique...")

            # Plan B : on suppose des noms classiques connus
            guess = [
                "grille-tarifaire-classique-particuliers.pdf",
                "grille-tarifaire-fixe-2ans-particuliers.pdf",
                "grille-tarifaire-heures-eco-particuliers.pdf",
                "grille-tarifaire-modulo-particuliers.pdf",
                "grille-tarifaire-extra-eco-particuliers.pdf",
                "grille-tarifaire-soir-week-end-particuliers.pdf",
            ]
            pdfs = [urljoin(self.base_url, g) for g in guess]
        return pdfs

    def check_last_modified(self, url):
        """Retourne la date de dernière modification (si disponible)."""
        try:
            r = requests.head(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200 and "Last-Modified" in r.headers:
                return r.headers["Last-Modified"]
            return None
        except Exception:
            return None

    def load_cache(self):
        if not os.path.exists(self.cache_path):
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_cache(self, data):
        payload = {"timestamp": datetime.now().isoformat(), "files": data}
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Erreur écriture cache:", e)

    def download_pdf(self, url):
        """Télécharge le PDF vers DOWNLOAD_DIR (désactivé par défaut)."""
        fname = os.path.basename(urlparse(url).path)
        dest = os.path.join(os.path.dirname(self.cache_path), DOWNLOAD_DIR, fname)
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                with open(dest, "wb") as f:
                    f.write(r.content)
                print(f"📥 Téléchargé: {fname}")
                return dest
            else:
                print(f"⚠️ Échec téléchargement {url} ({r.status_code})")
        except Exception as e:
            print("Erreur téléchargement:", e)

    def check_for_updates(self):
        print(f"🔍 Vérification du CDN Ohm: {self.base_url}")
        files = self.list_pdfs()
        if not files:
            print("❌ Aucun PDF détecté (listing vide).")
            return

        cache = self.load_cache().get("files", {})
        updated = {}

        for pdf in files:
            lastmod = self.check_last_modified(pdf)
            updated[pdf] = lastmod or "unknown"

        new_files = [f for f in updated if f not in cache]
        changed = [
            f for f in updated
            if f in cache and cache[f] != updated[f]
        ]

        if new_files or changed:
            print("🚨 Nouveaux ou mis à jour détectés :")
            for f in new_files:
                print(" ➕ Nouveau :", f)
                # self.download_pdf(f)
            for f in changed:
                print(" ♻️ Modifié :", f)
                # self.download_pdf(f)
            self.save_cache(updated)
        else:
            print("✅ Aucune nouvelle grille depuis la dernière vérification.")


if __name__ == "__main__":
    wd = OhmCDNWatchdog()
    wd.check_for_updates()
