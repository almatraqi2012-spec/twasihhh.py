import requests, telebot, time, json, os, threading
from telebot import types
from flask import Flask

# --- [ إعدادات السيرفر لمنع التوقف ] ---
app = Flask('')
@app.route('/')
def home(): return "V36 SYSTEM ACTIVE"
def run_server(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run_server).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v36_final.json"

bot = telebot.TeleBot(API_TOKEN)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "free_usage": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل "القناص V36" - فحص 3 منصات ] ---
def get_v36_analysis(symbol):
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 7: s += "USDT"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # محاولة جلب البيانات من عدة مصادر لضمان عدم ظهور "العملة غير موجودة"
    urls = [
        f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100",
        f"https://api1.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100",
        f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
    ]
    
    data = None
    source = "BINANCE"
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if "mexc" in url: source = "MEXC"
                break
        except: continue

    if not data or not isinstance(data, list) or len(data) < 50:
        return f"⚠️ تعذر العثور على `{s}`. تأكد من الرمز الصحيح.", None

    try:
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        vols = [float(c[5]) for c in data]
        p = closes[-1]

        # 1. RSI & EMA
        up = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        dn = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rsi = 100 - (100 / (1 + (sum(up)/sum(dn) if sum(dn) != 0 else 1)))
        ema = sum(closes[-20:]) / 20

        # 2. MACD (Simplified)
        macd = (sum(closes[-12:]) / 12) - (sum(closes[-26:]) / 26)

        # 3. Bollinger Bands (Deviation)
        std_dev = (sum([(x - ema)**2 for x in closes[-20:]]) / 20)**0.5
        
        # خوارزمية التوقع (قوة المؤشرات 5)
        if p > ema and macd > 0 and rsi > 52:
            sig, pred, emo = "🚀 صعود (LONG)", "خضراء صاعدة 📈", "🟢"
            t1, t2, sl = p + (std_dev * 1.8), p + (std_dev * 3), p - (std_dev * 2)
        elif p < ema and macd < 0 and rsi < 48:
            sig, pred, emo = "📉 هبوط (SHORT)", "حمراء هابطة 📉", "🔴"
            t1, t2, sl = p - (std_dev * 1.8), p - (std_dev * 3), p + (std_dev * 2)
        else:
            sig, pred, emo = "⚖️ حركة عرضية", "شمعة متذبذبة ⏳", "🟡"
            t1, t2, sl = p * 1.02, p * 1.04, p * 0.98

        chart = f"https://s3.tradingview.com/snapshots/m/{source}:{s}.png"
        res = (f"📊 **تقرير التحليل الفني V36 PRO**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}$` | 🌡️ RSI: `{round(rsi,1)}` \n"
               f"🌊 السيولة: `{'🔥 قوية' if vols[-1] > (sum(vols[-20:])/20) else '⚖️ هادئة'}`\n━━━━━━━━━━━━━━\n"
               f"💡 الإشارة: **{sig}**\n🔮 التوقع: **{pred}**\n━━━━━━━━━━━━━━\n"
               f"🎯 هدف 1: `{round(t1, 5)}` ✅\n🎯 هدف 2: `{round(t2, 5)}` 🔥\n🛡️ الوقف: `{round(sl, 5)}` ⛔\n\n"
               f"✅ تحليل: MACD + RSI + EMA + Bollinger + Volume")
        return res, chart
    except: return "⚠️ خطأ في معالجة البيانات.", None

# --- [ الشحن والقوائم ] ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.message.chat.id
    if call.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ ($):")
        bot.register_next_step_handler(msg, create_invoice)
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 حول لـ: `{MY_WALLET}` ثم أرسل الإيصال.")
        bot.register_next_step_handler(call.message, wait_for_receipt)
    elif call.data.startswith("adm_confirm_"):
        tid = call.data.split("_")[2]
        db["vip"][str(tid)] = time.time() + (30 * 86400)
        save_db()
        bot.send_message(int(tid), "✅ تم تفعيل اشتراك VIP!")

def create_invoice(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD'}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط الدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"📝 فاتورة بـ {amt}$:", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ أدخل مبلغاً صحيحاً.")

def wait_for_receipt(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل", callback_data=f"adm_confirm_50_{m.chat.id}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"طلب شحن من {m.chat.id}", reply_markup=mk)
        bot.send_message(m.chat.id, "✅ تم إرسال الإيصال للمراجعة.")

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة 📉", "👤 حسابي")
    mk.row("💰 شحن الرصيد")
    bot.send_message(m.chat.id, "📊 **مرحباً بك في رادار V36 المطور**", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة 📉")
def ana_init(m):
    uid = str(m.from_user.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    if not is_vip and db["free_usage"].get(uid, 0) >= 5:
        return bot.send_message(m.chat.id, "❌ انتهت المحاولات المجانية (5/5). يرجى الشحن.")
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل عملة 📉", "👤 حسابي", "💰 شحن الرصيد"]: return
    bot.send_message(m.chat.id, "⏳ جاري جلب الشارت وتشريح البيانات...")
    res, chart = get_v36_analysis(m.text)
    if chart:
        uid = str(m.from_user.id)
        if not db["vip"].get(uid, 0) > time.time():
            db["free_usage"][uid] = db["free_usage"].get(uid, 0) + 1; save_db()
        try: bot.send_photo(m.chat.id, chart, caption=res, parse_mode="Markdown")
        except: bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, res)

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def dep_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ آلي", callback_data="pay_auto"), types.InlineKeyboardButton("💳 يدوي", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    st = "VIP ✅" if db["vip"].get(uid, 0) > time.time() else f"مجاني ({db['free_usage'].get(uid,0)}/5)"
    bot.send_message(m.chat.id, f"👤 حسابك: {st}\n🆔: `{uid}`")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
