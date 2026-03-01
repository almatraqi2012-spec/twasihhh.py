import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ سيرفر التشغيل والـ Webhook ] ---
app = Flask('')

@app.route('/')
def home(): return "Radar Pro V3 Final is 100% Active"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and (data.get('status') == 'success' or data.get('status') == 1):
        description = data.get('description', '')
        if "VIP_" in description:
            uid = description.split("_")[1]
            db["vip"][uid] = time.time() + (30 * 86400)
            save_db()
            try:
                bot.send_message(uid, "🌟 مبروك! تم تفعيل اشتراكك VIP تلقائياً.\nاستمتع الآن بكافة ميزات الرادار بلا حدود.")
            except: pass
            return "OK", 200
    return "No Action", 200

def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# --- [ الإعدادات - يرجى مراجعة المفاتيح ] ---
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

# --- [ المحرك الفني "القناص" V3 المنقح ] ---
def get_analysis(symbol):
    try:
        s_clean = symbol.upper().replace("/", "").strip()
        if not s_clean.endswith("USDT"): s_clean += "USDT"
        
        # جلب البيانات من بينانس أو مكسيك
        url = f"https://api.binance.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
        r = requests.get(url, timeout=10)
        source = "BINANCE"
        if r.status_code != 200:
            url = f"https://api.mexc.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
            r = requests.get(url, timeout=10); source = "MEXC"
            
        data = r.json()
        closes = [float(c[4]) for c in data]
        price = closes[-1]
        
        # حساب المؤشرات (RSI, BB, MACD)
        diffs = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        avg_gain = sum([d for d in diffs[-14:] if d > 0]) / 14
        avg_loss = sum([-d for d in diffs[-14:] if d < 0]) / 14
        rsi = 100 - (100 / (1 + (avg_gain/avg_loss if avg_loss != 0 else 1)))
        
        sma20 = sum(closes[-20:]) / 20
        variance = sum([(x - sma20)**2 for x in closes[-20:]]) / 20
        std_dev = variance**0.5
        upper_band = sma20 + (std_dev * 2)
        lower_band = sma20 - (std_dev * 2)
        
        ema12 = sum(closes[-12:]) / 12
        ema26 = sum(closes[-26:]) / 26
        macd_line = ema12 - ema26

        # --- المنطق الفني الصارم (إصلاح التناقض) ---
        if rsi >= 70 or price >= upper_band:
            signal = "⚠️ جني أرباح / خطر"
            desc = "المؤشرات وصلت لتشبع شرائي (قمة)، يفضل الخروج الآن."
            target, stop = "قريب من القمة", "خروج فوراً"
        elif rsi <= 35 or price <= lower_band:
            signal = "🚀 شراء قوي (قاع مؤكد)"
            desc = "انعكاس سعري مرتقب من منطقة تشبع بيعي، فرصة ممتازة."
            target, stop = round(price * 1.055, 4), round(price * 0.96, 4)
        elif macd_line > 0 and rsi > 45:
            signal = "📈 ترند صاعد (استمرارية)"
            desc = "الزخم إيجابي والسيولة تدخل العملة، الأهداف محققة بإذن الله."
            target, stop = round(price * 1.035, 4), round(price * 0.97, 4)
        elif rsi < 50 and price < sma20:
            signal = "📉 ترند هابط (ضعف)"
            desc = "العملة تحت الضغط البيعي، لا ننصح بالدخول قبل الاختراق."
            target, stop = "---", "---"
        else:
            signal = "⚖️ منطقة تجميع عرضية"
            desc = "السعر يتحرك في نطاق ضيق، مناسب للمراقبة أو التجميع الهادئ."
            target, stop = round(price * 1.018, 4), round(price * 0.985, 4)

        chart_url = f"https://www.tradingview.com/chart/?symbol={source}:{s_clean}"
        
        return (f"🏛 **رادار القابضة V3 - المحلل الخبير**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s_clean} | `{source}`\n💰 السعر: `{price}`\n"
                f"📊 RSI: {rsi:.1f} | BB: {'قاع' if price < lower_band else 'قمة' if price > upper_band else 'وسط'}\n"
                f"📊 MACD: {'إيجابي' if macd_line > 0 else 'سلبي'}\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{signal}**\n📌 الحالة: {desc}\n━━━━━━━━━━━━━━\n"
                f"🎯 الهدف القادم: `{target}`\n🛡️ الوقف: `{stop}`\n"
                f"🔗 [فتح الشارت المباشر]({chart_url})")
    except: return None

