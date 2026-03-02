import requests, telebot, time, json, os
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ 1. محرك Flask لاستقبال الدفع (الويب هوك) ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar System V14: ONLINE 24/7"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        # التحقق من حالة الدفع (تلقائي بنسبة 100%)
        if data and str(data.get('status')) in ['paid', 'success', '1']:
            desc = data.get('description', '')
            if "CHARGE_" in desc:
                uid = desc.split("_")[1]
                db["vip"][uid] = time.time() + (30 * 86400) # تفعيل 30 يوم
                save_db()
                bot.send_message(uid, "🌟 **مبروك! تم تفعيل اشتراكك VIP تلقائياً.**\nاستمتع الآن بأقوى تحليلات السوق.")
                bot.send_message(OWNER_ID, f"💰 **عملية دفع ناجحة!**\nالمستخدم: `{uid}` دفع وتم تفعيله آلياً.")
    except: pass
    return "OK", 200

def run_server():
    app.run(host='0.0.0.0', port=8080)

# تشغيل السيرفر في خلفية منفصلة لضمان عدم تداخل المهام
Thread(target=run_server).start()

# --- [ 2. الإعدادات والمفاتيح (بدقة 100%) ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v14_stable.json"

# تفعيل الخيوط المتعددة (20 خيط) لضمان سرعة الرد على مئات المستخدمين معاً
bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=20)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "usage": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ 3. محرك التحليل الاحترافي (Binance + MEXC) ] ---
def get_analysis(symbol):
    try:
        s_clean = symbol.upper().replace("/", "").strip()
        if not s_clean.endswith("USDT"): s_clean += "USDT"
        
        # محاولة جلب البيانات من بينانس أو ماكسيك (لشمولية كل العملات)
        source = "BINANCE"
        url = f"https://api.binance.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=50"
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            source = "MEXC"
            url = f"https://api.mexc.com/api/v3/klines?symbol={s_clean}&interval=15m&limit=50"
            r = requests.get(url, timeout=5)
            
        data = r.json()
        closes = [float(c[4]) for c in data]
        price = closes[-1]
        
        # تحليل واقعي (Bollinger Bands + SMA)
        sma = sum(closes[-20:]) / 20
        std = (sum([(x - sma)**2 for x in closes[-20:]]) / 20)**0.5
        up, low = sma + (std * 2), sma - (std * 2)

        if price <= low:
            sig, stat = "🚀 شراء (منطقة ارتداد ذهبية)", "السعر عند القاع المتوقع. فرصة صعود قوية."
            t1, t2, sl = price * 1.045, price * 1.085, price * 0.96
        elif price >= up:
            sig, stat = "⚠️ جني أرباح / انتظار", "السعر تضخم ووصل للسقف. لا ينصح بالدخول الآن."
            t1, t2, sl = price * 1.01, price * 1.02, price * 0.985
        else:
            sig, stat = "📈 اتجاه صاعد مستمر", "الزخم إيجابي والسعر يتجه لاختبار المقاومة القادمة."
            t1, t2, sl = up, up * 1.04, price * 0.975

        return (f"🏛 **رادار القابضة V14 - تحليل ذكي**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s_clean} | `{source}`\n💰 السعر: `{price}`\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف 1: `{round(t1, 4)}`\n🎯 هدف 2: `{round(t2, 4)}`\n🛡️ الوقف: `{round(sl, 4)}`\n\n"
                f"🔗 [عرض الشارت المباشر](https://www.tradingview.com/chart/?symbol={source}:{s_clean})")
    except: return None

# --- [ 4. واجهة المستخدم والأوامر ] ---
@bot.message_handler(commands=['start'])
def start(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "💎 حسابي")
    mk.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في رادار القابضة V14**\nنظام التحليل الرقمي والدفع الآلي المطور.", reply_markup=mk)

# --- [ نظام الدفع التلقائي المقيد (50$ كحد أدنى) ] ---
@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def ask_pay(m):
    msg = bot.send_message(m.chat.id, "💰 **أدخل مبلغ الشحن لتفعيل VIP:**\n⚠️ أقل مبلغ للتفعيل هو **50 دولار**.")
    bot.register_next_step_handler(msg, process_pay)

def process_pay(m):
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ يرجى إدخال أرقام فقط (مثال: 50).")
        return
    amt = int(m.text)
    if amt < 50:
        bot.send_message(m.chat.id, "❌ عذراً، لا يمكن قبول مبلغ أقل من **50 دولار**.")
        return
    
    bot.send_message(m.chat.id, "⏳ جاري تجهيز فاتورة الشحن...")
    payload = {"merchant": OXA_API_KEY, "amount": amt, "currency": "USDT", "network": "TRC20", "description": f"CHARGE_{m.from_user.id}"}
    try:
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=payload).json()
        if r.get("payUrl"):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🔗 اضغط هنا للدفع المباشر", url=r['payUrl']))
            bot.send_message(m.chat.id, f"✅ **الفاتورة جاهزة بقيمة {amt}$**\nسيتم التفعيل آلياً بعد الدفع بنجاح.", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ خطأ في الاتصال ببوابة الدفع.")

# --- [ نظام الدفع اليدوي والمحفظة ] ---
@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    msg = (f"👨‍💻 **قسم التفعيل اليدوي:**\n\n"
           f"تحويل مبلغ **50$** (USDT-TRC20) للعنوان التالي:\n\n"
           f"`{WALLET_ADDRESS}`\n\n"
           f"📸 **أرسل صورة الإيصال** هنا لتفعيل حسابك.")
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل 30 يوم", callback_data=f"vip_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 **إيصال جديد من:** {m.from_user.id}", reply_markup=mk)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم استلام الإثبات، بانتظار مراجعة الإدارة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("vip_"))
def admin_confirm(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400); save_db()
    bot.send_message(uid, "🌟 **مبروك! تم تفعيل اشتراكك VIP يدوياً.**")
    bot.answer_callback_query(c.id, "تم التفعيل")

# --- [ نظام التحليل والحساب ] ---
@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ask_ana(m):
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, do_ana)

def do_ana(m):
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري قراءة السوق...")
    res = get_analysis(m.text)
    if res: bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ لم نجد بيانات للعملة.")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    v = db["vip"].get(uid, 0) > time.time()
    bot.send_message(m.chat.id, f"📊 **معلومات حسابك:**\n👤 الحالة: {'VIP 🌟' if v else 'مجاني 👤'}")

# --- [ 5. صمام الأمان لمنع التوقف (المحرك الدوار) ] ---
if __name__ == "__main__":
    while True:
        try:
            print("🚀 البوت انطلق في بيئة السيرفر...")
            bot.polling(none_stop=True, interval=0, timeout=50)
        except Exception as e:
            print(f"🔄 إعادة تشغيل تلقائي بسبب خطأ: {e}")
            time.sleep(5)
