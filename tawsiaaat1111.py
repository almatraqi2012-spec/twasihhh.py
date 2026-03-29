import requests, telebot, time, json, os, threading, datetime
import pandas as pd
from telebot import types
from flask import Flask

# --- [ الإعدادات الكبرى - بياناتك ثابتة ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718 
MY_USDT_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
OXAPAY_MERCHANT_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
DB_FILE = "radar_v2000_final.json"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

@app.route('/')
def index(): return "Radar System is Online & Active 🚀"

# --- [ نظام قاعدة البيانات المطور ] ---
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

# --- [ فحص الـ VIP والمالك ] ---
def is_vip(uid):
    uid = str(uid)
    if int(uid) == OWNER_ID: return True # المالك VIP للأبد
    if uid in db["vip_list"]:
        try:
            exp = datetime.datetime.strptime(db["vip_list"][uid], '%Y-%m-%d')
            if datetime.datetime.now() < exp: return True
            else:
                del db["vip_list"][uid]; save_db()
        except: return False
    return False

# --- [ المحرك التحليلي الخبير ] ---
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
                tp = cp * 1.03 if side == "LONG 🚀" else cp * 0.97
                sl = df[3].iloc[-10:].min() * 0.985 if side == "LONG 🚀" else df[2].iloc[-10:].max() * 1.015
                chart = f"https://www.tradingview.com/chart/?symbol={source.split()[0]}:{s}"
                msg = (f"🏛 **تقرير رادار القابضة الخبير ({source})**\n━━━━━━━━━━━━━━\n"
                       f"🪙 العملة: #{s}\n📊 الإشارة: **{side}**\n\n"
                       f"📥 الدخول: `{cp}`\n🎯 الهدف: `{round(tp,4)}`\n🛑 الوقف: `{round(sl,4)}`\n\n"
                       f"✅ الحالة: {vol_status}\n━━━━━━━━━━━━━━\n"
                       f"📈 [عرض الشارت المباشر]({chart})")
                return msg, s
        except: continue
    return None, None

# --- [ نظام العداد الذكي ] ---
def check_limit(uid):
    uid = str(uid)
    if int(uid) == OWNER_ID: return True, 0 # المالك لا حدود له
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    if uid not in db["users"]: db["users"][uid] = {"count": 0, "last_date": today}
    
    u_data = db["users"][uid]
    if u_data.get("last_date") != today: # تصفير يومي تلقائي
        u_data["count"] = 0
        u_data["last_date"] = today
        save_db()

    limit = 6 if is_vip(uid) else 5
    if u_data["count"] >= limit: return False, limit
    return True, u_data["count"]

