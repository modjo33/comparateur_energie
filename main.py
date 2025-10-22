import schedule
import time
from scrapers import edf, engie
from utils import db, alertes

def mise_a_jour():
    print("Lancement de la mise à jour des tarifs...")

    fournisseurs = [edf, engie]
    for f in fournisseurs:
        try:
            print(f"Récupération pour {f.NOM_FOURNISSEUR}...")
            data = f.scrape()
            db.sauvegarder_tarifs(f.NOM_FOURNISSEUR, data)
        except Exception as e:
            print(f"Erreur pour {f.NOM_FOURNISSEUR}: {e}")

    print("Vérification terminée.")

# Planifie la tâche à 9h chaque jour
schedule.every().day.at("09:00").do(mise_a_jour)

if __name__ == "__main__":
    print("Comparateur d’énergie en veille...")
    while True:
        schedule.run_pending()
        time.sleep(60)
