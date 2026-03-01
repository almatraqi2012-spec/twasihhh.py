import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask
from threading import Thread

# --- [ السيرفر الوهمي لبقاء البوت حياً ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar Pro is Live!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "final_db.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ إدارة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                if "usage" not in data: data["usage"] = {}
                if "vip" not in data: data["vip"] = {OWNER_ID: 9999999999}
                return data
        except: pass
    return {"vip": {OWNER_ID: 9999999999}, "usage": {}}

db = load_db()

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump(db, f)

def check_access(uid):
    now = time.time()
    today = datetime.date.today().isoformat()
    if uid not in db["usage"]: db["usage"][uid] = {"count": 0, "last_reset": today, "total_free": 0}
    
    if uid in db["vip"] and db["vip"][uid] > now:
        if db["usage"][uid].get("last_reset") != today:
            db["usage"][uid]["count"] = 0
            db["usage"][uid]["last_reset"] = today
            save_db()
        return (True, "ok") if db["usage"][uid]["count"] < 10 else (False, "daily_limit")
    
    if db["usage"][uid].get("total_free", 0) < 5:
        return True, "free_ok"
    return False, "need_sub"

# --- [ محرك التحليل الاحترافي ] ---
def get_pro_analysis(symbol):
    try:
        symbol = symbol.upper().replace("/", "").strip()
        if not symbol.endswith("USDT"): symbol += "USDT"

        # جلب البيانات (15 دقيقة لتحليل أدق)
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
        res = requests.get(url, timeout=5).json()
        source = "BINANCE"

        if isinstance(res, dict):
            url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
            res = requests.get(url, timeout=5).json()
            source = "MEXC"

        closes = [float(c[4]) for c in res]
        volumes = [float(c[5]) for c in res]
        highs = [float(c[2]) for c in res]
        lows = [float(c[3]) for c in res]
        
        live_price = closes[-1]
        
        # 1. حساب RSI (14)
        gains = sum([max(0, closes[i] - closes[i-1]) for i in range(-14, 0)])
        losses = sum([max(0, closes[i-1] - closes[i]) for i in range(-14, 0)])
        rsi = 100 - (100 / (1 + (gains/losses if losses != 0 else 1)))

        # 2. حساب المتوسطات (SMA 20 & SMA 50)
        sma20 = sum(closes[-20:]) / 20
        sma50 = sum(closes[-50:]) / 50

        # 3. تحليل السيولة
        avg_vol = sum(volumes[-20:]) / 20
        vol_ratio = volumes[-1] / avg_vol

        # --- نظام النقاط لاتخاذ القرار ---
        score = 0
        if rsi < 35: score += 2  # منطقة شراء
        if rsi > 65: score -= 2  # منطقة بيع
        if live_price > sma20: score += 1 # اتجاه صاعد قصير
        if live_price > sma50: score += 1 # اتجاه صاعد متوسط
        if vol_ratio > 1.2: score += 1 if live_price > sma20 else -1 # سيولة تدعم الاتجاه

        # --- توليد الإشارة بناءً على النقاط ---
        if score >= 3:
            s, t = "🚀 شراء قوي (اكتمال الشروط)", "🔥 سيولة ضخمة واتجاه صاعد"
            tg, sl = live_price * 1.04, live_price * 0.97
        elif score <= -3:
            s, t = "⚠️ بيع (خروج فوري)", "📉 انهيار في الدعم وتضخم سعري"
            tg, sl = live_price * 0.96, live_price * 1.03
        elif rsi < 30:
            s, t = "🎯 اقتناص قاع", "📈 ارتداد تقني وشيك من منطقة التشبع"
            tg, sl = live_price * 1.03, live_price * 0.98
        elif live_price > sma20:
            s, t = "📈 اتجاه إيجابي", "✅ استمرار الصعود مع الحذر"
            tg, sl = live_price * 1.02, live_price * 0.99
        else:
            s, t = "📉 اتجاه سلبي", "❌ لا ينصح بالدخول.. السعر تحت المتوسط"
            tg, sl = live_price * 0.95, live_price * 1.02

        vol_desc = "💎 عالية" if vol_ratio > 1 else "🌑 ضعيفة"

        return (f"🏛 **رادار القابضة الاحترافي** | `{source}`\n"
                f"━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{symbol}\n"
                f"💰 السعر: `{live_price:.4f}`\n"
                f"📊 RSI: {rsi:.1f} | السيولة: {vol_desc}\n"
                f"━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{s}**\n"
                f"📌 التحليل: {t}\n"
                f"━━━━━━━━━━━━━━\n"
                f"🎯 الهدف: `{tg:.4f}` (3%-5%)\n"
                f"🛡️ الوقف: `{sl:.4f}`\n"
                f"🔗 [الشارت المباشر](https://www.tradingview.com/chart/?symbol={source}:{symbol})")
    except: return None

# --- [ الأوامر كما هي مع تحسين الردود ] ---
@bot.message_handler(commands=['start'])
def start_cmd(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 تحليل عملة", "💎 حالة اشتراكي")
    markup.add("💳 بيانات الدفع (70$)", "👨‍💻 تفعيل الحساب")
    bot.send_message(m.chat.id, f"👋 أهلاً بك في رادار القابضة V2\nالآن نعتمد نظام التحليل النقطي الذكي لضمان دقة التوصيات.", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_messages(m):
    uid = str(m.from_user.id)
    if m.text == "🔍 تحليل عملة":
        can, reason = check_access(uid)
        if can:
            msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثلاً: BTC):")
            bot.register_next_step_handler(msg, process_analysis)
        else:
            bot.send_message(m.chat.id, "❌ انتهت محاولاتك. يرجى الاشتراك (70$) للحصول على وصول غير محدود.")

def process_analysis(m):
    uid = str(m.from_user.id)
    res = get_pro_analysis(m.text)
    if res:
        # خصم المحاولة فقط عند نجاح التحليل
        if uid in db["vip"] and db["vip"][uid] > time.time():
            db["usage"][uid]["count"] += 1
        else:
            db["usage"][uid]["total_free"] = db["usage"][uid].get("total_free", 0) + 1
        save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ رمز غير صحيح أو العملة غير مدعومة حالياً.")

bot.infinity_polling()
