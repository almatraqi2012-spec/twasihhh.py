import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ 1. السيرفر والويب هوك ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar System Active"

@app.route('/webhook', methods=['POST'])
def webhook():
    # هذا الجزء لاستقبال تأكيدات الدفع التلقائي من OxaPay
    data = request.json
    if data.get('status') == 'success':
        uid = data.get('description').split()[-1]
        activate_user_logic(uid, 30)
    return "OK", 200

def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# --- [ 2. الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'FYYUOW-LY5JFH-BLBLUZ-9M6BTO'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_pro_db.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ 3. وظائف النظام ] ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return {"vip": {}, "usage": {}}

db = load_db()

def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

def activate_user_logic(uid, days):
    uid = str(uid)
    db["vip"][uid] = time.time() + (days * 86400)
    if uid not in db["usage"]: db["usage"][uid] = {"count": 0, "last_reset": ""}
    db["usage"][uid]["count"] = 0 # تصفير العداد عند التفعيل
    save_db()

# --- [ 4. محرك التحليل النقطي ] ---
def get_analysis(symbol):
    try:
        symbol = symbol.upper().replace("/", "").strip()
        if not symbol.endswith("USDT"): symbol += "USDT"
        res = requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=50").json()
        closes = [float(c[4]) for c in res]
        rsi_g = sum([max(0, closes[i] - closes[i-1]) for i in range(-14, 0)])
        rsi_l = sum([max(0, closes[i-1] - closes[i]) for i in range(-14, 0)])
        rsi = 100 - (100 / (1 + (rsi_g/rsi_l if rsi_l != 0 else 1)))
        price = closes[-1]
        
        if rsi < 30: s, t = "🚀 شراء قوي", "تشبع بيعي - ارتداد وشيك"
        elif rsi > 70: s, t = "⚠️ بيع/جني أرباح", "تشبع شرائي - تصحيح متوقع"
        else: s, t = "📉 اتجاه سلبي", "لا توجد إشارة دخول قوية"
        
        return f"🏛 **رادار القابضة**\n🪙 العملة: #{symbol}\n💰 السعر: `{price}`\n📊 RSI: {rsi:.1f}\n💡 الإشارة: {s}\n📌 التحليل: {t}\n🎯 الهدف: `{price*1.03:.4f}`\n🛡️ الوقف: `{price*0.97:.4f}`"
    except: return None

# --- [ 5. معالجة الرسائل ] ---
@bot.message_handler(commands=['start'])
def start(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 تحليل عملة", "💎 حسابي")
    markup.add("💳 اشتراك VIP", "👨‍💻 تفعيل الحساب")
    bot.send_message(m.chat.id, "مرحباً بك في رادار القابضة V2\nحلل عملاتك بدقة الحيتان.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def check(m):
    uid = str(m.from_user.id)
    now = time.time()
    today = datetime.date.today().isoformat()
    
    is_vip = uid in db["vip"] and db["vip"][uid] > now
    user_data = db["usage"].get(uid, {"count": 0, "last_reset": ""})
    
    if user_data["last_reset"] != today:
        user_data["count"] = 0
        user_data["last_reset"] = today

    if is_vip:
        if user_data["count"] < 5:
            msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة:")
            bot.register_next_step_handler(msg, process_item)
        else:
            bot.send_message(m.chat.id, "❌ انتهى حدك اليومي (5 عملات). حاول غداً.")
    else:
        bot.send_message(m.chat.id, "⚠️ هذا القسم للمشتركين فقط. اشترك لتتمكن من التحليل.")
    db["usage"][uid] = user_data
    save_db()

def process_item(m):
    res = get_analysis(m.text)
    if res:
        db["usage"][str(m.from_user.id)]["count"] += 1
        save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ رمز خطأ.")

# --- [ 6. نظام الدفع اليدوي والتلقائي ] ---
@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP")
def pay(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ دفع تلقائي (OxaPay)", callback_data="oxa"))
    bot.send_message(m.chat.id, f"تفعيل VIP لمدة شهر:\n1- دفع تلقائي عبر الزر.\n2- أو حول لعنواننا وارسل الصورة:\n`{WALLET_ADDRESS}`", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "oxa")
def oxa_pay(c):
    # كود الربط التلقائي مع OxaPay
    res = requests.post("https://api.oxapay.com/api/v2/checkout", json={
        "merchant": OXA_API_KEY, "amount": 50, "currency": "USDT", "network": "TRC20",
        "description": f"VIP {c.from_user.id}"
    }).json()
    if res.get("status") == "success":
        bot.send_message(c.message.chat.id, f"🔗 رابط الدفع التلقائي:\n{res.get('payUrl')}")

# استلام إثبات الدفع اليدوي (صورة)
@bot.message_handler(content_types=['photo'])
def handle_proof(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ تفعيل 50$ (شهر)", callback_data=f"act_{m.from_user.id}_30"))
    markup.add(types.InlineKeyboardButton("✅ تفعيل 25$ (15 يوم)", callback_data=f"act_{m.from_user.id}_15"))
    bot.send_message(OWNER_ID, f"🔔 وصل إثبات دفع من: `{m.from_user.id}`", reply_markup=markup)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم إرسال الإثبات للمالك. سيتم التفعيل قريباً.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def owner_act(c):
    #act_ID_DAYS
    _, uid, days = c.data.split("_")
    activate_user_logic(uid, int(days))
    bot.send_message(OWNER_ID, f"✅ تم تفعيل {uid} لمدة {days} يوم.")
    bot.send_message(uid, f"🌟 تم تفعيل حسابك بنجاح لمدة {days} يوم! يمكنك الآن تحليل 5 عملات يومياً.")

bot.infinity_polling()
