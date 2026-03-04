import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask
from threading import Thread

# --- [ إعدادات السيرفر ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V28 ULTRA - SMART ANALYSIS"
def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = 6016547718 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v28_db.json"

bot = telebot.TeleBot(API_TOKEN)

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

# --- [ محرك التحليل الذكي - نسخة تصحيح الأخطاء ] ---
def get_smart_analysis(symbol):
    s = symbol.upper().replace("/", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    source = "BINANCE"
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=7)
        if r.status_code != 200:
            source = "MEXC"
            url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
            r = requests.get(url, timeout=7)
        data = r.json()
        
        # استخراج البيانات الأساسية
        opens = [float(c[1]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        closes = [float(c[4]) for c in data]
        vols = [float(c[5]) for c in data]
        p = closes[-1]

        # 1. حساب مؤشر الزخم (Momentum) بدقة
        momentum = closes[-1] - closes[-4] # مقارنة السعر الحالي بسعره قبل 4 ساعات
        
        # 2. كشف "الشموع الانعكاسية" (Price Action)
        last_candle_body = abs(closes[-1] - opens[-1])
        prev_candle_body = abs(closes[-2] - opens[-2])
        is_bullish_engulfing = (closes[-1] > opens[-1]) and (closes[-1] > highs[-2]) and (momentum > 0)
        is_bearish_engulfing = (closes[-1] < opens[-1]) and (closes[-1] < lows[-2]) and (momentum < 0)

        # 3. حساب مستويات الدعم والمقاومة الحقيقية (بناءً على السيولة)
        support = min(lows[-50:])
        resistance = max(highs[-50:])

        # --- خوارزمية اتخاذ القرار "المصححة" ---
        # حالة الشراء: زخم صاعد + شمعة ابتلاعية + ابتعاد عن المقاومة
        if is_bullish_engulfing and p < (resistance * 0.98):
            sig, stat, emo = "🚀 انفجار صاعد (LONG)", "تم رصد دخول سيولة قوية (Smart Money) واختراق لقمة الشمعة السابقة.", "🟢"
            t1, t2, sl = p*1.05, p*1.10, lows[-1]*0.99
            
        # حالة الهبوط: زخم هابط + كسر قاع الشمعة السابقة
        elif is_bearish_engulfing or (momentum < 0 and p < support * 1.02):
            sig, stat, emo = "📉 هبوط مستمر (SHORT)", "ضغط بيعي كبير وتأكيد كسر اتجاه. السعر يستهدف مستويات أدنى.", "🔴"
            t1, t2, sl = p*0.95, p*0.90, highs[-1]*1.01
            
        # حالة التذبذب: السعر محصور بين الدعم والمقاومة بدون زخم
        else:
            sig, stat, emo = "⏳ انتظار (Neutral)", "السوق في منطقة تجميع عرضي. لا توجد إشارة واضحة حالياً.", "⚪"
            t1, t2, sl = "---", "---", "---"

        return (f"🏛 **رادار القابضة V28 - تحليل الخبرة**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} {emo}\n💰 السعر الحالي: `{p}`\n📊 الاتجاه: `{'صاعد' if momentum > 0 else 'هابط'}`\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 السبب: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف أول: `{t1}`\n🎯 هدف ثاني: `{t2}`\n🛡️ الوقف: `{sl}`\n\n"
                f"🔗 [شارت {platform} المباشر](https://www.tradingview.com/chart/?symbol={source}:{s})")
    except: return None

# --- [ واجهة المستخدم - نفس هيكلك السابق ] ---
@bot.message_handler(commands=['start'])
def start(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "👤 حسابي")
    mk.row("💳 اشتراك VIP", "👨‍💻 تفعيل يدوي")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V28 - نسخة التصحيح**\nتم تعديل المنطق التحليلي بناءً على السلوك السعري الحقيقي.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    uid = str(m.from_user.id)
    now = time.time()
    today = str(datetime.date.today())
    vip_expiry = db["vip"].get(uid, 0)
    
    if vip_expiry > 0 and now > vip_expiry:
        bot.send_message(m.chat.id, "❌ **انتهى اشتراكك VIP.**")
        return

    is_vip = vip_expiry > now
    user_usage = db["usage"].get(uid, {"count": 0, "date": today})
    if user_usage["date"] != today: user_usage = {"count": 0, "date": today}
    limit = 5 if is_vip else 1
    
    if user_usage["count"] >= limit:
        bot.send_message(m.chat.id, "⚠️ انتهت حصتك اليومية.")
        return

    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    uid = str(m.from_user.id)
    if m.text in ["🔍 تحليل عملة", "👤 حسابي", "💳 اشتراك VIP", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "🔍 جاري تحليل السلوك السعري...")
    res = get_smart_analysis(m.text)
    if res:
        today = str(datetime.date.today())
        u = db["usage"].get(uid, {"count": 0, "date": today})
        if u["date"] != today: u = {"count": 0, "date": today}
        u["count"] += 1; db["usage"][uid] = u; save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ فشل التحليل.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    bot.send_message(m.chat.id, f"🆔 معرفك: `{uid}`\n🌟 الحالة: {'VIP ✅' if is_v else 'مجاني 👤'}")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP")
def vip_info(m):
    bot.send_message(m.chat.id, f"💰 السعر: 50$ شهرياً\n📍 المحفظة (TRC20):\n`{WALLET_ADDRESS}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, "أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل 30 يوم", callback_data=f"act_{m.from_user.id}"))
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(OWNER_ID, f"🔔 إيصال من: `{m.from_user.id}`", reply_markup=btn)

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def admin_act(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db(); bot.send_message(uid, "🌟 تم تفعيل VIP.")
    bot.answer_callback_query(c.id, "تم")

if __name__ == "__main__":
    bot.polling(none_stop=True)
