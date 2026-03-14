import requests, telebot, time, json, os, threading
from telebot import types
from flask import Flask, request

# --- [ 1. سيرفر الاستقبال والويب هوك ] ---
app = Flask(__name__)

@app.route('/')
def home(): 
    return "RADAR V45 POWERFUL ENGINE ONLINE"

@app.route('/payment/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and data.get('status') == 'confirmed':
        target_id = data.get('description') 
        if target_id:
            db["vip"][str(target_id)] = time.time() + (30 * 86400)
            save_db()
            try: bot.send_message(int(target_id), "✅ **تم تفعيل VIP بنجاح!**")
            except: pass
    return "OK", 200

# --- [ 2. الإعدادات والبيانات ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v45_final.json"

bot = telebot.TeleBot(API_TOKEN)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "free_usage": {}, "users": []}

db = load_db()

def save_db():
    try:
        with open(DB_FILE, 'w') as f: json.dump(db, f)
    except: pass

# --- [ 3. محرك التحليل V45 - الهجومي والواقعي ] ---
def get_v45_analysis(symbol):
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 7: s += "USDT"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    configs = [
        {"url": f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100", "source": "BINANCE"},
        {"url": f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100", "source": "MEXC"}
    ]
    
    data, source_name = None, "BINANCE"
    for cfg in configs:
        try:
            r = requests.get(cfg["url"], headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                source_name = cfg["source"]
                break
        except: continue

    if not data or len(data) < 30: return None

    try:
        closes = [float(c[4]) for c in data]
        p = closes[-1]
        
        # مؤشرات الحركة السريعة
        up = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        dn = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rsi = 100 - (100 / (1 + (sum(up)/sum(dn) if sum(dn) != 0 else 1)))
        
        ema_fast = sum(closes[-10:]) / 10 # متوسط سريع جداً للاستجابة
        ema_slow = sum(closes[-30:]) / 30
        std_dev = (sum([(x - ema_slow)**2 for x in closes[-20:]]) / 20)**0.5

        # تحليل الاتجاه الهجومي
        if p > ema_fast and rsi > 50:
            # حالة الصعود القوي (LONG)
            sig, emo, txt = "🚀 دخول شراء (LONG)", "🟢", "انفجار سعري وزخم صعودي قوي جداً."
            t1, t2, sl = p + (std_dev * 1.8), p + (std_dev * 3.5), p - (std_dev * 2.2)
            
        elif p < ema_fast and rsi < 50:
            # حالة الهبوط القوي (SHORT)
            sig, emo, txt = "📉 دخول بيع (SHORT)", "🔴", "انهيار في الدعم وضغط بيعي حاد."
            t1, t2, sl = p - (std_dev * 1.8), p - (std_dev * 3.5), p + (std_dev * 2.2)
            
        else:
            # منطقة تذبذب بسيطة
            sig, emo, txt = "⏳ ترقب - حركة جانبية", "⚪", "السعر في مرحلة تجميع، انتظر كسر القمة أو القاع."
            t1, t2, sl = p * 1.02, p * 1.05, p * 0.97

        chart_link = f"https://www.tradingview.com/chart/?symbol={source_name}:{s}"
        
        return (f"🏛 **رادار القابضة - التقرير الفني V45**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}` | 📊 RSI: `{round(rsi,1)}` \n"
                f"🌐 المصدر: {source_name} | 🛡️ الحالة: واقعية 🔥\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 التحليل: {txt}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف 1: `{round(t1, 5)}` \n🎯 هدف 2: `{round(t2, 5)}` \n🛡️ الوقف: `{round(sl, 5)}` \n\n"
                f"🔗 [عرض الشارت المباشر]({chart_link})")
    except: return None

# --- [ 4. نظام الشحن والخدمات ] ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.message.chat.id
    if call.data == "pay_auto":
        create_invoice(call.message, 50)
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 حول 50$ (TRC20):\n`{MY_WALLET}`\nأرسل الإيصال.")
        bot.register_next_step_handler(call.message, wait_for_receipt)
    elif call.data.startswith("confirm_"):
        target_id = str(call.data.split("_")[-1])
        db["vip"][target_id] = time.time() + (30 * 86400)
        save_db()
        bot.answer_callback_query(call.id, "✅ تم التفعيل!")
        try: bot.send_message(int(target_id), "✅ **تم تفعيل VIP بنجاح.**")
        except: pass

def create_invoice(m, amt):
    try:
        res = requests.post("https://api.oxapay.com/merchants/request", 
                            json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD', 'description': str(m.chat.id)}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 ادفع الآن", url=res['payLink']))
            bot.send_message(m.chat.id, "🏛 فاتورة اشتراك VIP", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ عطل مؤقت.")

def wait_for_receipt(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل الآن", callback_data=f"confirm_{m.chat.id}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"🔔 إيصال من: `{m.chat.id}`", reply_markup=mk)
        bot.send_message(m.chat.id, "⏳ جاري المراجعة...")

# --- [ 5. القوائم والتشغيل ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة 📈", "👤 حسابي")
    mk.row("💰 شحن الرصيد")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V45 PRO**\nأقوى محرك تحليل هجومي.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة 📈")
def ana_init(m):
    uid = str(m.from_user.id)
    if not (db["vip"].get(uid, 0) > time.time()) and db["free_usage"].get(uid, 0) >= 5:
        return bot.send_message(m.chat.id, "❌ اشترك في VIP للاستمرار.")
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة:")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل عملة 📈", "👤 حسابي", "💰 شحن الرصيد"]: return
    bot.send_message(m.chat.id, "⏳ جاري تحليل الاتجاه والسيولة...")
    res = get_v45_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if not (db["vip"].get(uid, 0) > time.time()):
            db["free_usage"][uid] = db["free_usage"].get(uid, 0) + 1
            save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ الرمز غير مدعوم.")

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def dep_menu(m):
    mk = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("⚡ دفع آلي", callback_data="pay_auto"),
        types.InlineKeyboardButton("💳 إرسال إيصال", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اشتراك VIP (50$):", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    st = "VIP 👑" if is_vip else f"مجاني ({db['free_usage'].get(uid, 0)}/5)"
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n🆔: `{uid}`\n🌟 الحالة: {st}")

def run_bot():
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
