import requests, telebot, time, json, os, threading
from telebot import types
from flask import Flask, request

# --- [ 1. سيرفر الاستقبال والويب هوك ] ---
app = Flask('')

@app.route('/')
def home(): return "RADAR SYSTEM IS FULLY ACTIVE"

@app.route('/payment/webhook', methods=['POST'])
def webhook():
    data = request.json
    # التفعيل الآلي عند استلام تأكيد من بوابة الدفع
    if data and data.get('status') == 'confirmed':
        target_id = data.get('description') 
        if target_id:
            db["vip"][str(target_id)] = time.time() + (30 * 86400)
            save_db()
            try: bot.send_message(int(target_id), "✅ **تم تفعيل اشتراك VIP آلياً بنجاح!**\nاستمتع بالتحليلات غير المحدودة.")
            except: pass
    return "OK", 200

def run_server():
    try: app.run(host='0.0.0.0', port=8080)
    except: pass
threading.Thread(target=run_server, daemon=True).start()

# --- [ 2. الإعدادات والبيانات ] ---
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v36_final.json"

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

# --- [ 3. محرك التحليل الخماسي ] ---
def get_v36_analysis(symbol):
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
        p = closes[-1]
        up = [max(0, closes[i] - closes[i-1]) for i in range(-14, 0)]
        dn = [max(0, closes[i-1] - closes[i]) for i in range(-14, 0)]
        rsi = 100 - (100 / (1 + (sum(up)/sum(dn) if sum(dn) != 0 else 1)))
        ema = sum(closes[-20:]) / 20
        macd = (sum(closes[-12:]) / 12) - (sum(closes[-26:]) / 26)
        std_dev = (sum([(x - ema)**2 for x in closes[-20:]]) / 20)**0.5

        if p > ema and macd > 0 and rsi > 52:
            sig, emo, txt = "🚀 دخول شراء (LONG)", "🟢", "السيولة إيجابية والترند صاعد."
            t1, t2, sl = p + (std_dev * 1.6), p + (std_dev * 2.8), p - (std_dev * 2.0)
        elif p < ema and macd < 0 and rsi < 48:
            sig, emo, txt = "📉 دخول بيع (SHORT)", "🔴", "ضغط بيعي واضح كسر المتوسطات."
            t1, t2, sl = p - (std_dev * 1.6), p - (std_dev * 2.8), p + (std_dev * 2.0)
        else:
            sig, emo, txt = "⏳ منطقة حيرة", "⚪", "السيولة متذبذبة حالياً."
            t1, t2, sl = p * 1.018, p * 1.035, p * 0.982

        chart_link = f"https://www.tradingview.com/chart/?symbol={source_name}:{s}"
        return (f"🏛 **رادار القابضة - التقرير الفني**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{s} {emo}\n💰 السعر: `{p}` | 📊 RSI: `{round(rsi,1)}` \n"
                f"🌐 المصدر: {source_name} | 🛡️ الحالة: واقعية\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{sig}**\n📌 التحليل: {txt}\n━━━━━━━━━━━━━━\n"
                f"🎯 هدف 1: `{round(t1, 5)}` \n🎯 هدف 2: `{round(t2, 5)}` \n🛡️ الوقف: `{round(sl, 5)}` \n\n"
                f"🔗 [عرض الشارت المباشر]({chart_link})")
    except: return None

