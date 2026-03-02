import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask, request
from threading import Thread

# --- [ إعدادات السيرفر والويب هوك ] ---
app = Flask('')
@app.route('/')
def home(): return "Radar V17 PRO - ONLINE 24/7"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        # التحقق من أن حالة الدفع "مدفوع"
        if data and str(data.get('status')) in ['paid', 'success', '1']:
            uid = data.get('description', '').replace('CHARGE_', '')
            if uid.isdigit():
                # التفعيل التلقائي في قاعدة البيانات
                db["vip"][uid] = time.time() + (30 * 86400)
                db["daily_limit"][uid] = {"count": 0, "last_reset": str(datetime.date.today())}
                save_db()
                bot.send_message(uid, "🌟 **مبروك! تم تأكيد الدفع وتفعيل اشتراك VIP تلقائياً لمدة 30 يوم.**\nلديك الآن 5 تحليلات دقيقة يومياً.")
                # إشعار لصاحب البوت
                bot.send_message(OWNER_ID, f"✅ تم دفع اشتراك تلقائي من المستخدم: {uid}")
    except: pass
    return "OK", 200

def run_server(): app.run(host='0.0.0.0', port=8080)
Thread(target=run_server).start()

# --- [ الإعدادات والمفاتيح ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
OXA_API_KEY = 'CE8H0F-ISXBD2-RXHALY-KZXUZU'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v17_final.json"

bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=30)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "free_usage": {}, "daily_limit": {}, "users": []}

db = load_db()
def save_db():
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ محرك التحليل الرباعي الدقيق ] ---
def get_analysis(symbol):
    try:
        s = symbol.upper().replace("/", "").strip()
        if not s.endswith("USDT"): s += "USDT"
        
        source = "BINANCE"
        url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=100"
        r = requests.get(url, timeout=7)
        if r.status_code != 200:
            source = "MEXC"
            url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=15m&limit=100"
            r = requests.get(url, timeout=7)
            
        data = r.json()
        closes = [float(c[4]) for c in data]
        highs = [float(c[2]) for c in data]
        lows = [float(c[3]) for c in data]
        p = closes[-1]
        
        sma = sum(closes[-20:]) / 20
        gains = [max(0, closes[i] - closes[i-1]) for i in range(1, 20)]
        losses = [max(0, closes[i-1] - closes[i]) for i in range(1, 20)]
        avg_g = sum(gains)/20; avg_l = sum(losses)/20
        rs = avg_g / (avg_l if avg_l != 0 else 1)
        rsi = 100 - (100 / (1 + rs))
        sup = min(lows[-50:]); resis = max(highs[-50:])
        
        if rsi < 35 and p <= sma:
            sig, stat = "🚀 شراء (منطقة ارتداد ذهبية)", "المؤشرات تشير لقاع فني مشبع بالبيع. نجاح متوقع جداً."
            t1, t2, sl = p*1.045, p*1.09, sup*0.97
        elif rsi > 65 or p >= resis:
            sig, stat = "⚠️ منطقة جني أرباح (خطر)", "السعر متضخم عند مقاومة قوية. يفضل الخروج فوراً."
            t1, t2, sl = p*1.01, p*1.02, p*0.99
        else:
            sig, stat = "📈 اتجاه صاعد مستقر", "الزحم معتدل والترند إيجابي. السعر يستهدف المقاومة القادمة."
            t1, t2, sl = resis, resis*1.035, sma*0.975

        return (f"🏛 **رادار القابضة V17 - المحلل الذكي**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} | 🏛 المصدر: `{source}`\n💰 السعر الحالي: `{p}` | 📊 RSI: `{round(rsi,1)}`\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 الحالة: {stat}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف أول: `{round(t1, 4)}`\n🎯 هدف ثاني: `{round(t2, 4)}`\n🛡️ الوقف: `{round(sl, 4)}`\n\n"
                f"🔗 [عرض الشارت المباشر](https://www.tradingview.com/chart/?symbol={source}:{s})")
    except: return None

