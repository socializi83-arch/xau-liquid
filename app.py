import os, time, requests, pandas as pd, yfinance as yf, pytz, threading
from datetime import datetime
from flask import Flask

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SYMBOL = "GC=F"
PARIS_TZ = pytz.timezone("Europe/Paris")
active_trade = None
last_brief_date = None

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def get_data(interval, period):
    df = yf.Ticker(SYMBOL).history(period=period, interval=interval, auto_adjust=False)
    if df.empty: return None
    return df.rename(columns={"High":"high","Low":"low","Close":"close"}).reset_index()

def is_trading_hours():
    now = datetime.now(PARIS_TZ)
    if now.weekday() >= 5: return False, "Week-end"
    mins = now.hour*60+now.minute
    if 540 <= mins <= 720: return True, "LONDRES"
    if 930 <= mins <= 1110: return True, "NEW YORK"
    return False, f"Hors session {now.strftime('%H:%M')}"

def daily_brief():
    global last_brief_date
    now = datetime.now(PARIS_TZ)
    if last_brief_date == now.strftime("%Y-%m-%d") or now.weekday()>=5: return
    df = get_data("1d", "10d")
    if df is None or len(df)<2: return
    pdh, pdl = float(df.iloc[-2]["high"]), float(df.iloc[-2]["low"])
    mid, rng = (pdh+pdl)/2, pdh-pdl
    biais = "🟢 Biais haussier" if float(df.iloc[-1]["close"])>mid else "🔴 Biais baissier"
    msg = f"☀️ *BRIEFING XAU/USD {now.strftime('%d/%m')}*\nPDH: {pdh:.2f}$\nPDL: {pdl:.2f}$\nMid: {mid:.2f}$\nRange: {rng:.2f}$\n{biais}\n\nPlan:\n1. Sweep PDH > {pdh*1.0008:.2f}$ -> SHORT\n2. Sweep PDL < {pdl*0.9992:.2f}$ -> LONG\n\nSurveillance 09h-12h et 15h30-18h30"
    send_telegram(msg)
    last_brief_date = now.strftime("%Y-%m-%d")

def check():
    global active_trade
    df_d = get_data("1d", "10d")
    df_m5 = get_data("5m", "2d")
    if df_d is None or df_m5 is None: return
    pdh, pdl = float(df_d.iloc[-2]["high"]), float(df_d.iloc[-2]["low"])
    mid = (pdh+pdl)/2
    last, cur = df_m5.iloc[-2], float(df_m5.iloc[-1]["close"])
    can_trade, sess = is_trading_hours()

    if active_trade:
        if (active_trade["type"]=="SHORT" and cur<=active_trade["tp1"]) or (active_trade["type"]=="LONG" and cur>=active_trade["tp1"]):
            send_telegram(f"✅ *TP1 ATTEINT {cur:.2f}$* - Passe en BE à {active_trade['entry']:.2f}$")
            active_trade = None
        return
    if not can_trade: return

    swipe_h = float(last["high"]) > pdh*1.0008 and float(last["close"]) < pdh
    swipe_l = float(last["low"]) < pdl*0.9992 and float(last["close"]) > pdl

    if swipe_h:
        sl, entry = float(last["high"])*1.0015, pdh
        msg = f"🚨 *SWIPE PDH XAU - {sess}*\n🔴 SHORT\n📍 ENTRÉE: {entry:.2f}$\n🛑 SL: {sl:.2f}$\n🎯 TP1: {mid:.2f}$\n🎯 TP2: {pdl:.2f}$"
        send_telegram(msg)
        active_trade = {"entry":entry,"tp1":mid,"tp2":pdl,"type":"SHORT"}
    elif swipe_l:
        sl, entry = float(last["low"])*0.9985, pdl
        msg = f"🚨 *SWIPE PDL XAU - {sess}*\n🟢 LONG\n📍 ENTRÉE: {entry:.2f}$\n🛑 SL: {sl:.2f}$\n🎯 TP1: {mid:.2f}$\n🎯 TP2: {pdh:.2f}$"
        send_telegram(msg)
        active_trade = {"entry":entry,"tp1":mid,"tp2":pdh,"type":"LONG"}

def loop():
    send_telegram("🤖 Bot XAU V3 démarré\nBriefing 08h55 + Londres 09-12h + NY 15h30-18h30")
    while True:
        now = datetime.now(PARIS_TZ)
        if now.hour==8 and now.minute==55: daily_brief()
        check()
        time.sleep(60)

app = Flask(__name__)
@app.route("/")
def home(): return f"Bot XAU actif - {datetime.now(PARIS_TZ).strftime('%H:%M')}"

threading.Thread(target=loop, daemon=True).start()
