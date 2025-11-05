import pandas as pd
from datetime import date

COLUMNS_STD = [
    "fournisseur",
    "offre",
    "option_tarifaire",
    "puissance_kVA",
    "type_prix",
    "prix",
    "unite",
    "ttc_ht",
    "source_url",
    "date_scrape",
]

def normaliser(df: pd.DataFrame, fournisseur: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=COLUMNS_STD)

    d = df.copy()

    # Renommage si présent dans le DF brut
    rename_map = {
        "Valeur": "prix",
        "Offre": "offre",
        "Puissance": "puissance_kVA",
        "Type": "type_prix",
        "Option": "option_tarifaire",
        "Source": "source_url",
    }
    for k, v in rename_map.items():
        if k in d.columns:
            d.rename(columns={k: v}, inplace=True)

    # Valeurs par défaut
    if "offre" not in d.columns:
        d["offre"] = f"Offre {fournisseur}"
    d["fournisseur"] = fournisseur

    # type_prix normalisé
    def _map_type(t):
        t = str(t).lower()
        if "kwh" in t:
            return "énergie"
        if "abo" in t or "abonnement" in t:
            return "abonnement"
        return "énergie"  # fallback

    d["type_prix"] = d.get("type_prix", "énergie").apply(_map_type)

    # unité selon type
    d["unite"] = d["type_prix"].apply(lambda x: "€/kWh" if x == "énergie" else "€/mois")

    # ttc/ht inconnu pour l’instant → à enrichir plus tard
    if "ttc_ht" not in d.columns:
        d["ttc_ht"] = None

    if "source_url" not in d.columns:
        d["source_url"] = None

    # option_tarifaire
    if "option_tarifaire" not in d.columns:
        d["option_tarifaire"] = None

    # date du jour
    d["date_scrape"] = date.today().isoformat()

    # Colonnes manquantes
    for col in COLUMNS_STD:
        if col not in d.columns:
            d[col] = None

    # Nettoyage
    d = d[COLUMNS_STD].drop_duplicates().reset_index(drop=True)

    return d
