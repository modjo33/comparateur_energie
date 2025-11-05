#!/usr/bin/env python3
import os
import re
import fitz  # PyMuPDF
import pandas as pd
import pytesseract
from PIL import Image
import io

class OhmPDFV10:
    """
    Extraction OCR fiable des grilles tarifaires Ohm Énergie
    basée sur PyMuPDF + Tesseract.
    Moins sexy que PaddleOCR, mais au moins ça ne plante pas à chaque version.
    """

    def __init__(self):
        self.fournisseur = "Ohm Énergie"

    def pdf_to_images(self, pdf_path):
        """Convertit les pages PDF en images PIL (300 DPI)."""
        images = []
        with fitz.open(pdf_path) as doc:
            for i, page in enumerate(doc):
                print(f"📄 Conversion page {i+1}/{len(doc)} en image...")
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                images.append(img)
        return images

    def ocr_page(self, image):
        """Effectue l’OCR sur une image et retourne le texte brut."""
        text = pytesseract.image_to_string(image, lang="fra")
        return text

    def extract_data_from_text(self, text, offre_label):
        """
        Recherche dans le texte brut les lignes de type :
        - Puissance : "3 kVA", "6 kVA", etc.
        - Prix : "4,50 €", "0.156 €/kWh", etc.
        """
        power_re = re.compile(r"(\d{1,2})\s*kva", re.I)
        price_re = re.compile(r"(\d+[.,]\d{2})\s*€", re.I)

        rows = []
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            if "kva" not in line.lower():
                continue

            m_p = power_re.search(line)
            if not m_p:
                continue

            puissance = f"{m_p.group(1)} kVA"
            context = " ".join(lines[i:i+4])  # quelques lignes autour
            prices = price_re.findall(context)

            for val_str in prices:
                try:
                    val = float(val_str.replace(",", "."))
                except ValueError:
                    continue

                # Heuristique pour deviner le type et l’unité
                if val > 1.5:
                    unit = "€/mois"
                    type_tarif = "Abonnement"
                else:
                    unit = "€/kWh"
                    type_tarif = "Énergie"

                rows.append({
                    "Fournisseur": self.fournisseur,
                    "Offre": offre_label,
                    "Type": type_tarif,
                    "Puissance": puissance,
                    "Valeur": val,
                    "Unité": unit,
                    "Prix_HT": round(val / 1.20, 4),
                    "Prix_TTC": val
                })
        return rows

    def scrape_from_files(self, file_list):
        all_rows = []

        for pdf_path in file_list:
            if not os.path.exists(pdf_path):
                print(f"❌ Fichier manquant : {pdf_path}")
                continue

            offre_label = re.sub(
                r"grille|tarifaire|ohm|energie|elec|pdf|_|-|[0-9]",
                "",
                os.path.basename(pdf_path),
                flags=re.I
            ).strip().title() or "Ohm"

            print(f"\n🔍 Lecture OCR : {os.path.basename(pdf_path)} ({offre_label})...")
            images = self.pdf_to_images(pdf_path)

            for page_idx, img in enumerate(images, start=1):
                print(f"🧠 OCR page {page_idx}/{len(images)}...")
                text = self.ocr_page(img)
                rows = self.extract_data_from_text(text, offre_label)
                all_rows.extend(rows)

        if not all_rows:
            print("⚠️ Aucun texte exploitable trouvé.")
            return pd.DataFrame()

        df = pd.DataFrame(all_rows)
        df = df.drop_duplicates(subset=["Fournisseur", "Offre", "Puissance", "Type", "Prix_TTC"])
        print(f"✅ Extraction terminée : {len(df)} lignes trouvées.")
        return df


if __name__ == "__main__":
    import glob

    BASE_DIR = "/mnt/c/Users/johan/OneDrive/Documents/ELECTRICITE PARTICULIER/OHM ENERGIE"
    files = glob.glob(os.path.join(BASE_DIR, "*.pdf"))

    if not files:
        print(f"❌ Aucun PDF trouvé dans {BASE_DIR}")
    else:
        scraper = OhmPDFV10()
        df = scraper.scrape_from_files(files)

        if df.empty:
            print("❌ Aucun tarif détecté.")
        else:
            print(df.to_string(index=False))
            out_csv = os.path.join(BASE_DIR, "ohm_tarifs_v10.csv")
            df.to_csv(out_csv, index=False)
            print(f"\n💾 Résultats enregistrés dans {out_csv}")