# --- [ 4. نظام الشحن ومعالجة الأزرار ] ---
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    uid = call.message.chat.id
    
    if call.data == "pay_auto":
        create_invoice(call.message, 50)
    
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📌 حول 50$ لعنوان المحفظة:\n`{MY_WALLET}`\n\nثم أرسل صورة الإيصال هنا.")
        bot.register_next_step_handler(call.message, wait_for_receipt)
    
    elif call.data.startswith("confirm_"):
        # إصلاح جذري لاستخراج الآيدي: نأخذ آخر عنصر بعد الفاصلة
        target_id = str(call.data.split("_")[-1])
        
        # التفعيل في قاعدة البيانات
        db["vip"][target_id] = time.time() + (30 * 86400)
        save_db()
        
        # رد فعل فوري للمالك
        bot.answer_callback_query(call.id, "✅ تم التفعيل بنجاح!", show_alert=True)
        
        # محاولة إبلاغ العميل
        try:
            bot.send_message(int(target_id), "✅ **تهانينا! تمت مراجعة إيصالك وتفعيل حسابك VIP لمدة 30 يوم بنجاح.**")
        except: pass
        
        # تحديث رسالة الإيصال عند المالك
        bot.edit_message_caption(chat_id=OWNER_ID, message_id=call.message.message_id, 
                                 caption=f"✅ تم التفعيل للعميل: `{target_id}`\nالحالة الآن: VIP 👑")

def create_invoice(m, amt):
    try:
        payload = {
            'merchant': OXAPAY_KEY,
            'amount': amt,
            'currency': 'USD',
            'description': str(m.chat.id) # نضع الآيدي هنا ليتم استخدامه في التفعيل الآلي
        }
        res = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 ادفع 50$ (تفعيل آلي)", url=res['payLink']))
            bot.send_message(m.chat.id, "🏛 **فاتورة اشتراك VIP**\nالمبلغ: 50 USDT\nالمدة: 30 يوم", reply_markup=mk)
    except: bot.send_message(m.chat.id, "⚠️ عطل مؤقت في بوابة الدفع.")

def wait_for_receipt(m):
    if m.photo:
        # هنا يتم تمرير الآيدي بشكل صريح في الزر
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل الحساب الآن", callback_data=f"confirm_user_{m.chat.id}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, 
                       caption=f"🔔 إيصال جديد من: `{m.chat.id}`\nاضغط على الزر أدناه للتفعيل فوراً:", 
                       reply_markup=mk)
        bot.send_message(m.chat.id, "✅ استلمنا الإيصال، سيتم تفعيل حسابك فور مراجعة المدير.")
    else:
        bot.send_message(m.chat.id, "⚠️ يرجى إرسال صورة الإيصال فقط.")

# --- [ 5. القوائم الرئيسية ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("🔍 تحليل عملة 📈", "👤 حسابي")
    mk.row("💰 شحن الرصيد")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V36 PRO**", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def dep_menu(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ دفع آلي", callback_data="pay_auto"), 
           types.InlineKeyboardButton("💳 إرسال إيصال", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن (سعر الاشتراك: 50$):", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "🔍 تحليل عملة 📈")
def ana_init(m):
    uid = str(m.from_user.id)
    now = time.time()
    is_vip = db["vip"].get(uid, 0) > now
    
    if not is_vip and db["free_usage"].get(uid, 0) >= 5:
        return bot.send_message(m.chat.id, "❌ انتهت محاولاتك المجانية (5/5).\nاشترك في VIP للحصول على وصول غير محدود.")
    
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (XRP, BTC, STABL...):")
    bot.register_next_step_handler(msg, ana_execute)

def ana_execute(m):
    if m.text in ["🔍 تحليل عملة 📈", "👤 حسابي", "💰 شحن الرصيد"]: return
    bot.send_message(m.chat.id, "⏳ جاري استخراج البيانات...")
    res = get_v36_analysis(m.text)
    if res:
        uid = str(m.from_user.id)
        if not (db["vip"].get(uid, 0) > time.time()):
            db["free_usage"][uid] = db["free_usage"].get(uid, 0) + 1
            save_db()
        bot.send_message(m.chat.id, res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, "⚠️ الرمز غير صحيح أو العملة غير مدعومة حالياً.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    st = "VIP 👑" if is_vip else f"مجاني ({db['free_usage'].get(uid, 0)}/5)"
    bot.send_message(m.chat.id, f"👤 **تفاصيل الحساب:**\n🆔: `{uid}`\n🌟 الحالة: {st}")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
