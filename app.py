import os, time, requests, yfinance as yf, pytz, threading
from datetime import datetime
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("CHAT_ID")
SYMBOL = "GC=F"
TZ = pytz.timezone("Europe/Paris")
app = Flask(__name__)

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        print("Telegram envoyé")
    except Exception as e:
        print(f"Erreur Telegram: {e}")

@app.route("/")
def home():
    return "Bot XAU en ligne - OK"

@app.route("/status")
def status():
    return f"OK - Paris {datetime.now(TZ).strftime('%H:%M')} - Token set: {bool(TOKEN)} - Chat set: {bool(CHAT)}"

def loop():
    send("🤖 *Bot XAU démarré - test OK*\nSi tu reçois ça, Telegram marche.")
    while True:
        time.sleep(60)

threading.Thread(target=loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
