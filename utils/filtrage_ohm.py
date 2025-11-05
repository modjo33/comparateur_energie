import pandas as pd

TVA_TAUX = 0.20  # TVA 20%
CTA_TAUX = 0.0271  # Contribution tarifaire d’acheminement
TAXES_FIXES = 0.0075  # Taxes diverses moyennes par kWh (en €)

def filtrer_et_enrichir(df):
    """Nettoie les données Ohm et calcule HT/TTC."""
    if df.empty:
        print("Aucune donnée à traiter.")
        return df

    df = df.copy()

    # Normalisation des noms de colonnes
    df.columns = [c.strip().capitalize() for c in df.columns]

    # Filtrage des valeurs aberrantes
    df = df[(df["Valeur"] > 0.05) & (df["Valeur"] < 1000)]
    df = df.drop_duplicates()

    # Type et unité
    df["Unite"] = df["Type"].apply(lambda x: "€/mois" if "abo" in x.lower() else "€/kWh")

    # Calcul HT/TTC
    def calcul_ht_ttc(row):
        if row["Unite"] == "€/kWh":
            ht = max(0, row["Valeur"] - TAXES_FIXES)
            ttc = round(ht * (1 + TVA_TAUX), 6)
        else:
            ht = round(row["Valeur"] / (1 + TVA_TAUX + CTA_TAUX), 2)
            ttc = round(ht * (1 + TVA_TAUX + CTA_TAUX), 2)
        return pd.Series({"Prix_HT": ht, "Prix_TTC": ttc})

    ht_ttc = df.apply(calcul_ht_ttc, axis=1)
    df = pd.concat([df, ht_ttc], axis=1)

    # Fréquence d’apparition (valeur plus fréquente = plus fiable)
    freq = df["Valeur"].value_counts().to_dict()
    df["Frequence"] = df["Valeur"].map(freq)

    # Tri des valeurs les plus plausibles
    df = df.sort_values(["Type", "Frequence"], ascending=[True, False])

    df["Date_scrape"] = pd.Timestamp.now().strftime("%Y-%m-%d")

    colonnes = [
        "Fournisseur", "Offre", "Type", "Unite",
        "Prix_HT", "Prix_TTC", "Valeur", "Frequence", "Date_scrape"
    ]
    return df[colonnes]
