import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ سيرفر التشغيل والـ Webhook ] ---
app = Flask('')

@app.route('/')
def home(): return "Radar Pro V3 is Fully Active"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and data.get('status') == 'success':
        description = data.get('description', '')
        if "VIP_" in description:
            uid = description.split("_")[1]
            db["vip"][uid] = time.time() + (30 * 86400)
            save_db()
            try:
                bot.send_message(uid, "🌟 مبروك! تم تفعيل اشتراكك VIP تلقائياً عبر نظام الدفع الذكي.\nيمكنك الآن التحليل بلا حدود يومياً.")
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

# --- [ محرك التحليل الاحترافي القناص ] ---
def get_analysis(symbol):
    try:
        s_clean = symbol.upper().replace("/", "").strip()
        if not s_clean.endswith("USDT"): s_clean += "USDT"
        
        # جلب البيانات
        url = f"https://api.binance.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
        r = requests.get(url, timeout=10)
        source = "BINANCE"
        if r.status_code != 200:
            url = f"https://api.mexc.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
            r = requests.get(url, timeout=10); source = "MEXC"
            
        data = r.json()
        closes = [float(c[4]) for c in data]
        price = closes[-1]
        
        # 1. RSI
        diffs = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        avg_gain = sum([d for d in diffs[-14:] if d > 0]) / 14
        avg_loss = sum([-d for d in diffs[-14:] if d < 0]) / 14
        rsi = 100 - (100 / (1 + (avg_gain/avg_loss if avg_loss != 0 else 1)))

        # 2. Bollinger Bands
        sma20 = sum(closes[-20:]) / 20
        variance = sum([(x - sma20)**2 for x in closes[-20:]]) / 20
        std_dev = variance**0.5
        upper_band = sma20 + (std_dev * 2)
        lower_band = sma20 - (std_dev * 2)

        # 3. MACD
        ema12 = sum(closes[-12:]) / 12
        ema26 = sum(closes[-26:]) / 26
        macd_line = ema12 - ema26

        # --- خوارزمية القرار المطورة ---
        score = 0
        if rsi < 38: score += 2
        if price <= lower_band * 1.01: score += 2
        if macd_line > -5: score += 1
        if price > sma20: score += 1

        if score >= 4:
            signal = "🚀 شراء قوي (ثقة عالية)"
            desc = "انفجار سعري متوقع. توافق مؤشرات القاع مع السيولة."
            target, stop = price * 1.052, price * 0.96
        elif score >= 2 or (rsi < 50 and price < sma20):
            signal = "📈 شراء مضاربي (فرصة سريعة)"
            desc = "تحرك إيجابي هادئ. مناسب للمضاربة السريعة (سكالبينج)."
            target, stop = price * 1.028, price * 0.975
        elif rsi > 68 or price >= upper_band * 0.99:
            signal = "⚠️ جني أرباح / خطر"
            desc = "وصلنا لمناطق تشبع شرائي قوية. ينصح بتأمين الأرباح."
            target, stop = "قريب من القمة", "جني أرباح فوراً"
        else:
            signal = "⚖️ منطقة تجميع عرضية"
            desc = "السعر يتحرك ببطء. مناسب للتجميع للمدى المتوسط."
            target, stop = price * 1.018, price * 0.985

        chart_url = f"https://www.tradingview.com/chart/?symbol={source}:{s_clean}"
        
        return (f"🏛 **رادار القابضة V3 - المحلل الخبير**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s_clean} | `{source}`\n💰 السعر الحالي: `{price}`\n"
                f"📊 RSI: {rsi:.1f} | BB: {'قاع' if price < lower_band else 'قمة' if price > upper_band else 'وسط'}\n"
                f"📊 MACD: {'إيجابي' if macd_line > 0 else 'سلبي'}\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{signal}**\n📌 الحالة: {desc}\n━━━━━━━━━━━━━━\n"
                f"🎯 الهدف القادم: `{target}`\n🛡️ وقف الخسارة: `{stop}`\n"
                f"🔗 [فتح الشارت المباشر لـ {s_clean}]({chart_url})")
    except: return None

# --- [ الأوامر والواجهة ] ---
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
    bot.send_message(m.chat.id, "👋 مرحباً بك في رادار القابضة V3.\nالبوت رقم #1 لتحليل سوق الكريبتو بدقة الحيتان.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ask_symbol(m):
    uid = str(m.from_user.id)
    is_vip = uid in db["vip"] and db["vip"][uid] > time.time()
    if is_vip or db["usage"][uid].get("free", 0) < 5:
        msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC أو SOL):")
        bot.register_next_step_handler(msg, perform_ana)
    else:
        bot.send_message(m.chat.id, "❌ انتهت محاولاتك المجانية (5/5).\nيرجى الاشتراك لمتابعة التحليل بلا حدود.")

def perform_ana(m):
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي"]:
        return # تجنب تداخل الأزرار
    bot.send_message(m.chat.id, "⏳ جاري تحليل المؤشرات (RSI, MACD, BB)...")
    res = get_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if uid not in db["vip"] or db["vip"][uid] <= time.time():
            db["usage"][uid]["free"] += 1
            save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ الرمز غير صحيح. تأكد من كتابة الاسم (مثل BTC).")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def start_oxa(m):
    bot.send_message(m.chat.id, "⏳ جاري الاتصال ببوابة OxaPay الآمنة...")
    try:
        # تأكد من أن الرابط الخاص بك مضاف في OxaPay كـ IPN
        res = requests.post("https://api.oxapay.com/api/v2/checkout", json={
            "merchant": OXA_API_KEY, 
            "amount": 50, 
            "currency": "USDT", 
            "network": "TRC20",
            "description": f"VIP_{m.from_user.id}"
        }, timeout=20).json()
        if res.get("status") == "success":
            bot.send_message(m.chat.id, f"✅ تم إنشاء الفاتورة بنجاح:\n\n🔗 [اضغط هنا للدفع الآمن]({res.get('payUrl')})\n\nسيتم تفعيل حسابك تلقائياً فور تأكيد الشبكة.", parse_mode="Markdown")
        else: bot.send_message(m.chat.id, "⚠️ فشل إنشاء الفاتورة، حاول مرة أخرى أو استخدم التفعيل اليدوي.")
    except: bot.send_message(m.chat.id, "⚠️ خطأ في الاتصال بالسيرفر. يرجى المحاولة لاحقاً.")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual_msg(m):
    bot.send_message(m.chat.id, f"الدفع اليدوي:\n1- حول 50$ لعنوان USDT-TRC20:\n`{WALLET_ADDRESS}`\n2- أرسل صورة التحويل هنا.")

@bot.message_handler(content_types=['photo'])
def handle_payment_photo(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تفعيل 30 يوم", callback_data=f"act_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إثبات جديد من: {m.from_user.id}", reply_markup=markup)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم استلام الإثبات بنجاح. سيقوم المالك بتفعيل حسابك قريباً.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def admin_confirm(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db()
    bot.send_message(uid, "🌟 مبروك! قام المالك بتفعيل اشتراكك VIP لمدة شهر.")
    bot.answer_callback_query(c.id, "تم التفعيل")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def my_account(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    status = "إشتراك VIP 🌟" if is_v else "حساب مجاني 👤"
    used = db["usage"][uid].get("free", 0)
    bot.send_message(m.chat.id, f"📊 معلومات الحساب:\n━━━━━━━━━━━━━━\n👤 الحالة: {status}\n🔄 التحليلات المجانية: {used}/5\n🆔 آيدي الحساب: `{uid}`", parse_mode="Markdown")

bot.infinity_polling()
