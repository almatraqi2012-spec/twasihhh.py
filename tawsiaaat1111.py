import requests, telebot, time, json, os, threading
from telebot import types
from flask import Flask, request

# --- [ 1. سيرفر الاستقبال والويب هوك - التفعيل الآلي ] ---
app = Flask('')

@app.route('/')
def home(): 
    return "RADAR SYSTEM V40 IS FULLY ACTIVE"

@app.route('/payment/webhook', methods=['POST'])
def webhook():
    data = request.json
    # التفعيل الآلي عند استلام تأكيد من بوابة الدفع Oxapay
    if data and data.get('status') == 'confirmed':
        target_id = data.get('description') 
        if target_id:
            db["vip"][str(target_id)] = time.time() + (30 * 86400)
            save_db()
            try: 
                bot.send_message(int(target_id), "✅ **تم تفعيل اشتراك VIP آلياً بنجاح!**\nاستمتع بالتحليلات غير المحدودة والدقيقة.")
            except: 
                pass
    return "OK", 200

def run_server():
    try: 
        app.run(host='0.0.0.0', port=8080)
    except: 
        pass

# تشغيل السيرفر في خلفية البوت
threading.Thread(target=run_server, daemon=True).start()

# --- [ 2. الإعدادات والبيانات المركزية ] ---
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v40_pro.json"

bot = telebot.TeleBot(API_TOKEN)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "free_usage": {}, "users": []}

db = load_db()

def save_db():
    try:
        with open(DB_FILE, 'w') as f: json.dump(db, f)
    except: pass

