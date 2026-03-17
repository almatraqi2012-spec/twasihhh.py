import requests, telebot, time, json, os, threading, datetime
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ الإعدادات الكبرى ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" # مفتاح التاجر الخاص بك
MY_USDT_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v1500_master.json"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ إدارة البيانات ] ---
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

# --- [ محرك التحليل الخبير ] ---
def expert_analysis(symbol):
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
                ema50 = df[4].ewm(span=50).mean().iloc[-1]
                vol_status = "مرتفعة 🔥" if df[5].iloc[-1] > df[5].rolling(20).mean().iloc[-1] else "مستقرة ⚖️"
                
                # منطق التحليل الفني
                side = "LONG 🚀" if cp > ema20 else "SHORT 📉"
                reason = "اختراق متوسط 20 وتدفق سيولة" if side == "LONG 🚀" else "كسر متوسط 20 وضغط بيعي"
                
                tp = cp * 1.03 if side == "LONG 🚀" else cp * 0.97
                sl = df[3].iloc[-10:].min() * 0.99 if side == "LONG 🚀" else df[2].iloc[-10:].max() * 1.01
                chart = f"https://www.tradingview.com/chart/?symbol={source.split()[0]}:{s}"
                
                text = (f"🏛 **تقرير رادار القابضة الفني ({source})**\n━━━━━━━━━━━━━━\n"
                        f"🪙 العملة: #{s}\n📊 الإشارة: **{side}**\n\n"
                        f"📥 سعر الدخول: `{cp}`\n🎯 الهدف المتوقع: `{round(tp,4)}`\n🛑 وقف الخسارة: `{round(sl,4)}`\n\n"
                        f"🔍 **لماذا هذه الصفقة؟**\n"
                        f"✅ الحالة: {reason}\n"
                        f"✅ السيولة الحالية: {vol_status}\n"
                        f"✅ الاتجاه: بناءً على تقاطع المتوسطات الأسيّة.\n━━━━━━━━━━━━━━\n"
                        f"📈 [مشاهدة الشارت المباشر من هنا]({chart})")
                return text, s
        except: continue
    return None, None

def is_vip(uid):
    uid = str(uid)
    if uid in db["vip_list"]:
        exp = datetime.datetime.strptime(db["vip_list"][uid], '%Y-%m-%d')
        return datetime.datetime.now() < exp
    return False

# --- [ واجهات الأزرار ] ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"][uid] = {"free_total": 0, "daily_count": 0}
    save_db()
    bot.send_message(uid, "🏛 **مرحباً بك في رادار القابضة V1500**\nنظام التحليل الخبير (Binance + MEXC).", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.chat.id)
    vip = is_vip(uid)
    u_data = db["users"].get(uid, {"free_total": 0, "daily_count": 0})
    count = u_data.get("daily_count", 0) if vip else u_data.get("free_total", 0)
    msg = (f"👤 **بيانات الحساب**\n━━━━━━━━━━━━━━\n🏆 الحالة: **{'👑 VIP' if vip else '🆓 مجاني'}**\n"
           f"🗓 انتهاء الاشتراك: `{db['vip_list'].get(uid, 'غير نشط')}`\n📊 استهلاك اليوم: **{count}/{'6' if vip else '5'}**\n━━━━━━━━━━━━━━")
    bot.send_message(uid, msg, parse_mode="Markdown")

# --- [ المحلل الذكي ] ---
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
    res, symbol = expert_analysis(m.text)
    if res:
        bot.send_message(uid, res, parse_mode="Markdown", disable_web_page_preview=False)
        if is_vip(uid): db["users"][uid]["daily_count"] += 1
        else: db["users"][uid]["free_total"] += 1
        save_db()
    else: bot.send_message(uid, "❌ العملة غير موجودة.")

# --- [ نظام التفعيل المزدوج (تلقائي + دراجون) ] ---
@bot.message_handler(func=lambda m: m.text == "👑 اشتراك VIP")
def vip_menu(m):
    text = "💎 **عضوية VIP الاحترافية (50$)**\n- 6 تحليلات خبيرة يومياً.\n- 6 توصيات آلية مع الشارت.\n- تفعيل فوري."
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ تفعيل تلقائي (فوري)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("📥 تفعيل يدوي (إرسال إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, text, reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def query_router(call):
    uid = str(call.message.chat.id)
    if call.data == "pay_auto":
        # طلب رابط دفع من OxaPay
        r = requests.post("https://api.oxapay.com/merchants/request", json={"merchant": OXAPAY_KEY, "amount": 50, "currency": "USDT", "description": uid}).json()
        if r.get("result") == 100: bot.send_message(uid, f"🔗 [اضغط هنا للدفع الفوري]({r.get('payLink')})", parse_mode="Markdown")
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📥 حول **50$ USDT** لـ:\n`{MY_USDT_WALLET}`\nثم أرسل صورة الإيصال.")
    elif call.data.startswith("confirm_"):
        tid = call.data.split("_")[1]
        exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        db["vip_list"][tid] = exp; save_db()
        bot.send_message(tid, f"👑 تم تفعيل اشتراكك! صالح حتى: {exp}")
        bot.edit_message_caption(chat_id=OWNER_ID, message_id=call.message.message_id, caption=f"✅ تم تفعيل {tid}")

# --- [ نظام دراجون: استقبال الإيصالات ] ---
@bot.message_handler(content_types=['photo', 'text'])
def support_logic(m):
    uid = str(m.chat.id)
    if m.text and (m.text.startswith('/') or m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي"]): return
    if uid == str(OWNER_ID): return
    if m.content_type == 'photo':
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton(f"✅ تفعيل {uid} (50$)", callback_data=f"confirm_{uid}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"🖼 إيصال جديد من: `{uid}`", reply_markup=mk)
        bot.send_message(uid, "✅ تم إرسال الإيصال للمالك.")
    else: bot.send_message(OWNER_ID, f"📩 رسالة من `{uid}`: {m.text}")

# --- [ محرك التوصيات الـ 6 (خلفية) ] ---
def auto_signals():
    sent = 0
    last_day = datetime.datetime.now().day
    while True:
        try:
            now = datetime.datetime.now()
            if now.day != last_day: sent = 0; last_day = now.day
            if sent < 6:
                ticker = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
                for item in sorted(ticker, key=lambda x: abs(float(x['priceChangePercent'])), reverse=True)[:10]:
                    res, s = expert_analysis(item['symbol'])
                    if res:
                        msg = f"💎 **توصية VIP إمبراطورية ({sent+1}/6)**\n" + res
                        for v_id in list(db["vip_list"].keys()):
                            if is_vip(v_id): bot.send_message(v_id, msg, parse_mode="Markdown")
                        sent += 1
                        time.sleep(3600 * 3) # توزيع التوصيات
                        break
            time.sleep(900)
        except: time.sleep(30)

def reset_limits():
    while True:
        now = datetime.datetime.now()
        if now.hour == 0 and now.minute == 0:
            for u in db["users"]: db["users"][u]["daily_count"] = 0
            save_db()
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=auto_signals, daemon=True).start()
    threading.Thread(target=reset_limits, daemon=True).start()
    bot.infinity_polling()
