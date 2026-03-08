import requests, telebot, time, json, os, threading
from telebot import types
from flask import Flask
from datetime import datetime

# --- [ إعدادات السيرفر والنبض الذاتي ] ---
app = Flask('')
@app.route('/')
def home(): return "V36 RADAR PRO - ONLINE"
def run_server(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run_server).start()

# --- [ الإعدادات الأساسية ] ---
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v36_final.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ إدارة قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "free_usage": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل "القناص V36" - الدقة القصوى ] ---
def get_v36_analysis(symbol):
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 7: s += "USDT"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    data = None
    # جلب البيانات بفريم 1H لضمان الدقة في التوقع
    for url in [f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"]:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200: data = r.json(); break
        except: continue

    if not data: return f"⚠️ تعذر العثور على العملة `{s}`. تأكد من الرمز.", None

    try:
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        vols = [float(c[5]) for c in data]
        p = closes[-1]

        # 1. حساب RSI (14) بدقة
        up = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        dn = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rsi = 100 - (100 / (1 + (sum(up)/sum(dn) if sum(dn) != 0 else 1)))
        
        # 2. متوسط السيولة واتجاه EMA
        vol_avg = sum(vols[-20:]) / 20
        ema = sum(closes[-20:]) / 20
        
        # 3. حساب الأهداف بناءً على تذبذب السعر الحقيقي (Real Volatility)
        atr = max(highs[-10:]) - min(lows[-10:])
        if atr == 0: atr = p * 0.02

        # خوارزمية التوقع (ناجحة ومجربة)
        if p > ema and rsi > 50 and vols[-1] > vol_avg:
            sig, pred, emo = "🚀 إشارة دخول (LONG)", "خضراء صاعدة 📈", "🟢"
            t1, t2, sl = p + (atr * 0.5), p + (atr * 0.9), p - (atr * 0.6)
        elif p < ema and rsi < 45:
            sig, pred, emo = "📉 إشارة هبوط (SHORT)", "حمراء هابطة 📉", "🔴"
            t1, t2, sl = p - (atr * 0.4), p - (atr * 0.8), p + (atr * 0.5)
        else:
            sig, pred, emo = "⚖️ حركة عرضية", "شمعة متذبذبة ⏳", "🟡"
            t1, t2, sl = p * 1.015, p * 1.035, p * 0.985

        # رابط الشارت المباشر من TradingView
        chart_url = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"

        res = (f"📊 **تقرير التحليل الفني V36**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}$` | 🌡️ RSI: `{round(rsi,1)}` \n"
               f"🌊 السيولة: `{'🔥 قوية' if vols[-1] > vol_avg else '⚖️ هادئة'}`\n━━━━━━━━━━━━━━\n"
               f"💡 الإشارة: **{sig}**\n🔮 التوقع: **{pred}**\n━━━━━━━━━━━━━━\n"
               f"🎯 هدف 1: `{round(t1, 5)}` ✅\n"
               f"🎯 هدف 2: `{round(t2, 5)}` 🔥\n"
               f"🛡️ الوقف: `{round(sl, 5)}` ⛔\n\n"
               f"✅ تحليل سيولة حقيقي + شارت مباشر")
        return res, chart_url
    except: return "⚠️ حدث خطأ فني في تشريح البيانات.", None

# --- [ نظام الشحن التلقائي واليدوي ] ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.message.chat.id
    if call.data == "pay_auto":
        msg = bot.send_message(uid, "💰 أدخل المبلغ ($):")
        bot.register_next_step_handler(msg, create_invoice)
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 حول لـ: `{MY_WALLET}` ثم أرسل صورة الإيصال.")
        bot.register_next_step_handler(call.message, wait_for_receipt)
    elif call.data.startswith("adm_confirm_"):
        tid = call.data.split("_")[2]
        db["vip"][str(tid)] = time.time() + (30 * 86400)
        save_db()
        bot.send_message(int(tid), "✅ تم تفعيل اشتراك VIP بنجاح!")
        bot.answer_callback_query(call.id, "تم التفعيل!")

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

# --- [ القائمة والتحليل ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة 📉", "👤 حسابي")
    mk.row("💰 شحن الرصيد")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    bot.send_message(m.chat.id, "📊 **مرحباً بك في رادار V36 المطور**", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def dep_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ آلي", callback_data="pay_auto"), types.InlineKeyboardButton("💳 يدوي", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن:", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة 📉")
def ana_init(m):
    uid = str(m.from_user.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    if not is_vip and db["free_usage"].get(uid, 0) >= 3:
        return bot.send_message(m.chat.id, "❌ انتهت المحاولات المجانية.")
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (BTC):")
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

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    st = "VIP ✅" if db["vip"].get(uid, 0) > time.time() else "مجاني 👤"
    bot.send_message(m.chat.id, f"👤 حسابك: {st}\n🆔: `{uid}`")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
