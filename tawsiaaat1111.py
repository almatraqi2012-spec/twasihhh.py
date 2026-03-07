import requests, telebot, time, os, threading, json
from datetime import datetime, timedelta
from telebot import types
from flask import Flask

# --- [ إعدادات السيرفر والويب ] ---
app = Flask(__name__)

# ================= [ ⚙️ الإعدادات الكبرى ] =================
# تم تحديث التوكن كما في رسالتك الأخيرة
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v36_database.json"

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- [ 💾 نظام إدارة القاعدة الذكي ] ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, 'r') as f: return json.load(f)
    except: return {}

def save_db(db):
    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)

# --- [ 🛡️ محرك التحليل الاستراتيجي V36 ] ---
def get_advanced_analysis(symbol):
    # تنظيف الرمز (btc -> BTCUSDT)
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 6: s += "USDT"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    data_4h = None
    
    # 1. جلب بيانات 4 ساعات (للتحليل الاستراتيجي القوي)
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=4h&limit=50"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200: data_4h = r.json()
    except: pass

    # 2. بديل MEXC في حال فشل بينانس
    if not data_4h or not isinstance(data_4h, list):
        try:
            url = f"https://www.mexc.com/open/api/v2/market/kline?symbol={s}&interval=4h&limit=50"
            r = requests.get(url, headers=headers, timeout=10).json()
            data_4h = r.get('data')
        except: pass

    if not data_4h or len(data_4h) < 20:
        return f"❌ لم أجد بيانات كافية للعملة `{s}`. تأكد من الرمز.", None

    try:
        closes = [float(k[4]) for k in data_4h]
        highs = [float(k[2]) for k in data_4h]
        lows = [float(k[3]) for k in data_4h]
        vols = [float(k[5]) for k in data_4h]
        
        p = closes[-1]
        ema10 = sum(closes[-10:]) / 10
        ema30 = sum(closes[-30:]) / 30
        vol_avg = sum(vols[-20:]) / 20
        
        # حساب المدى السعري لآخر يومين (لأهداف حقيقية)
        range_2d = max(highs[-12:]) - min(lows[-12:])
        if range_2d == 0: range_2d = p * 0.05

        # --- [ اتخاذ القرار الاستراتيجي ] ---
        if p > ema10 and ema10 > ema30 and vols[-1] > vol_avg:
            sig = "🟢 دخول شرائي (Trend Up)"
            strategy = "💰 نوع الصفقة: استثمار قصير (6-24 ساعة)"
            pred = "🚀 التوقع: استمرار الصعود واختبار مستويات عليا."
            t1, t2, sl = p + (range_2d * 0.4), p + (range_2d * 0.8), p - (range_2d * 0.5)
        elif p < ema10 and ema10 < ema30:
            sig = "🔴 خروج / بيع (Trend Down)"
            strategy = "📉 حالة السوق: هبوط مستمر - لا تشترِ الآن"
            pred = "⚠️ التوقع: ضغط بيعي، ابحث عن فرصة بيع (Short)."
            t1, t2, sl = p - (range_2d * 0.3), p - (range_2d * 0.6), p + (range_2d * 0.4)
        else:
            sig = "🟡 تذبذب (Sideways)"
            strategy = "⚖️ نوع الصفقة: سكالبينج سريع ومراقبة"
            pred = "⏳ التوقع: حركة عرضية مملة، انتظر الانفجار."
            t1, t2, sl = p * 1.02, p * 1.04, p * 0.97

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        
        text = (f"🐲 **رادار V36 الاستراتيجي**\n"
                f"━━━━━━━━━━━━━━\n"
                f"🪙 العملة: `{s}` | 💰 السعر: `{p}$` \n"
                f"📊 الإشارة: **{sig}**\n"
                f"💡 {strategy}\n"
                f"🔮 {pred}\n\n"
                f"🎯 هدف أول: `{round(t1, 5)}` ✅\n"
                f"🎯 هدف ثاني: `{round(t2, 5)}` 🔥\n"
                f"🛡️ الوقف: `{round(sl, 5)}` ⛔\n"
                f"━━━━━━━━━━━━━━\n"
                f"⏳ مدة الصفقة المتوقعة: `6 - 24 ساعة`\n"
                f"✅ تحليل سيولة الحيتان + فريم 4 ساعات حقيقي")
        return text, chart
    except Exception as e:
        return f"⚠️ خطأ فني أثناء تحليل `{s}`.", None

