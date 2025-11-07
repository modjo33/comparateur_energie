import os
import sqlite3
from datetime import datetime

# ===== CONFIG =====
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "state.db")


# ===== INITIALISATION =====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Table principale : fichiers PDF
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pdf_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            chemin_fichier TEXT,
            date_detectee TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Table secondaire : logs d'exécution
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            fournisseur TEXT,
            action TEXT,
            resultat TEXT,
            details TEXT
        )
    """)

    conn.commit()
    conn.close()


# ===== FONCTIONS PDF =====
def get_hash_for_url(url: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT hash FROM pdf_files WHERE url = ?", (url,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def insert_or_update_pdf(fournisseur, url, hash, chemin):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pdf_files (fournisseur, url, hash, chemin_fichier, date_detectee)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            hash = excluded.hash,
            chemin_fichier = excluded.chemin_fichier,
            date_detectee = excluded.date_detectee
    """, (fournisseur, url, hash, chemin, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()


# ===== LOGGING =====
def add_log(fournisseur, action, resultat, details=""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO logs (fournisseur, action, resultat, details)
        VALUES (?, ?, ?, ?)
    """, (fournisseur, action, resultat, details))
    conn.commit()
    conn.close()
