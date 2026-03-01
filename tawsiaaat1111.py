import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ سيرفر التشغيل والـ Webhook ] ---
app = Flask('')

@app.route('/')
def home(): return "Radar Pro is 100% Active"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and data.get('status') == 'success':
        # استخراج ID المستخدم من الوصف المرسل للفاتورة
        description = data.get('description', '')
        if "VIP_" in description:
            uid = description.split("_")[1]
            db["vip"][uid] = time.time() + (30 * 86400)
            save_db()
            try:
                bot.send_message(uid, "🌟 مبروك! تم تفعيل اشتراكك VIP تلقائياً عبر نظام الدفع الذكي.")
            except: pass
            return "OK", 200
    return "No Action", 200

def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_fixed_final.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "usage": {}}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل الاحترافي ] ---
def get_analysis(symbol):
    try:
        s_clean = symbol.upper().replace("/", "").strip()
        if not s_clean.endswith("USDT"): s_clean += "USDT"
        
        # جلب بيانات كافية للتحليل العميق (100 شمعة)
        url = f"https://api.binance.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
        r = requests.get(url, timeout=10)
        source = "BINANCE"
        if r.status_code != 200:
            url = f"https://api.mexc.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
            r = requests.get(url, timeout=10); source = "MEXC"
            
        data = r.json()
        closes = [float(c[4]) for c in data]
        price = closes[-1]
        
        # 1. حساب RSI
        diffs = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        avg_gain = sum([d for d in diffs[-14:] if d > 0]) / 14
        avg_loss = sum([-d for d in diffs[-14:] if d < 0]) / 14
        rsi = 100 - (100 / (1 + (avg_gain/avg_loss if avg_loss != 0 else 1)))

        # 2. حساب Bollinger Bands (20, 2)
        sma20 = sum(closes[-20:]) / 20
        variance = sum([(x - sma20)**2 for x in closes[-20:]]) / 20
        std_dev = variance**0.5
        upper_band = sma20 + (std_dev * 2)
        lower_band = sma20 - (std_dev * 2)

        # 3. حساب تقاطع MACD (مبسط)
        ema12 = sum(closes[-12:]) / 12
        ema26 = sum(closes[-26:]) / 26
        macd_line = ema12 - ema26

        # --- خوارزمية اتخاذ القرار (نظام النقاط) ---
        score = 0
        if rsi < 35: score += 2  # منطقة قاع
        if price <= lower_band: score += 2 # كسر البولينجر السفلي (ارتداد)
        if macd_line > 0: score += 1 # زخم إيجابي
        if price > sma20: score += 1 # ترند صاعد

        # تحديد الإشارة بناءً على القوة
        if score >= 4:
            signal = "🚀 شراء قوي جداً (ثقة عالية)"
            desc = "تطابق 4 مؤشرات: تشبع بيعي + ارتداد من البولينجر + سيولة MACD."
            target, stop = price * 1.055, price * 0.955
        elif score >= 2:
            signal = "📈 دخول مضاربي (ثقة متوسطة)"
            desc = "المؤشرات إيجابية تدريجياً، يفضل الدخول بأهداف قريبة."
            target, stop = price * 1.03, price * 0.97
        elif rsi > 70 or price >= upper_band:
            signal = "⚠️ جني أرباح / خروج"
            desc = "انتبه! السعر عند سقف البولينجر العلوي مع تضخم RSI."
            target, stop = "تم الوصول", "خروج فوراً"
        else:
            signal = "🚫 انتظار (مراقبة)"
            desc = "لا توجد إشارة دخول واضحة حالياً، انتظر تأكيد السيولة."
            target, stop = "---", "---"

        chart_url = f"https://www.tradingview.com/chart/?symbol={source}:{s_clean}"
        
        return (f"🏛 **رادار القابضة V3 - المحلل الخبير**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s_clean} | `{source}`\n💰 السعر الحالي: `{price}`\n"
                f"📊 RSI: {rsi:.1f} | BB: {'قاع' if price < lower_band else 'قمة' if price > upper_band else 'وسط'}\n"
                f"📊 MACD: {'إيجابي' if macd_line > 0 else 'سلبي'}\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{signal}**\n📌 الحالة: {desc}\n━━━━━━━━━━━━━━\n"
                f"🎯 الهدف القادم: `{target}`\n🛡️ وقف الخسارة: `{stop}`\n"
                f"🔗 [فتح الشارت المباشر لـ {s_clean}]({chart_url})")
    except: return None

# --- [ الأوامر الرئيسية ] ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔍 تحليل عملة", "💎 حسابي")
    m.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    return m

@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in db["usage"]: db["usage"][uid] = {"free": 0}
    save_db()
    bot.send_message(m.chat.id, "👋 رادار القابضة V2\nدقة في التحليل.. سرعة في التنفيذ.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ask_symbol(m):
    uid = str(m.from_user.id)
    is_vip = uid in db["vip"] and db["vip"][uid] > time.time()
    if is_vip or db["usage"][uid].get("free", 0) < 5:
        msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
        bot.register_next_step_handler(msg, perform_ana)
    else:
        bot.send_message(m.chat.id, "❌ انتهت محاولاتك المجانية. يرجى الاشتراك.")

def perform_ana(m):
    bot.send_message(m.chat.id, "⏳ جاري استخراج البيانات...")
    res = get_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if uid not in db["vip"] or db["vip"][uid] <= time.time():
            db["usage"][uid]["free"] += 1
            save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ العملة غير موجودة، تأكد من الرمز.")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def start_oxa(m):
    bot.send_message(m.chat.id, "⏳ جاري إنشاء فاتورة دفع آمنة...")
    try:
        res = requests.post("https://api.oxapay.com/api/v2/checkout", json={
            "merchant": OXA_API_KEY, "amount": 50, "currency": "USDT", "network": "TRC20",
            "description": f"VIP_{m.from_user.id}"
        }, timeout=15).json()
        if res.get("status") == "success":
            bot.send_message(m.chat.id, f"✅ رابط الدفع التلقائي:\n{res.get('payUrl')}\nسيتم تفعيل حسابك لحظياً فور تأكيد الدفع.")
        else: bot.send_message(m.chat.id, "⚠️ فشل الاتصال ببوابة الدفع.")
    except: bot.send_message(m.chat.id, "⚠️ البوابة تحت الصيانة، استخدم اليدوي.")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual_msg(m):
    bot.send_message(m.chat.id, f"ارسل صورة التحويل لعنوان محفظتنا:\n`{WALLET_ADDRESS}`")

@bot.message_handler(content_types=['photo'])
def handle_payment_photo(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تفعيل الحساب", callback_data=f"act_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إثبات دفع جديد من: {m.from_user.id}", reply_markup=markup)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم استلام الإثبات، بانتظار مراجعة الإدارة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def admin_confirm(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db()
    bot.send_message(uid, "🌟 مبروك! تم تفعيل اشتراكك VIP بنجاح.")
    bot.answer_callback_query(c.id, "تم التفعيل")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def my_account(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    status = "VIP 🌟" if is_v else "مجاني 👤"
    bot.send_message(m.chat.id, f"📊 حالتك: {status}\n🔄 المحاولات المستخدمة: {db['usage'][uid].get('free', 0)}/5")

bot.infinity_polling()
