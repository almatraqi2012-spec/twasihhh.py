import requests, telebot, time, json, os, datetime, random, threading
import pymongo, dns.resolver
from telebot import types
from flask import Flask, request

# --- [ 1. حل مشكلة DNS في الترمكس ] ---
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']

app = Flask(__name__)

# ================= [ ⚙️ 2. الإعدادات الكبرى - ركز هنا ] =================
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
VIP_PRICE = 50.0 

# قاعدة بيانات MongoDB (تأكد من وضع رابطك الخاص)
MONGO_URL = "mongodb+srv://USER:PASS@cluster.mongodb.net/radar_db" 
m_client = pymongo.MongoClient(MONGO_URL, tlsAllowInvalidCertificates=True)
db = m_client['radar_v36']
users_col = db['users']
# ========================================================================

bot = telebot.TeleBot(API_TOKEN)

# --- [ 3. محرك الويب هوك (الشحن التلقائي) ] ---
@app.route('/webhook/oxapay', methods=['POST'])
def oxapay_webhook():
    data = request.json
    if data.get('status') in ['Paid', 'Success']:
        uid = int(data.get('description'))
        amount = float(data.get('amount'))
        # إضافة الرصيد للمستخدم
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": amount}}, upsert=True)
        bot.send_message(uid, f"✅ **تم الشحن بنجاح!**\nتم إضافة {amount}$ إلى رصيدك آلياً.")
    return "OK", 200

def run_flask(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run_flask, daemon=True).start()

