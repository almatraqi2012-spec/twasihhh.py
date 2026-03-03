import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ إعدادات السيرفر والويب هوك ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V22 - BACK TO POWER"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        if data and str(data.get('status')) in ['paid', 'success', '1']:
            uid = data.get('description', '').replace('CHARGE_', '')
            if uid.isdigit():
                db["vip"][uid] = time.time() + (30 * 86400)
                save_db()
                bot.send_message(uid, "🌟 **تم تفعيل VIP بنجاح!** استمتع بالدقة الآن.")
    except: pass
    return "OK", 200

def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
BACKUP_PAY_LINK = "https://pay.oxapay.com/13416435/128048507"
DB_FILE = "radar_v22_final.json"

bot = telebot.TeleBot(API_TOKEN)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل "الواقعي" - كما طلبت ] ---
def get_analysis(symbol):
    try:
        s = symbol.upper().replace("/", "").strip()
        if not s.endswith("USDT"): s += "USDT"
        
        # جلب البيانات مباشرة من Binance
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=100"
        r = requests.get(url, timeout=10).json()
        
        closes = [float(c[4]) for c in r]
        highs = [float(c[2]) for c in r]; lows = [float(c[3]) for c in r]
        p = closes[-1]
        
        # 1. المتوسط المتحرك (الترند)
        sma = sum(closes[-25:]) / 25
        # 2. مؤشر RSI (الزخم)
        rsi_g = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        rsi_l = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rsi = 100 - (100 / (1 + (sum(rsi_g)/sum(rsi_l) if sum(rsi_l) != 0 else 1)))
        # 3. دعم ومقاومة حقيقية
        support = min(lows[-50:]); resistance = max(highs[-50:])

        # --- خوارزمية القرار الصارم ---
        if rsi < 32 and p > support:
            sig, stat, emo = "🚀 شراء ذهبي (صعود)", "ارتداد مؤكد من دعم صلب مع تشبع بيعي حاد.", "🟢"
            t1, t2, sl = p*1.04, p*1.08, p*0.96
        elif p < sma and rsi > 55:
            sig, stat, emo = "📉 بيع (هبوط حاد)", "السعر كسر الترند الصاعد والزحم سلبي جداً.", "🔴"
            t1, t2, sl = p*0.96, p*0.92, p*1.03
        elif p > sma and rsi < 65:
            sig, stat, emo = "📈 صعود مستقر", "العملة في قناة صاعدة فوق المتوسط. مواصلة الأهداف.", "🔵"
            t1, t2, sl = resistance, resistance*1.03, p*0.97
        else:
            sig, stat, emo = "⏳ حالة تذبذب", "المؤشرات متضاربة حالياً، انتظر وضوح الرؤية.", "⚪"
            t1, t2, sl = p*1.02, p*1.04, p*0.98

        return (f"🏛 **رادار القابضة V22 - التحليل الواقعي**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s}\n💰 السعر: `{p}` | 📊 RSI: `{round(rsi,1)}`\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف أول: `{round(t1, 4)}`\n🎯 هدف ثاني: `{round(t2, 4)}`\n🛡️ الوقف: `{round(sl, 4)}`\n"
                f"🔗 [شارت {s}](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
    except: return None

# --- [ واجهة البوت ] ---
@bot.message_handler(commands=['start'])
def start(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "💎 حسابي")
    mk.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V22**\nتمت استعادة القوة والدقة.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثلاً BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري التحليل الخوارزمي...")
    res = get_analysis(m.text)
    if res:
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ الرمز غير متاح حالياً. تأكد من كتابة الاسم (BTC).")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def pay_setup(m):
    msg = bot.send_message(m.chat.id, "💰 أدخل المبلغ (مثلاً 50):")
    bot.register_next_step_handler(msg, pay_final)

def pay_final(m):
    if not m.text.isdigit(): return
    bot.send_message(m.chat.id, "⏳ جاري إنشاء الفاتورة التلقائية...")
    try:
        p = {"merchant": OXA_API_KEY, "amount": int(m.text), "currency": "USDT", "network": "TRC20", "description": f"CHARGE_{m.from_user.id}", "callbackUrl": "https://twasihhh-py.onrender.com/webhook"}
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=p, timeout=10).json()
        if r.get("payUrl"):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 دفع الآن", url=r['payUrl']))
            bot.send_message(m.chat.id, f"✅ الفاتورة بقيمة {m.text}$:", reply_markup=markup); return
    except: pass
    bot.send_message(m.chat.id, f"⚠️ استخدم الرابط الاحتياطي: {BACKUP_PAY_LINK}")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc_info(m):
    is_v = db["vip"].get(str(m.from_user.id), 0) > time.time()
    bot.send_message(m.chat.id, f"🌟 الحالة: {'VIP نشط ✅' if is_v else 'حساب مجاني 👤'}")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "⏳ تم استلام الإيصال للمراجعة.")

if __name__ == "__main__":
    bot.polling(none_stop=True)
