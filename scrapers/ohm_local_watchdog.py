#!/usr/bin/env python3
# coding: utf-8

import os
import time
import pandas as pd
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scrapers.ohm_pdf_v2 import OhmPDFV2

# Chemin du dossier surveillé
WATCH_DIR = "/mnt/c/Users/johan/OneDrive/Documents/ELECTRICITE PARTICULIER/OHM ENERGIE/"

def find_pdfs(path):
    pdfs = []
    for root, _, files in os.walk(path):
        for f in files:
            if f.lower().endswith(".pdf") and "ohm" in f.lower():
                pdfs.append(os.path.join(root, f))
    return pdfs

def main():
    print(f"🔍 Scan du dossier local : {WATCH_DIR}")
    pdfs = find_pdfs(WATCH_DIR)
    if not pdfs:
        print("⚠️ Aucun fichier PDF Ohm trouvé.")
        return

    print(f"📄 {len(pdfs)} fichier(s) trouvé(s) :")
    for f in pdfs:
        print("  -", os.path.basename(f))

    s = OhmPDFV2()
    df = s.scrape_from_files(pdfs)

    if df.empty:
        print("⚠️ Aucune donnée exploitable extraite.")
        return

    output_file = os.path.join(WATCH_DIR, f"ohm_tarifs_extraits_{time.strftime('%Y%m%d')}.csv")
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"✅ Extraction terminée. Données enregistrées dans : {output_file}")

if __name__ == "__main__":
    main()
