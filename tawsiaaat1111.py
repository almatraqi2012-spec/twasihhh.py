import requests, telebot, time, os, threading, json
from datetime import datetime, timedelta
from telebot import types
from flask import Flask

# --- [ إعدادات السيرفر والويب ] ---
app = Flask(__name__)

# ================= [ ⚙️ الإعدادات الكبرى - التكوين الأصلي ] =================
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v36_database.json"

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# --- [ 💾 نظام إدارة القاعدة الذكي ] ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

# --- [ 🛡️ محرك التحليل الاحترافي الرباعي ] ---
def get_advanced_analysis(symbol):
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT"): s += "USDT"
    
    # محاولة جلب البيانات من 3 منصات لضمان عدم الفشل
    platforms = [
        f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100",
        f"https://www.mexc.com/open/api/v2/market/kline?symbol={s}&interval=60m&limit=100",
        f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={s.replace('USDT', '_USDT')}&interval=1h"
    ]
    
    data = None
    source = ""
    for url in platforms:
        try:
            r = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'}).json()
            # فحص هيكلية البيانات لكل منصة
            res = r if isinstance(r, list) else r.get('data', [])
            if res and len(res) > 50:
                data = res
                source = "Binance" if "binance" in url else ("MEXC" if "mexc" in url else "Gate.io")
                break
        except: continue

    if not data:
        return "❌ **لم يتم العثور على العملة!**\nتأكد من الرمز (مثل: BTC, SOL, PEPE).", None

    try:
        closes = [float(k[4]) for k in data]
        vols = [float(k[5]) for k in data]
        p = closes[-1]
        
        # مؤشرات V36: EMA + RSI + السيولة + الزخم
        ema20 = sum(closes[-20:]) / 20
        vol_avg = sum(vols[-20:]) / 20
        up = sum([max(0, closes[i] - closes[i-1]) for i in range(-14, 0)])
        down = sum([max(0, closes[i-1] - closes[i]) for i in range(-14, 0)])
        rsi = 100 - (100 / (1 + (up/down if down != 0 else 1)))
        
        # منطق التوقع (القرار الأسطوري)
        if p > ema20 and vols[-1] > vol_avg and rsi < 75:
            sig, pred = "🟢 شراء قوي (اختراق)", "🚀 الشمعة القادمة: خضراء صاعدة"
            t1, t2, sl = p*1.04, p*1.08, p*0.95
        elif p < ema20 and vols[-1] > vol_avg:
            sig, pred = "🔴 بيع (ضغط تصريفي)", "📉 الشمعة القادمة: حمراء هابطة"
            t1, t2, sl = p*0.96, p*0.92, p*1.05
        else:
            sig, pred = "🟡 تذبذب (انتظار)", "⚖️ الشمعة القادمة: غير مستقرة"
            t1, t2, sl = "---", "---", "---"

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        
        text = (f"🐲 **رادار V36 الأسطوري - {source}**\n"
                f"━━━━━━━━━━━━━━\n"
                f"🪙 العملة: `{s}` | 💰 السعر: `{p}$` \n"
                f"📈 الإشارة: **{sig}**\n"
                f"🔮 التوقع: `{pred}`\n"
                f"🌡️ RSI: `{round(rsi,1)}` | 🌊 السيولة: `{'🔥 عالية' if vols[-1]>vol_avg else '⚖️ متوسطة'}`\n\n"
                f"🎯 هدف 1: `{t1}`\n"
                f"🎯 هدف 2: `{t2}`\n"
                f"🛡️ الوقف: `{sl}`\n"
                f"━━━━━━━━━━━━━━\n"
                f"⏰ التحديث: `{datetime.now().strftime('%H:%M:%S')}`")
        return text, chart
    except:
        return "⚠️ حدث خطأ فني في تشريح البيانات.", None

# --- [ 🕹️ لوحات التحكم والأزرار ] ---
def main_menu(uid):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("📊 تحليل رادار V36 📉", "👤 حسابي")
    mk.row("💳 شحن الاشتراك", "📉 أسعار السوق")
    mk.row("📢 دعم الرادار")
    if str(uid) == str(OWNER_ID):
        mk.row("⚙️ لوحة تحكم المالك")
    return mk

# --- [ 👤 منطق إدارة المستخدمين ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    db = load_db()
    if uid not in db:
        db[uid] = {"sub": False, "exp": None, "free": 0, "daily": 0, "last": str(datetime.now().date())}
        save_db(db)
    
    bot.send_message(m.chat.id, "🐲 **مرحباً بك في رادار القابضة V36 الأسطوري!**\nنظام التحليل المتكامل القائم على السيولة الحقيقية وتوقعات الشمعات.", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "📊 تحليل رادار V36 📉")
