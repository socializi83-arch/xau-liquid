import os, time, requests, yfinance as yf, pytz, threading
from datetime import datetime
from flask import Flask

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT = os.getenv("CHAT_ID")
SYMBOL = "GC=F"
TZ = pytz.timezone("Europe/Paris")
active_trade = None
last_brief = None

app = Flask(__name__)

def send(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def get_data(interval, period):
    df = yf.Ticker(SYMBOL).history(period=period, interval=interval, auto_adjust=False)
    if df.empty: return None
    return df.rename(columns={"High":"high","Low":"low","Close":"close"}).reset_index()

def is_session():
    now = datetime.now(TZ)
    if now.weekday()>=5: return False, "Week-end"
    m = now.hour*60+now.minute
    if 540 <= m <= 720: return True, "LONDRES"
    if 930 <= m <= 1110: return True, "NEW YORK"
    return False, f"Hors session {now.strftime('%H:%M')}"

def briefing():
    global last_brief
    now = datetime.now(TZ)
    if last_brief == now.strftime("%Y-%m-%d") or now.weekday()>=5: return
    df = get_data("1d", "10d")
    if df is None: return
    pdh, pdl = float(df.iloc[-2]["high"]), float(df.iloc[-2]["low"])
    mid = (pdh+pdl)/2
    send(f"☀️ *BRIEFING XAU {now.strftime('%d/%m')}*\nPDH: {pdh:.2f}$\nPDL: {pdl:.2f}$\nMid: {mid:.2f}$\n\nPlan: Sweep PDH > {pdh*1.0008:.2f}$ = SHORT | Sweep PDL < {pdl*0.9992:.2f}$ = LONG\nSession 09-12h et 15h30-18h30 Paris")
    last_brief = now.strftime("%Y-%m-%d")

def check():
    global active_trade
    df_d = get_data("1d", "10d")
    df_m5 = get_data("5m", "2d")
    if df_d is None or df_m5 is None: return
    pdh, pdl = float(df_d.iloc[-2]["high"]), float(df_d.iloc[-2]["low"])
    mid = (pdh+pdl)/2
    last, cur = df_m5.iloc[-2], float(df_m5.iloc[-1]["close"])
    can, sess = is_session()
    if active_trade:
        if (active_trade["type"]=="SHORT" and cur<=active_trade["tp1"]) or (active_trade["type"]=="LONG" and cur>=active_trade["tp1"]):
            send(f"✅ *TP1 ATTEINT {cur:.2f}$* - Passe en BE à {active_trade['entry']:.2f}$")
            active_trade = None
        return
    if not can: return
    swipe_h = float(last["high"]) > pdh*1.0008 and float(last["close"]) < pdh
    swipe_l = float(last["low"]) < pdl*0.9992 and float(last["close"]) > pdl
    if swipe_h:
        send(f"🚨 *SWIPE PDH XAU - {sess}*\n🔴 SHORT\n📍 ENTRÉE: {pdh:.2f}$\n🎯 TP1: {mid:.2f}$\n🎯 TP2: {pdl:.2f}$")
        active_trade = {"entry":pdh,"tp1":mid,"tp2":pdl,"type":"SHORT"}
    elif swipe_l:
        send(f"🚨 *SWIPE PDL XAU - {sess}*\n🟢 LONG\n📍 ENTRÉE: {pdl:.2f}$\n🎯 TP1: {mid:.2f}$\n🎯 TP2: {pdh:.2f}$")
        active_trade = {"entry":pdl,"tp1":mid,"tp2":pdh,"type":"LONG"}

def loop():
    while True:
        now = datetime.now(TZ)
        if now.hour==8 and now.minute==55: briefing()
        check()
        time.sleep(60)

@app.route("/")
def home(): return "Bot XAU V3 en ligne"
@app.route("/status")
def status(): return f"Paris {datetime.now(TZ).strftime('%H:%M')} - Token OK - Trade {active_trade}"

threading.Thread(target=loop, daemon=True).start()
