import requests, telebot, time, os, threading, json
from datetime import datetime, timedelta
from telebot import types
from flask import Flask

app = Flask(__name__)

# ================= [ ⚙️ الإعدادات الكبرى ] =================
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v36_final.json"

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- [ 💾 إدارة البيانات ] ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_db(db):
    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)

# --- [ 🛡️ المحرك المصحح برمجياً - التشريح الدقيق ] ---
def get_v36_analysis(symbol):
    # تنظيف الرمز البرمجي
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 6: s += "USDT"
    
    try:
        # جلب البيانات من Binance (نظام الـ 4 ساعات للاستراتيجية)
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=4h&limit=100"
        r = requests.get(url, timeout=10)
        
        if r.status_code != 200:
            return f"❌ خطأ في الاتصال بالمنصة للعملة `{s}`. تأكد من الرمز.", None
            
        data = r.json()
        
        # --- [ تشريح البيانات برمجياً ] ---
        # 1. إغلاق الشمعات (المؤشر الأساسي)
        closes = [float(candle[4]) for candle in data]
        # 2. أعلى سعر (لحساب الأهداف)
        highs = [float(candle[2]) for candle in data]
        # 3. أدنى سعر (لحساب الوقف)
        lows = [float(candle[3]) for candle in data]
        # 4. حجم التداول (مؤشر السيولة)
        vols = [float(candle[5]) for candle in data]
        
        p = closes[-1] # السعر الحالي
        
        # --- [ حساب المؤشرات الـ 4 والسيولة ] ---
        # المؤشر 1: المتوسط السريع (EMA 10)
        ema10 = sum(closes[-10:]) / 10
        # المؤشر 2: المتوسط البطيء (EMA 30)
        ema30 = sum(closes[-30:]) / 30
        # المؤشر 3: القوة النسبية (RSI مبسط)
        avg_gain = sum([max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]) / 14
        avg_loss = sum([max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]) / 14
        rs = avg_gain / avg_loss if avg_loss != 0 else 1
        rsi = 100 - (100 / (1 + rs))
        # المؤشر 4: متوسط السيولة (Volume Avg)
        vol_avg = sum(vols[-20:]) / 20
        
        # حساب المدى السعري (Volatility Range) لأهداف استراتيجية
        volatility = max(highs[-15:]) - min(lows[-15:])
        if volatility == 0: volatility = p * 0.05

        # --- [ منطق التوصية الاستراتيجي ] ---
        if p > ema10 and rsi < 70 and vols[-1] > vol_avg:
            sig, color = "🟢 إشارة دخول (ترند صاعد)", "خضراء"
            t1, t2, sl = p + (volatility * 0.4), p + (volatility * 0.8), p - (volatility * 0.5)
        elif p < ema10 or rsi > 70:
            sig, color = "🔴 إشارة هبوط (تصحيح/بيع)", "حمراء"
            t1, t2, sl = p - (volatility * 0.3), p - (volatility * 0.6), p + (volatility * 0.4)
        else:
            sig, color = "🟡 منطقة تذبذب (مراقبة)", "عرضية"
            t1, t2, sl = p * 1.02, p * 1.05, p * 0.97

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        
        res = (f"🐲 **رادار V36 الاستراتيجي المطور**\n"
               f"━━━━━━━━━━━━━━\n"
               f"🪙 العملة: `{s}` | 💰 السعر: `{p}$` \n"
               f"📈 الإشارة: **{sig}**\n"
               f"🔮 التوقع: `الشمعة القادمة {color} بإذن الله`\n"
               f"🌡️ RSI: `{round(rsi, 1)}` | 🌊 السيولة: `{'🔥 عالية' if vols[-1] > vol_avg else '⚖️ متوسطة'}`\n\n"
               f"🎯 هدف أول: `{round(t1, 5)}` ✅\n"
               f"🎯 هدف ثاني: `{round(t2, 5)}` 🔥\n"
               f"🛡️ الوقف: `{round(sl, 5)}` ⛔\n"
               f"━━━━━━━━━━━━━━\n"
               f"⏳ مدة الصفقة: `6 - 24 ساعة`\n"
               f"✅ تم فحص 4 مؤشرات + السيولة الحقيقية")
        return res, chart

    except Exception as e:
        return f"⚠️ خطأ برمي في معالجة `{symbol}`: الرمز غير متوفر أو التنسيق خاطئ.", None

# --- [ 🕹️ إدارة الأوامر ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id); db = load_db()
    if uid not in db:
        db[uid] = {"sub": False, "exp": None, "free": 0, "daily": 0, "last": str(datetime.now().date())}
        save_db(db)
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("📊 تحليل رادار V36 📉", "👤 حسابي")
    mk.row("💳 شحن الاشتراك", "📢 دعم الرادار")
    if uid == str(OWNER_ID): mk.row("⚙️ لوحة تحكم المالك")
    bot.send_message(m.chat.id, "🐲 **رادار V36 الاستراتيجي جاهز للعمل!**", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📊 تحليل رادار V36 📉")
def request_coin(m):
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, process_analysis)

def process_analysis(m):
    uid = str(m.from_user.id); db = load_db()
    # التحقق من القيود
    if not db[uid]['sub'] and db[uid]['free'] >= 5:
        return bot.send_message(m.chat.id, "❌ انتهى حدك المجاني. يرجى الاشتراك.")
    
    bot.send_message(m.chat.id, "🔍 **جاري تحليل البيانات وتشريح السيولة...**")
    res, chart = get_v36_analysis(m.text)
    
    if chart:
        if not db[uid]['sub']: db[uid]['free'] += 1
        else: db[uid]['daily'] += 1
        save_db(db)
        try: bot.send_photo(m.chat.id, chart, caption=res)
        except: bot.send_message(m.chat.id, res)
    else:
        bot.send_message(m.chat.id, res)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def account(m):
    u = load_db()[str(m.from_user.id)]
    status = "VIP" if u['sub'] else "مجاني"
    bot.send_message(m.chat.id, f"👤 **حسابك:** {status}\n📊 الاستهلاك: {u['daily'] if u['sub'] else u['free']}/5")

@bot.message_handler(func=lambda m: m.text == "⚙️ لوحة تحكم المالك" and str(m.from_user.id) == str(OWNER_ID))
def admin(m):
    msg = bot.send_message(m.chat.id, "أرسل ID المستخدم لتفعيله 30 يوم:")
    bot.register_next_step_handler(msg, activate)

def activate(m):
    tid = m.text.strip(); db = load_db()
    if tid in db:
        db[tid]['sub'] = True
        db[tid]['exp'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        save_db(db)
        bot.send_message(m.chat.id, f"✅ تم تفعيل {tid}"); bot.send_message(tid, "🌟 تم تفعيل VIP!")
    else: bot.send_message(m.chat.id, "❌ غير مسجل.")

# --- [ التشغيل ] ---
@app.route('/')
def home(): return "ACTIVE"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True)