# --- [ واجهة المستخدم والأوامر ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة", "💎 حسابي")
    mk.row("💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي")
    return mk

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V17**\nنظام التحليلات الرقمية الموحد والأكثر دقة.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة")
def ana_init(m):
    uid = str(m.from_user.id)
    today = str(datetime.date.today())
    is_vip = db["vip"].get(uid, 0) > time.time()
    
    if is_vip:
        daily = db["daily_limit"].get(uid, {"count": 0, "last_reset": today})
        if daily["last_reset"] != today: daily = {"count": 0, "last_reset": today}
        if daily["count"] >= 5:
            bot.send_message(m.chat.id, "⚠️ **انتهت حصتك اليومية للـ VIP (5/5).**\nتتجدد المحاولات تلقائياً غداً.")
            return
    else:
        used = db["free_usage"].get(uid, 0)
        if used >= 5:
            bot.send_message(m.chat.id, "❌ **انتهت محاولاتك المجانية للأبد (5/5).**\nاشترك الآن لتفعيل الرادار يومياً.")
            return
    
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: SOL):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    uid = str(m.from_user.id)
    if m.text in ["🔍 تحليل عملة", "💎 حسابي", "💳 اشتراك VIP (OxaPay)", "👨‍💻 تفعيل يدوي"]: return
    bot.send_message(m.chat.id, "⏳ جاري فحص المؤشرات الرباعية واستخراج الأهداف...")
    res = get_analysis(m.text)
    if res:
        is_vip = db["vip"].get(uid, 0) > time.time()
        if is_vip:
            d = db["daily_limit"].get(uid, {"count": 0, "last_reset": str(datetime.date.today())})
            d["count"] += 1; db["daily_limit"][uid] = d
        else:
            db["free_usage"][uid] = db["free_usage"].get(uid, 0) + 1
        save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "⚠️ الرمز غير متاح حالياً أو يوجد ضغط على الشبكة.")

# --- [ التعديل المطلوب: نظام الدفع التلقائي ] ---
@bot.message_handler(func=lambda m: m.text == "💳 اشتراك VIP (OxaPay)")
def pay_setup(m):
    msg = bot.send_message(m.chat.id, "💰 **أدخل مبلغ التفعيل (الحد الأدنى 50$):**")
    bot.register_next_step_handler(msg, pay_final)

def pay_final(m):
    if not m.text.isdigit() or int(m.text) < 50:
        bot.send_message(m.chat.id, "❌ يرجى إدخال مبلغ 50$ فأكثر."); return
    
    amount = int(m.text)
    bot.send_message(m.chat.id, "⏳ جاري إنشاء فاتورة دفع مباشرة...")
    try:
        # إرسال طلب لـ OxaPay لإنشاء رابط دفع رسمي
        payload = {
            "merchant": OXA_API_KEY,
            "amount": amount,
            "currency": "USDT",
            "network": "TRC20", # شبكة USDT المفضلة
            "description": f"CHARGE_{m.from_user.id}",
            "callbackUrl": "https://twasihhh-py.onrender.com/webhook" # الرابط الذي أرسلته لي سابقاً
        }
        r = requests.post("https://api.oxapay.com/api/v2/checkout", json=payload, timeout=20).json()
        
        if r.get("payUrl"):
            markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 دفع الآن (بوابة OxaPay)", url=r['payUrl']))
            bot.send_message(m.chat.id, f"🏛 **فاتورة اشتراك VIP بقيمة {amount}$**\n\nاضغط على الزر أدناه لإتمام الدفع المباشر عبر البوابة.\nسيتم تفعيل حسابك تلقائياً بمجرد إرسال المبلغ.", reply_markup=markup)
        else:
            bot.send_message(m.chat.id, "⚠️ فشل في الاتصال بـ OxaPay، جرب لاحقاً.")
    except Exception as e:
        bot.send_message(m.chat.id, "⚠️ حدث خطأ في النظام أثناء توليد الفاتورة.")

@bot.message_handler(func=lambda m: m.text == "💎 حسابي")
def acc_info(m):
    uid = str(m.from_user.id)
    is_v = db["vip"].get(uid, 0) > time.time()
    if is_v:
        c = db["daily_limit"].get(uid, {}).get("count", 0)
        msg = f"🌟 **الحالة: VIP نشط**\n📅 الأيام المتبقية: {int((db['vip'][uid]-time.time())/86400)} يوم\n📈 استهلاك اليوم: {c}/5"
    else:
        c = db["free_usage"].get(uid, 0)
        msg = f"👤 **الحالة: حساب مجاني**\n📊 المحاولات المستخدمة: {c}/5 (مدى الحياة)"
    bot.send_message(m.chat.id, msg)

@bot.message_handler(func=lambda m: m.text == "👨‍💻 تفعيل يدوي")
def manual(m):
    bot.send_message(m.chat.id, f"أرسل مبلغ **50$** لعنواننا:\n`{WALLET_ADDRESS}`\nثم أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    btn = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل VIP", callback_data=f"v_{m.from_user.id}"))
    bot.send_message(OWNER_ID, f"🔔 إيصال دفع جديد من {m.from_user.id}", reply_markup=btn)
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "⏳ تم استلام الصورة، جاري مراجعتها من قبل الإدارة.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_"))
def admin_v(c):
    u = c.data.split("_")[1]
    db["vip"][u] = time.time() + (30 * 86400)
    db["daily_limit"][u] = {"count": 0, "last_reset": str(datetime.date.today())}
    save_db(); bot.send_message(u, "🌟 مبروك! تم تفعيل اشتراكك VIP بنجاح.")
    bot.answer_callback_query(c.id, "تم التفعيل")

if __name__ == "__main__":
    while True:
        try: bot.polling(none_stop=True, interval=0, timeout=60)
        except: time.sleep(5)