# --- [ واجهة المستخدم والأزرار ] ---
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
    bot.send_message(m.chat.id, "👋 أهلاً بك في رادار القابضة V3.\nالنسخة الاحترافية الكاملة للدفع والتحليل.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ask_symbol(m):
    uid = str(m.from_user.id)
    is_vip = uid in db["vip"] and db["vip"][uid] > time.time()
    if is_vip or db["usage"][uid].get("free", 0) < 5:
        msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC أو ETH):")
        bot.register_next_step_handler(msg, perform_ana)
    else: bot.send_message(m.chat.id, "❌ انتهت المحاولات المجانية. يرجى الاشتراك.")

def perform_ana(m):
    # منع تداخل الأوامر
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري تحليل المؤشرات (RSI, BB, MACD)...")
    res = get_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if uid not in db["vip"] or db["vip"][uid] <= time.time():
            db["usage"][uid]["free"] += 1
            save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ الرمز غير صحيح أو السيرفر مشغول.")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def start_oxa(m):
    bot.send_message(m.chat.id, "⏳ جاري إنشاء فاتورة دفع آمنة...")
    payload = {
        "merchant": OXA_API_KEY, 
        "amount": 50, 
        "currency": "USDT", 
        "network": "TRC20",
        "description": f"VIP_{m.from_user.id}",
        "callbackUrl": "https://twasihhh-py.onrender.com/webhook",
        "returnUrl": f"https://t.me/{(bot.get_me()).username}"
    }
    try:
        # استخدام هيدرز لضمان القبول
        headers = {'Content-Type': 'application/json'}
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=payload, headers=headers, timeout=20)
        res = r.json()
        if res.get("status") == "success" or res.get("payUrl"):
            pay_url = res.get('payUrl')
            bot.send_message(m.chat.id, f"✅ **فاتورة الاشتراك جاهزة**\n\n💰 المبلغ: 50 USDT\n🔗 [اضغط هنا للدفع الآمن]({pay_url})\n\nسيتم تفعيل حسابك تلقائياً فور تأكيد الدفع.", parse_mode="Markdown")
        else:
            bot.send_message(m.chat.id, f"⚠️ عذراً: {res.get('message', 'خطأ في الربط')}.\nيرجى استخدام التفعيل اليدوي حالياً.")
    except: bot.send_message(m.chat.id, "⚠️ خطأ في الاتصال ببوابة OxaPay.")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual_msg(m):
    bot.send_message(m.chat.id, f"أرسل صورة تحويل 50$ لعنوان USDT-TRC20:\n`{WALLET_ADDRESS}`\nثم انتظر تفعيل المالك.")

@bot.message_handler(content_types=['photo'])
def handle_payment_photo(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تفعيل 30 يوم", callback_data=f"act_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إثبات دفع جديد من: {m.from_user.id}", reply_markup=markup)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم استلام الإثبات، سيتم مراجعته وتفعيلك قريباً.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def admin_confirm(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db()
    bot.send_message(uid, "🌟 مبروك! تم تفعيل اشتراكك VIP لمدة شهر بنجاح.")
    bot.answer_callback_query(c.id, "تم التفعيل")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def my_account(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    bot.send_message(m.chat.id, f"📊 تفاصيل الحساب:\n👤 الحالة: {'VIP 🌟' if is_v else 'مجاني 👤'}\n🔄 الاستهلاك: {db['usage'][uid].get('free', 0)}/5")

bot.infinity_polling()
