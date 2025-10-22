import sqlite3
import pandas as pd
import os

DB_PATH = "data/tarifs.db"

def init_db():
    if not os.path.exists("data"):
        os.mkdir("data")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tarifs (
            fournisseur TEXT,
            offre TEXT,
            prix_kwh REAL,
            abonnement REAL,
            date_scrape TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def sauvegarder_tarifs(fournisseur, df):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    df["fournisseur"] = fournisseur
    df.to_sql("tarifs", conn, if_exists="append", index=False)
    conn.close()
