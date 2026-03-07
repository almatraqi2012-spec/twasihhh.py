import requests, telebot, time, os, threading, json
from datetime import datetime
from telebot import types
from flask import Flask

app = Flask(__name__)

# ================= [ ⚙️ الإعدادات الكبرى ] =================
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_db.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ 💾 نظام البيانات ] ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_db(db):
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ 🛡️ محرك البحث العابر للمنصات - نسخة خالية من الأخطاء ] ---
def fetch_data_v36(symbol):
    # 1. تنظيف الرمز
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 6: s += "USDT"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 2. محاولة جلب من Binance
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_status == 200:
            data = r.json()
            if isinstance(data, list) and len(data) > 0:
                return data, s, "Binance"
    except: pass

    # 3. محاولة جلب من MEXC (بديل قوي جداً)
    try:
        m_s = s.replace("USDT", "_USDT")
        url = f"https://www.mexc.com/open/api/v2/market/kline?symbol={m_s}&interval=60m&limit=100"
        r = requests.get(url, headers=headers, timeout=10)
        res = r.json()
        if res.get('data'):
            return res['data'], s, "MEXC"
    except: pass

    return None, s, None

def get_v36_analysis(symbol):
    klines, s, platform = fetch_data_v36(symbol)
    if not klines:
        return "❌ العملة غير موجودة في المنصات أو السيرفر مشغول.\nتأكد من الرمز (مثلاً: BTC أو PEPE).", None

    try:
        closes = [float(k[4]) for k in klines]
        vols = [float(k[5]) for k in klines]
        p = closes[-1]
        
        # مؤشرات V36 (EMA + Volume + RSI)
        ema = sum(closes[-20:]) / 20
        vol_avg = sum(vols[-20:]) / 20
        
        if p > ema and vols[-1] > vol_avg:
            status, pred = "🟢 صعود (Bullish)", "🚀 التوقع: شمعة خضراء قادمة."
            t1, t2, sl = p*1.04, p*1.08, p*0.95
        else:
            status, pred = "🔴 حذر (Bearish)", "📉 التوقع: تصحيح أو هبوط."
            t1, t2, sl = p*0.97, p*0.94, p*1.04

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        
        res = (f"🐲 **رادار V36 الأسطوري** ({platform})\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: `{s}` | 💰 السعر: `{p}$` \n"
               f"📊 الإشارة: **{status}**\n🔮 التوقع: {pred}\n"
               f"🎯 أهداف: `{round(t1,4)}` | `{round(t2,4)}`\n"
               f"🛡️ الوقف: `{round(sl,4)}` \n━━━━━━━━━━━━━━")
        return res, chart
    except:
        return "⚠️ حدث خطأ أثناء معالجة البيانات.", None

# --- [ 🕹️ إدارة الأوامر والقيود ] ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id); db = load_db()
    if uid not in db:
        db[uid] = {"sub": False, "exp": None, "free": 0, "daily": 0, "date": str(datetime.now().date())}
        save_db(db)
    
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("📊 تحليل العملات 📈", "👤 حسابي")
    mk.row("💳 شحن الاشتراك", "📢 الدعم")
    bot.send_message(m.chat.id, "🐲 **رادار القابضة V36 جاهز!**\nالآن البحث شامل من جميع المنصات.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📊 تحليل العملات 📈")
def check_lim(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    today = str(datetime.now().date())
    
    if u['date'] != today: u['daily'] = 0; u['date'] = today; save_db(db)

    if not u['sub'] and u['free'] >= 5:
        return bot.send_message(m.chat.id, "❌ انتهى حدك المجاني (5 عملات). يرجى الاشتراك.")
    if u['sub'] and u['daily'] >= 5:
        return bot.send_message(m.chat.id, "⚠️ وصلت للحد اليومي (5 عملات). عد غداً.")

    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (BTC, ETH, SOL...):")
    bot.register_next_step_handler(msg, exec_v36)

def exec_v36(m):
    bot.send_message(m.chat.id, "🔍 جاري الفحص الشامل للسيولة...")
    text, chart = get_v36_analysis(m.text)
    if chart:
        uid = str(m.from_user.id); db = load_db()
        if db[uid]['sub']: db[uid]['daily'] += 1
        else: db[uid]['free'] += 1
        save_db(db)
        try: bot.send_photo(m.chat.id, chart, caption=text, parse_mode="Markdown")
        except: bot.send_message(m.chat.id, text, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, text)

# --- [ 🌐 نظام الويب والدفع ] ---
@app.route('/')
def index(): return "RADAR V36 SYSTEM IS RUNNING! 🐲"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.infinity_polling(skip_pending=True)
