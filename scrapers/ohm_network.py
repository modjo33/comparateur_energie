import json
import re
import pandas as pd
from datetime import datetime
from playwright.sync_api import sync_playwright


class OhmNetworkScraper:
    NOM_FOURNISSEUR = "Ohm Énergie"
    PAGE_URL = "https://www.ohm-energie.com/offres-electricite"

    def scrape(self):
        print(f"Scraping {self.NOM_FOURNISSEUR} (interception réseau complète)...")
        data = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            def handle_response(response):
                try:
                    content_type = response.headers.get("content-type", "")
                    if any(x in content_type for x in ["json", "javascript", "text"]):
                        body = response.text()
                        if not body:
                            return

                        # recherche de valeurs numériques pertinentes
                        for val in re.findall(r"\d+[.,]\d+", body):
                            fv = float(val.replace(",", "."))
                            if 0.05 <= fv <= 0.6:
                                data.append({
                                    "Offre": self.NOM_FOURNISSEUR,
                                    "Valeur": fv,
                                    "Type": "kWh",
                                    "Puissance": None
                                })
                            elif 8 <= fv <= 80:
                                data.append({
                                    "Offre": self.NOM_FOURNISSEUR,
                                    "Valeur": fv,
                                    "Type": "Abonnement",
                                    "Puissance": None
                                })
                except Exception:
                    pass

            # Interception des réponses
            page.on("response", handle_response)

            # Visite de la page
            page.goto(self.PAGE_URL, timeout=90000)
            page.wait_for_load_state("networkidle")
            browser.close()

        if not data:
            print("Aucune donnée interceptée sur le réseau (endpoints cachés ou chiffrés).")
            return pd.DataFrame(columns=["Offre", "Valeur", "Type", "Puissance", "Fournisseur"])

        df = pd.DataFrame(data)
        df["Fournisseur"] = self.NOM_FOURNISSEUR
        df["Date"] = datetime.now().strftime("%Y-%m-%d")

        print(f"{len(df)} valeurs interceptées sur le réseau.")
        return df.drop_duplicates().reset_index(drop=True)
