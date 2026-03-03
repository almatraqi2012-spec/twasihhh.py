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
                bot.send_message(uid, "🌟 **تم تفعيل اشتراك VIP تلقائياً!**\nاستمتع بالتحليلات الدقيقة الآن.")
                bot.send_message(6016547718, f"✅ تفعيل تلقائي ناجح للمستخدم: {uid}")
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

# --- [ محرك التحليل المطور ] ---
def get_analysis(symbol):
    try:
        s = symbol.upper().replace("/", "").replace(" ", "").strip()
        if not s.endswith("USDT"): s += "USDT"
        
        # استخدام رابط API أكثر استقراراً
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=100"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            closes = [float(c[4]) for c in data]
            highs = [float(c[2]) for c in data]; lows = [float(c[3]) for c in data]
            p = closes[-1]
            sma = sum(closes[-25:]) / 25
            
            # حساب RSI
            gains = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
            losses = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
            avg_g = sum(gains)/14; avg_l = sum(losses)/14
            rsi = 100 - (100 / (1 + (avg_g/avg_l if avg_l != 0 else 1)))
            
            sup = min(lows[-60:]); res = max(highs[-60:])

            if rsi < 35 and p <= sup * 1.01:
                sig, stat, emo = "🚀 صعود (قاع ارتدادي)", "مشبع بالبيع عند دعم قوي.", "🟢"
                t1, t2, sl = p*1.04, p*1.08, p*0.96
            elif rsi > 65 or (p < sma and rsi > 50):
                sig, stat, emo = "📉 هبوط متوقع", "كسر للمتوسطات وضغط بيعي عالي.", "🔴"
                t1, t2, sl = p*0.96, p*0.92, p*1.03
            else:
                sig, stat, emo = "📈 اتجاه صاعد معتدل", "السعر مستقر فوق المتوسط.", "🔵"
                t1, t2, sl = res, res*1.03, p*0.97

            return (f"🏛 **رادار القابضة V17**\n━━━━━━━━━━━━━━\n"
                    f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}`\n📊 RSI: `{round(rsi,1)}`\n━━━━━━━━━━━━━━\n"
                    f"💡 {sig}\n📌 {stat}\n━━━━━━━━━━━━━━\n"
                    f"🎯 هدف: `{round(t1, 4)}` | 🛡️ وقف: `{round(sl, 4)}`\n"
                    f"🔗 [عرض الشارت](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
    except: pass
    return None

# --- [ أوامر البوت ] ---
@bot.message_handler(commands=['start'])
def start(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "💎 حسابي")
    mk.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V17** جاهز للخدمة.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثلاً BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري تحليل السوق...")
    res = get_analysis(m.text)
    if res:
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ الرمز غير متاح حالياً. تأكد من كتابة الرمز بشكل صحيح (مثل: BTC أو ETH).")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def pay_setup(m):
    msg = bot.send_message(m.chat.id, "💰 أدخل مبلغ التفعيل بالدولار (مثال: 50):")
    bot.register_next_step_handler(msg, pay_final)

def pay_final(m):
    if not m.text.isdigit():
        bot.send_message(m.chat.id, "❌ يرجى إدخال أرقام فقط."); return
    
    amount = m.text
    status_msg = bot.send_message(m.chat.id, "⏳ جاري الاتصال ببوابة OxaPay وتوليد الفاتورة...")
    
    try:
        payload = {
            "merchant": OXA_API_KEY,
            "amount": int(amount),
            "currency": "USDT",
            "network": "TRC20",
            "description": f"CHARGE_{m.from_user.id}",
            "callbackUrl": "https://twasihhh-py.onrender.com/webhook"
        }
        # مهلة انتظار قصيرة (5 ثواني) لضمان عدم تعليق البوت
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=payload, timeout=8).json()
        
        if r.get("payUrl"):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط هنا للدفع الآن", url=r['payUrl']))
            bot.edit_message_text(f"✅ **فاتورة تفعيل VIP جاهزة**\n💰 المبلغ: {amount}$", m.chat.id, status_msg.message_id, reply_markup=markup)
            return
    except:
        pass
    
    # في حال الفشل أو التأخر، يقدم الرابط الاحتياطي فوراً
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط الدفع المباشر", url=BACKUP_PAY_LINK))
    bot.edit_message_text("⚠️ بوابة الدفع التلقائي مشغولة حالياً.\nيرجى استخدام الرابط الاحتياطي للدفع وتفعيل حسابك يدوياً:", m.chat.id, status_msg.message_id, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc_info(m):
    is_v = db["vip"].get(str(m.from_user.id), 0) > time.time()
    bot.send_message(m.chat.id, f"🌟 الحالة: {'VIP نشط ✅' if is_v else 'حساب مجاني 👤'}")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"أرسل لعنواننا: `{WALLET_ADDRESS}` وارسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    bot.send_message(m.chat.id, "⏳ تم استلام الإيصال، جاري المراجعة من قبل الإدارة.")
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل VIP", callback_data=f"v_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إيصال جديد من {m.from_user.id}", reply_markup=btn)

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def admin_v(c):
    u = c.data.split("_")[1]
    db["vip"][u] = time.time() + (30 * 86400)
    save_db(); bot.send_message(u, "🌟 مبروك! تم تفعيل اشتراكك VIP بنجاح."); bot.answer_callback_query(c.id, "تم")

if __name__ == "__main__":
    while True:
        try: bot.polling(none_stop=True, interval=0, timeout=60)
        except: time.sleep(5)
