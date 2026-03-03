import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ إعدادات السيرفر ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V20 PRO - PREMIUM"

def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
BACKUP_PAY_LINK = "https://pay.oxapay.com/13416435/128048507"
DB_FILE = "db_v20_pro.json"

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

# --- [ المحرك التحليلي العميق ] ---
def fetch_data(symbol):
    s = symbol.upper().replace("/", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # 1. محاولة جلب البيانات من Binance
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=100"
        r = requests.get(url, timeout=5).json()
        if isinstance(r, list): return r, s, "Binance"
    except: pass
    
    # 2. محاولة جلب البيانات من MEXC (لجميع العملات)
    try:
        url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=15m&limit=100"
        r = requests.get(url, timeout=5).json()
        if isinstance(r, list): return r, s, "MEXC"
    except: pass
    
    return None, s, None

def get_pro_analysis(symbol):
    data, full_symbol, source = fetch_data(symbol)
    if not data: return None
    
    try:
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        volumes = [float(c[5]) for c in data]
        p = closes[-1]
        
        # مؤشرات احترافية
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50
        
        # RSI الاحترافي
        gains = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        avg_g = sum(gains); avg_l = sum(losses)
        rsi = 100 - (100 / (1 + (avg_g/avg_l if avg_l != 0 else 1)))
        
        # كشف السيولة (واقعية التوصية)
        avg_vol = sum(volumes[-10:]) / 10
        vol_surge = volumes[-1] > avg_vol * 1.5

        # --- خوارزمية القرار الواقعي ---
        if rsi < 30 and p > lows[-1] and vol_surge:
            sig, stat, emo = "🚀 انفجار صعودي (شراء قوي)", "تم رصد سيولة داخلة عند قاع تاريخي. ارتداد حقيقي متوقع.", "🟢"
            t1, t2, sl = p*1.04, p*1.08, p*0.96
        elif p < sma_20 and rsi > 55:
            sig, stat, emo = "📉 هبوط (كسر اتجاه)", "السعر فقد الدعم الرئيسي والزخم يضعف. تجنب الدخول تماماً.", "🔴"
            t1, t2, sl = p*0.96, p*0.92, p*1.03
        elif p > sma_50 and rsi > 50:
            sig, stat, emo = "📈 اتجاه صاعد مستمر", "العملة في "Trend" صاعد قوي مدعوم بالسيولة.", "🔵"
            t1, t2, sl = max(highs[-20:]), max(highs[-20:])*1.05, sma_20
        else:
            sig, stat, emo = "⏳ منطقة حيرة (مراقبة)", "السيولة منخفضة والمؤشرات متضاربة. لا ننصح بالمخاطرة الآن.", "⚪"
            t1, t2, sl = p*1.02, p*1.05, p*0.98

        return (f"🏛 **رادار القابضة V20 - النسخة الاحترافية**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{full_symbol} ({source})\n💰 السعر: `{p}` | 📊 RSI: `{round(rsi,1)}`\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف أول: `{round(t1, 4)}`\n🎯 هدف ثاني: `{round(t2, 4)}`\n🛡️ الوقف: `{round(sl, 4)}`\n"
                f"🔗 [عرض الشارت المباشر](https://www.tradingview.com/chart/?symbol={source}:{full_symbol})")
    except: return None

# --- [ واجهة المستخدم ] ---
@bot.message_handler(commands=['start'])
def start(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "💎 حسابي")
    mk.row("💳 تفعيل VIP", "👨‍💻 تفعيل يدوي")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V20**\nنظام التحليل الخوارزمي الموحد (Binance & MEXC).", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    msg = bot.send_message(m.chat.id, "🎯 أرسل اسم العملة (مثال: BTC أو PEPE):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 تفعيل VIP", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري فحص السيولة والاتجاه...")
    res = get_pro_analysis(m.text)
    if res:
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ الرمز غير موجود في Binance أو MEXC، أو هناك ضغط على السيرفر.")

@bot.message_handler(func=lambda m: m.text == "💳 تفعيل VIP")
def pay_setup(m):
    msg = bot.send_message(m.chat.id, "💰 أدخل مبلغ الاشتراك (مثلاً 50):")
    bot.register_next_step_handler(msg, pay_final)

def pay_final(m):
    if not m.text.isdigit(): return
    try:
        p = {"merchant": OXA_API_KEY, "amount": int(m.text), "currency": "USDT", "network": "TRC20", "description": f"CHARGE_{m.from_user.id}"}
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=p, timeout=10).json()
        if r.get("payUrl"):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 دفع الآن", url=r['payUrl']))
            bot.send_message(m.chat.id, f"✅ فاتورة VIP بقيمة {m.text}$:", reply_markup=markup)
            return
    except: pass
    bot.send_message(m.chat.id, f"⚠️ استخدم الرابط المباشر: {BACKUP_PAY_LINK}")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc_info(m):
    is_v = db["vip"].get(str(m.from_user.id), 0) > time.time()
    bot.send_message(m.chat.id, f"🌟 الحالة: {'VIP نشط ✅' if is_v else 'مجاني 👤'}")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "⏳ تم استلام الإيصال، سيتم مراجعته فوراً.")

if __name__ == "__main__":
    bot.polling(none_stop=True)
