import pandas as pd
import re

def structurer_tarifs(df_raw):
    out = []
    for _, row in df_raw.iterrows():
        offre = row["Offre"].strip().replace(".", "").title()
        val = row["Valeur"]
        unite = row["Unité"]

        # Identification du type
        if "kwh" in unite.lower():
            type_ = "énergie"
        elif "mois" in unite.lower() or "abonnement" in offre.lower():
            type_ = "abonnement"
        else:
            type_ = "autre"

        # Détection d’une puissance dans le texte d’origine
        puiss = None
        m = re.search(r"([0-9]+)\s*kva", offre, flags=re.I)
        if m:
            puiss = f"{m.group(1)} kVA"

        out.append({
            "fournisseur": row["Fournisseur"],
            "offre": offre,
            "type": type_,
            "puissance_kVA": puiss,
            "prix_HT": row["Prix_HT"],
            "prix_TTC": row["Prix_TTC"]
        })

    return pd.DataFrame(out)
