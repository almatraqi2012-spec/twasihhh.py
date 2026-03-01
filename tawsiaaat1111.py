import requests, telebot, time, json, os
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ سيرفر التشغيل ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar Elite V3.2 is Online"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # OxaPay يرسل الحالة كـ integer أو string أحياناً، لذا نتحقق من الاثنين
    status = data.get('status')
    if data and (status == 'success' or status == 1 or status == '1'):
        desc = data.get('description', '')
        if "VIP_" in desc:
            uid = desc.split("_")[1]
            db["vip"][uid] = time.time() + (30 * 86400)
            save_db()
            try: bot.send_message(uid, "🌟 **تهانينا! تم تفعيل اشتراكك VIP تلقائياً.**\nيمكنك الآن استخدام كافة ميزات الرادار بلا حدود.")
            except: pass
    return "OK", 200

def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_pro_db.json"

bot = telebot.TeleBot(API_TOKEN)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "usage": {}}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ المحرك الفني المطور - دقة عالية ] ---
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
        
        # حساب المؤشرات
        sma20 = sum(closes[-20:]) / 20
        diffs = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        avg_gain = sum([d for d in diffs[-14:] if d > 0]) / 14
        avg_loss = sum([-d for d in diffs[-14:] if d < 0]) / 14
        rsi = 100 - (100 / (1 + (avg_gain/avg_loss if avg_loss != 0 else 1)))
        
        # Bollinger Bands
        std = (sum([(x - sma20)**2 for x in closes[-20:]]) / 20)**0.5
        up, low = sma20 + (std * 2), sma20 - (std * 2)

        # منطق الإشارات (واقعي ومباشر)
        if rsi < 40 or price <= low:
            sig, stat = "🚀 شراء (منطقة ارتداد)", "المؤشرات في قاع سعري، فرصة جيدة للصعود."
            tp, sl = round(price * 1.04, 2), round(price * 0.965, 2)
        elif rsi > 65 or price >= up:
            sig, stat = "⚠️ جني أرباح (قمة)", "السعر عند مقاومة البولينجر مع تضخم RSI."
            tp, sl = "قريب من الهدف", "تأمين أرباح"
        elif price > sma20:
            sig, stat = "📈 ترند صاعد (قوي)", "استقرار السعر فوق المتوسط يدعم استمرار الإيجابية."
            tp, sl = round(price * 1.03, 2), round(price * 0.975, 2)
        else:
            sig, stat = "📉 ضغط بيعي", "العملة تحت المتوسط، يفضل انتظار الاختراق."
            tp, sl = "---", "---"

        return (f"🏛 **رادار القابضة V3 - المحلل الخبير**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s_clean} | `{source}`\n💰 السعر: `{price}`\n📊 RSI: {rsi:.1f}\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 الهدف: `{tp}`\n🛡️ الوقف: `{sl}`\n"
                f"🔗 [الشارت المباشر](https://www.tradingview.com/chart/?symbol={source}:{s_clean})")
    except: return None

# --- [ الأوامر والواجهة ] ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔍 تحليل عملة", "💎 حسابي")
    m.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    return m

@bot.message_handler(commands=['start'])
def welcome(m):
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في رادار القابضة V3 Pro**\nنظام تحليل احترافي ودفع آمن.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ask(m):
    uid = str(m.from_user.id)
    is_vip = uid in db["vip"] and db["vip"][uid] > time.time()
    if is_vip or db["usage"].get(uid, {}).get("free", 0) < 5:
        msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثلاً BTC):")
        bot.register_next_step_handler(msg, ana)
    else: bot.send_message(m.chat.id, "❌ انتهت محاولاتك المجانية. اشترك للتحليل بلا حدود.")

def ana(m):
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري استخراج البيانات وتحليل السيولة...")
    res = get_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if uid not in db["vip"] or db["vip"][uid] <= time.time():
            if uid not in db["usage"]: db["usage"][uid] = {"free": 0}
            db["usage"][uid]["free"] += 1
            save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown", disable_web_page_preview=True)
    else: bot.send_message(m.chat.id, "⚠️ الرمز غير مدعوم حالياً.")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def pay(m):
    bot.send_message(m.chat.id, "⏳ جاري إنشاء فاتورة دفع آمنة...")
    
    # الربط البرمجي الصحيح والمطابق للمواصفات العالمية لـ OxaPay
    endpoint = "https://api.oxapay.com/api/v2/checkout"
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
        # إرسال الطلب كـ JSON مع Headers صريحة
        r = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
        res = r.json()
        
        # التحقق من نجاح العملية أو وجود رابط دفع
        if res.get("status") in ["success", 200, "200", 1, "1"] or "payUrl" in res:
            pay_url = res.get('payUrl')
            bot.send_message(m.chat.id, 
                f"✅ **تم إنشاء الفاتورة بنجاح**\n\n"
                f"💰 المبلغ: 50 USDT (TRC20)\n\n"
                f"🔗 [اضغط هنا للدفع الآمن]({pay_url})\n\n"
                f"سيتم تفعيل حسابك آلياً فور تأكيد المعاملة.", 
                parse_mode="Markdown")
        else:
            err = res.get('message', 'Validation Error')
            bot.send_message(m.chat.id, f"⚠️ فشل الربط: {err}\nيرجى التواصل مع الدعم أو التفعيل اليدوي.")
    except Exception as e:
        bot.send_message(m.chat.id, "⚠️ خطأ في الاتصال بالبوابة الآمنة.")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"أرسل صورة التحويل لعنوان محفظتنا:\n`{WALLET_ADDRESS}`\nالمبلغ: 50$")

@bot.message_handler(content_types=['photo'])
def photo(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ تفعيل الاشتراك", callback_data=f"act_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إثبات جديد من: {m.from_user.id}", reply_markup=mk)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم استلام الإثبات، بانتظار مراجعة الإدارة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def act(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db()
    bot.send_message(uid, "🌟 مبروك! تم تفعيل اشتراكك VIP بنجاح.")
    bot.answer_callback_query(c.id, "تم التفعيل")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    used = db["usage"].get(uid, {}).get("free", 0)
    bot.send_message(m.chat.id, f"📊 تفاصيل حسابك:\n👤 الحالة: {'VIP 🌟' if is_v else 'مجاني 👤'}\n🔄 الاستهلاك المجاني: {used}/5")

bot.infinity_polling()
