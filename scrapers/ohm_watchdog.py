#!/usr/bin/env python3
# coding: utf-8
"""
ohm_watchdog.py
Surveille la page CGV d'Ohm Énergie et signale l'apparition de nouveaux PDF.
- Utilise requests avec headers "humains".
- Si échec ou pas de PDFs, bascule sur Playwright (navigateur headless).
- Sauvegarde un cache JSON et affiche les nouveaux liens.
- Optionnel : envoi d'email si variables d'environnement SMTP renseignées.

Usage:
    python scrapers/ohm_watchdog.py
"""

import os
import re
import json
import requests
from datetime import datetime

CACHE_FILENAME = "ohm_pdf_cache.json"
PAGE_URL = "https://www.ohm-energie.com/cgv/"
REQUEST_TIMEOUT = 20  # secondes


class OhmWatchdog:
    def __init__(self, page_url=PAGE_URL, cache_file=CACHE_FILENAME):
        self.page_url = page_url
        # placer le cache dans le même dossier que ce script (pratique pour cron)
        base = os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(base, cache_file)

    def fetch_pdf_links_requests(self):
        """Récupère les liens PDF en utilisant requests + headers pour ressembler à un navigateur."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }
        try:
            r = requests.get(self.page_url, headers=headers, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
        except Exception as e:
            print(f"❌ Erreur requests -> {self.page_url}: {e}")
            return [], e
        html = r.text
        pdfs = re.findall(r'https?://[^\s"\'<>]+\.pdf', html, flags=re.IGNORECASE)
        pdfs = sorted(set(pdfs))
        return pdfs, None

    def fetch_pdf_links_playwright(self):
        """Fallback : charge la page via Playwright (headless) et extrait les PDFs."""
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            print("⚠️ Playwright non installé ou import échoué :", e)
            return [], e

        pdfs = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0 Safari/537.36"
                ))
                page = context.new_page()
                page.goto(self.page_url, timeout=45000)
                # attendre le rendu raisonnable
                page.wait_for_load_state("networkidle", timeout=30000)
                html = page.content()
                browser.close()
                pdfs = re.findall(r'https?://[^\s"\'<>]+\.pdf', html, flags=re.IGNORECASE)
                pdfs = sorted(set(pdfs))
        except Exception as e:
            return [], e
        return pdfs, None

    def load_cache(self):
        if not os.path.exists(self.cache_file):
            return []
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("pdfs", [])
        except Exception:
            return []

    def save_cache(self, pdfs):
        payload = {"timestamp": datetime.now().isoformat(), "pdfs": pdfs}
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print("Erreur sauvegarde cache :", e)

    def notify_new_pdfs(self, new_pdfs):
        """Affiche les nouveaux PDFs. Add hooks here for email/Slack/etc."""
        print("\n🚨 NOUVEAUX PDF DÉTECTÉS :")
        for p in new_pdfs:
            print(" ➕", p)

        # Exemples de points d'extension :
        # - send_mail(subject, body)  # implémenter plus bas si tu veux SMTP
        # - appeler un webhook Slack/Discord
        # - télécharger automatiquement le PDF vers ton dossier local

    def check_for_updates(self, try_playwright=True):
        print(f"🔍 Vérification des grilles Ohm sur {self.page_url}")
        pdfs, err = self.fetch_pdf_links_requests()
        if err or not pdfs:
            if err:
                print("Requests a échoué (ou renvoyé erreur).")
            else:
                print("Requests n'a trouvé aucun PDF.")
            if try_playwright:
                print("➡️ Tentative via Playwright (fallback)...")
                pdfs, pw_err = self.fetch_pdf_links_playwright()
                if pw_err:
                    print("Playwright erreur :", pw_err)
        if not pdfs:
            print("⚠️ Aucun lien PDF trouvé (après fallback).")
            return False

        previous = self.load_cache()
        new = [p for p in pdfs if p not in previous]
        removed = [p for p in previous if p not in pdfs]

        if new or removed:
            if new:
                self.notify_new_pdfs(new)
            if removed:
                print("\n🗑️ PDF supprimés depuis la dernière vérification :")
                for p in removed:
                    print(" ➖", p)
            # mettre à jour le cache
            self.save_cache(pdfs)
            return True
        else:
            print("✅ Aucune nouvelle grille depuis la dernière vérification.")
            return False


# --------------------------
# Optionnel : envoi d'e-mail (SMTP)
# Pour l'activer, définir les variables d'environnement suivantes :
#   OHM_SMTP_HOST, OHM_SMTP_PORT, OHM_SMTP_USER, OHM_SMTP_PASS, OHM_SMTP_TO
# --------------------------
def send_mail_smtp(subject: str, body: str):
    import os
    import smtplib
    from email.message import EmailMessage

    host = os.environ.get("OHM_SMTP_HOST")
    port = int(os.environ.get("OHM_SMTP_PORT", "587"))
    user = os.environ.get("OHM_SMTP_USER")
    pwd = os.environ.get("OHM_SMTP_PASS")
    recipient = os.environ.get("OHM_SMTP_TO")

    if not (host and user and pwd and recipient):
        print("ℹ️ SMTP non configuré. Configure OHM_SMTP_* pour activer l'e-mail.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = recipient
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
        print("✅ Email envoyé à", recipient)
        return True
    except Exception as e:
        print("Erreur envoi SMTP :", e)
        return False


if __name__ == "__main__":
    wd = OhmWatchdog()
    changed = wd.check_for_updates(try_playwright=True)

    # Exemple : envoyer un mail si changement
    if changed:
        # Compose simple notification
        prev = wd.load_cache()  # cache déjà mis à jour par check_for_updates
        body = f"Changements détectés sur {PAGE_URL}\nVoir {wd.cache_file}"
        # Si tu veux envoyer, décommente la ligne suivante (et configure OHM_SMTP_*)
        # send_mail_smtp("Ohm: nouvelle grille détectée", body)
