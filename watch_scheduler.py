import schedule
import time
import subprocess
from datetime import datetime

def run_watch():
    print(f"🚀 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Lancement du watcher de grilles...")
    try:
        subprocess.run(["python", "scrapers/watch_tarifs_diff_mail.py"], check=True)
        print("✅ Exécution terminée.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur lors du scraping : {e}")

# Planifie 2 passages par jour (modifie les heures si tu veux)
schedule.every().day.at("07:00").do(run_watch)
schedule.every().day.at("20:00").do(run_watch)

print("🕒 Surveillance planifiée : 09:00 et 16:00 chaque jour.")
print("💤 Laisse ce script tourner (Ctrl+C pour arrêter).")

while True:
    schedule.run_pending()
    time.sleep(60)
