import requests
from bs4 import BeautifulSoup
import re
import pdfplumber
import pandas as pd
from io import BytesIO

url = "https://www.edf.fr/particuliers/offres-d-electricite/tarif-bleu"
print(f"🔍 Recherche du PDF EDF sur {url}...")

r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

soup = BeautifulSoup(r.text, "html.parser")
pdf_links = [a["href"] for a in soup.find_all("a", href=True) if "tarif" in a["href"].lower() and a["href"].endswith(".pdf")]

if not pdf_links:
    raise ValueError("❌ Aucun lien PDF trouvé sur la page EDF Tarif Bleu.")

pdf_url = pdf_links[0] if pdf_links[0].startswith("https") else "https://www.edf.fr" + pdf_links[0]
print(f"📄 Téléchargement du PDF : {pdf_url}")

r = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
r.raise_for_status()

with pdfplumber.open(BytesIO(r.content)) as pdf:
    data = []
    for i, page in enumerate(pdf.pages):
        table = page.extract_table()
        if not table:
            continue
        for row in table:
            if any(cell for cell in row):
                data.append([i + 1] + row)

df = pd.DataFrame(data)
print(df.head(15).to_string(index=False))

out = "edf_tarif_bleu_auto.csv"
df.to_csv(out, index=False)
print(f"💾 Données enregistrées dans {out}")
