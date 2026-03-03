import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ إعدادات السيرفر والويب هوك ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V18 PRO - FULL POWER"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if data and str(data.get('status')) in ['paid', 'success', '1']:
            uid = data.get('description', '').replace('CHARGE_', '')
            if uid.isdigit():
                db["vip"][uid] = time.time() + (30 * 86400)
                save_db()
                bot.send_message(uid, "🌟 **تهانينا! تم تفعيل اشتراكك VIP بنجاح.**\nلديك الآن وصول كامل لأدق التحليلات.")
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
DB_FILE = "radar_v18_final.json"

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

# --- [ خوارزمية التحليل الاحترافية ] ---
def get_analysis(symbol):
    try:
        s = symbol.upper().replace("/", "").strip()
        if not s.endswith("USDT"): s += "USDT"
        
        # محاولة جلب البيانات بذكاء
        endpoints = [
            f"https://api.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=100",
            f"https://api1.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=100"
        ]
        
        data = None
        for url in endpoints:
            try:
                r = requests.get(url, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    break
            except: continue
            
        if not data: return None

        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        p = closes[-1]
        
        # مؤشرات دقيقة
        sma_short = sum(closes[-20:]) / 20
        sma_long = sum(closes[-50:]) / 50
        
        # RSI
        gains = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        avg_g = sum(gains) / 14; avg_l = sum(losses) / 14
        rsi = 100 - (100 / (1 + (avg_g/avg_l if avg_l != 0 else 1)))
        
        sup = min(lows[-40:]); res = max(highs[-40:])

        # --- خوارزمية اتخاذ القرار ---
        if rsi < 32 and p > sup:
            sig, stat, emo = "🚀 شراء (منطقة ارتداد ذهبية)", "السعر عند دعم صلب مع تشبع بيعي حاد. فرصة صعود قوية جداً.", "🟢"
            t1, t2, sl = p*1.045, p*1.09, p*0.96
        elif p < sma_long and rsi < 45:
            sig, stat, emo = "📉 هبوط (نزيف مستمر)", "العملة تحت ضغط بيعي وتتداول تحت المتوسطات الكبرى. تجنب الدخول.", "🔴"
            t1, t2, sl = p*0.97, p*0.94, p*1.03
        elif p > sma_short and rsi < 65:
            sig, stat, emo = "📈 اتجاه صاعد قوي", "الزحم إيجابي والسعر يتجه لاختراق القمة التالية.", "🔵"
            t1, t2, sl = res, res*1.03, p*0.975
        else:
            sig, stat, emo = "⏳ حالة تذبذب (مراقبة)", "السوق غير مستقر حالياً. ننتظر كسر منطقة المقاومة أو الدعم.", "⚪"
            t1, t2, sl = p*1.02, p*1.05, p*0.98

        return (f"🏛 **رادار القابضة V18 - المحلل الذكي**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} {emo}\n💰 السعر الحالي: `{p}`\n📊 مؤشر الزحم RSI: `{round(rsi,1)}`\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف أول: `{round(t1, 4)}`\n🎯 هدف ثاني: `{round(t2, 4)}`\n🛡️ الوقف (الأمان): `{round(sl, 4)}`\n"
                f"🔗 [شارت {s} المباشر](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
    except: return None

# --- [ واجهة المستخدم ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "💎 حسابي")
    mk.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V18**\nمرحباً بك في أقوى نظام تحليلي خوارزمي.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثلاً BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعبل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري استخراج البيانات وتحليل الاتجاه...")
    res = get_analysis(m.text)
    if res:
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ فشل جلب البيانات. تأكد من اسم العملة بشكل صحيح.")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def pay_setup(m):
    msg = bot.send_message(m.chat.id, "💰 أدخل المبلغ بالدولار (مثلاً 50):")
    bot.register_next_step_handler(msg, pay_final)

def pay_final(m):
    if not m.text.isdigit(): return
    amt = m.text
    try:
        payload = {"merchant": OXA_API_KEY, "amount": int(amt), "currency": "USDT", "network": "TRC20", "description": f"CHARGE_{m.from_user.id}", "callbackUrl": "https://twasihhh-py.onrender.com/webhook"}
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=payload, timeout=8).json()
        if r.get("payUrl"):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط هنا للدفع الفوري", url=r['payUrl']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة VIP بمبلغ {amt}$", reply_markup=markup)
            return
    except: pass
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 رابط الدفع الاحتياطي", url=BACKUP_PAY_LINK))
    bot.send_message(m.chat.id, "⚠️ البوابة مشغولة حالياً. استخدم الرابط المباشر للدفع والتفعيل:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc_info(m):
    is_v = db["vip"].get(str(m.from_user.id), 0) > time.time()
    bot.send_message(m.chat.id, f"🌟 الحالة: {'VIP نشط ✅' if is_v else 'حساب مجاني 👤'}")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"أرسل لعنواننا: `{WALLET_ADDRESS}` وارسل صورة الإيصال.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل VIP", callback_data=f"v_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إيصال جديد من {m.from_user.id}", reply_markup=btn)
    bot.send_message(m.chat.id, "⏳ تم استلام الإيصال، سيتم تفعيلك فور التأكد.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def admin_v(c):
    u = c.data.split("_")[1]
    db["vip"][u] = time.time() + (30 * 86400)
    save_db(); bot.send_message(u, "🌟 مبروك! تم تفعيل اشتراكك VIP بنجاح."); bot.answer_callback_query(c.id, "تم")

if __name__ == "__main__":
    bot.polling(none_stop=True)
