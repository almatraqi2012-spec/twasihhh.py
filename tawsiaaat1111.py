import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask
from threading import Thread

# --- [ سيرفر البقاء ] ---
app = Flask('')
@app.route('/')
def home(): return "Professional Radar is Active"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'FYYUOW-LY5JFH-BLBLUZ-9M6BTO'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_pro_v3.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return {"vip": {}, "usage": {}}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل الاحترافي V3 ] ---
def get_analysis(symbol):
    try:
        symbol = symbol.upper().replace("/", "").strip()
        if not symbol.endswith("USDT"): symbol += "USDT"
        
        # جلب بيانات كافية (100 شمعة) لتحليل دقيق
        res = requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100", timeout=5).json()
        if isinstance(res, dict): # إذا فشل بينانس جرب ماكسيك
            res = requests.get(f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100", timeout=5).json()

        closes = [float(c[4]) for c in res]
        highs = [float(c[2]) for c in res]
        lows = [float(c[3]) for c in res]
        
        # 1. حساب RSI
        gains = sum([max(0, closes[i] - closes[i-1]) for i in range(-14, 0)])
        losses = sum([max(0, closes[i-1] - closes[i]) for i in range(-14, 0)])
        rsi = 100 - (100 / (1 + (gains/losses if losses != 0 else 1)))
        
        # 2. حساب المتوسطات (SMA 20)
        sma20 = sum(closes[-20:]) / 20
        current_price = closes[-1]
        
        # --- خوارزمية اتخاذ القرار ---
        if rsi < 32 and current_price > (min(lows[-10:]) * 0.99):
            signal = "🚀 شراء قوي (منطقة قاع)"
            advice = "السعر في منطقة تشبع بيعي حاد مع بوادر ارتداد."
            target = current_price * 1.04 # هدف 4%
            stop = current_price * 0.96  # وقف 4%
        elif current_price > sma20 and rsi < 60:
            signal = "📈 دخول (ترند صاعد)"
            advice = "السعر بدأ بالاختراق فوق المتوسط، اتجاه إيجابي."
            target = current_price * 1.03
            stop = current_price * 0.97
        elif rsi > 68:
            signal = "⚠️ جني أرباح / بيع"
            advice = "تضخم في المؤشرات، قد يبدأ السعر بالتصحيح قريباً."
            target = current_price * 0.97
            stop = current_price * 1.03
        else:
            signal = "⚖️ مراقبة (تذبذب)"
            advice = "السعر في منطقة حيرة، انتظر اختراق المتوسط أو هبوط للقاع."
            target = sma20
            stop = current_price * 0.95

        return (f"🏛 **رادار القابضة - المحلل الذكي**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{symbol}\n💰 السعر: `{current_price}`\n📊 RSI: {rsi:.1f}\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{signal}**\n📌 النصيحة: {advice}\n━━━━━━━━━━━━━━\n"
                f"🎯 الهدف القادم: `{target:.4f}`\n🛡️ وقف الخسارة: `{stop:.4f}`")
    except: return None

# --- [ الأوامر والخدمات ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["usage"]:
        db["usage"][uid] = {"count": 0, "free_used": 0}
        save_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 تحليل عملة", "💎 حسابي")
    markup.add("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي (ارسل صورة)")
    bot.send_message(m.chat.id, f"أهلاً بك {m.from_user.first_name} في رادار القابضة النسخة الاحترافية V3.\nنظامنا يحلل السوق بناءً على حركة الحيتان والمؤشرات الفنية الحقيقية.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def check_limit(m):
    uid = str(m.from_user.id)
    is_vip = uid in db["vip"] and db["vip"][uid] > time.time()
    
    # المستخدم المجاني له 5 محاولات فقط مدى الحياة
    if not is_vip and db["usage"][uid].get("free_used", 0) >= 5:
        bot.send_message(m.chat.id, "❌ انتهت محاولاتك المجانية (5/5).\nللحصول على 5 تحليلات يومياً، يرجى الاشتراك في VIP.")
        return

    # المشترك VIP له 5 محاولات يومياً (تتجدد تلقائياً)
    if is_vip:
        today = datetime.date.today().isoformat()
        if db["usage"][uid].get("last_date") != today:
            db["usage"][uid]["count"] = 0
            db["usage"][uid]["last_date"] = today
        
        if db["usage"][uid]["count"] >= 5:
            bot.send_message(m.chat.id, "❌ انتهى حدك اليومي (5/5). حاول غداً.")
            return

    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: SOL):")
    bot.register_next_step_handler(msg, process_ana)

def process_ana(m):
    uid = str(m.from_user.id)
    res = get_analysis(m.text)
    if res:
        is_vip = uid in db["vip"] and db["vip"][uid] > time.time()
        if is_vip: db["usage"][uid]["count"] += 1
        else: db["usage"][uid]["free_used"] += 1
        save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ الرمز غير صحيح أو خارج نطاق الرادار.")

# --- [ قسم الدفع المطور ] ---
@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def oxa_payment(m):
    res = requests.post("https://api.oxapay.com/api/v2/checkout", json={
        "merchant": OXA_API_KEY, "amount": 50, "currency": "USDT", "network": "TRC20",
        "description": f"VIP_{m.from_user.id}"
    }).json()
    if res.get("status") == "success":
        bot.send_message(m.chat.id, f"⚡ رابط الدفع التلقائي آمن 100%:\n{res.get('payUrl')}\nسيتم تفعيل حسابك فور إتمام العملية.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تفعيل 50$ (شهر)", callback_data=f"act_{m.from_user.id}_30"))
    bot.send_message(OWNER_ID, f"🔔 إثبات جديد من {m.from_user.id}", reply_markup=markup)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ وصل الإثبات، جاري المراجعة والتفعيل.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def finalize(c):
    _, uid, days = c.data.split("_")
    db["vip"][uid] = time.time() + (int(days) * 86400)
    save_db()
    bot.send_message(uid, "🌟 تم تفعيل اشتراكك VIP بنجاح! لديك الآن 5 محاولات تحليل كل يوم.")
    bot.send_message(OWNER_ID, "تم التفعيل بنجاح.")

bot.infinity_polling()
