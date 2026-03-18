import requests, telebot, time, json, os, threading, datetime
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ الإعدادات الكبرى - ضع بياناتك هنا ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718 
MY_USDT_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
# ⬇️ مفتاح التاجر (Merchant Key) الخاص بـ OxaPay
OXAPAY_MERCHANT_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
DB_FILE = "radar_v2000_final.json"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)
@app.route('/')
def index():
    return "Radar System is Online & Active 🚀"
# --- [ نظام قاعدة البيانات ] ---
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

# --- [ المحرك التحليلي الخبير (Binance + MEXC) ] ---
def fetch_expert_analysis(symbol):
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
                cp = df[4].iloc[-1]
                ema20 = df[4].ewm(span=20).mean().iloc[-1]
                vol_status = "انفجار سيولة 🔥" if df[5].iloc[-1] > df[5].rolling(20).mean().iloc[-1] * 1.5 else "سيولة مستقرة ⚖️"
                
                side = "LONG 🚀" if cp > ema20 else "SHORT 📉"
                reason = "السعر يتداول فوق المتوسطات مع زخم شرائي" if side == "LONG 🚀" else "ضغط بيعي وكسر مستويات الدعم"
                
                tp = cp * 1.03 if side == "LONG 🚀" else cp * 0.97
                sl = df[3].iloc[-10:].min() * 0.985 if side == "LONG 🚀" else df[2].iloc[-10:].max() * 1.015
                chart = f"https://www.tradingview.com/chart/?symbol={source.split()[0]}:{s}"
                
                msg = (f"🏛 **تقرير رادار القابضة الخبير ({source})**\n━━━━━━━━━━━━━━\n"
                       f"🪙 العملة: #{s}\n📊 الإشارة: **{side}**\n\n"
                       f"📥 الدخول: `{cp}`\n🎯 الهدف: `{round(tp,4)}`\n🛑 الوقف: `{round(sl,4)}`\n\n"
                       f"🔍 **لماذا هذه الصفقة؟**\n"
                       f"✅ السبب: {reason}\n"
                       f"✅ الحالة: {vol_status}\n━━━━━━━━━━━━━━\n"
                       f"📈 [عرض الشارت المباشر]({chart})")
                return msg, s
        except: continue
    return None, None

def is_vip(uid):
    uid = str(uid)
    if uid in db["vip_list"]:
        exp = datetime.datetime.strptime(db["vip_list"][uid], '%Y-%m-%d')
        if datetime.datetime.now() < exp: return True
        else:
            del db["vip_list"][uid]; save_db()
    return False

# --- [ واجهات الأزرار ] ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي")
    return m

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"][uid] = {"free_total": 0, "daily_count": 0}
    save_db()
    bot.send_message(uid, "🏛 **مرحباً بك في رادار القابضة V2000**\nأقوى بوت تحليل وتوصيات في الشرق الأوسط.", reply_markup=main_menu())

# --- [ زر حسابي الشغال ] ---
@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.chat.id)
    vip = is_vip(uid)
    u_data = db["users"].get(uid, {"free_total": 0, "daily_count": 0})
    count = u_data.get("daily_count", 0) if vip else u_data.get("free_total", 0)
    limit = "6" if vip else "5"
    
    msg = (f"👤 **معلومات حسابك**\n━━━━━━━━━━━━━━\n"
           f"🏆 الحالة: **{'👑 VIP' if vip else '🆓 مجاني'}**\n"
           f"🗓 الانتهاء: `{db['vip_list'].get(uid, 'لا يوجد')}`\n"
           f"📊 استهلاك اليوم: **{count}/{limit}**\n━━━━━━━━━━━━━━")
    bot.send_message(uid, msg, parse_mode="Markdown")

# --- [ المحلل الذكي (نظام 6/6) ] ---
@bot.message_handler(func=lambda m: m.text == "🔍 المحلل الذكي")
def analysis_gate(m):
    uid = str(m.chat.id)
    u_data = db["users"].get(uid, {"free_total": 0, "daily_count": 0})
    if not is_vip(uid) and u_data.get("free_total", 0) >= 5:
        return bot.send_message(uid, "⚠️ انتهت محاولاتك المجانية (5/5).")
    if is_vip(uid) and u_data.get("daily_count", 0) >= 6:
        return bot.send_message(uid, "🚫 اكتملت حصتك اليومية (6/6). انتظر للغد.")
    
    msg = bot.send_message(uid, "📝 أرسل رمز العملة (مثال: SOL):")
    bot.register_next_step_handler(msg, run_analysis)

def run_analysis(m):
    uid = str(m.chat.id)
    if m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي"]: return
    res, symbol = fetch_expert_analysis(m.text)
    if res:
        bot.send_message(uid, res, parse_mode="Markdown")
        if is_vip(uid): db["users"][uid]["daily_count"] += 1
        else: db["users"][uid]["free_total"] += 1
        save_db()
    else: bot.send_message(uid, "❌ العملة غير مدعومة حالياً.")

