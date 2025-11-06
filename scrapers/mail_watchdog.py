import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import re

# --- Config identique à ton watcher principal ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "johan.faydherbe@gmail.com"
SMTP_PASS = "nykmkclnagsabysh"
ALERT_EMAIL = "johan.faydherbe@gmail.com"

# --- Chemin du log principal ---
LOG_FILE = "/mnt/c/Users/johan/Downloads/scraper_hp_hc/switchloopfinal/pdf_tarifs/logs/watch_tarifs.log"


def resume_depuis_log(contenu: str) -> str:
    """
    Analyse rapide du log pour générer un résumé propre :
    - compte les grilles détectées
    - liste les fournisseurs concernés
    """
    resume = []
    lignes = contenu.splitlines()

    grilles = [l for l in lignes if "Nouvelle grille" in l]
    inchanges = [l for l in lignes if "PDF inchangé" in l]
    erreurs = [l for l in lignes if "Erreur" in l or "❌" in l]
    fournisseurs = set()

    for ligne in lignes:
        match = re.search(r"🔎 (.+?) →", ligne)
        if match:
            fournisseurs.add(match.group(1).strip())

    total_grilles = len(grilles)
    total_fournisseurs = len(fournisseurs)

    resume.append(f"👀 Fournisseurs analysés : <b>{total_fournisseurs}</b>")
    resume.append(f"📄 Nouvelles grilles détectées : <b>{total_grilles}</b>")
    resume.append(f"✅ PDF inchangés : {len(inchanges)}")
    resume.append(f"⚠️ Erreurs détectées : {len(erreurs)}")

    if grilles:
        resume.append("<hr><b>Détails des nouvelles grilles :</b><ul>")
        for l in grilles[:10]:
            resume.append(f"<li>{l}</li>")
        resume.append("</ul>")
    elif erreurs:
        resume.append("<hr><b>Erreurs relevées :</b><ul>")
        for l in erreurs[:5]:
            resume.append(f"<li>{l}</li>")
        resume.append("</ul>")
    else:
        resume.append("<p>Tout est calme. Aucun changement majeur.</p>")

    return "<br>".join(resume)


def envoyer_mail_watchdog():
    if not os.path.exists(LOG_FILE):
        print("⚠️ Aucun log à envoyer.")
        return

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        contenu_log = f.read()

    resume_html = resume_depuis_log(contenu_log)

    msg = MIMEMultipart()
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_EMAIL
    msg["Subject"] = "📋 Rapport surveillance grilles tarifaires"

    corps_html = MIMEText(
        f"<h2>Rapport automatique du comparateur</h2>"
        f"<div style='font-family:Arial,sans-serif;font-size:14px;'>{resume_html}</div>"
        f"<br><p style='color:gray;'>Fichier de log complet en pièce jointe.</p>",
        "html",
        "utf-8",
    )
    msg.attach(corps_html)

    # Ajout du fichier log complet
    with open(LOG_FILE, "rb") as f:
        piece = MIMEApplication(f.read(), Name=os.path.basename(LOG_FILE))
    piece["Content-Disposition"] = f'attachment; filename="{os.path.basename(LOG_FILE)}"'
    msg.attach(piece)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print("✅ Rapport détaillé envoyé avec succès.")
    except Exception as e:
        print(f"❌ Échec envoi rapport : {e}")


if __name__ == "__main__":
    envoyer_mail_watchdog()
