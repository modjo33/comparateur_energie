import pandas as pd
import requests
import pdfplumber
import io
import re
from playwright.sync_api import sync_playwright

class AlpiqScraper:
    NOM_FOURNISSEUR = "Alpiq"
    PAGE_URL = "https://particuliers.alpiq.fr/"
    FALLBACK_PDF = "https://particuliers.alpiq.fr/grille-tarifaire/particuliers/gtr_elec_part.pdf"

    def scrape(self):
        print(f"Scraping {self.NOM_FOURNISSEUR}...")

        pdf_url = None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.PAGE_URL, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle")
                links = page.eval_on_selector_all("a", "els => els.map(e => e.href)")
                browser.close()

            pdf_links = [l for l in links if l and l.lower().endswith(".pdf")]
            if pdf_links:
                pdf_url = pdf_links[0]
                print(f"PDF trouvé automatiquement : {pdf_url}")
            else:
                print("Aucun lien PDF détecté automatiquement. Utilisation du lien de secours.")
                pdf_url = self.FALLBACK_PDF

        except Exception as e:
            print(f"Erreur Playwright (boucle ou blocage probable) : {e}")
            print("Utilisation du lien de secours.")
            pdf_url = self.FALLBACK_PDF

        # Téléchargement du PDF
        response = requests.get(pdf_url, allow_redirects=True)
        response.raise_for_status()

        # Extraction du texte
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            texte = "\n".join(page.extract_text() or "" for page in pdf.pages)

        nombres = re.findall(r"\d+[.,]\d+", texte)
        data = []
        for val in nombres:
            try:
                prix = float(val.replace(",", "."))
                if 0.05 <= prix <= 0.35:
                    data.append(["Offre Alpiq", prix, ""])
            except ValueError:
                continue

        if not data:
            print("Aucune donnée cohérente trouvée dans le PDF.")
            return pd.DataFrame(columns=["Offre", "Prix_kWh", "Abonnement", "Fournisseur"])

        df = pd.DataFrame(data, columns=["Offre", "Prix_kWh", "Abonnement"])
        df["Fournisseur"] = self.NOM_FOURNISSEUR
        print(f"{len(df)} valeurs extraites depuis le PDF.")
        return df