# --- [ نظام الاشتراك VIP المزدوج ] ---
@bot.message_handler(func=lambda m: m.text == "👑 اشتراك VIP")
def vip_page(m):
    text = "💎 **عضوية رادار VIP (50$)**\n\n✅ 6 تحليلات خبيرة يومياً.\n✅ 6 توصيات آلية تصلك للخاص.\n✅ تحليل (Binance + MEXC)."
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ تفعيل تلقائي (OxaPay)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("📥 تفعيل يدوي (إرسال إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, text, reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    uid = str(call.message.chat.id)
    
    if call.data == "pay_auto":
        # استخدام مفتاح التاجر لإنشاء رابط دفع
        payload = {"merchant": OXAPAY_MERCHANT_KEY, "amount": 50, "currency": "USDT", "description": uid}
        try:
            r = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
            if r.get("result") == 100:
                bot.send_message(uid, f"🔗 [اضغط هنا للدفع الفوري والتفعيل]({r.get('payLink')})", parse_mode="Markdown")
        except: bot.send_message(uid, "⚠️ عذراً، بوابة الدفع غير مستقرة حالياً.")
        
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📥 حول **50$ USDT** لـ:\n`{MY_USDT_WALLET}`\nثم أرسل صورة الإيصال هنا.")
        
    elif call.data.startswith("dragon_"): # نظام دراجون للتفعيل
        target_id = call.data.split("_")[1]
        exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        db["vip_list"][target_id] = exp; save_db()
        bot.send_message(target_id, f"👑 **تم تفعيل VIP بنجاح!**\nصالح حتى: {exp}")
        bot.edit_message_caption(chat_id=OWNER_ID, message_id=call.message.message_id, caption=f"✅ تم تفعيل المشترك `{target_id}`")

# --- [ استقبال الإيصالات (المالك) ] ---
@bot.message_handler(content_types=['photo', 'text'])
def handle_all(m):
    uid = str(m.chat.id)
    if m.text and (m.text.startswith('/') or m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي"]): return
    if uid == str(OWNER_ID): return
    
    if m.content_type == 'photo':
        admin_mk = types.InlineKeyboardMarkup()
        admin_mk.add(types.InlineKeyboardButton(f"✅ تفعيل {uid} (50$)", callback_data=f"dragon_{uid}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"🖼 إيصال جديد من `{uid}`", reply_markup=admin_mk)
        bot.send_message(uid, "✅ تم إرسال الإيصال، انتظر التفعيل الفوري.")
    else:
        bot.send_message(OWNER_ID, f"📩 رسالة دعم من `{uid}`: {m.text}")

# --- [ محرك التوصيات الـ 6 والإنعاش ] ---
def recommendation_loop():
    sent_today = 0
    last_day = datetime.datetime.now().day
    while True:
        try:
            now = datetime.datetime.now()
            if now.day != last_day: sent_today = 0; last_day = now.day
            if sent_today < 6:
                ticker = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
                for item in sorted(ticker, key=lambda x: abs(float(x['priceChangePercent'])), reverse=True)[:10]:
                    res, s = fetch_expert_analysis(item['symbol'])
                    if res:
                        vips = [u for u in db["vip_list"] if is_vip(u)]
                        for v_id in vips:
                            try: bot.send_message(v_id, f"💎 **توصية VIP ({sent_today+1}/6)**\n" + res, parse_mode="Markdown")
                            except: pass
                        sent_today += 1
                        time.sleep(10800) # توصية كل 3 ساعات
                        break
            time.sleep(600)
        except: time.sleep(60)

def reset_daily_usage():
    while True:
        now = datetime.datetime.now()
        if now.hour == 0 and now.minute == 0:
            for u in db["users"]: db["users"][u]["daily_count"] = 0
            save_db()
        time.sleep(60)


# تأكد أن هذا الجزء في نهاية الملف تماماً
if __name__ == "__main__":
    # 1. تشغيل خيط التوصيات التلقائية
    threading.Thread(target=auto_signals_engine, daemon=True).start()
    
    # 2. تشغيل خيط تصفير العداد اليومي
    threading.Thread(target=reset_limits, daemon=True).start()
    
    # 3. جلب المنفذ من نظام Render (إجباري لـ Web Service)
    port = int(os.environ.get("PORT", 10000))
    
    # 4. تشغيل Flask (الرسيفر) في خيط مستقل
    # هذا هو السطر الذي سيجعل UptimeRobot يعطيك Up (أخضر)
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    print(f"📡 Radar System is LIVE on Port: {port}")
    
    # 5. تشغيل البوت الأساسي (يجب أن يكون الأخير دائماً)
    bot.infinity_polling()
