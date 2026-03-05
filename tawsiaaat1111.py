import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask
from threading import Thread

# --- [ سيرفر لضمان العمل المستمر ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V32 PRO - SHARP & READY"
def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات الأساسية - عدلها بمعرفاتك ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = 6016547718 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v32_final.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ إدارة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "usage": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل V32 الاحترافي ] ---
def get_v32_analysis(symbol):
    s = symbol.upper().replace("/", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # محاولة جلب البيانات من بينانس أو ميكس سي
    source = "BINANCE"
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            source = "MEXC"
            url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
            r = requests.get(url, timeout=10)
        data = r.json()
        
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        p = closes[-1]

        # مؤشرات ذكية لكشف الاتجاه (EMA + Momentum)
        ema_20 = sum(closes[-20:]) / 20
        momentum = (closes[-1] - closes[-10]) / closes[-10] * 100

        # توليد رابط الشارت كصورة (TradingView Snapshot)
        chart_url = f"https://s3.tradingview.com/snapshots/m/{s if source == 'BINANCE' else 'MEXC:' + s}.png"

        # --- خوارزمية القرار (صعود أو هبوط) ---
        if p > ema_20 and momentum > 0.5:
            type_deal, sig, emo = "LONG (شراء)", "🟢 صعود حقيقي", "🚀"
            stat = "تم رصد انفجار سعري فوق المتوسط. السيولة إيجابية والاتجاه قوي."
            t1, t2, sl = p*1.05, p*1.10, p*0.97
        elif p < ema_20 and momentum < -0.5:
            type_deal, sig, emo = "SHORT (بيع)", "🔴 هبوط حاد", "📉"
            stat = "السعر كسر مستويات الدعم والزخم سلبي جداً. توقع استمرار النزيف."
            t1, t2, sl = p*0.95, p*0.90, p*1.03
        else:
            type_deal, sig, emo = "WAIT (انتظار)", "⚪ تذبذب عرضي", "⏳"
            stat = "السوق غير واضح حالياً. ننتظر كسر القمة أو القاع لتحديد الدخول."
            t1, t2, sl = "---", "---", "---"

        msg = (f"🏛 **رادار القابضة V32 - تحليل {type_deal}**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}`\n📊 الإشارة: **{sig}**\n━━━━━━━━━━━━━━\n"
               f"📝 التحليل: {stat}\n━━━━━━━━━━━━━━\n"
               f"🎯 هدف 1: `{t1}`\n🎯 هدف 2: `{t2}`\n🛡️ الوقف: `{sl}`\n\n"
               f"🔗 [الشارت المباشر من هنا](https://www.tradingview.com/chart/?symbol={source}:{s})")
        return msg, chart_url
    except: return None, None

# --- [ واجهة المستخدم والتحكم ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "👤 حسابي")
    mk.row("💳 اشتراك VIP", "👨‍💻 تفعيل يدوي")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في رادار القابضة V32**\nنظام التوصيات المطور (صعود/هبوط) مع الشارت المباشر.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    uid = str(m.from_user.id)
    now = time.time()
    today = str(datetime.date.today())
    
    # فحص الاشتراكVIP
    vip_expiry = db["vip"].get(uid, 0)
    if vip_expiry > 0 and now > vip_expiry:
        bot.send_message(m.chat.id, "❌ **انتهى اشتراكك VIP.** يرجى التجديد للاستمرار.")
        return

    # فحص العداد اليومي (5 محاولات للجميع حالياً)
    u_usage = db["usage"].get(uid, {"count": 0, "date": today})
    if u_usage["date"] != today: u_usage = {"count": 0, "date": today}
    
    if u_usage["count"] >= 5:
        bot.send_message(m.chat.id, "⚠️ **انتهت حصتك اليومية (5/5).** حاول غداً.")
        return

    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    uid = str(m.from_user.id)
    if m.text in ["🔍 تحليل عملة", "👤 حسابي", "💳 اشتراك VIP", "👨‍💻 تفعيل يدوي"]: return
    
    bot.send_message(m.chat.id, "🔍 جاري سحب البيانات وتحليل الشارت...")
    res, chart = get_v32_analysis(m.text)
    
    if res:
        today = str(datetime.date.today())
        u = db["usage"].get(uid, {"count": 0, "date": today})
        u["count"] += 1; db["usage"][uid] = u; save_db()
        
        # إرسال الصورة مع النص
        try:
            bot.send_photo(m.chat.id, chart, caption=res, parse_mode="Markdown")
        except:
            bot.send_message(m.chat.id, res, parse_mode="Markdown")
        
        bot.send_message(m.chat.id, f"📊 استهلاكك اليومي: {u['count']}/5")
    else:
        bot.send_message(m.chat.id, "⚠️ الرمز غير صحيح أو المنصة غير مستجيبة.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    expiry = db["vip"].get(uid, 0)
    status = "VIP نشط ✅" if expiry > time.time() else "حساب مجاني 👤"
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n🆔 معرفك: `{uid}`\n🌟 الحالة: **{status}**")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP")
def vip_info(m):
    bot.send_message(m.chat.id, f"💰 **باقة VIP:** 50$ شهرياً\n📍 العنوان (TRC20):\n`{WALLET_ADDRESS}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, "أرسل صورة الإيصال هنا ليتم تفعيلك يدوياً.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل 30 يوم", callback_data=f"act_{m.from_user.id}"))
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(OWNER_ID, f"🔔 إيصال من: `{m.from_user.id}`", reply_markup=btn)
    bot.send_message(m.chat.id, "⏳ تم استلام الإيصال، انتظر التفعيل.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def admin_act(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db(); bot.send_message(uid, "🌟 تم تفعيل VIP بنجاح!"); bot.answer_callback_query(c.id, "تم")

if __name__ == "__main__":
    bot.polling(none_stop=True)
