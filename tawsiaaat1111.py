import requests, telebot, time, json, os, datetime, threading
import pymongo, dns.resolver
from telebot import types
from flask import Flask, request

# --- [ 1. حل مشكلات السيرفر (Render/VPS) ] ---
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']
app = Flask(__name__)

# ================= [ ⚙️ 2. الإعدادات الكبرى - ضع بياناتك هنا ] =================
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
VIP_PRICE = 50.0 

# رابط قاعدة البيانات (استبدل كلمة_المرور_هنا بالباسوورد الخاص بك)
MONGO_URL = "mongodb+srv://Abduh:C2ZfQWTyO04jK7Nr@cluster0.mongodb.net/?retryWrites=true&w=majority"

try:
    m_client = pymongo.MongoClient(MONGO_URL, tlsAllowInvalidCertificates=True, connectTimeoutMS=30000)
    db = m_client['radar_v36']
    users_col = db['users']
    m_client.admin.command('ping') # اختبار الاتصال
    print("✅ متصل بقاعدة البيانات بنجاح!")
except Exception as e:
    print(f"❌ خطأ في قاعدة البيانات: {e}")
# =========================================================================

bot = telebot.TeleBot(API_TOKEN)

# --- [ 3. محرك التحليل المزدوج (Binance + MEXC) ] ---
def get_v36_analysis(symbol):
    s = symbol.upper().replace("/", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # محاولة جلب البيانات من بينانس أولاً ثم ميكسي
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10).json()
        if 'code' in r: # إذا لم تجدها بينانس، نبحث في ميكسي
            url_mexc = f"https://www.mexc.com/open/api/v2/market/kline?symbol={s}&interval=60m&limit=100"
            r = requests.get(url_mexc).json()['data']
        
        closes = [float(c[4]) for c in r]
        vols = [float(c[5]) for c in r]
        p = closes[-1]
        
        # فلترة القوة والتركيز (حجم التداول + المتوسطات)
        avg_vol = sum(vols[-20:]) / 20
        is_high_vol = vols[-1] > avg_vol * 1.3
        ema20 = sum(closes[-20:])/20
        ema50 = sum(closes[-50:])/50

        chart_url = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"

        if p > ema20 and p > ema50 and is_high_vol:
            res, sig = "🟢 **دخول انفجاري (قوة شراء)**", "سيولة عالية + اتجاه صاعد"
            t1, t2, sl = p*1.05, p*1.10, p*0.94
        elif p < ema20 and p < ema50:
            res, sig = "🔴 **خروج / هبوط (قوة بيع)**", "سيولة ضعيفة + اتجاه هابط"
            t1, t2, sl = p*0.95, p*0.90, p*1.06
        else:
            res, sig = "⚪ **منطقة تذبذب (انتظار)**", "لا توجد سيولة كافية حالياً"
            t1, t2, sl = "---", "---", "---"

        return f"{res}\n━━━━━━━━━━━━━━\n🪙 العملة: {s}\n💰 السعر: `{p}$`\n📊 التحليل: {sig}\n🎯 هدف 1: `{t1}`\n🎯 هدف 2: `{t2}`\n🛡️ الوقف: `{sl}`", chart_url
    except: return None, None

# --- [ 4. القوائم الرئيسية ] ---
def main_menu(uid):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل العملة (V36)", "👤 حسابي")
    mk.row("📈 أسعار السوق", "💳 شحن الرصيد")
    if uid == OWNER_ID:
        mk.row("📢 إذاعة (للإدارة)", "👥 إحصائيات البوت")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    user = users_col.find_one({"user_id": uid})
    if not user:
        users_col.insert_one({"user_id": uid, "balance": 0.0, "vip_expiry": 0})
    bot.send_message(m.chat.id, "🐲 **مرحباً بك في رادار القابضة V36**\nنظام التحليل المطور والمرتبط بقاعدة البيانات السحابية.", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "📈 أسعار السوق")
