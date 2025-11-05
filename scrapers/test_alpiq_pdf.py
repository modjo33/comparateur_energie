import requests, pdfplumber, io

url = "https://particuliers.alpiq.fr/grille-tarifaire/particuliers/gtr_elec_part.pdf"
response = requests.get(url)
response.raise_for_status()

with pdfplumber.open(io.BytesIO(response.content)) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"\n----- PAGE {i+1} -----\n")
        texte = page.extract_text() or ""
        print(texte[:1500])  # on affiche juste les 1500 premiers caractères
