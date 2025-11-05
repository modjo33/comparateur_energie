#!/usr/bin/env python3
import os
import re
import requests
from datetime import datetime

# Base supposée pour les PDF (ajustée selon leur structure CDN)
CDN_BASE = "https://www.ohm-energie.com/content/dam/ohm-public/pdf/"
# Dossier où tu veux stocker et surveiller
LOCAL_DIR = "/mnt/c/Users/johan/OneDrive/Documents/ELECTRICITE PARTICULIER/OHM ENERGIE"
# Fichier de suivi
STATE_FILE = os.path.join(LOCAL_DIR, "ohm_watchdog_state.txt")

def fetch_listing():
    """Essaie d'obtenir la liste des fichiers PDF du CDN Ohm."""
    try:
        resp = requests.get(CDN_BASE, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"⚠️ Impossible d'accéder à {CDN_BASE}: {e}")
        return []

    urls = re.findall(r'href="([^"]+\.pdf)"', resp.text)
    full_urls = [u if u.startswith("http") else CDN_BASE + u for u in urls]
    full_urls = [u for u in full_urls if "ohm" in u.lower()]
    return sorted(set(full_urls))

def load_previous_state():
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_state(urls):
    with open(STATE_FILE, "w") as f:
        for u in sorted(urls):
            f.write(u + "\n")

def check_new_files():
    print(f"🔍 Vérification des grilles Ohm : {CDN_BASE}")
    old_urls = load_previous_state()
    new_urls = fetch_listing()
    if not new_urls:
        print("⚠️ Aucun fichier détecté (CDN vide ou bloqué).")
        return

    new_links = [u for u in new_urls if u not in old_urls]

    if not new_links:
        print("✅ Aucune nouvelle grille détectée.")
    else:
        print("🚨 Nouvelles grilles détectées :")
        for u in new_links:
            print(f" ➕ {u}")

        # Sauvegarde de l’état mis à jour
        save_state(set(new_urls))
        print("📦 État mis à jour.")

if __name__ == "__main__":
    check_new_files()
