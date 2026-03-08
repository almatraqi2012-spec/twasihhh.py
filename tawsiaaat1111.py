import requests, telebot, time, json, os, threading
from telebot import types
from flask import Flask
from datetime import datetime, timedelta

# --- [ إعدادات السيرفر والنبض ] ---
app = Flask('')
@app.route('/')
def home(): return "V36 STRATEGIC SYSTEM ACTIVE"
def run_server(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run_server).start()

# --- [ الإعدادات الكبرى - ضع مفاتيحك هنا ] ---
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" # مفتاح الدفع التلقائي
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v36_db.json"

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

# --- [ محرك التحليل "القناص V36" ] ---
def get_v36_analysis(symbol):
    # تنظيف الرمز لضمان عدم حدوث خطأ "العملة غير موجودة"
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 7: s += "USDT"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    # محاولة جلب البيانات من 3 مصادر مختلفة لضمان النجاح
    data = None
    for api_url in [f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100",
                    f"https://api1.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100",
                    f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"]:
        try:
            r = requests.get(api_url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                break
        except: continue

    if not data or len(data) < 50:
        return f"⚠️ عذراً، الرمز `{s}` غير متاح حالياً في محرك السيولة. تأكد من كتابته بشكل صحيح (مثال: BTC).", None

    try:
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        vols = [float(c[5]) for c in data]
        p = closes[-1]

        # 1. تحليل السيولة (Volume Force)
        vol_avg = sum(vols[-20:]) / 20
        liq_status = "🔥 سيولة انفجارية" if vols[-1] > vol_avg * 1.5 else "⚖️ سيولة مستقرة"

        # 2. مؤشر RSI (قوة الزخم)
        up = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        dn = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rsi = 100 - (100 / (1 + (sum(up)/sum(dn) if sum(dn) != 0 else 1)))

        # 3. اتجاه EMA (المتوسطات)
        ema = sum(closes[-20:]) / 20
        
        # 4. توقع الشمعة القادمة (خوارزمية V36)
        if p > ema and rsi > 50 and vols[-1] > vol_avg:
            sig, pred, emo = "🚀 صعود قوي (Bullish)", "خضراء صاعدة 📈", "🟢"
            t1, t2, sl = p*1.03, p*1.07, p*0.965
        elif p < ema and rsi < 45:
            sig, pred, emo = "📉 هبوط متوقع (Bearish)", "حمراء هابطة 📉", "🔴"
            t1, t2, sl = p*0.97, p*0.93, p*1.035
        else:
            sig, pred, emo = "⚖️ حركة عرضية", "شمعة متذبذبة ⏳", "🟡"
            t1, t2, sl = p*1.015, p*1.04, p*0.98

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        res = (f"📊 **تقرير التحليل الاستراتيجي V36**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: #{s} {emo}\n💰 السعر الحالي: `{p}$` \n🌊 السيولة: `{liq_status}`\n"
               f"🌡️ الزخم (RSI): `{round(rsi, 1)}` | 📍 الاتجاه: `{'فوق المتوسط' if p > ema else 'تحت المتوسط'}`\n━━━━━━━━━━━━━━\n"
               f"💡 الإشارة: **{sig}**\n🔮 توقع الشمعة القادمة: **{pred}**\n━━━━━━━━━━━━━━\n"
               f"🎯 هدف أول: `{round(t1, 5)}` ✅\n🎯 هدف ثاني: `{round(t2, 5)}` 🔥\n🛡️ الوقف: `{round(sl, 5)}` ⛔\n\n"
               f"✅ تحليل ناجح مبني على 4 مؤشرات + تدفق السيولة")
        return res, chart
    except: return "⚠️ خطأ في تشريح البيانات.", None

# --- [ نظام الشحن التلقائي Oxapay ] ---
def create_invoice(uid, amount):
    url = "https://api.oxapay.com/merchants/request"
    data = {"merchant": OXAPAY_KEY, "amount": amount, "currency": "USD", "lifeTime": 30, "feePaidByPayer": 1, "callbackUrl": "", "description": f"VIP_{uid}"}
    try:
        r = requests.post(url, json=data).json()
        if r.get("status") == "success": return r.get("payUrl"), r.get("trackId")
    except: pass
    return None, None

def check_payment(track_id, uid):
    url = "https://api.oxapay.com/merchants/get/payment"
    data = {"merchant": OXAPAY_KEY, "trackId": track_id}
    while True:
        try:
            r = requests.post(url, json=data).json()
            if r.get("status") == "Paid":
                db["vip"][str(uid)] = time.time() + (30 * 86400)
                save_db()
                bot.send_message(uid, "🌟 **تهانينا! تم تفعيل اشتراك VIP تلقائياً.**\nاستمتع الآن بكافة الميزات.")
                break
        except: pass
        time.sleep(20)

# --- [ واجهة البوت والأزرار ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة 📈", "👤 حسابي")
    mk.row("💳 شحن VIP (تلقائي)", "👨‍💻 تفعيل يدوي")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    bot.send_message(m.chat.id, "📊 **مرحباً بك في نظام التحليل الفني المطور V36**\nتحليل دقيق، سيولة حقيقية، وشحن تلقائي.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة 📈")
def ana_init(m):
    uid = str(m.from_user.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    if not is_vip and db["free_usage"].get(uid, 0) >= 3:
        return bot.send_message(m.chat.id, "❌ انتهت محاولاتك المجانية. يرجى الاشتراك.")
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل عملة 📈", "👤 حسابي", "💳 شحن VIP (تلقائي)", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "🔍 **جاري تشريح السيولة وفحص الشمعات...**")
    res, chart = get_v36_analysis(m.text)
    if chart:
        uid = str(m.from_user.id)
        if not db["vip"].get(uid, 0) > time.time():
            db["free_usage"][uid] = db["free_usage"].get(uid, 0) + 1; save_db()
        try: bot.send_photo(m.chat.id, chart, caption=res, parse_mode="Markdown")
        except: bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, res)

@bot.message_handler(func=lambda m: m.text == "💳 شحن VIP (تلقائي)")
def vip_auto(m):
    bot.send_message(m.chat.id, "⏳ جاري إنشاء فاتورة الدفع...")
    pay_url, track_id = create_invoice(m.from_user.id, 50)
    if pay_url:
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("💳 اضغط هنا للدفع الآن", url=pay_url))
        bot.send_message(m.chat.id, "✅ فاتورتك جاهزة (50$ USDT/Crypto):\nسيتم تفعيل حسابك فور إتمام الدفع تلقائياً.", reply_markup=btn)
        threading.Thread(target=check_payment, args=(track_id, m.from_user.id), daemon=True).start()
    else:
        bot.send_message(m.chat.id, "⚠️ فشل الاتصال ببوابة الدفع. حاول لاحقاً أو استخدم التفعيل اليدوي.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    status = "VIP نشط ✅" if db["vip"].get(uid, 0) > time.time() else "حساب مجاني 👤"
    bot.send_message(m.chat.id, f"👤 **معلومات الحساب:**\n🆔 المعرف: `{uid}`\n🛡️ الحالة: {status}")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"📍 حول 50$ لعنوان (TRC20):\n`{WALLET_ADDRESS}`\nثم أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "⏳ تم استلام الإيصال. جاري المراجعة والتفعيل يدوياً...")

if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True)