def market_p(m):
    try:
        res = requests.get("https://api.binance.com/api/v3/ticker/price?symbols=[\"BTCUSDT\",\"ETHUSDT\",\"SOLUSDT\"]").json()
        text = "📊 **نبض السوق اللحظي:**\n\n"
        for c in res: text += f"🔹 {c['symbol'].replace('USDT','')}: `{round(float(c['price']),2)}$` \n"
        bot.send_message(m.chat.id, text, parse_mode="Markdown")
    except: bot.send_message(m.chat.id, "⚠️ عطل مؤقت في جلب الأسعار.")

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل العملة (V36)")
def ana_init(m):
    user = users_col.find_one({"user_id": m.from_user.id})
    if user.get('vip_expiry', 0) < time.time() and m.from_user.id != OWNER_ID:
        return bot.send_message(m.chat.id, "❌ **اشتراكك منتهي!**\nيرجى شحن رصيدك وتفعيل الـ VIP من قسم 'حسابي'.")
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC أو PEPE):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل العملة (V36)", "👤 حسابي", "📈 أسعار السوق", "💳 شحن الرصيد"]: return
    bot.send_message(m.chat.id, "⏳ جاري فحص السيولة والاتجاه (Binance + MEXC)...")
    res, chart = get_v36_analysis(m.text)
    if res:
        try: bot.send_photo(m.chat.id, chart, caption=res, parse_mode="Markdown")
        except: bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ العملة غير موجودة أو هناك ضغط على السيرفر.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    user = users_col.find_one({"user_id": m.from_user.id})
    bal = user.get('balance', 0.0)
    exp = user.get('vip_expiry', 0)
    status = "VIP ✅" if exp > time.time() else "مجاني 👤"
    
    mk = types.InlineKeyboardMarkup()
    if bal >= VIP_PRICE and exp < time.time():
        mk.add(types.InlineKeyboardButton("🌟 تفعيل VIP (خصم 50$)", callback_data="buy_vip"))
    
    bot.send_message(m.chat.id, f"👤 **بياناتك:**\n💰 رصيدك: `{bal}$` \n🌟 الحالة: {status}", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "buy_vip")
def buy_vip_cb(c):
    uid = c.from_user.id
    user = users_col.find_one({"user_id": uid})
    if user['balance'] >= VIP_PRICE:
        expiry = time.time() + (30 * 86400)
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -VIP_PRICE}, "$set": {"vip_expiry": expiry}})
        bot.send_message(uid, "✅ **تم تفعيل الـ VIP بنجاح لمدة 30 يوم!**")
    else: bot.answer_callback_query(c.id, "❌ رصيدك غير كافٍ.")

@bot.message_handler(func=lambda m: m.text == "💳 شحن الرصيد")
def deposit_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (OxaPay)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("👨‍💻 تفعيل يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن المفضلة:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def pay_cbs(c):
    if c.data == "pay_auto":
        bot.send_message(c.message.chat.id, "⏳ جاري إنشاء رابط الدفع...")
        payload = {'merchant': OXAPAY_KEY, 'amount': VIP_PRICE, 'currency': 'USD', 'description': str(c.from_user.id)}
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط للدفع", url=res['payLink']))
            bot.send_message(c.message.chat.id, "بمجرد الدفع، سيتم إضافة الرصيد تلقائياً:", reply_markup=mk)
    elif c.data == "pay_manual":
        bot.send_message(c.message.chat.id, f"📍 حول {VIP_PRICE}$ لعنوان TRC20:\n`{WALLET_ADDRESS}`\nثم أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل الرصيد", callback_data=f"adm_dep_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إيصال شحن جديد من: `{m.from_user.id}`", reply_markup=mk)
    bot.send_message(m.chat.id, "⏳ تم إرسال الإيصال للإدارة للمراجعة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_dep_"))
def admin_deposit(c):
    if c.from_user.id != OWNER_ID: return
    uid = int(c.data.split("_")[2])
    users_col.update_one({"user_id": uid}, {"$inc": {"balance": VIP_PRICE}})
    bot.send_message(uid, f"🌟 **مبروك!** تم شحن حسابك بـ {VIP_PRICE}$ بنجاح.")
    bot.answer_callback_query(c.id, "✅ تم الشحن")

@bot.message_handler(func=lambda m: m.text == "📢 إذاعة (للإدارة)" and m.from_user.id == OWNER_ID)
def broadcast_init(m):
    msg = bot.send_message(m.chat.id, "📝 اكتب الرسالة التي تريد إرسالها للجميع:")
    bot.register_next_step_handler(msg, broadcast_exec)

def broadcast_exec(m):
    count = 0
    for u in users_col.find():
        try:
            bot.send_message(u['user_id'], m.text)
            count += 1
        except: pass
    bot.send_message(OWNER_ID, f"✅ تم الإرسال لـ {count} مستخدم.")

# تشغيل Flask للسيرفر
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
threading.Thread(target=run_flask, daemon=True).start()

if __name__ == "__main__":
    print("🐲 الرادار V36 يعمل الآن...")
    bot.infinity_polling()
