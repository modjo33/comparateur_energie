import pandas as pd
import pdfplumber
import io
import re
import requests
from playwright.sync_api import sync_playwright

class HappeScraper:
    NOM_FOURNISSEUR = "Happ-e"
    PAGE_URL = "https://www.happ-e.fr/offre-electricite/"
    FALLBACK_PDF = "https://www.happ-e.fr/content/dam/happe-public/pdf/grille_tarifaire.pdf"

    def scrape(self):
        print(f"Scraping {self.NOM_FOURNISSEUR}...")

        pdf_url = None
        try:
            # Étape 1 : tentative de détection automatique sur la page
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.PAGE_URL, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle")
                links = page.eval_on_selector_all("a", "els => els.map(e => e.href)")
                browser.close()
            pdf_links = [l for l in links if l and ".pdf" in l.lower()]
            if pdf_links:
                pdf_url = pdf_links[0]
                print(f"PDF détecté automatiquement : {pdf_url}")
            else:
                print("Aucun lien PDF détecté. Utilisation du lien de secours.")
                pdf_url = self.FALLBACK_PDF
        except Exception as e:
            print(f"Erreur Playwright : {e}")
            print("Utilisation du lien de secours.")
            pdf_url = self.FALLBACK_PDF

        # Étape 2 : téléchargement avec en-tête "navigateur"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        print(f"Téléchargement du PDF depuis {pdf_url} ...")
        response = requests.get(pdf_url, headers=headers, allow_redirects=True)
        response.raise_for_status()

        # Étape 3 : extraction du texte
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            texte = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # Étape 4 : extraction des valeurs de prix
        nombres = re.findall(r"\d+[.,]\d+", texte)
        data = []
        for val in nombres:
            try:
                prix = float(val.replace(",", "."))
                if 0.05 <= prix <= 0.35:
                    data.append(["Offre Happ-e", prix, ""])
            except ValueError:
                continue

        if not data:
            print("Aucune donnée cohérente trouvée dans le PDF.")
            return pd.DataFrame(columns=["Offre", "Prix_kWh", "Abonnement", "Fournisseur"])

        df = pd.DataFrame(data, columns=["Offre", "Prix_kWh", "Abonnement"])
        df["Fournisseur"] = self.NOM_FOURNISSEUR
        print(f"{len(df)} valeurs extraites depuis le PDF.")
        return df
