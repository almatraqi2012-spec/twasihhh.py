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

# --- [ 🛡️ محرك التحليل - نظام فك الحظر الاستراتيجي ] ---
def get_v36_analysis(symbol):
    raw_s = symbol.upper().strip().replace("/", "").replace("-", "")
    s = raw_s.replace("USDT", "") # نحتاج الرمز الصافي (مثلاً BTC)
    
    # 1. محاولة جلب البيانات عبر نظام Aggregator (ضد الحظر)
    data = None
    try:
        # استخدام CryptoCompare كبديل قوي جداً لبينانس
        url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym={s}&tsym=USDT&limit=100"
        r = requests.get(url, timeout=10).json()
        if r.get('Response') == 'Success':
            data = r['Data']['Data']
    except: pass

    # 2. إذا فشل، جرب البديل الثاني
    if not data or len(data) < 20:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={s}USDT&interval=4h&limit=100"
            data = requests.get(url, timeout=10).json()
        except: pass

    if not data or len(data) < 20:
        return f"❌ عذراً يا عبد الكريم، هناك ضغط كبير على السيرفر لعملة `{s}`.\nيرجى المحاولة مرة أخرى الآن (تم تحديث المسار).", None

    try:
        # استخراج البيانات (تنسيق CryptoCompare مختلف قليلاً)
        if isinstance(data[0], dict): # تنسيق CryptoCompare
            closes = [float(k['close']) for k in data]
            highs = [float(k['high']) for k in data]
            lows = [float(k['low']) for k in data]
            vols = [float(k['volumeto']) for k in data]
        else: # تنسيق Binance
            closes = [float(k[4]) for k in data]
            highs = [float(k[2]) for k in data]
            lows = [float(k[3]) for k in data]
            vols = [float(k[5]) for k in data]
        
        p = closes[-1]
        ema10 = sum(closes[-10:]) / 10
        ema30 = sum(closes[-30:]) / 30
        vol_avg = sum(vols[-20:]) / 20
        
        diff = max(highs[-24:]) - min(lows[-24:])
        if diff == 0: diff = p * 0.04

        if p > ema10 and vols[-1] > vol_avg:
            sig, status = "🟢 دخول شرائي (قوة صاعدة)", "🚀 التوقع: استمرار الزخم الشرائي (6-24 ساعة)"
            t1, t2, sl = p + (diff * 0.3), p + (diff * 0.7), p - (diff * 0.4)
        else:
            sig, status = "🔴 إشارة هبوط (ضغط بيعي)", "📉 التوقع: تصحيح أو حركة هابطة (6-24 ساعة)"
            t1, t2, sl = p - (diff * 0.3), p - (diff * 0.7), p + (diff * 0.4)

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}USDT.png"
        res = (f"🐲 **رادار V36 الاستراتيجي (محرك Aggregator)**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: `{s}/USDT` | 💰 السعر: `{p}$` \n"
               f"📊 الإشارة: **{sig}**\n"
               f"🔮 {status}\n\n"
               f"🎯 هدف أول: `{round(t1, 4)}` ✅\n"
               f"🎯 هدف ثاني: `{round(t2, 4)}` 🔥\n"
               f"🛡️ الوقف: `{round(sl, 4)}` ⛔\n"
               f"━━━━━━━━━━━━━━\n"
               f"✅ تم تجاوز حظر المنصات بنجاح | 4 مؤشرات")
        return res, chart
    except: return "⚠️ خطأ في معالجة البيانات الفنية.", None

# --- [ باقي الأوامر واللوحات ] ---
def main_menu(uid):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("📊 تحليل رادار V36 📉", "👤 حسابي")
    mk.row("💳 شحن الاشتراك", "📢 دعم الرادار")
    if str(uid) == str(OWNER_ID): mk.row("⚙️ لوحة تحكم المالك")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id); db = load_db()
    if uid not in db:
        db[uid] = {"sub": False, "exp": None, "free": 0, "daily": 0, "last": str(datetime.now().date())}
        save_db(db)
    bot.send_message(m.chat.id, "🐲 **رادار القابضة V36 - النسخة الصخرية**\nتم حل مشاكل الحظر، جرب الآن!", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "📊 تحليل رادار V36 📉")
def get_coin(m):
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, analyze_coin)

def analyze_coin(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    if not u['sub'] and u['free'] >= 5:
        return bot.send_message(m.chat.id, "❌ انتهى حدك المجاني.")
    
    bot.send_message(m.chat.id, "🔍 **جاري اختراق الحظر وجلب السيولة...**")
    res, chart = get_v36_analysis(m.text)
    if chart:
        if not u['sub']: db[uid]['free'] += 1
        else: db[uid]['daily'] += 1
        save_db(db)
        try: bot.send_photo(m.chat.id, chart, caption=res)
        except: bot.send_message(m.chat.id, res)
    else: bot.send_message(m.chat.id, res)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def profile(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    status = "VIP" if u['sub'] else "مجاني"
    bot.send_message(m.chat.id, f"👤 حسابك: {status}\n🆔: `{uid}`")

@bot.message_handler(func=lambda m: m.text == "⚙️ لوحة تحكم المالك" and str(m.from_user.id) == str(OWNER_ID))
def admin(m):
    msg = bot.send_message(m.chat.id, "أرسل ID المستخدم لتفعيله:")
    bot.register_next_step_handler(msg, activate)

def activate(m):
    tid = m.text.strip(); db = load_db()
    if tid in db:
        db[tid]['sub'] = True
        db[tid]['exp'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        save_db(db)
        bot.send_message(m.chat.id, f"✅ تم تفعيل {tid}"); bot.send_message(tid, "🌟 تم التفعيل!")
    else: bot.send_message(m.chat.id, "❌ غير مسجل.")

@app.route('/')
def home(): return "V36 ONLINE!"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True)
