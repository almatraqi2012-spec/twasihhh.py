import requests, telebot, time, json, os, datetime, threading
import pymongo, dns.resolver
from telebot import types
from flask import Flask

# --- [ 1. إعدادات السيرفر والـ DNS ] ---
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']
app = Flask(__name__)

# ================= [ ⚙️ 2. الإعدادات الكبرى ] =================
API_TOKEN = '8461494562:AAEiYC05gZysQqJPyONhs3Kdw5vhy54TyGk'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
VIP_PRICE = 50.0 

# رابط قاعدة البيانات (تأكد من وضع باسووردك C2ZfQWTyO04jK7Nr)
MONGO_URL = "mongodb+srv://Abduh:C2ZfQWTyO04jK7Nr@cluster0.mongodb.net/?retryWrites=true&w=majority"

try:
    m_client = pymongo.MongoClient(MONGO_URL, tlsAllowInvalidCertificates=True, connectTimeoutMS=30000)
    db = m_client['radar_v36']
    users_col = db['users']
    print("✅ متصل بقاعدة بيانات Abduh بنجاح!")
except Exception as e:
    print(f"❌ خطأ قاعدة البيانات: {e}")

bot = telebot.TeleBot(API_TOKEN)

# --- [ 3. نظام Flask لإبقاء رندر حياً ] ---
@app.route('/')
def home():
    return "Radar V36 is Live! 🐲"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- [ 4. محرك التحليل الاحترافي ] ---
def get_v36_analysis(symbol):
    s = symbol.upper().replace("/", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10).json()
        if 'code' in r: # تجربة MEXC إذا لم تكن في بينانس
            url_mexc = f"https://www.mexc.com/open/api/v2/market/kline?symbol={s}&interval=60m&limit=100"
            r = requests.get(url_mexc).json()['data']
        
        closes = [float(c[4]) for c in r]
        p = closes[-1]
        ema20 = sum(closes[-20:])/20
        ema50 = sum(closes[-50:])/50
        
        chart_url = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"

        if p > ema20:
            res, sig = "🟢 **شراء قوي (انفجار السعر)**", "الاتجاه صاعد + سيولة عالية"
            t1, t2, sl = p*1.05, p*1.12, p*0.94
        else:
            res, sig = "🔴 **منطقة حذر / بيع**", "الاتجاه هابط أو تذبذب ضعيف"
            t1, t2, sl = p*0.96, p*0.90, p*1.05

        return f"{res}\n━━━━━━━━━━━━━━\n🪙 العملة: {s}\n💰 السعر: `{p}$`\n📊 الإشارة: {sig}\n🎯 هدف 1: `{round(t1,5)}`\n🎯 هدف 2: `{round(t2,5)}`\n🛡️ الوقف: `{round(sl,5)}`", chart_url
    except: return None, None

# --- [ 5. القوائم الرئيسية والتحكم ] ---
def main_menu(uid):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل العملة (V36)", "👤 حسابي")
    mk.row("📉 أسعار السوق", "💳 شحن الرصيد")
    if uid == OWNER_ID:
        mk.row("📢 إذاعة للإدارة", "📊 الإحصائيات")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    if not users_col.find_one({"user_id": uid}):
        users_col.insert_one({"user_id": uid, "balance": 0.0, "vip_expiry": 0})
    bot.send_message(m.chat.id, "🐲 **مرحباً بك في رادار V36**\nأقوى نظام تحليل مرتبط بسحابة MongoDB.", reply_markup=main_menu(uid))

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل العملة (V36)")
def ana_req(m):
    user = users_col.find_one({"user_id": m.from_user.id})
    if user.get('vip_expiry', 0) < time.time() and m.from_user.id != OWNER_ID:
        return bot.send_message(m.chat.id, "❌ **اشتراكك VIP منتهي!**\nاشحن رصيدك وفعل الاشتراك من قسم 'حسابي'.")
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_exec)

def ana_exec(m):
    bot.send_message(m.chat.id, "⏳ جاري فحص السيولة...")
    res, chart = get_v36_analysis(m.text)
    if res:
        try: bot.send_photo(m.chat.id, chart, caption=res, parse_mode="Markdown")
        except: bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ لم أجد بيانات لهذه العملة.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def account(m):
    user = users_col.find_one({"user_id": m.from_user.id})
    bal = user.get('balance', 0.0)
    exp = user.get('vip_expiry', 0)
    status = "VIP ✅" if exp > time.time() else "مجاني 👤"
    
    mk = types.InlineKeyboardMarkup()
    if bal >= VIP_PRICE and exp < time.time():
        mk.add(types.InlineKeyboardButton("🌟 تفعيل VIP (خصم 50$)", callback_data="buy_vip"))
    
    bot.send_message(m.chat.id, f"👤 **بيانات حسابك:**\n💰 رصيدك: `{bal}$` \n🌟 الحالة: {status}", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "💳 شحن الرصيد")
def deposit(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (OxaPay)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("👨‍💻 تفعيل يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الإيداع:", reply_markup=mk)

# --- [ 6. معالجة العمليات الخلفية ] ---
@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    uid = c.from_user.id
    if c.data == "buy_vip":
        user = users_col.find_one({"user_id": uid})
        if user['balance'] >= VIP_PRICE:
            expiry = time.time() + (30 * 86400)
            users_col.update_one({"user_id": uid}, {"$inc": {"balance": -VIP_PRICE}, "$set": {"vip_expiry": expiry}})
            bot.send_message(uid, "✅ تم تفعيل الـ VIP بنجاح لمدة شهر!")
        else: bot.answer_callback_query(c.id, "❌ رصيدك غير كافٍ.")
    
    elif c.data == "pay_manual":
        bot.send_message(uid, f"📍 حول {VIP_PRICE}$ لعنوان TRC20:\n`{WALLET_ADDRESS}`\nثم أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تأكيد الشحن", callback_data=f"admin_add_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إيصال من: `{m.from_user.id}`", reply_markup=mk)
    bot.send_message(m.chat.id, "⏳ تم إرسال الإيصال للإدارة والمراجعة...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("admin_add_"))
def admin_add(c):
    if c.from_user.id != OWNER_ID: return
    target_id = int(c.data.split("_")[2])
    users_col.update_one({"user_id": target_id}, {"$inc": {"balance": VIP_PRICE}})
    bot.send_message(target_id, "🌟 تم شحن حسابك بـ 50$ بنجاح!")
    bot.answer_callback_query(c.id, "تم التأكيد ✅")

# --- [ 7. تشغيل البوت بنظام حماية الـ 409 ] ---
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("🚀 الرادار V36 انطلق الآن...")
    while True:
        try:
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True, timeout=60)
        except Exception as e:
            print(f"🔄 إعادة تشغيل بسبب: {e}")
            time.sleep(5)
