import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask
from threading import Thread

# --- [ سيرفر التشغيل ] ---
app = Flask('')
@app.route('/')
def home(): return "Professional High-Confidence Radar Active"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'FYYUOW-LY5JFH-BLBLUZ-9M6BTO'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_fixed_v4.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return {"vip": {}, "usage": {}}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل الحاسم ] ---
def get_analysis(symbol):
    try:
        symbol = symbol.upper().replace("/", "").strip()
        if not symbol.endswith("USDT"): symbol += "USDT"
        
        # جلب البيانات من بينانس أو ماكسيك
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
        res = requests.get(url, timeout=5).json()
        source = "BINANCE"
        if isinstance(res, dict):
            url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
            res = requests.get(url, timeout=5).json()
            source = "MEXC"

        closes = [float(c[4]) for c in res]
        price = closes[-1]
        sma20 = sum(closes[-20:]) / 20
        sma50 = sum(closes[-50:]) / 50
        
        # حساب RSI
        gains = sum([max(0, closes[i] - closes[i-1]) for i in range(-14, 0)])
        losses = sum([max(0, closes[i-1] - closes[i]) for i in range(-14, 0)])
        rsi = 100 - (100 / (1 + (rsi_g/rsi_l if (rsi_l := losses) != 0 else 1)))

        # اتخاذ قرار حاسم
        if rsi < 35 or (price > sma20 and sma20 > sma50):
            signal = "🚀 شراء (فرصة قوية)"
            target = price * 1.05
            stop = price * 0.96
            desc = "تحليل فني يشير لصعود قوي ودخول سيولة."
        elif rsi > 65 or price < sma50:
            signal = "⚠️ خروج / بيع"
            target = price * 0.95
            stop = price * 1.04
            desc = "منطقة تشبع شرائي أو كسر ترند.. احذر."
        else:
            signal = "📈 ترند صاعد مستقر"
            target = price * 1.03
            stop = price * 0.98
            desc = "العملة في مسار إيجابي تدريجي."

        chart_url = f"https://www.tradingview.com/chart/?symbol={source}:{symbol}"
        
        return (f"🏛 **رادار القابضة الاحترافي**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{symbol} | `{source}`\n💰 السعر: `{price}`\n📊 RSI: {rsi:.1f}\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{signal}**\n📌 الحالة: {desc}\n━━━━━━━━━━━━━━\n"
                f"🎯 الهدف: `{target:.4f}`\n🛡️ الوقف: `{stop:.4f}`\n"
                f"🔗 [اضغط هنا لفتح الشارت المباشر]({chart_url})")
    except: return None

# --- [ الأوامر وإصلاح الأزرار ] ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔍 تحليل عملة", "💎 حسابي")
    m.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    return m

@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in db["usage"]: db["usage"][uid] = {"count":0, "free":0}
    save_db()
    bot.send_message(m.chat.id, "👋 مرحباً بك في رادار القابضة الرسمي.\nنظام تحليل ذكي يعتمد على حركة الحيتان والمؤشرات الحية.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def start_ana(m):
    uid = str(m.from_user.id)
    is_vip = uid in db["vip"] and db["vip"][uid] > time.time()
    free_used = db["usage"][uid].get("free", 0)

    if is_vip or free_used < 5:
        msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
        bot.register_next_step_handler(msg, run_ana)
    else:
        bot.send_message(m.chat.id, "❌ انتهت المحاولات المجانية. يرجى الاشتراك.")

def run_ana(m):
    res = get_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if uid not in db["vip"] or db["vip"][uid] <= time.time():
            db["usage"][uid]["free"] += 1
        save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown", disable_web_page_preview=False)
    else:
        bot.send_message(m.chat.id, "⚠️ رمز العملة غير مدعوم.")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def oxa_pay(m):
    try:
        res = requests.post("https://api.oxapay.com/api/v2/checkout", json={
            "merchant": OXA_API_KEY, "amount": 50, "currency": "USDT", "network": "TRC20",
            "description": f"VIP_{m.from_user.id}"
        }).json()
        if res.get("status") == "success":
            bot.send_message(m.chat.id, f"✅ اضغط للدفع التلقائي:\n{res.get('payUrl')}")
    except: bot.send_message(m.chat.id, "⚠️ عطل مؤقت في بوابة الدفع.")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"ارسل صورة التحويل إلى المحفظة:\n`{WALLET_ADDRESS}`\nسيتم التفعيل فوراً بعد المراجعة.")

@bot.message_handler(content_types=['photo'])
def handle_photo(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تفعيل 30 يوم", callback_data=f"v_{m.from_user.id}_30"))
    bot.send_message(OWNER_ID, f"إثبات دفع من {m.from_user.id}", reply_markup=markup)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم الاستلام، انتظر تفعيل المالك.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def finalize(c):
    _, uid, days = c.data.split("_")
    db["vip"][uid] = time.time() + (int(days) * 86400)
    save_db()
    bot.send_message(uid, "🌟 تم تفعيل اشتراكك بنجاح! حلل الآن.")
    bot.answer_callback_query(c.id, "تم التفعيل")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc(m):
    uid = str(m.from_user.id)
    v = db["vip"].get(uid, 0) > time.time()
    status = "VIP" if v else "مجاني"
    bot.send_message(m.chat.id, f"👤 الحالة: {status}\n📊 المحاولات المجانية المستخدمة: {db['usage'][uid].get('free', 0)}/5")

bot.infinity_polling()
