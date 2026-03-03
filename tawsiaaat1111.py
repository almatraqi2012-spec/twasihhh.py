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
                bot.send_message(uid, "🌟 **مبروك! تم تفعيل اشتراكك VIP تلقائياً.**\nأنت الآن تملك أقوى رادار تحليلي في السوق.")
                bot.send_message(6016547718, f"✅ تم تفعيل اشتراك تلقائي للمستخدم: {uid}")
    except: pass
    return "OK", 200

def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات والمفاتيح ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
BACKUP_PAY_LINK = "https://pay.oxapay.com/13416435/128048507"
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

# --- [ محرك التحليل الخوارزمي الرباعي - V17 PRO ] ---
def get_analysis(symbol):
    try:
        s = symbol.upper().replace("/", "").strip()
        if not s.endswith("USDT"): s += "USDT"
        
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=100"
        r = requests.get(url, timeout=7).json()
        
        closes = [float(c[4]) for c in r]
        highs = [float(c[2]) for c in r]; lows = [float(c[3]) for c in r]
        p = closes[-1]
        
        # 1. حساب المتوسط المتحرك (الترند)
        sma = sum(closes[-25:]) / 25
        # 2. حساب RSI (الزحم)
        rsi_period = 14
        gains = [max(0, closes[i] - closes[i-1]) for i in range(-rsi_period, 0)]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(-rsi_period, 0)]
        avg_g = sum(gains)/rsi_period; avg_l = sum(losses)/rsi_period
        rs = avg_g / (avg_l if avg_l != 0 else 1)
        rsi = 100 - (100 / (1 + rs))
        # 3. تحديد الدعوم والمقاومات (Price Action)
        sup = min(lows[-60:]); res = max(highs[-60:])

        # --- [ منطق القرار الخوارزمي ] ---
        
        # الحالة الأولى: صعود مؤكد (Long)
        if rsi < 35 and p > sup and p >= (sum(closes[-5:])/5): # تشبع بيعي + بداية ارتداد
            sig, stat = "🚀 إشارة: صعود (شراء)", "المؤشرات اتفقت على ارتداد من قاع صلب. الزحم بدأ في التحول للإيجابية."
            t1, t2, sl = p*1.035, p*1.07, p*0.965
            emoji = "🟢"
        
        # الحالة الثانية: هبوط مؤكد (Short/Sell)
        elif rsi > 65 or (p < sma and rsi > 50): # تشبع شرائي أو كسر متوسط
            sig, stat = "📉 إشارة: هبوط (بيع)", "السوق تحت ضغط بيعي كبير، السعر كسر المتوسطات الفنية ويستهدف مناطق أدنى."
            t1, t2, sl = p*0.96, p*0.93, p*1.03
            emoji = "🔴"

        # الحالة الثالثة: اتجاه صاعد مستقر (Trend Following)
        elif p > sma and rsi < 60:
            sig, stat = "📈 استمرار الصعود", "العملة في قناة صاعدة مستقرة فوق المتوسط المتحرك. فرصة جيدة للمواصلة."
            t1, t2, sl = res, res*1.02, p*0.97
            emoji = "🔵"
            
        else:
            sig, stat = "⏳ وضع الانتظار", "المؤشرات متضاربة حالياً. يفضل عدم الدخول وانتظار إشارة تأكيد أقوى."
            t1, t2, sl = p*1.02, p*1.04, p*0.98
            emoji = "⚪"

        return (f"🏛 **رادار القابضة V17 - التحليل الاحترافي**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} {emoji}\n💰 السعر الحالي: `{p}`\n📊 مؤشر القوة RSI: `{round(rsi,1)}`\n━━━━━━━━━━━━━━\n"
                f"💡 {sig}\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف أول: `{round(t1, 4)}`\n🎯 هدف ثاني: `{round(t2, 4)}`\n🛡️ الوقف (Stop Loss): `{round(sl, 4)}`\n━━━━━━━━━━━━━━\n"
                f"🔗 [عرض الشارت المباشر](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
    except: return None

# --- [ واجهة المستخدم والأوامر ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "💎 حسابي")
    mk.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V17**\nنظام التحليل الخوارزمي الموحد.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    uid = str(m.from_user.id); today = str(datetime.date.today())
    is_vip = db["vip"].get(uid, 0) > time.time()
    if is_vip:
        daily = db["daily_limit"].get(uid, {"count": 0, "last_reset": today})
        if daily["last_reset"] != today: daily = {"count": 0, "last_reset": today}
        if daily["count"] >= 5:
            bot.send_message(m.chat.id, "⚠️ انتهت حصتك اليومية (5/5)."); return
    else:
        if db["free_usage"].get(uid, 0) >= 5:
            bot.send_message(m.chat.id, "❌ انتهت المحاولات المجانية. اشترك للوصول الكامل."); return
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    uid = str(m.from_user.id)
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري استدعاء البيانات وتحليل الاتجاه...")
    res = get_analysis(m.text)
    if res:
        is_vip = db["vip"].get(uid, 0) > time.time()
        if is_vip:
            d = db["daily_limit"].get(uid, {"count": 0, "last_reset": str(datetime.date.today())})
            d["count"] += 1; db["daily_limit"][uid] = d
        else: db["free_usage"][uid] = db["free_usage"].get(uid, 0) + 1
        save_db(); bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ الرمز غير متاح حالياً.")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def pay_setup(m):
    msg = bot.send_message(m.chat.id, "💰 **أدخل مبلغ التفعيل (الحد الأدنى 50$):**")
    bot.register_next_step_handler(msg, pay_final)

def pay_final(m):
    if not m.text.isdigit() or int(m.text) < 50:
        bot.send_message(m.chat.id, "❌ يرجى إدخال مبلغ 50$ فأكثر."); return
    amount = m.text
    try:
        payload = {"merchant": OXA_API_KEY, "amount": int(amount), "currency": "USDT", "network": "TRC20", "description": f"CHARGE_{m.from_user.id}", "callbackUrl": "https://twasihhh-py.onrender.com/webhook"}
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=payload, timeout=10).json()
        if r.get("payUrl"):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 تفعيل تلقائي (OxaPay)", url=r['payUrl']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء الفاتورة بمبلغ {amount}$", reply_markup=markup)
            return
    except: pass
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط دفع احتياطي", url=BACKUP_PAY_LINK))
    bot.send_message(m.chat.id, "⚠️ البوابة مزدحمة، استخدم الرابط الاحتياطي:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc_info(m):
    uid = str(m.from_user.id); is_v = db["vip"].get(uid, 0) > time.time()
    msg = f"🌟 الحالة: {'VIP' if is_v else 'مجاني'}\n📊 محاولات اليوم: {db['daily_limit'].get(uid, {}).get('count', 0) if is_v else db['free_usage'].get(uid, 0)}/5"
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"أرسل لعنواننا: `{WALLET_ADDRESS}` وارسل صورة الإيصال.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل VIP", callback_data=f"v_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إيصال من {m.from_user.id}", reply_markup=btn)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def admin_v(c):
    u = c.data.split("_")[1]
    db["vip"][u] = time.time() + (30 * 86400)
    save_db(); bot.send_message(u, "🌟 تم تفعيل VIP بنجاح!"); bot.answer_callback_query(c.id, "تم")

if __name__ == "__main__":
    while True:
        try: bot.polling(none_stop=True, interval=0, timeout=60)
        except: time.sleep(5)
