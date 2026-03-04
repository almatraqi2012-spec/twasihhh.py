import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask
from threading import Thread

# --- [ إعدادات السيرفر لضمان العمل المستمر ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V27 PRO - SYSTEM READY"
def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات - ضع معلوماتك هنا ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = 6016547718 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v27_final_db.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ إدارة قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "usage": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل "الواقعي" العابر للمنصات ] ---
def get_analysis_pro(symbol):
    s = symbol.upper().replace("/", "").replace(" ", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # محاولة جلب البيانات من Binance أولاً ثم MEXC
    platform = "BINANCE"
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=7)
        if r.status_code != 200:
            platform = "MEXC"
            url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
            r = requests.get(url, timeout=7)
        data = r.json()
        
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        p = closes[-1]

        # 1. RSI (قوة الزخم لآخر 14 شمعة)
        g = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        l = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rsi = 100 - (100 / (1 + (sum(g)/sum(l) if sum(l) != 0 else 1)))
        
        # 2. SMA 50 (الاتجاه العام للسعر)
        sma = sum(closes[-50:]) / 50
        
        # 3. مستويات الدعم والمقاومة
        sup, res = min(lows[-40:]), max(highs[-40:])

        # --- خوارزمية التوصية الصارمة ---
        if rsi < 31 and p >= sup:
            sig, stat, emo = "🚀 شراء (LONG)", "تشبع بيعي حاد عند منطقة دعم. فرصة ارتداد صاعدة.", "🟢"
            t1, t2, sl = p*1.045, p*1.09, sup*0.975
        elif rsi > 69 or (p < sma and rsi > 55):
            sig, stat, emo = "📉 بيع (SHORT)", "ضعف في الزخم وكسر للمتوسط. السعر مرشح للهبوط.", "🔴"
            t1, t2, sl = p*0.96, p*0.92, p*1.04
        elif p > sma and rsi > 48:
            sig, stat, emo = "📈 صعود مستمر", "الاتجاه صاعد والمؤشرات تدعم مواصلة الأهداف.", "🔵"
            t1, t2, sl = res, res*1.04, p*0.97
        else:
            sig, stat, emo = "⏳ حالة تذبذب عرضي", "المؤشرات متداخلة. يفضل الانتظار خارج السوق حالياً.", "⚪"
            t1, t2, sl = p*1.02, p*1.04, p*0.98

        return (f"🏛 **رادار القابضة V27 - تقرير احترافي**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}` | 📊 RSI: `{round(rsi,1)}`\n"
                f"🌐 المنصة: `{platform}` | 🛡️ الدقة: `عالية`\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 التحليل: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف 1: `{round(t1, 4)}` | 🎯 هدف 2: `{round(t2, 4)}`\n🛡️ الوقف: `{round(sl, 4)}`\n\n"
                f"🔗 [عرض الشارت المباشر](https://www.tradingview.com/chart/?symbol={platform}:{s})")
    except: return None

# --- [ واجهة المستخدم والقيود ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "👤 حسابي")
    mk.row("💳 اشتراك VIP", "👨‍💻 تفعيل يدوي")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في رادار القابضة V27**\nنظام التوصيات الذكي بمحاولات يومية محدودة.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    uid = str(m.from_user.id)
    now = time.time()
    today = str(datetime.date.today())
    
    # 1. التحقق من انتهاء اشتراك VIP
    vip_expiry = db["vip"].get(uid, 0)
    if vip_expiry > 0 and now > vip_expiry:
        bot.send_message(m.chat.id, "❌ **انتهت فترة اشتراكك الـ VIP.**\nيرجى التواصل مع الإدارة لتجديد اشتراكك والاستمرار في استخدام الرادار.")
        return

    is_vip = vip_expiry > now
    
    # 2. نظام العداد اليومي
    user_usage = db["usage"].get(uid, {"count": 0, "date": today})
    if user_usage["date"] != today: user_usage = {"count": 0, "date": today}

    # 3. تحديد القيود (5 للـ VIP و 1 للمجاني)
    limit = 5 if is_vip else 1
    
    if user_usage["count"] >= limit:
        msg = "⚠️ **لقد استهلكت حصتك الـ VIP اليومية (5/5).** حاول غداً." if is_vip else "❌ **انتهت محاولتك المجانية الوحيدة لهذا اليوم.** اشترك في VIP لتصل لـ 5 يومياً."
        bot.send_message(m.chat.id, msg)
        return

    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    uid = str(m.from_user.id)
    if m.text in ["🔍 تحليل عملة", "👤 حسابي", "💳 اشتراك VIP", "👨‍💻 تفعيل يدوي"]: return
    
    bot.send_message(m.chat.id, "⏳ جاري استدعاء البيانات وتحليل المؤشرات...")
    res = get_analysis_pro(m.text)
    
    if res:
        today = str(datetime.date.today())
        user_usage = db["usage"].get(uid, {"count": 0, "date": today})
        if user_usage["date"] != today: user_usage = {"count": 0, "date": today}
        
        user_usage["count"] += 1
        db["usage"][uid] = user_usage
        save_db()
        
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ فشل في جلب العملة. تأكد من الرمز (مثلاً SOL).")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    expiry = db["vip"].get(uid, 0)
    now = time.time()
    today = str(datetime.date.today())
    count = db["usage"].get(uid, {"count": 0, "date": today})["count"]
    
    if expiry > now:
        days_left = int((expiry - now) / 86400)
        status = f"VIP نشط ✅ (ينتهي بعد {days_left} يوم)"
        limit = 5
    else:
        status = "مجاني 👤"
        limit = 1
    
    msg = (f"👤 **معلومات حسابك:**\n━━━━━━━━━━━━━━\n"
           f"🌟 الحالة: **{status}**\n📈 استهلاك اليوم: {count}/{limit}\n🆔 معرفك: `{uid}`")
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP")
def vip_info(m):
    bot.send_message(m.chat.id, f"💳 **باقة VIP (الرادار الاحترافي):**\n━━━━━━━━━━━━━━\n- 5 تحليلات يومية شاملة.\n- توصيات دخول وخروج دقيقة.\n- أهداف واقعية بناءً على الدعم والمقاومة.\n\n💰 السعر: 50$ شهرياً\n📍 المحفظة (TRC20):\n`{WALLET_ADDRESS}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, "أرسل صورة إيصال التحويل الآن ليتم تفعيل اشتراكك يدوياً.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل 30 يوم", callback_data=f"act_{m.from_user.id}"))
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(OWNER_ID, f"🔔 إيصال دفع جديد من: `{m.from_user.id}`", reply_markup=btn, parse_mode="Markdown")
    bot.send_message(m.chat.id, "⏳ تم استلام الإيصال، جاري مراجعته من قبل الإدارة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def admin_act(c):
    uid = c.data.split("_")[1]
    # إضافة شهر (30 يوم) من لحظة الضغط
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db()
    bot.send_message(uid, "🌟 **مبروك! تم تفعيل/تجديد اشتراكك VIP بنجاح.**\nلديك الآن 5 تحليلات يومية دقيقة.")
    bot.answer_callback_query(c.id, "تم التفعيل")

if __name__ == "__main__":
    bot.polling(none_stop=True)
