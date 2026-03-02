import requests, telebot, time, json, os
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ سيرفر التشغيل ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V5 Digital Pro is Online"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and (data.get('status') in ['success', 1, '1']):
        desc = data.get('description', '')
        if "VIP_" in desc:
            uid = desc.split("_")[1]
            db["vip"][uid] = time.time() + (30 * 86400)
            save_db()
            try: bot.send_message(uid, "🌟 **تم تفعيل اشتراكك VIP تلقائياً!**\nاستمتع الآن بأقوى التوصيات الرقمية.")
            except: pass
    return "OK", 200

def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# --- [ الإعدادات والمفاتيح ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v5_final.json"

bot = telebot.TeleBot(API_TOKEN)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "usage": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ المحرك الرقمي الدقيق V5 ] ---
def get_analysis(symbol):
    try:
        s_clean = symbol.upper().replace("/", "").strip()
        if not s_clean.endswith("USDT"): s_clean += "USDT"
        
        url = f"https://api.binance.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
        r = requests.get(url, timeout=10)
        source = "BINANCE"
        if r.status_code != 200:
            url = f"https://api.mexc.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
            r = requests.get(url, timeout=10); source = "MEXC"
            
        data = r.json()
        closes = [float(c[4]) for c in data]
        price = closes[-1]
        
        # مؤشرات الحساب
        sma = sum(closes[-20:]) / 20
        diffs = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        avg_gain = sum([d for d in diffs[-14:] if d > 0]) / 14
        avg_loss = sum([-d for d in diffs[-14:] if d < 0]) / 14
        rsi = 100 - (100 / (1 + (avg_gain/avg_loss if avg_loss != 0 else 1)))
        std = (sum([(x - sma)**2 for x in closes[-20:]]) / 20)**0.5
        up, low = sma + (std * 2), sma - (std * 2)

        # --- خوارزمية الأهداف الرقمية (إصبار المشترك بالأرقام) ---
        if rsi < 40 or price <= low:
            sig, stat = "🚀 شراء مضاربي (فرصة قوية)", "العملة في منطقة قاع ارتدادي، السيولة تبدأ بالدخول."
            t1, t2, sl = price * 1.025, price * 1.05, price * 0.97
        elif rsi > 65 or price >= up:
            sig, stat = "⚠️ جني أرباح / بيع (قمة)", "السعر متضخم حالياً. إذا كنت داخل الصفقة اجنِ أرباحك عند الأهداف."
            t1, t2, sl = price * 1.01, price * 1.02, price * 0.985 # أهداف تأمين
        elif price > sma:
            sig, stat = "📈 استمرار صعود (ترند إيجابي)", "العملة تحافظ على زخمها فوق المتوسط السعري."
            t1, t2, sl = price * 1.035, price * 1.06, price * 0.975
        else:
            sig, stat = "📉 ضغط بيعي (مراقبة)", "الاتجاه الحالي هابط، انتظر الاستقرار أو الدخول عند الأهداف."
            t1, t2, sl = price * 0.95, price * 0.92, price * 1.02 # أهداف شراء من أسفل

        # تنسيق الأرقام ليكون مريحاً للعين (4 أرقام عشرية)
        t1, t2, sl = round(t1, 4), round(t2, 4), round(sl, 4)

        return (f"🏛 **رادار القابضة V5 - المحلل الرقمي**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s_clean} | `{source}`\n💰 السعر: `{price}`\n📊 RSI: {rsi:.1f} | BB: {'قاع' if price < low else 'قمة' if price > up else 'وسط'}\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف أول: `{t1}`\n🎯 هدف ثاني: `{t2}`\n🛡️ الوقف: `{sl}`\n\n"
                f"🔗 [عرض الشارت المباشر](https://www.tradingview.com/chart/?symbol={source}:{s_clean})")
    except: return None

# --- [ واجهة المستخدم ] ---
def main_menu(uid):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔍 تحليل عملة", "💎 حسابي")
    m.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    if str(uid) == OWNER_ID: m.row("📊 لوحة الإدارة")
    return m

@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: 
        db["users"].append(uid)
        db["usage"][uid] = {"free": 0}
        save_db()
    bot.send_message(m.chat.id, "👋 مرحباً بك في رادار القابضة V5.\nنظام التوصيات الرقمية الدقيقة.", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ask(m):
    uid = str(m.from_user.id)
    is_vip = uid in db["vip"] and db["vip"][uid] > time.time()
    if is_vip or db["usage"].get(uid, {}).get("free", 0) < 5:
        msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثلاً BTC):")
        bot.register_next_step_handler(msg, ana)
    else: bot.send_message(m.chat.id, "❌ انتهت المحاولات المجانية. يرجى الاشتراك.")

def ana(m):
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي", "📊 لوحة الإدارة"]: return
    bot.send_message(m.chat.id, "⏳ جاري استخراج الأهداف الرقمية...")
    res = get_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if uid not in db["vip"] or db["vip"][uid] <= time.time():
            db["usage"][uid]["free"] += 1
            save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown", disable_web_page_preview=True)
    else: bot.send_message(m.chat.id, "⚠️ الرمز غير موجود أو السيرفر مشغول.")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def pay(m):
    bot.send_message(m.chat.id, "⏳ جاري طلب فاتورة من OxaPay...")
    payload = {
        "merchant": OXA_API_KEY, "amount": 50, "currency": "USDT", "network": "TRC20",
        "description": f"VIP_{m.from_user.id}",
        "callbackUrl": "https://twasihhh-py.onrender.com/webhook",
        "returnUrl": f"https://t.me/{(bot.get_me()).username}"
    }
    try:
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=payload, timeout=20)
        res = r.json()
        if res.get("status") in ["success", 200, 1, "1"] or "payUrl" in res:
            bot.send_message(m.chat.id, f"✅ **فاتورة VIP جاهزة**\n\n🔗 [اضغط هنا للدفع الآمن]({res.get('payUrl')})\n\nسيتم التفعيل تلقائياً فور تأكيد المعاملة.", parse_mode="Markdown")
        else: bot.send_message(m.chat.id, f"⚠️ عذراً: {res.get('message', 'خطأ بالربط')}")
    except: bot.send_message(m.chat.id, "⚠️ فشل الاتصال ببوابة الدفع.")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"أرسل صورة التحويل لعنوان محفظتنا:\n`{WALLET_ADDRESS}`\nالمبلغ: 50$")

@bot.message_handler(content_types=['photo'])
def photo(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ تفعيل الحساب", callback_data=f"act_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إثبات جديد من {m.from_user.id}", reply_markup=mk)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ استلمنا الصورة، جاري المراجعة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def act(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db()
    bot.send_message(uid, "🌟 مبروك! تم تفعيل اشتراكك VIP بنجاح.")
    bot.answer_callback_query(c.id, "تم!")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc(m):
    uid = str(m.from_user.id)
    v = db["vip"].get(uid, 0) > time.time()
    bot.send_message(m.chat.id, f"📊 **معلومات الحساب:**\n👤 الحالة: {'VIP 🌟' if v else 'مجاني 👤'}\n🔄 المحاولات: {db['usage'].get(uid, {}).get('free', 0)}/5")

bot.infinity_polling()