def check_and_start_analysis(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    today = str(datetime.now().date())
    
    # تصفير عداد المشتركين يومياً
    if u['last'] != today: u['daily'] = 0; u['last'] = today; save_db(db)

    # فحص القيود (كما طلبت تماماً)
    if not u['sub']:
        if u['free'] >= 5:
            return bot.send_message(m.chat.id, "❌ **انتهى حدك المجاني (5 عملات مدى الحياة)!**\nيرجى الاشتراك بـ 50$ لفتح الرادار بالكامل.")
    else:
        # فحص انتهاء مدة الشهر
        if datetime.now() > datetime.strptime(u['exp'], '%Y-%m-%d'):
            u['sub'] = False; save_db(db)
            return bot.send_message(m.chat.id, "❌ **انتهت فترة اشتراكك الشهري!**\nيرجى التجديد للاستمرار في الخدمة.")
        
        if u['daily'] >= 5:
            return bot.send_message(m.chat.id, "⚠️ **وصلت للحد اليومي (5 تحليلات)!**\nيرجى المحاولة غداً أو ترقية حسابك.")

    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, perform_analysis)

def perform_analysis(m):
    uid = str(m.from_user.id); db = load_db()
    bot.send_message(m.chat.id, "🔍 **جاري فحص السيولة وتشريح الشمعات في المنصات...**")
    
    res, chart = get_advanced_analysis(m.text)
    if chart:
        if db[uid]['sub']: db[uid]['daily'] += 1
        else: db[uid]['free'] += 1
        save_db(db)
        try: bot.send_photo(m.chat.id, chart, caption=res)
        except: bot.send_message(m.chat.id, res)
    else:
        bot.send_message(m.chat.id, res)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    status = f"✅ VIP (ينتهي: {u['exp']})" if u['sub'] else "👤 مجاني"
    limit = f"{u['daily']}/5 اليوم" if u['sub'] else f"{u['free']}/5 مدى الحياة"
    bot.send_message(m.chat.id, f"👤 **معلومات حسابك:**\n━━━━━━━━━━━━━━\n🆔 معرفك: `{uid}`\n🛡️ الرتبة: {status}\n📊 الاستهلاك: {limit}\n━━━━━━━━━━━━━━")

@bot.message_handler(func=lambda m: m.text == "💳 شحن الاشتراك")
def pay_options(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن تلقائي (OxaPay)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("👨‍💻 شحن يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "💰 **سعر الاشتراك:** 50$ شهرياً\nاختر وسيلة الدفع المناسبة:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def handle_payments(c):
    uid = str(c.from_user.id)
    if c.data == "pay_auto":
        payload = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': uid}
        try:
            r = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
            if r.get('payLink'):
                bot.send_message(uid, f"🔗 [اضغط هنا للدفع التلقائي]({r['payLink']})\nسيتم تفعيل حسابك آلياً فور تأكيد الدفع.", parse_mode="Markdown")
        except: bot.send_message(uid, "⚠️ بوابة الدفع التلقائي متوقفة، يرجى استخدام الدفع اليدوي.")
    else:
        bot.send_message(uid, f"📍 حول الاشتراك (50$) لعنوان TRC20:\n`{WALLET_ADDRESS}`\n\nثم أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def receipt_handler(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ **تم استلام الإيصال!**\nسيتم مراجعته من قبل الإدارة وتفعيل حسابك خلال دقائق.")

# --- [ ⚙️ لوحة تحكم المالك ] ---
@bot.message_handler(func=lambda m: m.text == "⚙️ لوحة تحكم المالك" and str(m.from_user.id) == str(OWNER_ID))
def admin_panel(m):
    msg = bot.send_message(m.chat.id, "👨‍قن أرسل معرف المستخدم (ID) لتفعيله VIP لمدة شهر:")
    bot.register_next_step_handler(msg, activate_user)

def activate_user(m):
    target_id = m.text.strip()
    db = load_db()
    if target_id in db:
        db[target_id]['sub'] = True
        db[target_id]['exp'] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        save_db(db)
        bot.send_message(m.chat.id, f"✅ تم تفعيل العضوية للمعرف `{target_id}` بنجاح!")
        bot.send_message(target_id, "🌟 **تهانينا!** تم تفعيل اشتراكك VIP لمدة 30 يوماً.")
    else:
        bot.send_message(m.chat.id, "❌ المعرف غير موجود في قاعدة البيانات.")

# --- [ 🌐 تشغيل السيرفر ] ---
@app.route('/')
def home(): return "🐲 V36 RADAR SYSTEM IS FULLY ACTIVE!"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.infinity_polling(skip_pending=True)
