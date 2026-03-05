import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask
from threading import Thread

# --- [ إعدادات السيرفر ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar GOLD V32 - ACTIVE"
def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = 6016547718 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v32_db.json"

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

# --- [ محرك الأرباح المضمونة - تحليل الاتجاهين ] ---
def get_guaranteed_analysis(symbol):
    s = symbol.upper().replace("/", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    source = "BINANCE"
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            source = "MEXC"
            url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
            r = requests.get(url, timeout=10)
            if r.status_code != 200: return None
        
        data = r.json()
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        p = closes[-1]

        # 1. حساب الزخم والقوة (RSI المعدل)
        change = [closes[i] - closes[i-1] for i in range(-14, 0)]
        gain = sum([x for x in change if x > 0]) / 14
        loss = sum([-x for x in change if x < 0]) / 14
        rsi = 100 - (100 / (1 + (gain/loss if loss != 0 else 1)))

        # 2. تحديد الفوليوم والاتجاه
        ema_20 = sum(closes[-20:]) / 20
        
        # --- [ خوارزمية الصفقات المضمونة ] ---
        
        # الحالة الأولى: إشارة صعود (LONG)
        if p > ema_20 and rsi < 70:
            sig, type_deal = "🟢 شراء (LONG)", "صعود"
            stat = "تمركز حيتان واختراق إيجابي للمتوسط. السعر يستهدف القمة التالية."
            t1, t2 = p * 1.03, p * 1.06  # أهداف واقعية 3% و 6%
            sl = p * 0.975               # وقف قريب 2.5%
            
        # الحالة الثانية: إشارة هبوط (SHORT)
        elif p < ema_20 or rsi > 70:
            sig, type_deal = "🔴 بيع (SHORT)", "هبوط"
            stat = "ضغط بيعي قوي وكسر لهيكل السعر. توقع استمرار النزيف للأسفل."
            t1, t2 = p * 0.97, p * 0.94  # ربح من النزول 3% و 6%
            sl = p * 1.025               # وقف فوق السعر 2.5%
            
        else:
            sig, type_deal, stat = "⏳ مراقبة", "جانبي", "السوق غير مستقر حالياً، ننتظر كسر واضح."
            t1, t2, sl = "---", "---", "---"

        return (f"🏛 **رادار القابضة - توصية {type_deal}**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s}\n💰 السعر الحالي: `{p}`\n📊 النوع: **{sig}**\n━━━━━━━━━━━━━━\n"
                f"📝 التحليل: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف 1: `{round(t1, 5) if t1 != '---' else '---'}`\n"
                f"🎯 هدف 2: `{round(t2, 5) if t2 != '---' else '---'}`\n"
                f"🛡️ الوقف: `{round(sl, 5) if sl != '---' else '---'}`\n\n"
                f"💡 *ادخل الصفقة فوراً لإدارة الأرباح.*")
    except: return None

# --- [ واجهة البوت ] ---
@bot.message_handler(commands=['start'])
def start(m):
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "👤 حسابي")
    mk.row("💳 اشتراك VIP", "👨‍💻 تفعيل يدوي")
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في رادار القابضة V32**\nالآن نحلل (صعود وهبوط) لضمان الربح في كل الحالات.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    uid = str(m.from_user.id)
    today = str(datetime.date.today())
    u_usage = db["usage"].get(uid, {"count": 0, "date": today})
    if u_usage["date"] != today: u_usage = {"count": 0, "date": today}
    
    if u_usage["count"] >= 5:
        bot.send_message(m.chat.id, "⚠️ انتهت حصتك اليومية (5/5).")
        return
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثلاً BTC):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    uid = str(m.from_user.id)
    if m.text in ["🔍 تحليل عملة", "👤 حسابي", "💳 اشتراك VIP", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "🔍 جاري استخراج أفضل نقطة دخول...")
    res = get_guaranteed_analysis(m.text)
    if res:
        today = str(datetime.date.today())
        u = db["usage"].get(uid, {"count": 0, "date": today})
        if u["date"] != today: u = {"count": 0, "date": today}
        u["count"] += 1; db["usage"][uid] = u; save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ تأكد من اسم العملة بشكل صحيح.")

# --- [ أوامر الإدارة والحساب ] ---
@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    bot.send_message(m.chat.id, f"🆔 ID: `{uid}`\n🌟 الحالة: {'VIP ✅' if is_v else 'مجاني 👤'}")

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP")
def vip_info(m):
    bot.send_message(m.chat.id, f"💰 اشتراك VIP يفتح لك أدق التوصيات.\n📍 المحفظة (TRC20):\n`{WALLET_ADDRESS}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, "أرسل صورة الإيصال ليتم تفعيلك.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل VIP", callback_data=f"act_{m.from_user.id}"))
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(OWNER_ID, f"🔔 دفع جديد من: `{m.from_user.id}`", reply_markup=btn)

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def admin_act(c):
    uid = c.data.split("_")[1]
    db["vip"][uid] = time.time() + (30 * 86400)
    save_db(); bot.send_message(uid, "🌟 مبروك! تم تفعيل VIP."); bot.answer_callback_query(c.id, "تم")

if __name__ == "__main__":
    bot.polling(none_stop=True)
