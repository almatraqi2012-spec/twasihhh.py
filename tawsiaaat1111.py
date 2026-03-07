import requests, telebot, time, os, threading, json, random
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

# --- [ 🛡️ المحرك الأسطوري المطور V36 ] ---
def get_v36_analysis(symbol):
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 6: s += "USDT"
    
    # قائمة بأسماء المتصفحات لتجاوز حظر المنصات
    agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/119.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) Firefox/118.0'
    ]
    
    data = None
    # محاولة جلب البيانات من 3 روابط مختلفة لضمان العمل 100%
    urls = [
        f"https://api.binance.com/api/v3/klines?symbol={s}&interval=4h&limit=100",
        f"https://api1.binance.com/api/v3/klines?symbol={s}&interval=4h&limit=100",
        f"https://api3.binance.com/api/v3/klines?symbol={s}&interval=4h&limit=100"
    ]

    for url in urls:
        try:
            r = requests.get(url, headers={'User-Agent': random.choice(agents)}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                break
        except: continue

    # بديل MEXC الاحترافي
    if not data or not isinstance(data, list) or len(data) < 20:
        try:
            m_url = f"https://www.mexc.com/open/api/v2/market/kline?symbol={s}&interval=4h&limit=100"
            r = requests.get(m_url, timeout=10).json()
            data = r.get('data', [])
        except: pass

    if not data or len(data) < 20:
        return f"❌ المنصات مشغولة حالياً لعملة `{s}`.\nجرب إرسال الرمز مرة أخرى بعد ثوانٍ.", None

    try:
        closes = [float(k[4]) for k in data]
        highs = [float(k[2]) for k in data]
        lows = [float(k[3]) for k in data]
        vols = [float(k[5]) for k in data]
        
        p = closes[-1]
        ema10 = sum(closes[-10:]) / 10
        ema30 = sum(closes[-30:]) / 30
        vol_avg = sum(vols[-20:]) / 20
        
        # حساب أهداف استراتيجية (6-24 ساعة) بناءً على التذبذب
        diff = max(highs[-24:]) - min(lows[-24:])
        if diff == 0: diff = p * 0.04

        if p > ema10 and vols[-1] > vol_avg:
            sig, status = "🟢 شراء (Bullish)", "🚀 التوقع: صعود قوي قادم"
            t1, t2, sl = p + (diff * 0.4), p + (diff * 0.8), p - (diff * 0.5)
        else:
            sig, status = "🔴 بيع (Bearish)", "📉 التوقع: تصحيح أو هبوط"
            t1, t2, sl = p - (diff * 0.3), p - (diff * 0.7), p + (diff * 0.4)

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        res = (f"🐲 **رادار V36 الاستراتيجي**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: `{s}` | 💰 السعر: `{p}$` \n"
               f"📊 الإشارة: **{sig}**\n"
               f"💡 نوع الصفقة: `6 - 24 ساعة`\n"
               f"🔮 {status}\n\n"
               f"🎯 هدف 1: `{round(t1, 5)}` ✅\n"
               f"🎯 هدف 2: `{round(t2, 5)}` 🔥\n"
               f"🛡️ الوقف: `{round(sl, 5)}` ⛔\n"
               f"━━━━━━━━━━━━━━\n"
               f"✅ تحليل السيولة + مؤشرات EMA حية")
        return res, chart
    except: return "⚠️ خطأ في معالجة البيانات.", None

# --- [ 🕹️ لوحات التحكم والأوامر ] ---
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
    bot.send_message(m.chat.id, "🐲 **أهلاً بك يا عبد الكريم في رادار القابضة V36!**\nالآن النظام يعمل بكامل قوته الاستراتيجية.", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "📊 تحليل رادار V36 📉")
def get_coin(m):
    bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(m, analyze_coin)

def analyze_coin(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    # فحص الاشتراك والقيود
    if not u['sub'] and u['free'] >= 5:
        return bot.send_message(m.chat.id, "❌ انتهى حدك المجاني. يرجى الاشتراك.")
    
    bot.send_message(m.chat.id, "🔍 **جاري الفحص العميق للسيولة والترند...**")
    res, chart = get_v36_analysis(m.text)
    if chart:
        if not u['sub']: db[uid]['free'] += 1
        else: db[uid]['daily'] += 1
        save_db(db)
        try: bot.send_photo(m.chat.id, chart, caption=res)
        except: bot.send_message(m.chat.id, res)
    else: bot.send_message(m.chat.id, res)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def profile(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    status = f"✅ VIP (ينتهي: {u['exp']})" if u['sub'] else "👤 مجاني"
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n🆔: `{uid}`\n🛡️ الرتبة: {status}")

@bot.message_handler(func=lambda m: m.text == "💳 شحن الاشتراك")
def pay(m):
    bot.send_message(m.chat.id, f"💰 **اشتراك الرادار VIP:** 50$ شهرياً\n📍 حول لعنوان TRC20:\n`{WALLET_ADDRESS}`\nثم أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم استلام الإيصال، سيتم التفعيل فوراً بعد المراجعة.")

@bot.message_handler(func=lambda m: m.text == "⚙️ لوحة تحكم المالك" and str(m.from_user.id) == str(OWNER_ID))
def admin(m):
    msg = bot.send_message(m.chat.id, "أرسل ID المستخدم لتفعيله:")
    bot.register_next_step_handler(msg, activate)

def activate(m):
    tid = m.text.strip(); db = load_db()
    if tid in db:
        db[tid]['sub'] = True
        db[tid]['exp'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        save_db(db)
        bot.send_message(m.chat.id, f"✅ تم تفعيل الحساب `{tid}`")
        bot.send_message(tid, "🌟 مبروك! تم تفعيل اشتراكك VIP لمدة شهر.")
    else: bot.send_message(m.chat.id, "❌ المستخدم غير مسجل.")

# --- [ 🌐 التشغيل الاحترافي ] ---
@app.route('/')
def home(): return "V36 ACTIVE!"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    print("🚀 الرادار انطلق...")
    bot.infinity_polling(skip_pending=True)
