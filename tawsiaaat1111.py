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
DB_FILE = "radar_empire_mega_v600.json"

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

# --- [ 3. محرك جلب البيانات المزدوج (بينانس + مكسيك) ] ---
def fetch_market_data(symbol):
    s = symbol.upper().replace("#", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # محاولة جلب البيانات من منصتين لضمان عدم فقدان أي عملة
    urls = [
        (f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100", "Binance 🟡", f"BINANCE:{s}"),
        (f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100", "MEXC 🟢", f"MEXC:{s}")
    ]
    
    for url, ex_name, tv_sym in urls:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                cols = ['t','o','h','l','c','v','ct','q','n','tb','tq','i'] if "binance" in url else ['t','o','h','l','c','v','ct','q']
                df = pd.DataFrame(data, columns=cols[:len(data[0])]).astype(float)
                return df, s, ex_name, f"https://www.tradingview.com/chart/?symbol={tv_sym}"
        except: continue
    return None, s, None, None

def calculate_params(df):
    cp = df['c'].iloc[-1]
    ema = df['c'].ewm(span=20).mean().iloc[-1]
    side = "LONG 🚀" if cp > ema else "SHORT 📉"
    # حساب أهداف ذكية (نسبية بناءً على الفولتالية)
    tp1, tp2 = (cp * 1.025, cp * 1.055) if side == "LONG 🚀" else (cp * 0.975, cp * 0.945)
    sl = df['l'].iloc[-15:].min() * 0.985 if side == "LONG 🚀" else df['h'].iloc[-15:].max() * 1.015
    return side, cp, round(tp1, 4), round(tp2, 4), round(sl, 4)

# --- [ 4. نظام الدفع التلقائي (Callback) ] ---
def create_oxapay_bill(uid, amount):
    url = "https://api.oxapay.com/merchants/request"
    data = {
        "merchant": OXAPAY_KEY,
        "amount": amount,
        "currency": "USDT",
        "description": str(uid),
        "callbackUrl": f"{WEBHOOK_URL}/payment/callback"
    }
    try:
        res = requests.post(url, json=data).json()
        return res.get("payLink")
    except: return None

@app.route('/payment/callback', methods=['POST'])
def payment_callback():
    data = request.json
    if data and data.get('status') in ['paid', 'confirmed']:
        uid = str(data.get('description'))
        expiry_date = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        db["vip_list"][uid] = expiry_date
        save_db()
        bot.send_message(uid, f"👑 **تم تفعيل اشتراكك التلقائي بنجاح!**\nينتهي في: {expiry_date}")
    return "OK", 200

# --- [ 5. التحقق من صلاحية VIP ] ---
def is_vip(uid):
    uid = str(uid)
    if uid in db["vip_list"]:
        expiry = datetime.datetime.strptime(db["vip_list"][uid], '%Y-%m-%d')
        if datetime.datetime.now() < expiry: return True
        else:
            del db["vip_list"][uid]
            save_db()
    return False

# --- [ 6. المحلل الذكي (نظام الـ 5 محاولات) ] ---
@bot.message_handler(func=lambda m: m.text == "🔍 المحلل الذكي")
def analysis_gate(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"][uid] = {"free_count": 0}
    
    if not is_vip(uid) and db["users"][uid]["free_count"] >= 5:
        return bot.send_message(uid, "⚠️ انتهت محاولاتك المجانية (5/5).\nيرجى تفعيل الـ VIP للتحليل غير المحدود.")
    
    msg = bot.send_message(uid, "📝 أرسل رمز العملة (مثال: SOL):")
    bot.register_next_step_handler(msg, run_analysis)

def run_analysis(m):
    uid = str(m.chat.id)
    df, fs, ex, chart = fetch_market_data(m.text)
    if df is not None:
        side, entry, tp1, tp2, sl = calculate_params(df)
        msg = (f"🏛 **نتائج رادار {ex}**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: #{fs}\n📊 الإشارة: **{side}**\n\n"
               f"📥 الدخول: `{entry}`\n🎯 هدف 1: `{tp1}`\n🎯 هدف 2: `{tp2}`\n🛑 الوقف: `{sl}`\n"
               f"━━━━━━━━━━━━━━\n📈 [عرض الشارت المباشر]({chart})")
        bot.send_message(uid, msg, parse_mode="Markdown", disable_web_page_preview=False)
        if not is_vip(uid):
            db["users"][uid]["free_count"] += 1
            save_db()
    else: bot.send_message(uid, "❌ لم يتم العثور على العملة في بينانس أو مكسيك.")

# --- [ 7. نظام الدعم الآمن وتفعيل الإيصالات ] ---
@bot.message_handler(func=lambda m: m.text == "📞 الدعم")
def support_handler(m):
    bot.send_message(m.chat.id, "👋 قسم الدعم الفني:\nأرسل رسالتك أو صورة إيصال التحويل اليدوي هنا مباشرة.")

@bot.message_handler(content_types=['photo', 'text'])
def support_logic(m):
    uid = str(m.chat.id)
    if uid == str(OWNER_ID) or m.text in ["🔍 المحلل الذكي", "👑 تفعيل الـ VIP (50$)", "👤 حسابي", "📞 الدعم"]: return
    
    if m.content_type == 'photo':
        bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
        bot.send_message(OWNER_ID, f"🖼 **إيصال جديد من:** `{uid}`\nلتفعيله: `/activate {uid}`")
        bot.send_message(uid, "✅ تم إرسال الإيصال، انتظر التفعيل.")
    else:
        bot.send_message(OWNER_ID, f"📩 **رسالة من:** `{uid}`\n{m.text}")
        bot.send_message(uid, "✅ تم استلام رسالتك.")

# --- [ 8. أوامر المالك والإدارة ] ---
@bot.message_handler(commands=['activate'])
def admin_activate(m):
    if m.chat.id == OWNER_ID:
        try:
            target = m.text.split()[1]
            exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            db["vip_list"][target] = exp
            save_db()
            bot.send_message(target, f"👑 **تم تفعيل الـ VIP لمدة شهر!**\nينتهي في: {exp}")
            bot.send_message(OWNER_ID, f"✅ تم التفعيل للآيدي {target}")
        except: bot.send_message(OWNER_ID, "استخدم: `/activate ID`")

# --- [ 9. رادار التوصيات التلقائي الشامل ] ---
def auto_radar_loop():
    sent_today = 0
    last_day = datetime.datetime.now().day
    while True:
        try:
            now = datetime.datetime.now()
            if now.day != last_day: sent_today = 0; last_day = now.day
            
            if sent_today < 6:
                ticker = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
                potential = [i for i in ticker if abs(float(i['priceChangePercent'])) > 1.8 and i['symbol'].endswith("USDT")]
                
                for item in sorted(potential, key=lambda x: abs(float(x['priceChangePercent'])), reverse=True):
                    df, fs, ex, chart = fetch_market_data(item['symbol'])
                    if df is not None:
                        vol = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
                        if vol > 2.8: # سيولة قوية
                            side, entry, tp1, tp2, sl = calculate_params(df)
                            msg = (f"💎 **توصية VIP آلية ({sent_count+1}/6)**\n━━━━━━━━━━━━━━\n"
                                   f"🪙 العملة: #{fs} | {ex}\n🔥 سيولة: `{round(vol, 2)}x`\n\n"
                                   f"📥 الدخول: `{entry}`\n🎯 هدف 1: `{tp1}`\n🎯 هدف 2: `{tp2}`\n🛑 الوقف: `{sl}`\n"
                                   f"━━━━━━━━━━━━━━\n📈 [عرض الشارت]({chart})")
                            
                            vips = list(db["vip_list"].keys())
                            for v_id in vips:
                                if is_vip(v_id):
                                    try: bot.send_message(v_id, msg, parse_mode="Markdown")
                                    except: pass
                            sent_today += 1
                            time.sleep(3600 * 2.5) # فاصل زمني
                            break
            time.sleep(900)
        except: time.sleep(30)

# --- [ 10. واجهة المستخدم النهائية ] ---
@bot.message_handler(func=lambda m: m.text == "👑 تفعيل الـ VIP (50$)")
def vip_section(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ دفع تلقائي وتفعيل فوري", callback_data="p_auto"))
    mk.add(types.InlineKeyboardButton("📥 دفع يدوي (إيصال تحويل)", callback_data="p_manual"))
    bot.send_message(m.chat.id, "💎 **اشتراك VIP الإمبراطوري**\nسعر الاشتراك: **50$ شهرياً**\nاختر طريقة الدفع:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data.startswith("p_"))
def pay_callbacks(call):
    if call.data == "p_manual":
        bot.send_message(call.message.chat.id, f"📥 حول **50$** لـ:\n`{MY_USDT_WALLET}`\nثم أرسل صورة الإيصال هنا.")
    elif call.data == "p_auto":
        link = create_oxapay_bill(call.message.chat.id, 50)
        if link: bot.send_message(call.message.chat.id, f"🔗 [اضغط هنا للدفع التلقائي 50$]({link})", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.chat.id)
    status = "👑 VIP" if is_vip(uid) else "🆓 مجاني"
    exp = db["vip_list"].get(uid, "غير نشط")
    count = db["users"].get(uid, {}).get("free_count", 0)
    bot.send_message(uid, f"👤 **معلوماتك:**\n🏆 الحالة: {status}\n🗓 الانتهاء: {exp}\n📊 تحليلاتك: {count}/5")

@bot.message_handler(commands=['start'])
def welcome_home(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔍 المحلل الذكي", "👑 تفعيل الـ VIP (50$)", "👤 حسابي", "📞 الدعم")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة - النسخة الإمبراطورية V600**\nأقوى أداة تداول في تلجرام.", reply_markup=markup)

@app.route('/')
def home(): return "Radar Mega Active 🏛"

if __name__ == "__main__":
    threading.Thread(target=auto_radar_loop, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
