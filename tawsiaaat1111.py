import requests, telebot, time, json, os, threading, datetime
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ الإعدادات الكبرى - ضع بياناتك هنا ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718 
MY_USDT_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# ⬇️ ضع مفتاح التاجر هنا ليعمل الدفع التلقائي
OXAPAY_MERCHANT_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
DB_FILE = "radar_global_final_v1400.json"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__) # نظام لاستقبال تنبيهات الدفع التلقائي

# --- [ إدارة قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"users": {}, "vip_list": {}}

db = load_db()
def save_db():
    try:
        with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)
    except: pass

# --- [ محرك جلب البيانات من المنصتين ] ---
def fetch_global_data(symbol):
    s = symbol.upper().replace("#", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    endpoints = [
        (f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100", "Binance 🟡"),
        (f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100", "MEXC 🟢")
    ]
    for url, source in endpoints:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                df = pd.DataFrame(r.json()).astype(float)
                cp, ema = df[4].iloc[-1], df[4].ewm(span=20).mean().iloc[-1]
                side = "LONG 🚀" if cp > ema else "SHORT 📉"
                tp = cp * 1.025 if side == "LONG 🚀" else cp * 0.975
                sl = df[3].iloc[-15:].min() * 0.99 if side == "LONG 🚀" else df[2].iloc[-15:].max() * 1.01
                return f"🏛 **نتائج تحليل {source}**\n━━━━━━━━━━━━━━\n🪙 العملة: #{s}\n📊 الإشارة: **{side}**\n📥 الدخول: `{cp}`\n🎯 الهدف: `{round(tp,4)}`\n🛑 الوقف: `{round(sl,4)}`", s
        except: continue
    return None, None

def is_vip(uid):
    uid = str(uid)
    if uid in db["vip_list"]:
        exp = datetime.datetime.strptime(db["vip_list"][uid], '%Y-%m-%d')
        return datetime.datetime.now() < exp
    return False

# --- [ نظام الدفع التلقائي OxaPay ] ---
def create_auto_payment(uid):
    url = "https://api.oxapay.com/merchants/request"
    data = {
        "merchant": OXAPAY_MERCHANT_KEY,
        "amount": 50,
        "currency": "USDT",
        "lifeTime": 60,
        "feePaidByPayer": 1,
        "description": str(uid),
        "callbackUrl": "https://your-server-link.com/webhook" # ضع رابط السيرفر هنا
    }
    try:
        res = requests.post(url, json=data).json()
        if res.get("result") == 100: return res.get("payLink")
    except: return None

@app.route('/webhook', methods=['POST'])
def payment_webhook():
    data = request.json
    if data and data.get('status') in ['paid', 'confirmed']:
        uid = str(data.get('description'))
        exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        db["vip_list"][uid] = exp; save_db()
        bot.send_message(uid, f"👑 **تم تفعيل اشتراكك التلقائي بنجاح!**\nصالح حتى: {exp}")
    return "OK", 200

# --- [ الواجهات الرئيسية ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"][uid] = {"free_total": 0, "daily_count": 0}
    save_db()
    m_menu = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m_menu.add("🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي")
    bot.send_message(uid, "🏛 **رادار القابضة V1400**\nأهلاً بك في نظام التداول العالمي.", reply_markup=m_menu)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.chat.id)
    vip = is_vip(uid)
    u_data = db["users"].get(uid, {"free_total": 0, "daily_count": 0})
    count = u_data.get("daily_count", 0) if vip else u_data.get("free_total", 0)
    limit = "6" if vip else "5"
    msg = (f"👤 **بيانات الحساب**\n━━━━━━━━━━━━━━\n🏆 الحالة: **{'👑 VIP' if vip else '🆓 مجاني'}**\n"
           f"🗓 انتهاء الاشتراك: `{db['vip_list'].get(uid, 'غير نشط')}`\n📊 استهلاك اليوم: **{count}/{limit}**\n━━━━━━━━━━━━━━")
    bot.send_message(uid, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔍 المحلل الذكي")
def analysis_gate(m):
    uid = str(m.chat.id)
    u_data = db["users"].get(uid, {"free_total": 0, "daily_count": 0})
    if not is_vip(uid) and u_data.get("free_total", 0) >= 5:
        return bot.send_message(uid, "⚠️ انتهت محاولاتك المجانية.")
    if is_vip(uid) and u_data.get("daily_count", 0) >= 6:
        return bot.send_message(uid, "🚫 اكتملت حصتك اليومية (6/6).")
    msg = bot.send_message(uid, "📝 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, process_analysis)

def process_analysis(m):
    uid = str(m.chat.id)
    if m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي"]: return
    res, symbol = fetch_global_data(m.text)
    if res:
        bot.send_message(uid, res, parse_mode="Markdown")
        if is_vip(uid): db["users"][uid]["daily_count"] += 1
        else: db["users"][uid]["free_total"] += 1
        save_db()
    else: bot.send_message(uid, "❌ العملة غير موجودة.")

@bot.message_handler(func=lambda m: m.text == "👑 اشتراك VIP")
def vip_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ تفعيل تلقائي (فوري)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("📥 تفعيل يدوي (إرسال إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "💎 **باقة VIP الاحترافية (50$)**\nاختر وسيلة الدفع:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def router(call):
    uid = str(call.message.chat.id)
    if call.data == "pay_auto":
        link = create_auto_payment(uid)
        if link: bot.send_message(uid, f"🔗 [اضغط هنا للدفع والتفعيل الفوري]({link})", parse_mode="Markdown")
        else: bot.send_message(uid, "⚠️ عذراً، بوابة الدفع معطلة حالياً.")
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📥 حول **50$ USDT** لـ:\n`{MY_USDT_WALLET}`\nثم أرسل صورة الإيصال.")
    elif call.data.startswith("act_"): # تفعيل المالك (نظام دراجون)
        tid = call.data.split("_")[1]
        exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        db["vip_list"][tid] = exp; save_db()
        bot.send_message(tid, f"👑 تم تفعيل اشتراكك بنجاح حتى: {exp}")
        bot.edit_message_caption(chat_id=OWNER_ID, message_id=call.message.message_id, caption=f"✅ تم تفعيل المشترك {tid}")

@bot.message_handler(content_types=['photo', 'text'])
def handle_support(m):
    uid = str(m.chat.id)
    if m.text and (m.text.startswith('/') or m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي"]): return
    if uid == str(OWNER_ID): return
    if m.content_type == 'photo':
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton(f"✅ تفعيل {uid} (50$)", callback_data=f"act_{uid}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"🖼 إيصال جديد من: `{uid}`", reply_markup=mk)
        bot.send_message(uid, "✅ تم إرسال الإيصال للمراجعة.")
    else: bot.send_message(OWNER_ID, f"📩 رسالة من `{uid}`: {m.text}")

# --- [ محركات التوصيات والوقت ] ---
def run_signals():
    sent = 0
    while True:
        if sent < 6:
            # (منطق جلب التوصيات وإرسالها للـ VIP)
            sent += 1
            time.sleep(3600 * 3)
        time.sleep(600)

if __name__ == "__main__":
    threading.Thread(target=run_signals, daemon=True).start()
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True).start()
    bot.infinity_polling()