# --- [ الواجهات ] ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي")
    return m

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.chat.id)
    check_limit(uid) # لإنشاء بيانات المستخدم
    
    # رسالة ترحيب احترافية ومصلحة برمجياً
    welcome_text = """🏛 **مرحباً بك في المحلل الذكي⚡**

النظام مخصص **فقط** لتحليل أسواق الكريبتو والمضاربة اللحظية:
🔶 منصة **Binance** (بينانس)
🟢 منصة **MEXC** (إم إي إكس سي)

**ماذا يقدم لك الرادار؟**
🎯 تحليل فني دقيق لكل العملات الرقمية.
🔍 رادار لاقتناص السيولة وتقاطعات المؤشرات.
🚫 **تنبيه:** النظام لا يدعم أسواق الفوركس أو الأسهم حالياً.

**أقوى بوت تحليل وتوصيات في خدمتك! 🚀**"""
    
    bot.send_message(uid, welcome_text, reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.chat.id)
    vip = is_vip(uid)
    _, count = check_limit(uid)
    limit = "6" if vip else "5"
    if int(uid) == OWNER_ID: limit = "∞"
    
    msg = (f"👤 **معلومات حسابك**\n━━━━━━━━━━━━━━\n"
           f"🏆 الحالة: **{'👑 VIP' if vip else '🆓 مجاني'}**\n"
           f"📊 استهلاك اليوم: **{count}/{limit}**\n━━━━━━━━━━━━━━")
    bot.send_message(uid, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🔍 المحلل الذكي")
def analysis_gate(m):
    uid = str(m.chat.id)
    allowed, current = check_limit(uid)
    if not allowed:
        return bot.send_message(uid, f"🚫 اكتملت حصتك اليومية ({current}/{current}). انتظر للغد.")
    
    msg = bot.send_message(uid, "📝 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, run_analysis)

def run_analysis(m):
    uid = str(m.chat.id)
    if m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي"]: return
    res, symbol = fetch_expert_analysis(m.text)
    if res:
        bot.send_message(uid, res, parse_mode="Markdown")
        db["users"][uid]["count"] += 1
        save_db()
    else: bot.send_message(uid, "❌ العملة غير مدعومة حالياً.")

@bot.message_handler(func=lambda m: m.text == "👑 اشتراك VIP")
def vip_page(m):
    text = "💎 **عضوية رادار VIP (50$)**\n\n✅ 6 تحليلات خبيرة يومياً.\n✅ توصيات آلية (Binance + MEXC) تصلك فوراً."
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ تفعيل تلقائي (OxaPay)", callback_data="pay_auto"),
           types.InlineKeyboardButton("📥 تفعيل يدوي (إرسال إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, text, reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def handle_calls(call):
    uid = str(call.message.chat.id)
    if call.data == "pay_auto":
        payload = {"merchant": OXAPAY_MERCHANT_KEY, "amount": 50, "currency": "USDT", "description": uid}
        try:
            r = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
            if r.get("result") == 100:
                bot.send_message(uid, f"🔗 [اضغط هنا للدفع والتفعيل]({r.get('payLink')})", parse_mode="Markdown")
        except: bot.send_message(uid, "⚠️ بوابة الدفع غير مستقرة.")
    elif call.data == "pay_manual":
        bot.send_message(uid, f"📥 حول **50$ USDT** لـ:\n`{MY_USDT_WALLET}`\nثم أرسل صورة الإيصال.")
    elif call.data.startswith("dragon_"):
        target_id = call.data.split("_")[1]
        exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        db["vip_list"][target_id] = exp; save_db()
        bot.send_message(target_id, f"👑 **تم تفعيل VIP بنجاح!**\nصالح حتى: {exp}")
        bot.edit_message_caption(chat_id=OWNER_ID, message_id=call.message.message_id, caption=f"✅ تم تفعيل `{target_id}`")

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    uid = str(m.chat.id)
    if int(uid) == OWNER_ID: return
    admin_mk = types.InlineKeyboardMarkup()
    admin_mk.add(types.InlineKeyboardButton(f"✅ تفعيل {uid}", callback_data=f"dragon_{uid}"))
    bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"🖼 إيصال جديد من `{uid}`", reply_markup=admin_mk)
    bot.send_message(uid, "✅ تم إرسال الإيصال للمراجعة.")

# --- [ محرك التوصيات الـ 6 (إصلاح شامل) ] ---
def recommendation_loop():
    print("🚀 محرك التوصيات انطلق...")
    sent_count = 0
    last_reset = datetime.datetime.now().day
    while True:
        try:
            now = datetime.datetime.now()
            if now.day != last_reset: sent_count = 0; last_reset = now.day
            
            if sent_count < 6:
                ticker = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
                top_movers = sorted(ticker, key=lambda x: float(x['priceChangePercent']), reverse=True)[:10]
                for item in top_movers:
                    res, s = fetch_expert_analysis(item['symbol'])
                    if res:
                        vips = [u for u in db["vip_list"] if is_vip(u)]
                        vips.append(str(OWNER_ID))
                        for v_id in set(vips):
                            try: bot.send_message(v_id, f"💎 **توصية VIP حقيقية ({sent_count+1}/6)**\n" + res, parse_mode="Markdown")
                            except: pass
                        sent_count += 1
                        time.sleep(14400) # إرسال توصية كل 4 ساعات لتغطية اليوم
                        break
            time.sleep(600)
        except Exception as e:
            print(f"Error in loop: {e}"); time.sleep(60)

# --- [ التشغيل النهائي ] ---
if __name__ == "__main__":
    threading.Thread(target=recommendation_loop, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=port), daemon=True).start()
    
    print(f"📡 Radar V2000 is LIVE on Port {port}")
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