# --- [ 🕹️ لوحات التحكم ] ---
def main_menu(uid):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("📊 تحليل رادار V36 📉", "👤 حسابي")
    mk.row("💳 شحن الاشتراك", "📢 دعم الرادار")
    if str(uid) == str(OWNER_ID):
        mk.row("⚙️ لوحة تحكم المالك")
    return mk

# --- [ 👤 منطق إدارة المستخدمين ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id); db = load_db()
    if uid not in db:
        db[uid] = {"sub": False, "exp": None, "free": 0, "daily": 0, "last": str(datetime.now().date())}
        save_db(db)
    bot.send_message(m.chat.id, "🐲 **مرحباً بك في رادار القابضة V36 الأسطوري!**\nتحليل استراتيجي متكامل للفوز بالصفقات.", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "📊 تحليل رادار V36 📉")
def check_limits(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    today = str(datetime.now().date())
    if u.get('last') != today: u['daily'] = 0; u['last'] = today; save_db(db)

    if not u['sub']:
        if u['free'] >= 5:
            return bot.send_message(m.chat.id, "❌ **انتهى حدك المجاني (5 عملات)!**\nاشترك بـ 50$ لفتح الرادار الاستراتيجي.")
    else:
        if datetime.now() > datetime.strptime(u['exp'], '%Y-%m-%d'):
            u['sub'] = False; save_db(db)
            return bot.send_message(m.chat.id, "❌ **انتهى اشتراكك!** يرجى التجديد.")
        if u['daily'] >= 5:
            return bot.send_message(m.chat.id, "⚠️ **وصلت للحد اليومي (5 تحليلات)!** عد غداً.")

    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, perform_analysis)

def perform_analysis(m):
    uid = str(m.from_user.id); db = load_db()
    bot.send_message(m.chat.id, "🔍 **جاري تشريح حركة السعر وفريم الـ 4 ساعات...**")
    res, chart = get_advanced_analysis(m.text)
    if chart:
        if db[uid]['sub']: db[uid]['daily'] += 1
        else: db[uid]['free'] += 1
        save_db(db)
        try: bot.send_photo(m.chat.id, chart, caption=res)
        except: bot.send_message(m.chat.id, res)
    else: bot.send_message(m.chat.id, res)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    status = f"✅ VIP (ينتهي: {u['exp']})" if u['sub'] else "👤 مجاني"
    limit = f"{u['daily']}/5 اليوم" if u['sub'] else f"{u['free']}/5 مدى الحياة"
    bot.send_message(m.chat.id, f"👤 **حسابك:**\n🆔: `{uid}`\n🛡️ الرتبة: {status}\n📊 الاستهلاك: {limit}")

@bot.message_handler(func=lambda m: m.text == "💳 شحن الاشتراك")
def pay_options(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن تلقائي", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("👨‍💻 شحن يدوي", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "💰 **سعر الاشتراك:** 50$ شهرياً\nاختر وسيلة الدفع:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def handle_payments(c):
    uid = str(c.from_user.id)
    if c.data == "pay_auto":
        payload = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': uid}
        try:
            r = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
            if r.get('payLink'):
                bot.send_message(uid, f"🔗 [رابط الدفع]({r['payLink']})", parse_mode="Markdown")
        except: bot.send_message(uid, "⚠️ البوابة متوقفة، استخدم اليدوي.")
    else:
        bot.send_message(uid, f"📍 TRC20:\n`{WALLET_ADDRESS}`\nأرسل الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def receipt_handler(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم إرسال الإيصال للمراجعة.")

@bot.message_handler(func=lambda m: m.text == "⚙️ لوحة تحكم المالك" and str(m.from_user.id) == str(OWNER_ID))
def admin_panel(m):
    msg = bot.send_message(m.chat.id, "أرسل ID المستخدم لتفعيله 30 يوماً:")
    bot.register_next_step_handler(msg, activate_user)

def activate_user(m):
    target_id = m.text.strip(); db = load_db()
    if target_id in db:
        db[target_id]['sub'] = True
        db[target_id]['exp'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        save_db(db)
        bot.send_message(m.chat.id, f"✅ تم تفعيل `{target_id}`")
        bot.send_message(target_id, "🌟 تم تفعيل اشتراكك VIP لمدة شهر!")
    else: bot.send_message(m.chat.id, "❌ المعرف غير موجود.")

# --- [ 🌐 التشغيل وحل Conflict ] ---
@app.route('/')
def home(): return "🐲 V36 RADAR ACTIVE!"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True)
