import pandas as pd
from playwright.sync_api import sync_playwright

class BaseScraper:
    NOM_FOURNISSEUR = None
    URL = None
    SELECTEUR_TABLE = "table"

    def __init__(self):
        self.data = []

    def fetch_page(self):
        """
        Ouvre la page avec Playwright et retourne le HTML complet.
        On attend que le réseau soit inactif plutôt qu'un sélecteur précis,
        pour éviter les timeouts sur les sites qui chargent en JavaScript.
        """
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(self.URL, timeout=60000)
            page.wait_for_load_state("networkidle")  # Attend que tout le JS ait fini
            html = page.content()
            browser.close()
        return html

    def parse(self, html):
        """
        À surcharger dans chaque sous-classe.
        Doit renvoyer un DataFrame pandas contenant les colonnes principales.
        """
        raise NotImplementedError("La méthode parse() doit être implémentée dans le scraper spécifique.")

    def scrape(self):
        """
        Méthode principale : télécharge la page et retourne un DataFrame
        avec les données extraites et le nom du fournisseur.
        """
        print(f"Scraping {self.NOM_FOURNISSEUR}...")
        html = self.fetch_page()
        df = self.parse(html)
        df["Fournisseur"] = self.NOM_FOURNISSEUR
        print(f"{self.NOM_FOURNISSEUR} : {len(df)} lignes extraites.")
        return df
