import json, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

with open("ngrok_url.json","r",encoding="utf-8") as f:
    data=json.load(f)
url=data.get("url", "")
kamera=data.get("kamera", "")

gonder_email='****************'
gonder_sifre='***************'

msg=MIMEMultipart()
msg['From']=gonder_email
msg['To']='********************'  # Alıcı email adresi
msg['Subject']='Kamera Server Baslatildi'

body=f"""Merhaba,\n\nKamera server basarili bir sekilde baslatildi!\n\nKamera URL: {url}\n\nKamera Feed: {kamera}\n\nBaslama Zamani: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\nYapay Zeka Asistani Sistemi\n"""

msg.attach(MIMEText(body,'plain','utf-8'))

server=smtplib.SMTP_SSL('smtp.gmail.com',465)
server.login(gonder_email,gonder_sifre)
server.send_message(msg)
server.quit()
print('EMAIL_SENT')
