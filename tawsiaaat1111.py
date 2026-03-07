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
DB_FILE = "radar_v36_database.json"

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- [ 💾 إدارة القاعدة ] ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_db(db):
    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)

# --- [ 🛡️ المحرك الصخري المطور - حل مشكلة البيانات ] ---
def get_advanced_analysis(symbol):
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 6: s += "USDT"
    
    # 1. جلب البيانات بنظام "الصياد المتعدد"
    data = None
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # محاولة بينانس (الفريم الاستراتيجي 4 ساعات)
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=4h&limit=100"
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
    except: pass

    # محاولة MEXC (البديل الذهبي)
    if not data or not isinstance(data, list) or len(data) < 10:
        try:
            url = f"https://www.mexc.com/open/api/v2/market/kline?symbol={s}&interval=4h&limit=100"
            r = requests.get(url, headers=headers, timeout=15).json()
            data = r.get('data', [])
        except: pass

    # فحص نهائي للبيانات
    if not data or len(data) < 10:
        return f"❌ عذراً يا عبد الكريم، المنصات ترفض إعطاء بيانات لـ `{s}` حالياً.\nتأكد أن العملة مدرجة في Binance أو MEXC بنفس الاسم.", None

    try:
        # استخراج البيانات بمرونة (سواء كانت قائمة أو قاموس)
        closes = [float(k[4]) for k in data]
        highs = [float(k[2]) for k in data]
        lows = [float(k[3]) for k in data]
        vols = [float(k[5]) for k in data]
        
        p = closes[-1]
        ema10 = sum(closes[-10:]) / 10
        ema30 = sum(closes[-min(30, len(closes)):]) / min(30, len(closes))
        vol_avg = sum(vols[-min(20, len(vols)):]) / min(20, len(vols))
        
        # حساب أهداف استراتيجية بناءً على تذبذب 48 ساعة
        range_act = max(highs[-12:]) - min(lows[-12:])
        if range_act <= 0: range_act = p * 0.05

        if p > ema10 and vols[-1] > vol_avg:
            sig, strategy = "🟢 إشارة دخول (ترند صاعد)", "💰 نوع الصفقة: استثمار قصير (6-24 ساعة)"
            pred = "🚀 التوقع: استمرار الزخم الشرائي نحو الأهداف."
            t1, t2, sl = p + (range_act * 0.4), p + (range_act * 0.8), p - (range_act * 0.5)
        else:
            sig, strategy = "🔴 إشارة هبوط / تصحيح", "📉 حالة السوق: ضغط بيعي - انتظر القاع"
            pred = "⚠️ التوقع: العملة تحت الضغط، لا ينصح بالشراء الآن."
            t1, t2, sl = p - (range_act * 0.3), p - (range_act * 0.6), p + (range_act * 0.4)

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        res = (f"🐲 **رادار V36 الاستراتيجي**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: `{s}` | 💰 السعر: `{p}$` \n"
               f"📊 الاتجاه: **{sig}**\n"
               f"💡 {strategy}\n"
               f"🔮 {pred}\n\n"
               f"🎯 هدف أول: `{round(t1, 5)}` ✅\n"
               f"🎯 هدف ثاني: `{round(t2, 5)}` 🔥\n"
               f"🛡️ وقف الخسارة: `{round(sl, 5)}` ⛔\n"
               f"━━━━━━━━━━━━━━\n"
               f"✅ تحليل سيولة حقيقي (فريم 4 ساعات)")
        return res, chart
    except Exception as e:
        return f"⚠️ خطأ فني أثناء تشريح بيانات `{s}`. حاول مرة أخرى.", None

# --- [ 🕹️ لوحات التحكم ] ---
def main_menu(uid):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("📊 تحليل رادار V36 📉", "👤 حسابي")
    mk.row("💳 شحن الاشتراك", "📢 دعم الرادار")
    if str(uid) == str(OWNER_ID): mk.row("⚙️ لوحة تحكم المالك")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id); db = load_db()
    if uid not in db:
        db[uid] = {"sub": False, "exp": None, "free": 0, "daily": 0, "last": str(datetime.now().date())}
        save_db(db)
    bot.send_message(m.chat.id, "🐲 **رادار القابضة V36 الأسطوري جاهز!**", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "📊 تحليل رادار V36 📉")
def step_1(m):
    bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(m, step_2)

def step_2(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    # فحص القيود
    if not u['sub'] and u['free'] >= 5:
        return bot.send_message(m.chat.id, "❌ انتهى حدك المجاني. يرجى الاشتراك.")
    
    bot.send_message(m.chat.id, "🔍 **جاري الفحص العميق للسيولة والترند...**")
    res, chart = get_advanced_analysis(m.text)
    if chart:
        if not u['sub']: db[uid]['free'] += 1
        else: db[uid]['daily'] += 1
        save_db(db)
        try: bot.send_photo(m.chat.id, chart, caption=res)
        except: bot.send_message(m.chat.id, res)
    else: bot.send_message(m.chat.id, res)

# --- [ 🌐 نظام الويب وحل Conflict ] ---
@app.route('/')
def home(): return "RADAR V36 ONLINE!"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    print("🚀 الرادار انطلق...")
    bot.infinity_polling(skip_pending=True)
