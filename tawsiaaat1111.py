import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask
from threading import Thread

# --- [ إعدادات السيرفر لضمان العمل 24/7 ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V25 PRO - ACTIVE"
def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات الأساسية - عدلها بما يناسبك ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = 6016547718  # الـ ID الخاص بك
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_database.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ إدارة قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "free_usage": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل "القناص" ] ---
def get_pro_analysis(symbol):
    s = symbol.upper().replace("/", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # جلب البيانات (بينانس ثم ميكس سي)
    source = "BINANCE"
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=7)
        if r.status_code != 200:
            source = "MEXC"
            url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
            r = requests.get(url, timeout=7)
        data = r.json()
        
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        volumes = [float(c[5]) for c in data]
        p = closes[-1]

        # 1. RSI (الزخم)
        g = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        l = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rsi = 100 - (100 / (1 + (sum(g)/sum(l) if sum(l) != 0 else 1)))
        
        # 2. SMA (الاتجاه العام)
        sma = sum(closes[-50:]) / 50
        
        # 3. الدعوم والمقاومات
        sup, res = min(lows[-40:]), max(highs[-40:])

        # --- الخوارزمية الذهبية لاتخاذ القرار ---
        if rsi < 32 and p >= sup:
            sig, stat, emo = "🚀 شراء (LONG)", "العملة في منطقة ارتداد قوية مع تشبع بيعي حاد.", "🟢"
            t1, t2, sl = p*1.04, p*1.08, sup*0.98
        elif p < sma and rsi > 55:
            sig, stat, emo = "📉 هبوط (SHORT)", "السعر كسر المتوسط والزخم يضعف. تجنب الشراء.", "🔴"
            t1, t2, sl = p*0.96, p*0.92, p*1.04
        elif p > sma and rsi > 45:
            sig, stat, emo = "📈 صعود مستقر", "العملة تحافظ على اتجاه صاعد فوق المتوسط الرئيسي.", "🔵"
            t1, t2, sl = res, res*1.05, p*0.97
        else:
            sig, stat, emo = "⏳ منطقة حيرة", "السيولة متذبذبة حالياً. ننتظر اختراق القمة أو القاع.", "⚪"
            t1, t2, sl = p*1.02, p*1.05, p*0.98

        return (f"🏛 **رادار القابضة - التقرير الفني**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}` | 📊 RSI: `{round(rsi,1)}`\n"
                f"🌐 المصدر: `{source}` | 🛡️ الحالة: `واقعية`\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 التحليل: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف 1: `{round(t1, 4)}`\n🎯 هدف 2: `{round(t2, 4)}`\n🛡️ الوقف: `{round(sl, 4)}`\n\n"
                f"🔗 [عرض الشارت المباشر](https://www.tradingview.com/chart/?symbol={source}:{s})")
    except: return None

# --- [ واجهة البوت ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "👤 حسابي")
    mk.row("💳 اشتراك VIP", "👨‍💻 تفعيل يدوي")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في رادار القابضة V25**\nنظام التوصيات الأكثر أماناً ودقة.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    uid = str(m.from_user.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    used = db["free_usage"].get(uid, 0)
    
    if not is_vip and used >= 3:
        bot.send_message(m.chat.id, "❌ **انتهت المحاولات المجانية.**\nيرجى الاشتراك في VIP للحصول على تحليلات غير محدودة.")
        return
        
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    uid = str(m.from_user.id)
    if m.text in ["🔍 تحليل عملة", "👤 حسابي", "💳 اشتراك VIP", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري تحليل السوق بعمق...")
    res = get_pro_analysis(m.text)
    if res:
        if not db["vip"].get(uid, 0) > time.time():
            db["free_usage"][uid] = db["free_usage"].get(uid, 0) + 1; save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ فشل جلب البيانات. تأكد من الرمز صحيحاً.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    status = "VIP نشط ✅" if is_v else "حساب مجاني 👤"
    bot.send_message(m.chat.id, f"🆔 معرفك: `{uid}`\n🌟 الحالة: **{status}**")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP")
def vip_info(m):
    info = (f"💳 **مميزات اشتراك VIP:**\n"
            f"━━━━━━━━━━━━━━\n"
            f"✅ تحليلات غير محدودة لجميع العملات.\n"
            f"✅ توصيات فائقة الدقة (صعود وهبوط).\n"
            f"✅ دعم فني مباشر.\n\n"
            f"💰 السعر: 50$ شهرياً\n"
            f"📍 العنوان (TRC20):\n`{WALLET_ADDRESS}`")
    bot.send_message(m.chat.id, info, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, "أرسل صورة إيصال التحويل هنا، وسيتم تفعيلك فوراً.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    # إرسال الإيصال للمدير مع أزرار تفعيل
    btn = types.InlineKeyboardMarkup()
    btn.add(types.InlineKeyboardButton("✅ تفعيل 30 يوم", callback_data=f"set_30_{m.from_user.id}"))
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(OWNER_ID, f"🔔 إيصال جديد من: `{m.from_user.id}`", reply_markup=btn, parse_mode="Markdown")
    bot.send_message(m.chat.id, "⏳ تم استلام الإيصال. جاري المراجعة من قبل الإدارة...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("set_"))
def admin_activate(c):
    # set_30_ID
    uid = c.data.split("_")[2]
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db()
    bot.send_message(uid, "🌟 **مبروك! تم تفعيل اشتراك VIP بنجاح.**\nاستمتع الآن بأقوى التحليلات.")
    bot.answer_callback_query(c.id, "تم التفعيل بنجاح!")

if __name__ == "__main__":
    bot.polling(none_stop=True)
