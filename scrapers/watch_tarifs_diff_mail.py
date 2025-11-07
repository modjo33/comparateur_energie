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

# --- Fix d'import pour trouver utils même si on exécute depuis /scrapers ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.log_utils import add_entry  # <-- import maintenant fonctionnel

# === CONFIGURATION ===
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "johan.faydherbe@gmail.com"
SMTP_PASS = "nykmkclnagsabysh"
ALERT_EMAIL = "johan.faydherbe@gmail.com"
ALWAYS_NOTIFY = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

PDF_STATE_FILE = os.path.join(DATA_DIR, "pdf_state.json")
ARCHIVE_ROOT = os.path.join(BASE_DIR, "archives", "pdf")

# === FOURNISSEURS ===
FOURNISSEURS = {
    # Groupe 1
    "Alpiq": "https://particuliers.alpiq.fr/electricite/nos-tarifs",
    "Alterna": "https://alterna-energie.fr/cgv-et-tarifs",
    "Dyneff": "https://dyneff-gaz.fr/offres/contrat-electricite/",
    "Elmy": "https://elmy.fr/documents",
    "Enercoop": "https://faq.enercoop.fr/hc/fr/articles/360024967152-Annexes-tarifaires",

    # Groupe 2
    "Engie": "https://particuliers.engie.fr/electricite.html",
    "Ilek": "https://www.ilek.fr/grilles-tarifaires",
    "Happ-e": "https://www.happ-e.fr/nos-offres",
    "GEG": "https://www.geg.fr/offres",

    # Groupe 3
    "La Bellenergie": "https://labellenergie.fr/offre-electricite-verte/",
    "Llum": "https://llum.fr/nos-offres",
    "Mint Énergie": "https://www.mint-energie.com/Pages/Informations/tarifs_elec.aspx",
    "Octopus Energy": "https://octopusenergy.fr/offre-electricite-tarifs",
    "Ohm Énergie": "https://ohm-energie.com/offre/gaz-et-electricite",
    "Plénitude": "https://eniplenitude.fr/offre-plenifix?option=commodity-1",
}

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
        print(f"❌ Échec envoi mail : {e}")


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


def safe_filename_from_url(url):
    name = os.path.basename(urlparse(url).path)
    if not name:
        name = f"file_{hashlib.sha1(url.encode()).hexdigest()[:8]}.pdf"
    return name


def ensure_archive_folder():
    folder = os.path.join(ARCHIVE_ROOT, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(folder, exist_ok=True)
    return folder


def try_handle_cookies_and_overlays(page):
    try:
        page.click("button:has-text('Tout accepter')", timeout=3000)
        print("   🍪 Cookies acceptés.")
        return
    except Exception:
        pass
    try:
        page.evaluate("""() => {
            const selectors = [
                '#axeptio_overlay','.axeptio_mount',
                '[id*="axeptio"]','[class*="cookie"]',
                '[id*="cookie"]','.cookie-banner','.consent'
            ];
            selectors.forEach(s => document.querySelectorAll(s).forEach(e=>e.remove()));
        }""")
        print("   🧹 Overlays cookies supprimés.")
    except Exception:
        pass


def download_pdf(context, url, save_path):
    r = context.request.get(url)
    if r.status != 200:
        raise Exception(f"HTTP {r.status}")
    data = r.body()
    with open(save_path, "wb") as f:
        f.write(data)
    return data


def find_pdf_links_in_dom(page, base_url=None):
    try:
        links = page.eval_on_selector_all("a[href$='.pdf']", "els => els.map(e => e.href)")
    except Exception:
        links = []
    found = []
    for link in links:
        if not link:
            continue
        low = link.lower()
        if any(x in low for x in ["cgv", "condition", "mention", "cookie", "confidentialite", "retractation", "/cgv/"]):
            print(f"   🚫 Lien ignoré (non tarifaire) : {link}")
            continue
        found.append(link if link.startswith("http") else urljoin(base_url, link))
    return list(dict.fromkeys(found))


def fetch_pdfs(page, context, provider, url, selector=None):
    results = []
    folder = ensure_archive_folder()
    timeout = 120000 if provider in ("Ilek", "GEG", "Elmy") else 60000
    page.goto(url, timeout=timeout, wait_until="load")
    page.wait_for_timeout(3000)
    try_handle_cookies_and_overlays(page)

    # === Cas spécifique GEG (nouvel onglet) ===
    if provider == "GEG" and selector:
        try:
            with context.expect_page() as new_page_info:
                page.click(selector, timeout=10000)
            new_page = new_page_info.value
            new_page.wait_for_load_state("load", timeout=120000)
            try_handle_cookies_and_overlays(new_page)
            links = find_pdf_links_in_dom(new_page, base_url=url)
            for link in links:
                name = safe_filename_from_url(link)
                save_path = os.path.join(folder, name)
                data = download_pdf(context, link, save_path)
                print(f"   🔎 PDF trouvé nouvel onglet : {link}")
                results.append((link, save_path, data))
            return results
        except Exception as e:
            print(f"   ⚠️ GEG nouvel onglet : {e}")

    # === Cas généraux DOM ===
    links = find_pdf_links_in_dom(page, base_url=url)
    for link in links:
        name = safe_filename_from_url(link)
        save_path = os.path.join(folder, name)
        data = download_pdf(context, link, save_path)
        print(f"   🔎 PDF téléchargé depuis DOM : {link}")
        results.append((link, save_path, data))
    return results


def main():
    print("⚡ Surveillance PDF (v2.2 — Groupes 1, 2 et 3 inclus)\n")
    state = charger_state()
    new_state = state.copy()
    changes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(
            accept_downloads=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        for provider, url in FOURNISSEURS.items():
            print(f"🔎 {provider} → {url}")
            selector = SELECTEURS_PDF.get(provider)
            try:
                fetched = fetch_pdfs(page, context, provider, url, selector)
                if not fetched:
                    print(f"   ⚠️ Aucun PDF détecté pour {provider}.")
                    continue
                for pdf_url, path, data in fetched:
                    h = sha256_bytes(data)
                    prev = state.get(pdf_url)
                    new_state[pdf_url] = h
                    if h != prev:
                        changes.append((provider, pdf_url, path))
                        add_entry(provider, os.path.basename(path), pdf_url)
                        print(f"   📄 Nouvelle grille détectée : {os.path.basename(path)}")
                    else:
                        print(f"   ✅ PDF inchangé : {os.path.basename(path)}")
            except PWTimeout:
                print(f"   ❌ Timeout pour {provider}")
            except Exception as e:
                print(f"   ❌ Erreur inattendue {provider}: {e}")

        browser.close()

    sauver_state(new_state)

    if changes:
        html = [
            "<h2 style='color:#0055cc'>⚡ Nouvelles grilles tarifaires détectées</h2>",
            "<table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse;font-family:sans-serif'>",
            "<tr style='background:#eaeaea'><th>Fournisseur</th><th>Fichier</th><th>URL</th></tr>",
        ]
        for prov, url, path in changes:
            html.append(f"<tr><td><b>{prov}</b></td><td>{os.path.basename(path)}</td><td><a href='{url}'>{url}</a></td></tr>")
        html.append("</table>")
        envoyer_mail("⚡ Nouvelles grilles tarifaires détectées", "\n".join(html))
    else:
        print("\n📢 Aucun changement détecté.")
        if ALWAYS_NOTIFY:
            envoyer_mail("✅ Surveillance PDF : RAS", "<p>Aucun changement détecté sur les grilles tarifaires aujourd’hui.</p>")


if __name__ == "__main__":
    main()
