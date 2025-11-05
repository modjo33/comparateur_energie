import requests
import pandas as pd
from bs4 import BeautifulSoup

url = "https://www.edf.fr/particuliers/offres-d-electricite/tarif-bleu-contrat"

print(f"🔍 Lecture de {url}...")

r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")

tables = soup.find_all("table")
data = []

for table in tables:
    caption = table.find("caption")
    label = caption.get_text(strip=True) if caption else "Sans titre"
    for row in table.find_all("tr"):
        cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if len(cols) >= 2:
            data.append([label] + cols)

df = pd.DataFrame(data, columns=["Tableau", "Col1", "Col2", "Col3", "Col4", "Col5"])
print(df.head(15).to_string(index=False))

out = "edf_tarif_bleu.csv"
df.to_csv(out, index=False)
print(f"💾 Données enregistrées dans {out}")
