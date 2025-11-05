import pandas as pd
import re
import io
import requests
import pdfplumber
from playwright.sync_api import sync_playwright

class TotalEnergiesScraper:
    NOM_FOURNISSEUR = "TotalEnergies"
    PAGE_URL = "https://www.totalenergies.fr/particuliers/electricite-et-gaz/offres-electricite"
    PDF_FALLBACK = "https://www.totalenergies.fr/sites/g/files/nytnzq121/files/atoms/files/grille-tarifaire-electricite.pdf"

    def _trouver_pdf(self):
        """Tente de détecter automatiquement un lien PDF sur la page web."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.PAGE_URL, timeout=60000)
            liens = page.query_selector_all("a[href$='.pdf']")
            urls_pdf = [a.get_attribute("href") for a in liens if a.get_attribute("href")]
            browser.close()

        urls_pdf = [u for u in urls_pdf if "tarif" in u.lower() or "grille" in u.lower()]
        if urls_pdf:
            print(f"PDF détecté automatiquement : {urls_pdf[0]}")
            return urls_pdf[0]
        print("Aucun PDF trouvé, utilisation du lien de secours.")
        return self.PDF_FALLBACK

    def _extraire_depuis_pdf(self, pdf_bytes):
        """Lit un PDF et extrait les valeurs de prix et abonnements."""
        data = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            texte = "\n".join(page.extract_text() or "" for page in pdf.pages)

        lignes = texte.splitlines()
        for i, ligne in enumerate(lignes):
            matches = re.findall(r"\d+[.,]\d+", ligne)
            if not matches:
                continue

            for val in matches:
                try:
                    prix = float(val.replace(",", "."))
                    if 0.05 <= prix <= 0.35:
                        data.append(["Offre TotalEnergies", prix, "kWh", ""])
                    elif 8 <= prix <= 60:
                        voisinage = " ".join(lignes[max(0, i-2): i+3])
                        puissance = re.findall(r"\b\d{1,2}\s?kVA\b", voisinage, flags=re.IGNORECASE)
                        puissance = puissance[0] if puissance else ""
                        data.append(["Offre TotalEnergies", prix, "Abonnement", puissance])
                except ValueError:
                    continue

        df = pd.DataFrame(data, columns=["Offre", "Valeur", "Type", "Puissance"])
        df["Fournisseur"] = self.NOM_FOURNISSEUR
        return df

    def scrape(self):
        print(f"Scraping {self.NOM_FOURNISSEUR}...")
        pdf_url = self._trouver_pdf()

        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(pdf_url, headers=headers)
        if r.status_code != 200:
            print(f"Erreur lors du téléchargement du PDF ({r.status_code})")
            return pd.DataFrame(columns=["Offre", "Valeur", "Type", "Puissance", "Fournisseur"])

        df = self._extraire_depuis_pdf(r.content)
        if df.empty:
            print("⚠️ Aucune donnée extraite du PDF.")
        else:
            print(f"{len(df)} valeurs extraites (prix + abonnements).")

        return df
