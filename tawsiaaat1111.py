import requests, telebot, time, json, os
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ إعدادات السيرفر والويب هوك ] ---
app = Flask('')

@app.route('/')
def home(): return "Radar V9 Ultimate is Running 24/7"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if data and (str(data.get('status')) in ['success', '1', 'paid', 'confirmed']):
            desc = data.get('description', '')
            if "VIP_" in desc:
                uid = desc.split("_")[1]
                db["vip"][uid] = time.time() + (30 * 86400)
                save_db()
                bot.send_message(uid, "🌟 **تهانينا! تم تفعيل اشتراكك VIP بنجاح.**\nلديك الآن وصول كامل لتحليلات الحيتان.")
                bot.send_message(OWNER_ID, f"💰 **عملية دفع ناجحة!**\nالمستخدم: `{uid}` تم تفعيله آلياً.")
    except: pass
    return "OK", 200

def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# --- [ الإعدادات والمفاتيح ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_final_v9.json"

bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=15)

# --- [ إدارة قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "usage": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل "القناص الرقمي" ] ---
def get_analysis(symbol):
    try:
        s_clean = symbol.upper().replace("/", "").strip()
        if not s_clean.endswith("USDT"): s_clean += "USDT"
        
        # محاولة جلب البيانات من Binance ثم MEXC
        source = "BINANCE"
        url = f"https://api.binance.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
        r = requests.get(url, timeout=7)
        
        if r.status_code != 200:
            source = "MEXC"
            url = f"https://api.mexc.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=100"
            r = requests.get(url, timeout=7)
            
        if r.status_code != 200: return None
            
        data = r.json()
        closes = [float(c[4]) for c in data]
        price = closes[-1]
        
        # مؤشرات الحساب الفني
        sma20 = sum(closes[-20:]) / 20
        diffs = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gain = sum([d for d in diffs[-14:] if d > 0]) / 14
        loss = sum([-d for d in diffs[-14:] if d < 0]) / 14
        rsi = 100 - (100 / (1 + (gain/loss if loss != 0 else 1)))
        std = (sum([(x - sma20)**2 for x in closes[-20:]]) / 20)**0.5
        up, low = sma20 + (std * 2), sma20 - (std * 2)

        # منطق التوصية الرقمي الصارم
        if rsi < 36 or price <= low:
            sig, stat = "🚀 شراء قوي (منطقة تجميع)", "السعر عند دعم تاريخي والمؤشرات في القاع. فرصة صعود ممتازة."
            t1, t2, sl = price * 1.045, price * 1.085, price * 0.962
        elif rsi > 67 or price >= up:
            sig, stat = "⚠️ جني أرباح / خروج", "تضخم شرائي واضح والوصول لمقاومة البولينجر. لا تغامر بالدخول."
            t1, t2, sl = price * 1.01, price * 1.02, price * 0.985
        elif price > sma20:
            sig, stat = "📈 اتجاه صاعد (زخم إيجابي)", "العملة تحافظ على تداولها فوق المتوسط السعري، استمرار الصعود مرجح."
            t1, t2, sl = up, up * 1.04, price * 0.975
        else:
            sig, stat = "📉 ضغط بيعي مؤقت", "السعر تحت المتوسط، يفضل انتظار إشارة اختراق واضحة."
            t1, t2, sl = price * 1.03, price * 1.06, price * 0.965

        return (f"🏛 **رادار القابضة V9 - تقرير الخبير**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s_clean} | `{source}`\n💰 السعر الحالي: `{price}`\n📊 مؤشر RSI: {rsi:.1f}\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف أول: `{round(t1, 4)}`\n🎯 هدف ثاني: `{round(t2, 4)}`\n🛡️ الوقف: `{round(sl, 4)}`\n\n"
                f"🔗 [فتح الشارت المباشر](https://www.tradingview.com/chart/?symbol={source}:{s_clean})")
    except: return None

# --- [ واجهة المستخدم والأزرار ] ---
def main_menu(uid):
    m = types.ReplyKeyboardMarkup(resize_keyboard=True)
    m.row("🔍 تحليل عملة", "💎 حسابي")
    m.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    if str(uid) == OWNER_ID: m.row("📊 الإدارة")
    return m

@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); db["usage"][uid] = {"free": 0}; save_db()
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V9 - النسخة الإمبراطورية**\nنظام التحليل العالمي والدفع التلقائي.", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def start_ana(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    if is_v or db["usage"].get(uid, {}).get("free", 0) < 5:
        msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثلاً BTC):")
        bot.register_next_step_handler(msg, process_ana)
    else: bot.send_message(m.chat.id, "❌ انتهت محاولاتك المجانية. يرجى الاشتراك.")

def process_ana(m):
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي", "📊 الإدارة"]: return
    bot.send_message(m.chat.id, "⏳ جاري تحليل السيولة وتحديد الأهداف الرقمية...")
    res = get_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if uid not in db["vip"] or db["vip"][uid] <= time.time():
            db["usage"][uid]["free"] += 1; save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown", disable_web_page_preview=True)
    else: bot.send_message(m.chat.id, "⚠️ الرمز غير موجود أو خارج التغطية.")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def pay(m):
    bot.send_message(m.chat.id, "⏳ جاري إنشاء رابط الدفع التلقائي...")
    payload = {
        "merchant": OXA_API_KEY, "amount": 50, "currency": "USDT", "network": "TRC20",
        "description": f"VIP_{m.from_user.id}",
        "callbackUrl": "https://twasihhh-py.onrender.com/webhook",
        "returnUrl": f"https://t.me/{(bot.get_me()).username}"
    }
    try:
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=payload, timeout=20)
        res = r.json()
        if res.get("payUrl"):
            bot.send_message(m.chat.id, f"💳 **فاتورة اشتراك VIP (دفع آمن)**\n\n🔗 [اضغط هنا لفتح رابط الدفع]({res.get('payUrl')})\n\n✅ التفعيل يتم تلقائياً فور الدفع بنظام الدراجون العالمي.", parse_mode="Markdown")
        else: bot.send_message(m.chat.id, f"⚠️ عذراً: {res.get('message')}")
    except: bot.send_message(m.chat.id, "⚠️ فشل الربط بالبوابة.")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc(m):
    uid = str(m.from_user.id)
    v = db["vip"].get(uid, 0) > time.time()
    bot.send_message(m.chat.id, f"📊 **تفاصيل حسابك:**\n👤 الحالة: {'VIP 🌟' if v else 'مجاني 👤'}\n🔄 الاستهلاك: {db['usage'].get(uid, {}).get('free', 0)}/5")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"أرسل صورة التحويل لعنواننا:\n`{WALLET_ADDRESS}`\nالمبلغ: 50$")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ تفعيل 30 يوم", callback_data=f"act_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إثبات جديد من {m.from_user.id}", reply_markup=mk)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ استلمنا الإثبات، بانتظار المراجعة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def admin_act(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400); save_db()
    bot.send_message(uid, "🌟 تم تفعيل VIP بنجاح."); bot.answer_callback_query(c.id, "تم!")

# --- [ نظام الحماية من التوقف (Anti-Stop System) ] ---
while True:
    try:
        print("🚀 البوت انطلق...")
        bot.polling(none_stop=True, interval=0, timeout=40)
    except Exception as e:
        print(f"🔄 إعادة تشغيل تلقائي بسبب: {e}")
        time.sleep(5)
