import os
import json
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


# =========================
#   CONFIG EMAIL GMAIL
# =========================

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "johan.faydherbe@gmail.com"
SMTP_PASS = "nykmkclnagsabysh"  # mot de passe d’application Gmail
ALERT_EMAIL = "johan.faydherbe@gmail.com"

# Envoie aussi un mail même s’il n’y a aucun changement
ALWAYS_NOTIFY = True


# =========================
#   DOSSIERS LOCAUX
# =========================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

HASH_FILE = os.path.join(DATA_DIR, "watch_tarifs_hashes.json")


# =========================
#   FOURNISSEURS SUIVIS
# =========================

FOURNISSEURS = {
    "Ohm Énergie": "https://www.ohm-energie.com/electricite/offres",
    "Ohm Énergie (CGV)": "https://www.ohm-energie.com/cgv",
    "EDF": "https://www.edf.fr/particuliers/offres-d-electricite",
    "TotalEnergies": "https://www.totalenergies.fr/particuliers/electricite-gaz",
    "Ekwateur": "https://www.ekwateur.com/energie/",
    "Alpiq": "https://www.alpiq.fr/offres-electricite-particuliers",
    "Alterna": "https://www.alterna.fr/offres",
    "Dyneff": "https://www.dyneff.fr/particuliers/offres",
    "Elecocite": "https://www.elecocite.fr/offres",
    "Elmy": "https://www.elmy.fr/offres",
    "Enercoop": "https://www.enercoop.fr/particuliers/offres/",
    "Gedia": "https://www.gedia.fr/offres",
    "GEG": "https://www.geg.fr/particuliers/offres",
    "Happ-e": "https://www.happ-e.fr/offres",
    "La Bellenergie": "https://www.labellenergie.fr/offres",
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
    "Urban Solar Energy": "https://www.urbansolarenergy.fr/offres-electricite/"
}


# =========================
#   ENVOI EMAIL (VERSION TESTÉE)
# =========================

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


# =========================
#   GESTION DES HASHES
# =========================

def charger_hashes():
    if not os.path.exists(HASH_FILE):
        return {}
    try:
        with open(HASH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def sauver_hashes(hashes):
    with open(HASH_FILE, "w", encoding="utf-8") as f:
        json.dump(hashes, f, ensure_ascii=False, indent=2)


# =========================
#   RÉCUPÉRATION DU CONTENU
# =========================

def snapshot_page(page, url):
    page.goto(url, timeout=45000, wait_until="load")
    page.wait_for_timeout(3000)
    return page.content()


# =========================
#   LOGIQUE PRINCIPALE
# =========================

def main():
    print("⚡ Surveillance des offres fournisseurs avec alerte mail\n")

    anciens_hashes = charger_hashes()
    nouveaux_hashes = {}
    changements = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for nom, url in FOURNISSEURS.items():
            print(f"🔎 {nom} → {url}")
            try:
                html = snapshot_page(page, url)
                h = hashlib.sha256(html.encode("utf-8")).hexdigest()
                nouveaux_hashes[nom] = h

                if nom not in anciens_hashes:
                    print("   📥 Première sauvegarde.")
                    changements.append((nom, url, "nouveau"))
                elif anciens_hashes[nom] != h:
                    print("   ⚡ Contenu modifié depuis le dernier scan.")
                    changements.append((nom, url, "modifié"))
                else:
                    print("   ✅ Aucun changement.")

            except PWTimeout:
                print("   ❌ Timeout (page lente ou bloquée).")
            except Exception as e:
                print(f"   ❌ Erreur inattendue : {e}")

        browser.close()

    sauver_hashes(nouveaux_hashes)

    # Envoi du mail selon les résultats
    if changements:
        lignes = ["<b>Les fournisseurs suivants ont modifié leurs pages d’offres :</b><br><ul>"]
        for nom, url, nature in changements:
            lignes.append(f"<li><b>{nom}</b> : <a href='{url}'>{url}</a> ({nature})</li>")
        lignes.append("</ul>")
        envoyer_mail("⚡ Nouvelle grille ou changement détecté", "<br>".join(lignes))
    else:
        print("\n📢 Aucun changement détecté.")
        if ALWAYS_NOTIFY:
            envoyer_mail(
                "✅ Surveillance tarifs : RAS",
                "Aucun changement détecté sur les pages d’offres surveillées.<br>Tout est calme côté fournisseurs."
            )


if __name__ == "__main__":
    main()
