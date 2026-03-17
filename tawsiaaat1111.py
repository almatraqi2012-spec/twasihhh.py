import requests, telebot, time, json, os, threading, datetime
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والتحصين ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_USDT_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" 
WEBHOOK_URL = "https://tawsiaaat1111.onrender.com" 
DB_FILE = "radar_empire_v1000.json"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. إدارة قاعدة البيانات ] ---
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

# --- [ 3. محرك الجلب والتحليل الفني ] ---
def fetch_market_data(symbol):
    s = symbol.upper().replace("#", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # فحص المنصات لضمان الدقة (بينانس ومكسيك)
    platforms = [
        (f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100", "Binance 🟡"),
        (f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100", "MEXC 🟢")
    ]
    
    for url, name in platforms:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # تنسيق البيانات
                cols = ['t','o','h','l','c','v','ct','q','n','tb','tq','i'] if "binance" in url else ['t','o','h','l','c','v','ct','q']
                df = pd.DataFrame(data, columns=cols[:len(data[0])]).astype(float)
                return df, s, name, f"https://www.tradingview.com/chart/?symbol={name.split()[0]}:{s}"
        except: continue
    return None, s, None, None

def calculate_logic(df):
    cp = df['c'].iloc[-1]
    ema = df['c'].ewm(span=20).mean().iloc[-1]
    side = "LONG 🚀" if cp > ema else "SHORT 📉"
    # حساب الأهداف (2.5% و 5%)
    tp1 = cp * 1.025 if side == "LONG 🚀" else cp * 0.975
    tp2 = cp * 1.05 if side == "LONG 🚀" else cp * 0.95
    sl = df['l'].iloc[-15:].min() * 0.985 if side == "LONG 🚀" else df['h'].iloc[-15:].max() * 1.015
    return side, cp, round(tp1, 4), round(tp2, 4), round(sl, 4)

# --- [ 4. نظام الصلاحية VIP ] ---
def is_vip(uid):
    uid = str(uid)
    if uid in db["vip_list"]:
        expiry = datetime.datetime.strptime(db["vip_list"][uid], '%Y-%m-%d')
        if datetime.datetime.now() < expiry: return True
        else:
            del db["vip_list"][uid]; save_db()
    return False

# --- [ 5. واجهات الأزرار ] ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي", "📞 الدعم الفني")
    return m

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.chat.id)
    if uid not in db["users"]:
        db["users"][uid] = {"free_total": 0, "daily_count": 0}
    save_db()
    bot.send_message(uid, "🏛 **مرحباً بك في رادار القابضة V1000**\nأقوى بوت تحليل وتوصيات عالمي.", reply_markup=main_menu())

# --- [ 6. المحلل الذكي (التحكم 6/6) ] ---
@bot.message_handler(func=lambda m: m.text == "🔍 المحلل الذكي")
def analysis_gate(m):
    uid = str(m.chat.id)
    u_data = db["users"].get(uid, {"free_total": 0, "daily_count": 0})
    
    if not is_vip(uid):
        if u_data.get("free_total", 0) >= 5:
            return bot.send_message(uid, "⚠️ انتهت محاولاتك المجانية (5/5).\nيرجى تفعيل VIP للتحليل اليومي (6 عملات).")
    else:
        if u_data.get("daily_count", 0) >= 6:
            return bot.send_message(uid, "🚫 **اكتملت حصتك اليومية (6/6)**\nانتظر حتى الغد لتتمكن من التحليل مجدداً.")

    msg = bot.send_message(uid, "📝 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, run_analysis_process)

def run_analysis_process(m):
    uid = str(m.chat.id)
    if m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي", "📞 الدعم الفني"]: return
    
    df, fs, ex, chart = fetch_market_data(m.text)
    if df is not None:
        side, entry, tp1, tp2, sl = calculate_logic(df)
        res = (f"🏛 **نتائج تحليل رادار {ex}**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: #{fs}\n📊 الإشارة: **{side}**\n\n"
               f"📥 الدخول: `{entry}`\n🎯 هدف 1: `{tp1}`\n🎯 هدف 2: `{tp2}`\n🛑 الوقف: `{sl}`\n"
               f"━━━━━━━━━━━━━━\n📈 [عرض الشارت المباشر]({chart})")
        bot.send_message(uid, res, parse_mode="Markdown")
        
        # تحديث العداد
        if is_vip(uid): db["users"][uid]["daily_count"] += 1
        else: db["users"][uid]["free_total"] += 1
        save_db()
    else: bot.send_message(uid, "❌ لم يتم العثور على العملة.")

# --- [ 7. نظام اشتراك VIP والدفع ] ---
@bot.message_handler(func=lambda m: m.text == "👑 اشتراك VIP")
def vip_page(m):
    text = (f"💎 **مميزات اشتراك VIP الإمبراطوري:**\n\n"
            f"✅ 6 تحليلات يدوية دقيقة يومياً.\n"
            f"✅ 6 توصيات آلية تصلك للخاص.\n"
            f"✅ دعم فني ذو أولوية.\n"
            f"✅ صلاحية لمدة 30 يوم.\n\n"
            f"💰 السعر: **50$ USDT**")
    
    mk = types.InlineKeyboardMarkup(row_width=1)
    # التفعيل التلقائي
    pay_url = f"https://oxapay.com/pay/50/USDT/{m.chat.id}"
    mk.add(types.InlineKeyboardButton("⚡ تفعيل تلقائي (OxaPay)", url=pay_url))
    # التفعيل اليدوي
    mk.add(types.InlineKeyboardButton("📥 تفعيل يدوي (إرسال إيصال)", callback_data="manual_pay"))
    
    bot.send_message(m.chat.id, text, reply_markup=mk, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = str(call.message.chat.id)
    if call.data == "manual_pay":
        msg = (f"📥 **قسم التفعيل اليدوي**\n\n"
               f"حول 50$ USDT (TRC20) للمحفظة:\n`{MY_USDT_WALLET}`\n\n"
               f"ثم أرسل **صورة الإيصال** هنا في الشات.")
        bot.send_message(uid, msg, parse_mode="Markdown")

# --- [ 8. استقبال الصور (الإيصالية) والدعم ] ---
@bot.message_handler(content_types=['photo', 'text'])
def central_handler(m):
    uid = str(m.chat.id)
    if m.text and (m.text.startswith('/') or m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي", "📞 الدعم الفني"]): return
    if uid == str(OWNER_ID): return

    if m.content_type == 'photo':
        bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
        bot.send_message(OWNER_ID, f"🖼 **إيصال جديد!**\nالآيدي: `{uid}`\nللتفعيل: `/activate {uid}`")
        bot.send_message(uid, "✅ تم إرسال الإيصال للمراجعة، انتظر التفعيل.")
    else:
        bot.send_message(OWNER_ID, f"📩 رسالة دعم من `{uid}`: {m.text}")
        bot.send_message(uid, "✅ تم إرسال رسالتك لفريق الدعم.")

# --- [ 9. رادار التوصيات التلقائية الـ 6 ] ---
def recommendation_engine():
    sent_today = 0
    last_day = datetime.datetime.now().day
    while True:
        try:
            now = datetime.datetime.now()
            if now.day != last_day: sent_today = 0; last_day = now.day
            
            if sent_today < 6:
                ticker = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
                # فرز العملات الأكثر صعوداً/هبوطاً بسيولة عالية
                potential = [i for i in ticker if abs(float(i['priceChangePercent'])) > 2.0 and i['symbol'].endswith("USDT")]
                for item in sorted(potential, key=lambda x: abs(float(x['priceChangePercent'])), reverse=True):
                    df, fs, ex, chart = fetch_market_data(item['symbol'])
                    if df is not None:
                        vol = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
                        if vol > 3.0: # شرط السيولة القوية
                            side, entry, tp1, tp2, sl = calculate_logic(df)
                            msg = (f"💎 **توصية VIP آلية ({sent_today+1}/6)**\n━━━━━━━━━━━━━━\n"
                                   f"🪙 العملة: #{fs} | {ex}\n📊 الإشارة: **{side}**\n\n"
                                   f"📥 الدخول: `{entry}`\n🎯 هدف 1: `{tp1}`\n🎯 هدف 2: `{tp2}`\n🛑 الوقف: `{sl}`\n"
                                   f"━━━━━━━━━━━━━━\n📈 [عرض الشارت]({chart})")
                            
                            for v_id in list(db["vip_list"].keys()):
                                if is_vip(v_id):
                                    try: bot.send_message(v_id, msg, parse_mode="Markdown")
                                    except: pass
                            sent_today += 1
                            time.sleep(3600 * 2.5) # فاصل زمني بين كل توصية
                            break
            time.sleep(900)
        except: time.sleep(30)

# --- [ 10. الإدارة والتشغيل ] ---
@bot.message_handler(commands=['activate'])
def manual_activation(m):
    if m.chat.id == OWNER_ID:
        try:
            target = m.text.split()[1]
            exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            db["vip_list"][target] = exp; save_db()
            bot.send_message(target, f"👑 **تم تفعيل VIP بنجاح!**\nصلاحية لمدة شهر حتى: {exp}")
            bot.send_message(OWNER_ID, f"✅ تم تفعيل {target}")
        except: bot.send_message(OWNER_ID, "⚠️ استخدم: `/activate ID`")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.chat.id)
    u = db["users"].get(uid, {})
    status = "👑 VIP" if is_vip(uid) else "🆓 مجاني"
    daily = u.get("daily_count", 0) if is_vip(uid) else u.get("free_total", 0)
    limit = "6" if is_vip(uid) else "5"
    bot.send_message(uid, f"👤 **بيانات حسابك:**\n🏆 الحالة: {status}\n🗓 الاستهلاك: {daily}/{limit}")

@bot.message_handler(func=lambda m: m.text == "📞 الدعم الفني")
def support_page(m):
    bot.send_message(m.chat.id, "👋 أرسل استفسارك وسيرد عليك الفريق فوراً.")

def daily_reset_loop():
    while True:
        now = datetime.datetime.now()
        if now.hour == 0 and now.minute == 0:
            for u in db["users"]: db["users"][u]["daily_count"] = 0
            save_db()
        time.sleep(60)

@app.route('/payment/callback', methods=['POST'])
def payment_callback():
    data = request.json
    if data and data.get('status') in ['paid', 'confirmed']:
        uid = str(data.get('description'))
        exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        db["vip_list"][uid] = exp; save_db()
        bot.send_message(uid, f"👑 تم تفعيل اشتراكك التلقائي بنجاح!")
    return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=recommendation_engine, daemon=True).start()
    threading.Thread(target=daily_reset_loop, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
