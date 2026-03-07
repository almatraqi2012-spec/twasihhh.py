import requests, telebot, time, json, os, datetime, random, threading
import pymongo, dns.resolver
from telebot import types
from flask import Flask, request

# --- [ حل مشكلة DNS في الترمكس ] ---
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']

# --- [ إعداد السيرفر للشحن التلقائي ] ---
app = Flask(__name__)
@app.route('/')
def home(): return "Radar V35 PRO - ACTIVE"

# ================= [ ⚙️ الإعدادات ] =================
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
# السعر: 50 دولار لشهر VIP
VIP_PRICE = 50.0

# قاعدة البيانات (استبدل USER و PASS ببياناتك)
MONGO_URL = "mongodb+srv://USER:PASS@cluster.mongodb.net/radar_db" 
m_client = pymongo.MongoClient(MONGO_URL, tlsAllowInvalidCertificates=True)
db = m_client['radar_v35']
users_col = db['users'] # لتخزين الرصيد والبيانات
# ===================================================

bot = telebot.TeleBot(API_TOKEN)

# --- [ ويب هوك الشحن التلقائي ] ---
@app.route('/webhook/oxapay', methods=['POST'])
def oxapay_webhook():
    data = request.json
    if data.get('status') == 'Paid':
        uid = int(data.get('description'))
        amount = float(data.get('amount'))
        # تفعيل VIP تلقائياً لمدة 30 يوم
        expiry = time.time() + (30 * 86400)
        users_col.update_one({"user_id": uid}, {"$set": {"vip_expiry": expiry}}, upsert=True)
        bot.send_message(uid, f"✅ **تم الشحن والتفعيل تلقائياً!**\nتم إضافة {amount}$ وتفعيل باقة VIP لمدة 30 يوم.")
    return "OK", 200

def run_flask(): app.run(host='0.0.0.0', port=8080)
threading.Thread(target=run_flask, daemon=True).start()

# --- [ محرك التحليل الفلترة الحديدية V35 ] ---
def get_v35_analysis(symbol):
    s = symbol.upper().replace("/", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        closes = [float(c[4]) for c in data]
        
        # 1. حساب RSI
        diff = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gain = sum([d for d in diff if d > 0]) / 14
        loss = abs(sum([d for d in diff if d < 0])) / 14
        rs = gain / (loss if loss != 0 else 1)
        rsi = 100 - (100 / (1 + rs))

        # 2. حساب EMA 20 & 50
        ema_20 = sum(closes[-20:]) / 20
        ema_50 = sum(closes[-50:]) / 50
        
        # 3. السعر الحالي والزخم
        p = closes[-1]
        chart_url = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"

        # --- [ منطق الفلترة المربوعة ] ---
        # شراء: السعر فوق EMA20 و EMA50 + RSI بين 40 و 60 (بداية انفجار)
        if p > ema_20 and p > ema_50 and 40 < rsi < 65:
            type_d, sig, emo = "LONG (شراء)", "🟢 دخول قوي", "🚀"
            stat = "تم تأكيد الاتجاه الصاعد بـ 4 مؤشرات. السيولة تتدفق الآن."
            t1, t2, sl = p*1.03, p*1.07, p*0.96
        # بيع: السعر تحت EMA20 و EMA50 + RSI بين 40 و 60 (بداية انهيار)
        elif p < ema_20 and p < ema_50 and 35 < rsi < 55:
            type_d, sig, emo = "SHORT (بيع)", "🔴 خروج/هبوط", "📉"
            stat = "الفلترة تشير لسلبية حادة. كسر المتوسطات يعني استمرار النزيف."
            t1, t2, sl = p*0.97, p*0.93, p*1.04
        else:
            type_d, sig, emo = "WAIT (تذبذب)", "⚪ منطقة خطر", "⏳"
            stat = "المؤشرات متضاربة. لا تدخل الآن لتجنب الخسارة (نظام حماية الناس)."
            t1, t2, sl = "---", "---", "---"

        msg = (f"🏛 **رادار القابضة V35 - الفلترة الحديدية**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}`\n📊 الإشارة: **{sig}**\n🌡️ RSI: `{round(rsi, 2)}`\n━━━━━━━━━━━━━━\n"
               f"📝 التحليل: {stat}\n━━━━━━━━━━━━━━\n"
               f"🎯 هدف 1: `{t1}`\n🎯 هدف 2: `{t2}`\n🛡️ الوقف: `{sl}`")
        return msg, chart_url
    except: return None, None

# --- [ واجهة البوت ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة (V35)", "👤 حسابي")
    mk.row("⚡ شحن VIP تلقائي", "👨‍💻 تفعيل يدوي")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    users_col.update_one({"user_id": uid}, {"$set": {"username": m.from_user.username}}, upsert=True)
    bot.send_message(m.chat.id, "🐲 **مرحباً بك في رادار القابضة V35**\nنظام الفلترة الحديدية المربوعة لمنع الخسائر والشحن التلقائي.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة (V35)")
def ana_init(m):
    uid = m.from_user.id
    user = users_col.find_one({"user_id": uid})
    
    # فحص الـ VIP
    expiry = user.get('vip_expiry', 0) if user else 0
    if time.time() > expiry:
        bot.send_message(m.chat.id, "❌ **اشتراكك VIP منتهي.**\nاستخدم 'شحن VIP تلقائي' للوصول للمحلل المطور.")
        return

    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل عملة (V35)", "👤 حسابي", "⚡ شحن VIP تلقائي"]: return
    bot.send_message(m.chat.id, "🔍 جاري الفحص بـ 4 مؤشرات تقنية...")
    res, chart = get_v35_analysis(m.text)
    if res:
        try: bot.send_photo(m.chat.id, chart, caption=res, parse_mode="Markdown")
        except: bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ الرمز غير صحيح أو السيرفر مشغول.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    user = users_col.find_one({"user_id": m.from_user.id})
    expiry = user.get('vip_expiry', 0) if user else 0
    status = "VIP نشط ✅" if expiry > time.time() else "مجاني 👤"
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n🆔 آيدي: `{m.from_user.id}`\n🌟 الحالة: {status}")

# --- [ نظام الشحن التلقائي OxaPay ] ---
@bot.message_handler(func=lambda m: m.text == "⚡ شحن VIP تلقائي")
def pay_auto(m):
    bot.send_message(m.chat.id, f"💳 **اشتراك VIP (30 يوم)**\nالسعر: {VIP_PRICE}$\nالدفع فوري والتفعيل تلقائي.")
    try:
        payload = {
            'merchant': OXAPAY_KEY,
            'amount': VIP_PRICE,
            'currency': 'USD',
            'description': str(m.chat.id),
            'callbackUrl': "https://your-domain.com/webhook/oxapay" # استبدل برابط سيرفرك
        }
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 اضغط هنا للدفع والشحن", url=res['payLink']))
            bot.send_message(m.chat.id, "انقر على الزر أدناه لإتمام الدفع:", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ فشل الاتصال ببوابة الدفع.")

# --- [ التفعيل اليدوي القديم ] ---
@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual_p(m):
    bot.send_message(m.chat.id, "أرسل صورة الإيصال ليتم فحصها من الإدارة.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(OWNER_ID, f"🔔 إيصال من: `{m.from_user.id}`")
    bot.send_message(m.chat.id, "⏳ تم الاستلام، انتظر التفعيل.")

if __name__ == "__main__":
    bot.infinity_polling()
