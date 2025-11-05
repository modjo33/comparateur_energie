import re
import pandas as pd

# Dictionnaire d’alias → nom officiel par fournisseur
# Ajuste ces valeurs quand tu connais les noms exacts (site, PDF, CGV).
OFFRE_ALIASES = {
    "Ohm Énergie": [
        # (regex sur notre label/texte, nom_officiel, score)
        (r"\b(be\s*ohm|be\s*base|be\b)",                 "Be Ohm Base", 0.9),
        (r"\b(classic|classique)\b",                     "Classique",    0.9),
        (r"(soir\s*&?\s*week\s*-?\s*end|week\s*end)",    "Soir & Week-end", 0.9),
        (r"\bmaxi\b",                                    "Maxi",         0.9),
        (r"\bfix(e|e)?\b",                               "Fixe",         0.8),
        (r"\b(ec|éco|eco)\b",                            "Éco",          0.8),
        (r"\blibert[eé]\b",                              "Liberté",      0.8),
    ],
    # Tu ajouteras ici d’autres fournisseurs plus tard.
}

def normaliser_nom_offre(fournisseur: str, offre_label: str) -> tuple[str|None, float]:
    """
    Transforme une étiquette heuristique en nom d’offre OFFICIEL via regex.
    Renvoie (nom_officiel, score_confiance). None si rien de trouvé.
    """
    if not isinstance(offre_label, str):
        return None, 0.0
    rules = OFFRE_ALIASES.get(fournisseur, [])
    txt = offre_label.lower()
    best = (None, 0.0)
    for pattern, officiel, score in rules:
        if re.search(pattern, txt, flags=re.IGNORECASE):
            if score > best[1]:
                best = (officiel, score)
    return best

def appliquer_catalogue(df: pd.DataFrame, fournisseur_col="Fournisseur", label_col="Offre_label") -> pd.DataFrame:
    """
    Ajoute deux colonnes:
      - offre_officielle : nom canonique standardisé
      - confiance_offre  : score [0..1]
    """
    if df.empty:
        return df.assign(offre_officielle=None, confiance_offre=0.0)

    def map_row(row):
        f = row.get(fournisseur_col)
        l = row.get(label_col)
        officiel, score = normaliser_nom_offre(f, l)
        return pd.Series({"offre_officielle": officiel, "confiance_offre": score})

    mapped = df.apply(map_row, axis=1)
    out = pd.concat([df.reset_index(drop=True), mapped], axis=1)
    return out
