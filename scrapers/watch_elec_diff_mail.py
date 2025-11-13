#!/usr/bin/env python3
# coding: utf-8

import os
import sys
import json
import hashlib
import smtplib
from datetime import datetime
from urllib.parse import urljoin, urlparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# Fix import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.log_utils import add_entry

# === CONFIG MAIL ===
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "johan.faydherbe@gmail.com"
SMTP_PASS = "nykmkclnagsabysh"
ALERT_EMAIL = "johan.faydherbe@gmail.com"
ALWAYS_NOTIFY = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

PDF_STATE_FILE = os.path.join(DATA_DIR, "pdf_state_elec.json")
ARCHIVE_ROOT = os.path.join(BASE_DIR, "archives", "pdf_elec")

# === FOURNISSEURS ÉLECTRICITÉ UNIQUEMENT ===
FOURNISSEURS_ELEC = {
    "Alpiq": "https://particuliers.alpiq.fr/electricite/nos-tarifs",
    "Alterna": "https://alterna-energie.fr/cgv-et-tarifs",
    "Elmy": "https://elmy.fr/documents",
    "Enercoop": "https://faq.enercoop.fr/hc/fr/articles/360024967152-Annexes-tarifaires",
    "Engie": "https://particuliers.engie.fr/electricite.html",
    "Ilek": "https://www.ilek.fr/grilles-tarifaires",
    "Happ-e": "https://www.happ-e.fr/nos-offres",
    "GEG": "https://www.geg.fr/offres",
    "La Bellenergie": "https://labellenergie.fr/offre-electricite-verte/",
    "Llum": "https://llum.fr/nos-offres",
    "Mint Énergie": "https://www.mint-energie.com/Pages/Informations/tarifs_elec.aspx",
    "Octopus Energy": "https://octopusenergy.fr/offre-electricite-tarifs",
    "Ohm Énergie": "https://ohm-energie.com/offre/electricite",
    "Plénitude": "https://eniplenitude.fr/offre-plenifix?option=commodity-1",
}

# Sélecteurs spécifiques
SELECTEURS_PDF = {
    "Engie": "text=Détails & Tarifs",
    "Happ-e": "text=Grille tarifaire",
    "GEG": "text=VOIR LES TARIFS",
    "Plénitude": "text=Voir la fiche",
}

# === OUTILS ===
def envoyer_mail(sujet, corps_html):
    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_EMAIL
    msg["Subject"] = sujet
    msg.attach(MIMEText(corps_html, "html", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print("✅ Mail envoyé avec succès.")
    except Exception as e:
        print(f"❌ Erreur envoi mail : {e}")


def charger_state():
    if not os.path.exists(PDF_STATE_FILE):
        return {}
    try:
        with open(PDF_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def sauver_state(state):
    with open(PDF_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def safe_filename(url):
    name = os.path.basename(urlparse(url).path)
    return name or f"file_{hashlib.md5(url.encode()).hexdigest()}.pdf"


def ensure_archive_folder():
    folder = os.path.join(ARCHIVE_ROOT, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(folder, exist_ok=True)
    return folder


def try_handle_cookies(page):
    try:
        page.click("button:has-text('Tout accepter')", timeout=3000)
        print("   🍪 Cookies acceptés.")
    except Exception:
        try:
            page.evaluate("""() => {
                document.querySelectorAll('[id*="cookie"],[class*="cookie"],.consent').forEach(e => e.remove());
            }""")
            print("   🧹 Bannière cookies supprimée.")
        except Exception:
            pass


def find_pdf_links(page, base_url):
    try:
        links = page.eval_on_selector_all("a[href$='.pdf']", "els => els.map(e => e.href)")
    except Exception:
        return []

    cleaned = []
    for link in links:
        if not link:
            continue
        low = link.lower()

        if any(x in low for x in ["cgv", "condition", "mentions"]):
            continue

        if not link.startswith("http"):
            link = urljoin(base_url, link)

        cleaned.append(link)

    return list(dict.fromkeys(cleaned))


def download_pdf(context, url, filename):
    r = context.request.get(url)
    if r.status != 200:
        raise Exception(f"HTTP {r.status}")
    data = r.body()
    with open(filename, "wb") as f:
        f.write(data)
    return data


def main():
    print("⚡ Surveillance des grilles ÉLECTRICITÉ (v1.0)\n")

    state = charger_state()
    new_state = state.copy()
    changes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        for provider, url in FOURNISSEURS_ELEC.items():
            print(f"🔎 {provider} → {url}")

            try:
                page.goto(url, timeout=90000)
                page.wait_for_load_state("load")
            except:
                print("   ❌ Erreur chargement page")
                continue

            try_handle_cookies(page)

            links = find_pdf_links(page, url)

            if not links:
                print("   ⚠️ Aucun PDF trouvé.")
                continue

            folder = ensure_archive_folder()

            for link in links:
                filename = safe_filename(link)
                fullpath = os.path.join(folder, filename)

                try:
                    data = download_pdf(context, link, fullpath)
                except Exception as e:
                    print(f"   ❌ Erreur DL PDF : {e}")
                    continue

                h = sha256_bytes(data)
                prev = state.get(link)

                new_state[link] = h

                if prev != h:
                    changes.append((provider, filename, link))
                    add_entry(provider, filename, link)
                    print(f"   📄 Nouveau PDF : {filename}")
                else:
                    print(f"   ✅ PDF inchangé : {filename}")

        browser.close()

    sauver_state(new_state)

    if changes:
        html = "<h2>Nouvelles grilles ÉLECTRICITÉ détectées</h2><ul>"
        for prov, fname, link in changes:
            html += f"<li><b>{prov}</b> → {fname}<br><a href='{link}'>{link}</a></li>"
        html += "</ul>"
        envoyer_mail("🚨 Nouvelle publication détectée : grilles ÉLECTRICITÉ mises à jour", html)
    else:
        print("\n📢 Aucun changement ÉLECTRICITÉ.")
        if ALWAYS_NOTIFY:
            envoyer_mail("Électricité : RAS", "<p>⚡Aucune nouvelle grille détectée, Tu peux boire ton café tranquille, tout est stable...</p>")


if __name__ == "__main__":
    main()
