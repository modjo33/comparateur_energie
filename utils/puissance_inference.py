import pandas as pd
import numpy as np

PUISSANCES_STD = ["3 kVA","6 kVA","9 kVA","12 kVA","15 kVA","18 kVA","24 kVA","30 kVA","36 kVA"]

def _unique_sorted(values, round_ndigits=2, tol=0.05):
    """Déduplique des valeurs proches (ex: 26.20 et 26.2001) puis trie."""
    vals = sorted({round(float(v), round_ndigits) for v in values})
    merged = []
    for v in vals:
        if not merged or abs(v - merged[-1]) > tol:
            merged.append(v)
    return merged

def infer_puissance_from_abos(df_abos: pd.DataFrame) -> pd.DataFrame:
    """Associe à chaque abonnement la puissance kVA la plus probable."""
    if df_abos.empty:
        return df_abos.assign(Puissance_kVA=None)

    work = df_abos.copy()

    # Choisir la source de prix pour ordonner
    base_col = "Prix_TTC" if "Prix_TTC" in work.columns and work["Prix_TTC"].notna().any() else "Valeur"

    uniques = _unique_sorted(work[base_col].dropna().tolist(), round_ndigits=2, tol=0.05)
    puissances = PUISSANCES_STD[:len(uniques)]
    mapping = dict(zip(uniques, puissances))

    def nearest_power(x):
        if pd.isna(x) or not uniques:
            return None
        closest = min(uniques, key=lambda u: abs(u - round(float(x), 2)))
        return mapping.get(closest)

    work["Puissance_kVA"] = work[base_col].apply(nearest_power)
    return work

def affecter_puissance(df: pd.DataFrame) -> pd.DataFrame:
    """Applique l’inférence de puissance aux abonnements et réassemble."""
    if df.empty:
        return df.assign(Puissance_kVA=None)

    df = df.copy()
    if "Puissance_kVA" not in df.columns:
        df["Puissance_kVA"] = None

    mask_abo = df["Type"].str.lower().str.startswith("abo")
    abo_df = df.loc[mask_abo]
    other_df = df.loc[~mask_abo]

    inferred = infer_puissance_from_abos(abo_df)
    out = pd.concat([other_df, inferred], ignore_index=True)

    # Créer une colonne de tri simple (évite les KeyError)
    def sort_index(row):
        if row["Type"].lower().startswith("abo"):
            try:
                idx = PUISSANCES_STD.index(row.get("Puissance_kVA"))
            except Exception:
                idx = 999
            return idx + 0.1  # abonnements avant énergie
        return 9999 + (row.get("Prix_TTC") or row.get("Valeur") or 0)

    out["_sort"] = out.apply(sort_index, axis=1)
    out = out.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)

    return out