# --- [ 4. ميزة إحصائيات السوق السريعة ] ---
def get_market_prices():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbols=[\"BTCUSDT\",\"ETHUSDT\",\"SOLUSDT\"]"
        res = requests.get(url).json()
        text = "📊 **أسعار السوق الحالية:**\n\n"
        for coin in res:
            symbol = coin['symbol'].replace("USDT", "")
            price = round(float(coin['price']), 2)
            text += f"🔹 {symbol}: `{price}$` \n"
        return text
    except: return "⚠️ عطل في جلب الأسعار."

# --- [ 5. محرك التحليل V36 - الفلترة الفائقة ] ---
def get_v36_analysis(symbol):
    s = symbol.upper().replace("/", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10).json()
        closes = [float(c[4]) for c in r]
        vols = [float(c[5]) for c in r] # حجم التداول
        p = closes[-1]
        
        # تحليل الفوليوم (هل هناك انفجار؟)
        avg_vol = sum(vols[-20:]) / 20
        is_high_vol = vols[-1] > avg_vol * 1.5

        # المؤشرات الفنية
        ema20, ema50 = sum(closes[-20:])/20, sum(closes[-50:])/50
        chart_url = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"

        if p > ema20 and p > ema50 and is_high_vol:
            res, sig = "🟢 **دخول انفجاري (V36)**", "شراء قوي + سيولة عالية"
            t1, t2, sl = p*1.04, p*1.08, p*0.95
        elif p < ema20 and p < ema50:
            res, sig = "🔴 **هبوط مستمر (V36)**", "بيع/خروج"
            t1, t2, sl = p*0.96, p*0.92, p*1.04
        else:
            res, sig = "⚪ **منطقة تذبذب**", "انتظار"
            t1, t2, sl = "---", "---", "---"

        return f"{res}\n━━━━━━━━━━━━━━\n🪙 {s}\n💰 السعر: `{p}`\n📊 الإشارة: {sig}\n🎯 هدف 1: `{t1}`\n🛡️ الوقف: `{sl}`", chart_url
    except: return None, None

# --- [ 6. القوائم والتحكم ] ---
def main_menu(uid):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل العملة (V36)", "👤 حسابي")
    mk.row("📈 أسعار السوق", "💳 شحن الرصيد")
    if uid == OWNER_ID:
        mk.row("📢 إذاعة (للإدارة)", "👥 الإحصائيات")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    # تسجيل المستخدم الجديد برصيد 0
    if not users_col.find_one({"user_id": uid}):
        users_col.insert_one({"user_id": uid, "balance": 0.0, "vip_expiry": 0})
    bot.send_message(m.chat.id, "🐲 **مرحباً بك في رادار القابضة V36**\nنظام التوصيات المطور والتحكم الكامل.", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "📈 أسعار السوق")
def market_p(m):
    bot.send_message(m.chat.id, get_market_prices(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل العملة (V36)")
def ana_init(m):
    user = users_col.find_one({"user_id": m.from_user.id})
    if user.get('vip_expiry', 0) < time.time():
        return bot.send_message(m.chat.id, "❌ **يجب تفعيل VIP أولاً.**\nيمكنك التفعيل من قسم 'حسابي' إذا كان لديك رصيد.")
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: SOL):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل العملة (V36)", "👤 حسابي", "📈 أسعار السوق", "💳 شحن الرصيد"]: return
    bot.send_message(m.chat.id, "🔍 جاري فحص السيولة والاتجاه...")
    res, chart = get_v36_analysis(m.text)
    if res:
        try: bot.send_photo(m.chat.id, chart, caption=res, parse_mode="Markdown")
        except: bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ رمز خاطئ.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    user = users_col.find_one({"user_id": m.from_user.id})
    bal = user.get('balance', 0.0)
    exp = user.get('vip_expiry', 0)
    status = "VIP ✅" if exp > time.time() else "مجاني 👤"
    
    mk = types.InlineKeyboardMarkup()
    if bal >= VIP_PRICE and exp < time.time():
        mk.add(types.InlineKeyboardButton("🌟 تفعيل VIP برصيدي", callback_data="buy_vip"))
    
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n🆔 آيدي: `{m.from_user.id}`\n💰 رصيدك: `{bal}$` \n🌟 الحالة: {status}", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "buy_vip")
def buy_vip_cb(c):
    uid = c.from_user.id
    user = users_col.find_one({"user_id": uid})
    if user['balance'] >= VIP_PRICE:
        expiry = time.time() + (30 * 86400)
        users_col.update_one({"user_id": uid}, {"$inc": {"balance": -VIP_PRICE}, "$set": {"vip_expiry": expiry}})
        bot.answer_callback_query(c.id, "✅ تم التفعيل!")
        bot.send_message(uid, "🌟 مبروك! تم خصم المبلغ وتفعيل اشتراكك VIP لمدة 30 يوم.")
    else:
        bot.answer_callback_query(c.id, "❌ رصيدك غير كافٍ.", show_alert=True)

# --- [ 7. نظام الشحن المزدوج ] ---
@bot.message_handler(func=lambda m: m.text == "💳 شحن الرصيد")
def deposit_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (OxaPay)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("👨‍💻 تفعيل يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الشحن المناسبة لك:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def pay_cbs(c):
    if c.data == "pay_auto":
        payload = {'merchant': OXAPAY_KEY, 'amount': VIP_PRICE, 'currency': 'USD', 'description': str(c.from_user.id)}
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 دفع الآن", url=res['payLink']))
            bot.send_message(c.message.chat.id, "اضغط للدفع التلقائي:", reply_markup=mk)
    elif c.data == "pay_manual":
        bot.send_message(c.message.chat.id, f"📍 حول {VIP_PRICE}$ لعنوان TRC20:\n`{WALLET_ADDRESS}`\nثم أرسل صورة الإيصال هنا.")

# --- [ 8. ميزات الإدارة (إذاعة + تفعيل) ] ---
@bot.message_handler(func=lambda m: m.text == "📢 إذاعة (للإدارة)" and m.from_user.id == OWNER_ID)
def broadcast_init(m):
    msg = bot.send_message(m.chat.id, "📝 أرسل الرسالة التي تريد تعميمها على الكل:")
    bot.register_next_step_handler(msg, broadcast_exec)

def broadcast_exec(m):
    users = users_col.find()
    count = 0
    for u in users:
        try:
            bot.send_message(u['user_id'], m.text)
            count += 1
        except: pass
    bot.send_message(OWNER_ID, f"✅ تم إرسال الرسالة إلى {count} مستخدم.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل 50$ رصيد", callback_data=f"adm_dep_{m.from_user.id}"))
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(OWNER_ID, f"🔔 إيصال من: `{m.from_user.id}`", reply_markup=mk)
    bot.send_message(m.chat.id, "⏳ جاري مراجعة إيصالك من قبل الإدارة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_dep_"))
def admin_deposit(c):
    if c.from_user.id != OWNER_ID: return
    uid = int(c.data.split("_")[2])
    users_col.update_one({"user_id": uid}, {"$inc": {"balance": VIP_PRICE}})
    bot.send_message(uid, f"🌟 تم إضافة {VIP_PRICE}$ لرصيدك يدوياً! يمكنك الآن التفعيل من 'حسابي'.")
    bot.answer_callback_query(c.id, "✅ تم شحن الرصيد")

if __name__ == "__main__":
    bot.infinity_polling()
