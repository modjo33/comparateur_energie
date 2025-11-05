import pandas as pd
import re

def enrichir_contexte(df):
    """
    Ajoute le nom de l’offre, la puissance estimée et l’option tarifaire
    en se basant sur les montants d’abonnement et les gammes connues d’Ohm.
    """
    if df.empty:
        print("Aucune donnée à enrichir.")
        return df

    df = df.copy()

    # 1️⃣ Nom d’offre probable selon la gamme de prix
    def guess_offer(row):
        if row["Type"].lower().startswith("abo"):
            if row["Valeur"] < 15:
                return "Ohm Be Base"
            elif row["Valeur"] < 25:
                return "Ohm Classic"
            elif row["Valeur"] < 40:
                return "Ohm Soir & Week-end"
            else:
                return "Ohm Maxi"
        else:
            if row["Valeur"] < 0.13:
                return "Ohm Eco"
            elif row["Valeur"] < 0.18:
                return "Ohm Fixe"
            else:
                return "Ohm Liberté"

    # 2️⃣ Estimation de puissance depuis abonnement (approximatif mais utile)
    def estimer_puissance(valeur):
        if valeur < 12:
            return "3 kVA"
        elif valeur < 17:
            return "6 kVA"
        elif valeur < 22:
            return "9 kVA"
        elif valeur < 30:
            return "12 kVA"
        elif valeur < 45:
            return "15 kVA"
        elif valeur < 60:
            return "18 kVA"
        else:
            return "36 kVA"

    # 3️⃣ Option tarifaire (repérage heuristique)
    def detect_option(row):
        v = row["Valeur"]
        if row["Type"].lower().startswith("abo"):
            return "Base"
        elif 0.05 <= v <= 0.12:
            return "Heures Creuses"
        elif 0.13 <= v <= 0.22:
            return "Heures Pleines"
        elif 0.23 <= v <= 0.35:
            return "Soir & Week-end"
        else:
            return "Inconnu"

    # Application
    df["Offre_label"] = df.apply(guess_offer, axis=1)
    df["Puissance_kVA"] = df["Valeur"].apply(estimer_puissance)
    df["Option_tarifaire"] = df.apply(detect_option, axis=1)

    # Réorganisation
    colonnes = [
        "Fournisseur", "Offre_label", "Type", "Option_tarifaire",
        "Puissance_kVA", "Prix_HT", "Prix_TTC", "Unite", "Valeur", "Date_scrape"
    ]
    return df[colonnes]
