import requests
import pandas as pd

url = "https://ekwateur.fr/api/price/electricity"
print(f"🔍 Lecture de {url}...")

r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

data = r.json()

rows = []
for offer in data:
    rows.append({
        "Offre": offer.get("offer_name"),
        "Type": offer.get("offer_type"),
        "Prix_HT": offer.get("price_ht"),
        "Prix_TTC": offer.get("price_ttc"),
        "Puissance": offer.get("power"),
    })

df = pd.DataFrame(rows)
print(df.head())

df.to_csv("ekwateur_api_tarifs.csv", index=False)
print("💾 Données enregistrées dans ekwateur_api_tarifs.csv")
