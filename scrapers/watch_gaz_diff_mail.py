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

# --- Fix import utils ---
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.log_utils import add_entry

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

PDF_STATE_FILE = os.path.join(DATA_DIR, "pdf_state_gaz.json")
ARCHIVE_ROOT = os.path.join(BASE_DIR, "archives", "pdf_gaz")

# === FOURNISSEURS GAZ ===
FOURNISSEURS_GAZ = {
    "Dyneff": "https://dyneff-gaz.fr/offres/contrat-electricite/",
    "Engie": "https://particuliers.engie.fr/electricite.html",
    "GEG": "https://www.geg.fr/offres",
    "Ohm Énergie": "https://ohm-energie.com/offre/gaz-et-electricite",
    "Plénitude": "https://eniplenitude.fr/offre-plenifix?option=commodity-1",
    "Mint Énergie": "https://www.mint-energie.com/Pages/Informations/tarifs_elec.aspx",
    "TotalEnergies": "https://www.totalenergies.fr/particuliers/electricite-gaz/offres-particuliers",
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
        print("✅ Mail gaz envoyé avec succès.")
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
        if any(x in low for x in ["cgv", "condition", "mention", "cookie", "confidentialite", "retractation"]):
            print(f"   🚫 Lien ignoré (non tarifaire) : {link}")
            continue
        found.append(link if link.startswith("http") else urljoin(base_url, link))
    return list(dict.fromkeys(found))

def pdf_contient_gaz(path):
    try:
        with open(path, "rb") as f:
            content = f.read().lower()
        keywords = [b"gaz", b"grdf", b"zone tarifaire", b"tarif gaz", b"gaz naturel", b"gaz & electricite", b"offre gaz"]
        return any(k in content for k in keywords)
    except Exception:
        return False

def fetch_totalenergies_pdf(context, page):
    """Recherche du lien PDF gaz TotalEnergies via analyse du nom de fichier."""
    print("   🔍 Recherche approfondie du lien PDF GAZ (analyse du texte et du nom du fichier)…")
    base_url = "https://www.totalenergies.fr"
    try:
        page.goto("https://www.totalenergies.fr/particuliers/electricite-gaz/offres-particuliers", timeout=90000)
        page.wait_for_timeout(4000)
        try_handle_cookies_and_overlays(page)

        # Récupère tous les liens PDF
        link_elements = page.query_selector_all("a[href$='.pdf']")
        candidats = []
        for a in link_elements:
            try:
                href = a.get_attribute("href")
                if not href:
                    continue
                text = (a.inner_text() or "").strip().lower()
                full_url = href if href.startswith("http") else urljoin(base_url, href)
                name = os.path.basename(urlparse(full_url).path).lower()

                # Mots-clés GAZ ou PDF tarifaire
                mots_cles = ["gaz", "grille", "tarif", "heures", "eco"]
                if any(mc in text for mc in mots_cles) or any(mc in name for mc in mots_cles):
                    candidats.append(full_url)
                    print(f"   🔎 Lien PDF candidat : {full_url}")
            except Exception:
                continue

        if not candidats:
            print("   ⚠️ Aucun lien PDF détecté, même élargi.")
            return None

        # Si plusieurs candidats, on filtre les plus probables
        candidats_gaz = [l for l in candidats if "gaz" in l.lower()]
        if candidats_gaz:
            print(f"   ✅ Lien PDF GAZ sélectionné : {candidats_gaz[0]}")
            return candidats_gaz[0]

        # Sinon, prend le plus récent contenant 'tarif' ou 'grille'
        for c in candidats:
            if "tarif" in c or "grille" in c:
                print(f"   ✅ Lien PDF tarifaire sélectionné (probable GAZ) : {c}")
                return c

        print("   ⚠️ Aucun lien correspondant trouvé malgré analyse étendue.")
        return None

    except Exception as e:
        print(f"   ❌ Erreur recherche TotalEnergies : {e}")
        return None

def fetch_pdfs(page, context, provider, url):
    results = []
    folder = ensure_archive_folder()

    # Cas spécial : TotalEnergies (recherche dynamique)
    if provider == "TotalEnergies":
        link = fetch_totalenergies_pdf(context, page)
        if not link:
            return results
        name = safe_filename_from_url(link)
        save_path = os.path.join(folder, name)
        data = download_pdf(context, link, save_path)
        results.append((link, save_path, data))
        return results

    # Cas classique
    page.goto(url, timeout=90000, wait_until="load")
    page.wait_for_timeout(3000)
    try_handle_cookies_and_overlays(page)

    links = find_pdf_links_in_dom(page, base_url=url)
    for link in links:
        name = safe_filename_from_url(link)
        save_path = os.path.join(folder, name)
        data = download_pdf(context, link, save_path)
        print(f"   🔎 PDF téléchargé depuis DOM : {link}")
        if pdf_contient_gaz(save_path) or provider == "Plénitude":
            results.append((link, save_path, data))
        else:
            print(f"   🚫 Ignoré (pas de contenu gaz) : {name}")
    return results

def main():
    print("🔥 Surveillance des grilles GAZ uniquement (v1.3)\n")
    state = charger_state()
    new_state = state.copy()
    changes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        for provider, url in FOURNISSEURS_GAZ.items():
            print(f"🔎 {provider} → {url}")
            try:
                fetched = fetch_pdfs(page, context, provider, url)
                if not fetched:
                    print(f"   ⚠️ Aucun PDF GAZ trouvé.")
                    continue
                for pdf_url, path, data in fetched:
                    h = sha256_bytes(data)
                    prev = state.get(pdf_url)
                    new_state[pdf_url] = h
                    if h != prev:
                        print(f"   📄 Nouvelle grille GAZ : {os.path.basename(path)}")
                        add_entry(provider, os.path.basename(path), pdf_url)
                        changes.append((provider, pdf_url, path))
                    else:
                        print(f"   ✅ PDF GAZ inchangé : {os.path.basename(path)}")
            except PWTimeout:
                print(f"   ❌ Timeout {provider}")
            except Exception as e:
                print(f"   ❌ Erreur inattendue {provider}: {e}")

        browser.close()

    sauver_state(new_state)

    if changes:
        html = [
            "<h2 style='color:#cc0000'>🔥 Nouvelles grilles GAZ détectées</h2>",
            "<table border='1' cellspacing='0' cellpadding='6' style='border-collapse:collapse;font-family:sans-serif'>",
            "<tr style='background:#eaeaea'><th>Fournisseur</th><th>Fichier</th><th>URL</th></tr>",
        ]
        for prov, url, path in changes:
            html.append(f"<tr><td><b>{prov}</b></td><td>{os.path.basename(path)}</td><td><a href='{url}'>{url}</a></td></tr>")
        html.append("</table>")
        envoyer_mail("🔥 Nouvelles grilles GAZ détectées", "\n".join(html))
    else:
        print("\n📢 Aucun changement GAZ détecté.")
        if ALWAYS_NOTIFY:
            envoyer_mail("✅ Surveillance GAZ : RAS", "<p>Aucune nouvelle grille gaz détectée aujourd’hui.</p>")

if __name__ == "__main__":
    main()
