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
DB_FILE = "radar_final_v620.json"

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

# --- [ 3. محرك جلب البيانات الذكي ] ---
def fetch_market_data(symbol):
    s = symbol.upper().replace("#", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # فحص منصتين لضمان استقرار الخدمة
    platforms = [
        (f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100", "Binance 🟡", f"BINANCE:{s}"),
        (f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100", "MEXC 🟢", f"MEXC:{s}")
    ]
    
    for url, ex_name, tv_sym in platforms:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # ضبط الأعمدة حسب اختلاف المنصة
                cols = ['t','o','h','l','c','v','ct','q','n','tb','tq','i'] if "binance" in url else ['t','o','h','l','c','v','ct','q']
                df = pd.DataFrame(data, columns=cols[:len(data[0])]).astype(float)
                return df, s, ex_name, f"https://www.tradingview.com/chart/?symbol={tv_sym}"
        except: continue
    return None, s, None, None

def calculate_params(df):
    cp = df['c'].iloc[-1]
    ema = df['c'].ewm(span=20).mean().iloc[-1]
    side = "LONG 🚀" if cp > ema else "SHORT 📉"
    # أهداف احترافية بناءً على السعر
    tp1, tp2 = (cp * 1.025, cp * 1.05) if side == "LONG 🚀" else (cp * 0.975, cp * 0.95)
    sl = df['l'].iloc[-15:].min() * 0.985 if side == "LONG 🚀" else df['h'].iloc[-15:].max() * 1.015
    return side, cp, round(tp1, 4), round(tp2, 4), round(sl, 4)

# --- [ 4. نظام الـ VIP والصلاحية الشهرية ] ---
def is_vip(uid):
    uid = str(uid)
    if uid in db["vip_list"]:
        expiry = datetime.datetime.strptime(db["vip_list"][uid], '%Y-%m-%d')
        if datetime.datetime.now() < expiry: return True
        else:
            del db["vip_list"][uid]
            save_db()
    return False

# --- [ 5. الدفع التلقائي ومعالجة الـ Callback ] ---
@app.route('/payment/callback', methods=['POST'])
def payment_callback():
    data = request.json
    if data and data.get('status') in ['paid', 'confirmed']:
        uid = str(data.get('description'))
        expiry_date = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        db["vip_list"][uid] = expiry_date
        save_db()
        try: bot.send_message(uid, f"👑 **تهانينا! تم تفعيل اشتراكك تلقائياً لمدة شهر.**\nينتهي في: {expiry_date}")
        except: pass
    return "OK", 200

# --- [ 6. واجهة المستخدم والأزرار ] ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔍 المحلل الذكي", "👑 تفعيل الـ VIP (50$)", "👤 حسابي", "📞 الدعم")
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"][uid] = {"free_count": 0}
    save_db()
    bot.send_message(m.chat.id, "🏛 **إمبراطورية رادار القابضة V620**\nجاهزون لصيد أقوى الفرص.", reply_markup=main_menu())

# --- [ 7. المحلل الذكي (العداد المجاني 5 مرات) ] ---
@bot.message_handler(func=lambda m: m.text == "🔍 المحلل الذكي")
def analysis_gate(m):
    uid = str(m.chat.id)
    count = db["users"].get(uid, {}).get("free_count", 0)
    
    if not is_vip(uid) and count >= 5:
        return bot.send_message(uid, "⚠️ انتهت محاولاتك المجانية (5/5).\nالرجاء تفعيل الـ VIP للتحليل غير المحدود.")
    
    msg = bot.send_message(uid, f"📝 أرسل رمز العملة (تحليلاتك: {count}/5):" if not is_vip(uid) else "📝 أرسل رمز العملة:")
    bot.register_next_step_handler(msg, process_analysis)

def process_analysis(m):
    uid = str(m.chat.id)
    if m.text in ["🔍 المحلل الذكي", "👑 تفعيل الـ VIP (50$)", "👤 حسابي", "📞 الدعم"]: return
    
    df, fs, ex, chart = fetch_market_data(m.text)
    if df is not None:
        side, entry, tp1, tp2, sl = calculate_params(df)
        msg = (f"🏛 **نتائج تحليل {ex}**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: #{fs}\n📊 الإشارة: **{side}**\n\n"
               f"📥 الدخول: `{entry}`\n🎯 هدف 1: `{tp1}`\n🎯 هدف 2: `{tp2}`\n🛑 الوقف: `{sl}`\n"
               f"━━━━━━━━━━━━━━\n📈 [عرض الشارت المباشر]({chart})")
        bot.send_message(uid, msg, parse_mode="Markdown", disable_web_page_preview=False)
        if not is_vip(uid):
            db["users"][uid]["free_count"] += 1
            save_db()
    else: bot.send_message(uid, "❌ لم يتم العثور على العملة المطلوبة.")

# --- [ 8. نظام الدعم الآمن وإيصالات الدفع ] ---
@bot.message_handler(func=lambda m: m.text == "📞 الدعم")
def support_info(m):
    bot.send_message(m.chat.id, "👋 قسم الدعم الفني:\nأرسل رسالتك أو صورة إيصال الدفع هنا مباشرة.")

@bot.message_handler(content_types=['photo', 'text'])
def support_logic(m):
    uid = str(m.chat.id)
    # حماية الأوامر من تداخل الدعم
    if m.text and (m.text.startswith('/') or m.text in ["🔍 المحلل الذكي", "👑 تفعيل الـ VIP (50$)", "👤 حسابي", "📞 الدعم"]): return
    if uid == str(OWNER_ID): return

    if m.content_type == 'photo':
        bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
        bot.send_message(OWNER_ID, f"🖼 **إيصال دفع جديد:**\nمن: `{uid}`\nللتفعيل أرسل: `/activate {uid}`")
        bot.send_message(uid, "✅ تم إرسال الإيصال للإدارة للمراجعة.")
    else:
        bot.send_message(OWNER_ID, f"📩 **رسالة من:** `{uid}`\n{m.text}")
        bot.send_message(uid, "✅ وصلت رسالتك للدعم.")

# --- [ 9. أوامر الإدارة ] ---
@bot.message_handler(commands=['activate'])
def manual_act(m):
    if m.chat.id == OWNER_ID:
        try:
            target = m.text.split()[1]
            exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            db["vip_list"][target] = exp
            save_db()
            bot.send_message(target, f"👑 **تم تفعيل الـ VIP لمدة شهر!**\nينتهي في: {exp}")
            bot.send_message(OWNER_ID, f"✅ تم تفعيل {target}")
        except: bot.send_message(OWNER_ID, "⚠️ أرسل: `/activate ID`")

# --- [ 10. رادار التوصيات التلقائي (6 توصيات) ] ---
def auto_radar_engine():
    sent_count = 0
    curr_day = datetime.datetime.now().day
    while True:
        try:
            now = datetime.datetime.now()
            if now.day != curr_day: sent_count = 0; curr_day = now.day
            
            if sent_count < 6:
                ticker = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
                potential = [i for i in ticker if abs(float(i['priceChangePercent'])) > 1.5 and i['symbol'].endswith("USDT")]
                
                for item in sorted(potential, key=lambda x: abs(float(x['priceChangePercent'])), reverse=True):
                    df, fs, ex, chart = fetch_market_data(item['symbol'])
                    if df is not None:
                        vol = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
                        if vol > 2.8: # سيولة انفجارية
                            side, entry, tp1, tp2, sl = calculate_params(df)
                            msg = (f"💎 **توصية VIP آلية ({sent_count+1}/6)**\n━━━━━━━━━━━━━━\n"
                                   f"🪙 العملة: #{fs} | {ex}\n🔥 سيولة: `{round(vol, 2)}x`\n\n"
                                   f"📥 الدخول: `{entry}`\n🎯 هدف 1: `{tp1}`\n🎯 هدف 2: `{tp2}`\n🛑 الوقف: `{sl}`\n"
                                   f"━━━━━━━━━━━━━━\n📈 [عرض الشارت المباشر]({chart})")
                            
                            for v_id in list(db["vip_list"].keys()):
                                if is_vip(v_id):
                                    try: bot.send_message(v_id, msg, parse_mode="Markdown")
                                    except: pass
                            sent_count += 1
                            time.sleep(3600 * 3) # فاصل 3 ساعات
                            break
            time.sleep(600)
        except: time.sleep(30)

# --- [ 11. معلومات الحساب والدفع ] ---
@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.chat.id)
    status = "👑 VIP" if is_vip(uid) else "🆓 مجاني"
    exp = db["vip_list"].get(uid, "غير نشط")
    count = db["users"].get(uid, {}).get("free_count", 0)
    bot.send_message(uid, f"👤 **بيانات حسابك:**\n━━━━━━━━━━━━━━\n🏆 الحالة: {status}\n🗓 تاريخ الانتهاء: {exp}\n📊 التحليل المجاني المستهلك: {count}/5\n━━━━━━━━━━━━━━")

@bot.message_handler(func=lambda m: m.text == "👑 تفعيل الـ VIP (50$)")
def vip_menu(m):
    mk = types.InlineKeyboardMarkup()
    # رابط OxaPay (استبدل بـ رابطك)
    mk.add(types.InlineKeyboardButton("⚡ دفع تلقائي (OxaPay)", url=f"https://oxapay.com/pay/50/USDT/{m.chat.id}"))
    mk.add(types.InlineKeyboardButton("📥 دفع يدوي (تحويل)", callback_data="manual_p"))
    bot.send_message(m.chat.id, "💎 **مميزات VIP الإمبراطورية:**\n\n✅ 6 توصيات آلية بدقة عالية.\n✅ تحليل غير محدود.\n✅ دعم فني مباشر.\n\nاختر وسيلة الدفع (50$ USDT):", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data == "manual_p")
def manual_p(call):
    bot.send_message(call.message.chat.id, f"📥 حول **50$** USDT (TRC20) لـ:\n`{MY_USDT_WALLET}`\n\nثم أرسل صورة الإيصال هنا.")

@app.route('/')
def home(): return "Radar Online 🏛"

if __name__ == "__main__":
    threading.Thread(target=auto_radar_engine, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
