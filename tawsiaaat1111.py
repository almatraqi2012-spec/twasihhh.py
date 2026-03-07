import requests, telebot, time, os, threading, json, random
from datetime import datetime, timedelta
from telebot import types
from flask import Flask

app = Flask(__name__)

# ================= [ ⚙️ الإعدادات الكبرى ] =================
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v36_final.json"

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- [ 💾 إدارة البيانات ] ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_db(db):
    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)

# --- [ 🛡️ محرك التحليل الاحترافي - نظام التجاوز ] ---
def get_v36_analysis(symbol):
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 6: s += "USDT"
    
    # قائمة بروابط API مختلفة لضمان الوصول
    urls = [
        f"https://api.binance.com/api/v3/klines?symbol={s}&interval=4h&limit=100",
        f"https://api1.binance.com/api/v3/klines?symbol={s}&interval=4h&limit=100",
        f"https://api3.binance.com/api/v3/klines?symbol={s}&interval=4h&limit=100"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    data = None
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                break
        except: continue

    if not data or not isinstance(data, list) or len(data) < 20:
        return f"⚠️ عذراً، لم نتمكن من سحب بيانات `{s}` من السوق حالياً. يرجى إعادة المحاولة.", None

    try:
        # استخراج البيانات بدقة متناهية
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        vols = [float(c[5]) for c in data]
        
        p = closes[-1] # السعر الحالي
        
        # المؤشرات الـ 4
        ema10 = sum(closes[-10:]) / 10
        ema30 = sum(closes[-30:]) / 30
        vol_avg = sum(vols[-20:]) / 20
        
        # حساب RSI دقيق
        up = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        down = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rs = (sum(up)/14) / (sum(down)/14) if sum(down) != 0 else 1
        rsi = 100 - (100 / (1 + rs))

        # حساب الأهداف بناءً على تذبذب 48 ساعة (ATR استراتيجي)
        atr = max(highs[-12:]) - min(lows[-12:])
        if atr == 0: atr = p * 0.05

        if p > ema10 and rsi < 70 and vols[-1] > vol_avg:
            sig, color = "🟢 إشارة دخول (ترند صاعد)", "خضراء 🚀"
            t1, t2, sl = p + (atr * 0.3), p + (atr * 0.7), p - (atr * 0.4)
        elif p < ema10 or rsi > 70:
            sig, color = "🔴 إشارة هبوط (تصحيح/بيع)", "حمراء 📉"
            t1, t2, sl = p - (atr * 0.3), p - (atr * 0.6), p + (atr * 0.4)
        else:
            sig, color = "🟡 منطقة تذبذب (مراقبة)", "عرضية ⚖️"
            t1, t2, sl = p * 1.02, p * 1.05, p * 0.98

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        res = (f"📈 **تقرير التحليل الاستراتيجي**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: `{s}` | 💰 السعر: `{p}$` \n"
               f"📊 الاتجاه: **{sig}**\n"
               f"🔮 الشمعة القادمة: `{color}`\n"
               f"🌡️ RSI: `{round(rsi, 1)}` | 🌊 السيولة: `{'🔥 قوية' if vols[-1] > vol_avg else '⚖️ هادئة'}`\n\n"
               f"🎯 هدف أول: `{round(t1, 5)}` ✅\n"
               f"🎯 هدف ثاني: `{round(t2, 5)}` 🔥\n"
               f"🛡️ الوقف: `{round(sl, 5)}` ⛔\n"
               f"━━━━━━━━━━━━━━\n"
               f"⏳ مدة الصفقة: `6 - 24 ساعة`\n"
               f"✅ تحليل سيولة + 4 مؤشرات فنية")
        return res, chart
    except:
        return "⚠️ حدث خطأ أثناء تشريح البيانات الفنية.", None

# --- [ 🕹️ لوحات التحكم ] ---
def main_menu(uid):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("📊 تحليل رادار V36 📉", "👤 حسابي")
    mk.row("💳 شحن الاشتراك", "📢 الدعم الفني")
    if str(uid) == str(OWNER_ID): mk.row("⚙️ إدارة النظام")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id); db = load_db()
    if uid not in db:
        db[uid] = {"sub": False, "exp": None, "free": 0, "daily": 0, "last": str(datetime.now().date())}
        save_db(db)
    bot.send_message(m.chat.id, "📊 **مرحباً بك في نظام التحليل الفني المطور.**", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "📊 تحليل رادار V36 📉")
def request_analysis(m):
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, process_analysis)

def process_analysis(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    if not u['sub'] and u['free'] >= 5:
        return bot.send_message(m.chat.id, "❌ انتهت الحدود المجانية. يرجى الاشتراك.")
    
    bot.send_message(m.chat.id, "🔍 **جاري فحص السوق وتشريح السيولة...**")
    res, chart = get_v36_analysis(m.text)
    
    if chart:
        if not u['sub']: db[uid]['free'] += 1
        else: db[uid]['daily'] += 1
        save_db(db)
        try: bot.send_photo(m.chat.id, chart, caption=res)
        except: bot.send_message(m.chat.id, res)
    else: bot.send_message(m.chat.id, res)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def account(m):
    u = load_db().get(str(m.from_user.id), {})
    status = "VIP" if u.get('sub') else "مجاني"
    bot.send_message(m.chat.id, f"👤 **حسابك:** {status}\n🆔: `{m.from_user.id}`")

@app.route('/')
def home(): return "RUNNING"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True)