# --- [ 3. محرك التحليل الاحترافي V40 - واقعي وغير كاذب ] ---
def get_v40_analysis(symbol):
    s = symbol.upper().strip().replace("/", "").replace("-", "")
    if not s.endswith("USDT") and len(s) < 7: s += "USDT"
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    configs = [
        {"url": f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100", "source": "BINANCE"},
        {"url": f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100", "source": "MEXC"},
        {"url": f"https://api.mexc.com/api/v3/klines?symbol={s.replace('USDT', '_USDT')}&interval=60m&limit=100", "source": "MEXC"}
    ]
    
    data, source_name = None, "BINANCE"
    for cfg in configs:
        try:
            r = requests.get(cfg["url"], headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                source_name = cfg["source"]
                break
        except: continue

    if not data or len(data) < 30: return None

    try:
        closes = [float(c[4]) for c in data]
        p = closes[-1] # السعر الحالي
        
        # مؤشر القوة النسبية RSI
        up = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        dn = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rsi = 100 - (100 / (1 + (sum(up)/sum(dn) if sum(dn) != 0 else 1)))
        
        # المتوسطات والانحراف المعياري
        ema = sum(closes[-20:]) / 20
        std_dev = (sum([(x - ema)**2 for x in closes[-20:]]) / 20)**0.5
        macd = (sum(closes[-12:]) / 12) - (sum(closes[-26:]) / 26)
        
        # Bollinger Bands للأهداف الواقعية
        upper_band = ema + (std_dev * 2)
        lower_band = ema - (std_dev * 2)

        # منطق التحليل - فلاتر الأمان ضد الكذب
        if p > ema and macd > 0 and 50 < rsi < 68:
            sig, emo, txt = "🚀 دخول شراء (LONG)", "🟢", "سيولة إيجابية مع زخم صحي (غير متضخم)."
            t1, t2, sl = p + (std_dev * 1.5), upper_band, p - (std_dev * 1.8)
            
        elif p < ema and macd < 0 and 32 < rsi < 48:
            sig, emo, txt = "📉 دخول بيع (SHORT)", "🔴", "ضغط بيعي واضح وكسر لمستويات الدعم."
            t1, t2, sl = p - (std_dev * 1.5), lower_band, p + (std_dev * 1.8)
            
        elif rsi >= 70:
            sig, emo, txt = "⚠️ تشبع شرائي (قمة)", "🟡", "العملة متضخمة جداً شرائياً. خطر الدخول الآن."
            t1, t2, sl = p * 1.01, upper_band * 1.01, p * 0.98
            
        elif rsi <= 30:
            sig, emo, txt = "⚠️ تشبع بيعي (قاع)", "🔵", "نزيف بيعي حاد، توقع ارتداد تصحيحي للأعلى قريباً."
            t1, t2, sl = p * 1.03, p * 1.06, p * 0.96
            
        else:
            sig, emo, txt = "⏳ منطقة حيرة", "⚪", "تذبذب عرضي، السيولة غير كافية لتحديد اتجاه."
            t1, t2, sl = p * 1.015, p * 1.03, p * 0.98

        chart_link = f"https://www.tradingview.com/chart/?symbol={source_name}:{s}"
        
        return (f"🏛 **رادار القابضة - التقرير الفني V40**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}` | 📊 RSI: `{round(rsi,1)}` \n"
                f"🌐 المصدر: {source_name} | 🛡️ الحالة: واقعية ✅\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 التحليل: {txt}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف 1: `{round(t1, 5)}` \n🎯 هدف 2: `{round(t2, 5)}` \n🛡️ الوقف: `{round(sl, 5)}` \n\n"
                f"🔗 [عرض الشارت المباشر]({chart_link})")
    except: return None

# --- [ 4. نظام الشحن ومعالجة الطلبات اليدوية والآلية ] ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.message.chat.id
    
    if call.data == "pay_auto":
        create_invoice(call.message, 50)
    
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 حول مبلغ 50$ لعنوان المحفظة (USDT.TRC20):\n`{MY_WALLET}`\n\nثم أرسل صورة الإيصال هنا.")
        bot.register_next_step_handler(call.message, wait_for_receipt)
    
    elif call.data.startswith("confirm_"):
        target_id = str(call.data.split("_")[-1])
        db["vip"][target_id] = time.time() + (30 * 86400)
        save_db()
        bot.answer_callback_query(call.id, "✅ تم التفعيل بنجاح!", show_alert=True)
        try:
            bot.send_message(int(target_id), "✅ **تهانينا! تمت مراجعة إيصالك وتفعيل حسابك VIP بنجاح.**")
        except: pass
        bot.edit_message_caption(chat_id=OWNER_ID, message_id=call.message.message_id, 
                                 caption=f"✅ تم التفعيل للعميل: `{target_id}`\nالحالة: VIP 👑")

def create_invoice(m, amt):
    try:
        payload = {
            'merchant': OXAPAY_KEY,
            'amount': amt,
            'currency': 'USD',
            'description': str(m.chat.id)
        }
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 ادفع 50$ (تفعيل آلي)", url=res['payLink']))
            bot.send_message(m.chat.id, "🏛 **فاتورة اشتراك VIP**\nالمبلغ: 50 USDT\nالمدة: 30 يوم", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ عطل مؤقت في بوابة الدفع.")

def wait_for_receipt(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل الحساب الآن", callback_data=f"confirm_user_{m.chat.id}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, 
                       caption=f"🔔 إيصال جديد من: `{m.chat.id}`\nاضغط لتفعيل اشتراكه فوراً:", 
                       reply_markup=mk)
        bot.send_message(m.chat.id, "✅ تم استلام الإيصال، سيتم تفعيل حسابك فور مراجعة المدير.")
    else:
        bot.send_message(m.chat.id, "⚠️ يرجى إرسال صورة الإيصال فقط.")

# --- [ 5. القوائم الرئيسية ومعالجة الرسائل ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: 
        db["users"].append(uid)
        save_db()
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة 📈", "👤 حسابي")
    mk.row("💰 شحن الرصيد")
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في رادار القابضة V40 PRO**\nأقوى نظام للتحليل الفني الواقعي في تليجرام.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def dep_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ دفع آلي (Oxapay)", callback_data="pay_auto"), 
           types.InlineKeyboardButton("💳 إرسال إيصال (يدوي)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن المناسبة لتفعيل الـ VIP (50$):", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة 📈")
def ana_init(m):
    uid = str(m.from_user.id)
    now = time.time()
    is_vip = db["vip"].get(uid, 0) > now
    
    if not is_vip and db["free_usage"].get(uid, 0) >= 5:
        return bot.send_message(m.chat.id, "❌ انتهت محاولاتك المجانية (5/5).\nاشترك في VIP للحصول على وصول غير محدود وتحليلات أكثر دقة.")
    
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC, XRP, SOL):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    # حماية من الأوامر المتداخلة
    if m.text in ["🔍 تحليل عملة 📈", "👤 حسابي", "💰 شحن الرصيد"]: return
    
    bot.send_message(m.chat.id, "⏳ جاري استخراج بيانات السوق وتحليل السيولة...")
    res = get_v40_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if not (db["vip"].get(uid, 0) > time.time()):
            db["free_usage"][uid] = db["free_usage"].get(uid, 0) + 1
            save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: 
        bot.send_message(m.chat.id, "⚠️ فشل جلب البيانات. تأكد من رمز العملة أو جرب لاحقاً.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    if is_vip:
        remaining = int((db["vip"][uid] - time.time()) / 86400)
        st = f"VIP 👑 (متبقي {remaining} يوم)"
    else:
        st = f"مجاني ({db['free_usage'].get(uid, 0)}/5 محاولات)"
    
    bot.send_message(m.chat.id, f"👤 **تفاصيل حسابك:**\n━━━━━━━━━━━━━━\n🆔: `{uid}`\n🌟 الحالة: {st}")

# --- [ 6. تشغيل البوت ] ---
if __name__ == "__main__":
    print("🏛 RADAR SYSTEM V40 IS STARTING...")
    bot.infinity_polling(skip_pending=True)
