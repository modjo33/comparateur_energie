from playwright.sync_api import sync_playwright
import pandas as pd

NOM_FOURNISSEUR = "EDF"

def scrape():
    url = "https://www.edf.fr/particuliers/contrat-et-conso/gerer-mon-contrat/tarif-bleu"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_selector("table")

        tables = page.query_selector_all("table")
        if not tables:
            print("Aucune table trouvée sur la page.")
            browser.close()
            return pd.DataFrame(columns=["Offre", "Prix_kWh", "Abonnement"])

        data = []
        for table in tables:
            rows = table.query_selector_all("tr")
            for row in rows[1:]:
                cols = [col.inner_text().strip() for col in row.query_selector_all("td")]
                if len(cols) >= 3:
                    data.append(cols[:3])

        browser.close()

    if not data:
        print("Données vides (structure EDF changée ?)")
        return pd.DataFrame(columns=["Offre", "Prix_kWh", "Abonnement"])

    df = pd.DataFrame(data, columns=["Offre", "Prix_kWh", "Abonnement"])
    return df
 