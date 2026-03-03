import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ إعدادات السيرفر والويب هوك ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V17 PRO - ONLINE 24/7"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if data and str(data.get('status')) in ['paid', 'success', '1']:
            uid = data.get('description', '').replace('CHARGE_', '')
            if uid.isdigit():
                db["vip"][uid] = time.time() + (30 * 86400)
                db["daily_limit"][uid] = {"count": 0, "last_reset": str(datetime.date.today())}
                save_db()
                bot.send_message(uid, "🌟 **تهانينا! تم تفعيل اشتراك VIP بنجاح لمدة 30 يوم.**\nلديك الآن 5 تحليلات دقيقة يومياً.")
    except: pass
    return "OK", 200

def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات والمفاتيح ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v17_final.json"

bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=30)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "free_usage": {}, "daily_limit": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل المطور - التعديل هنا فقط ] ---
def get_analysis(symbol):
    try:
        s = symbol.upper().replace("/", "").strip()
        if not s.endswith("USDT"): s += "USDT"
        
        # محاولة جلب البيانات من Binance (استخدام رابط مستقر)
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=100"
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return None
            
        data = r.json()
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        volumes = [float(c[5]) for c in data]
        p = closes[-1]
        
        # 1. المتوسط المتحرك (SMA 20)
        sma = sum(closes[-20:]) / 20
        # 2. مؤشر RSI (القوة النسبية) - حساب دقيق لآخر 14 شمعة
        gains = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        avg_g = sum(gains)/14; avg_l = sum(losses)/14
        rsi = 100 - (100 / (1 + (avg_g/avg_l if avg_l != 0 else 1)))
        # 3. تحليل السيولة (Volume)
        avg_vol = sum(volumes[-20:]) / 20
        vol_pumping = volumes[-1] > avg_vol * 1.3
        # 4. الدعوم والمقاومات
        support = min(lows[-40:]); resistance = max(highs[-40:])

        # --- خوارزمية التوصية الذكية ---
        if rsi < 33 and p <= sma * 1.01:
            sig, stat, emo = "🚀 شراء قوى (قاع لحظي)", "المؤشرات تشير لانفجار صعودي وشيك من منطقة دعم.", "🟢"
            t1, t2, sl = p*1.04, p*1.08, support*0.97
        elif rsi > 68 or (p < sma and rsi > 50):
            sig, stat, emo = "📉 نزول متوقع (تنبيه)", "السعر متضخم أو كسر المتوسط للأسفل. تجنب الشراء.", "🔴"
            t1, t2, sl = p*0.96, p*0.92, p*1.035
        elif p > sma and 45 < rsi < 65:
            sig, stat, emo = "📈 صعود مستقر", "الترند صاعد والسيولة مستمرة. الأهداف قريبة.", "🔵"
            t1, t2, sl = resistance, resistance*1.04, sma*0.98
        else:
            sig, stat, emo = "⏳ تذبذب (انتظار)", "السوق غير واضح الاتجاه حالياً. نراقب منطقة المقاومة.", "⚪"
            t1, t2, sl = p*1.02, p*1.05, p*0.98

        return (f"🏛 **رادار القابضة V17**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}` | 📊 RSI: `{round(rsi,1)}`\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف أول: `{round(t1, 4)}` | 🎯 هدف ثاني: `{round(t2, 4)}`\n🛡️ الوقف: `{round(sl, 4)}`\n\n"
                f"🔗 [عرض الشارت المباشر](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
    except: return None

# --- [ بقية الكود كما هو دون تغيير ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "💎 حسابي")
    mk.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V17**\nنظام التحليلات الرقمية الموحد والأكثر دقة.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    uid = str(m.from_user.id)
    today = str(datetime.date.today())
    is_vip = db["vip"].get(uid, 0) > time.time()
    if is_vip:
        daily = db["daily_limit"].get(uid, {"count": 0, "last_reset": today})
        if daily["last_reset"] != today: daily = {"count": 0, "last_reset": today}
        if daily["count"] >= 5:
            bot.send_message(m.chat.id, "⚠️ **انتهت حصتك اليومية للـ VIP (5/5).**"); return
    else:
        used = db["free_usage"].get(uid, 0)
        if used >= 5:
            bot.send_message(m.chat.id, "❌ **انتهت محاولاتك المجانية (5/5).**"); return
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    uid = str(m.from_user.id)
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري تحليل الاتجاه والمؤشرات...")
    res = get_analysis(m.text)
    if res:
        is_vip = db["vip"].get(uid, 0) > time.time()
        if is_vip:
            d = db["daily_limit"].get(uid, {"count": 0, "last_reset": str(datetime.date.today())})
            d["count"] += 1; db["daily_limit"][uid] = d
        else:
            db["free_usage"][uid] = db["free_usage"].get(uid, 0) + 1
        save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ الرمز غير متاح حالياً. تأكد من كتابة الرمز بشكل صحيح.")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def pay_setup(m):
    msg = bot.send_message(m.chat.id, "💰 **أدخل مبلغ التفعيل (مثال: 50):**")
    bot.register_next_step_handler(msg, pay_final)

def pay_final(m):
    if not m.text.isdigit(): return
    bot.send_message(m.chat.id, "⏳ جاري توليد الفاتورة...")
    try:
        p = {"merchant": OXA_API_KEY, "amount": int(m.text), "currency": "USDT", "network": "TRC20", "description": f"CHARGE_{m.from_user.id}"}
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=p, timeout=15).json()
        if r.get("payUrl"):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 رابط الدفع", url=r['payUrl']))
            bot.send_message(m.chat.id, f"✅ الفاتورة جاهزة:", reply_markup=markup)
    except: bot.send_message(m.chat.id, "⚠️ فشل في الاتصال بالبوابة.")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc_info(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    if is_v:
        c = db["daily_limit"].get(uid, {}).get("count", 0)
        msg = f"🌟 **الحالة: VIP نشط**\n📈 استهلاك اليوم: {c}/5"
    else:
        c = db["free_usage"].get(uid, 0)
        msg = f"👤 **الحالة: حساب مجاني**\n📊 الاستهلاك: {c}/5"
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"أرسل لعنواننا:\n`{WALLET_ADDRESS}`\nثم أرسل الإيصال.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل VIP", callback_data=f"v_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إيصال من {m.from_user.id}", reply_markup=btn)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "⏳ جاري مراجعة الإيصال...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def admin_v(c):
    u = c.data.split("_")[1]
    db["vip"][u] = time.time() + (30 * 86400)
    db["daily_limit"][u] = {"count": 0, "last_reset": str(datetime.date.today())}
    save_db(); bot.send_message(u, "🌟 تم تفعيل VIP بنجاح."); bot.answer_callback_query(c.id, "تم")

if __name__ == "__main__":
    bot.polling(none_stop=True)
