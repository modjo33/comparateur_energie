import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_USER = "johan.faydherbe@gmail.com"
SMTP_PASS = "BTZSBLFTIWGKCOFQ"  # ton mot de passe d’application
ALERT_EMAIL = "johan.faydherbe@gmail.com"

msg = MIMEMultipart()
msg["From"] = SMTP_USER
msg["To"] = ALERT_EMAIL
msg["Subject"] = "🔔 Test d’envoi d’alerte"
msg.attach(MIMEText("Si tu vois ce mail, ton alerte tarif fonctionne.", "plain"))

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    print("✅ Mail envoyé avec succès.")
except Exception as e:
    print(f"❌ Erreur d’envoi : {e}")
