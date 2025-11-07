import os
import json
from datetime import datetime

# Emplacement du fichier JSON
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
HISTORY_PATH = os.path.join(BASE_DIR, "data", "history.json")

def _load_history():
    """Charge le fichier history.json, ou crée une liste vide si absent."""
    if not os.path.exists(HISTORY_PATH):
        os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        return []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                return []
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_history(data):
    """Sauvegarde la liste mise à jour dans history.json."""
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_entry(fournisseur, nom_fichier, url):
    """
    Ajoute une nouvelle entrée dans le fichier d'historique.
    Chaque entrée contient :
      - date (horodatage)
      - fournisseur
      - nom du fichier
      - url source
    """
    historique = _load_history()

    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fournisseur": fournisseur or "Inconnu",
        "nom_fichier": nom_fichier or "—",
        "url": url or "—"
    }

    historique.append(entry)
    _save_history(historique)


def get_history():
    """Renvoie l'historique complet."""
    return _load_history()


def get_history_by_provider(fournisseur):
    """Renvoie uniquement les entrées d’un fournisseur donné."""
    data = _load_history()
    if fournisseur.lower() == "tous":
        return data
    return [d for d in data if d.get("fournisseur", "").lower() == fournisseur.lower()]
