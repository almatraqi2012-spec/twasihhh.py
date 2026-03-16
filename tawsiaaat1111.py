import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والتحصين ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_USDT_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" 
WEBHOOK_URL = "https://tawsiaaat1111.onrender.com" 
DB_FILE = "radar_empire_final.json"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. إدارة قاعدة البيانات المحلية ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"users": {}, "vip_list": []}

db = load_db()
def save_db():
    try:
        with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)
    except: pass

# --- [ 3. محرك جلب البيانات الذكي ] ---
def fetch_market_data(symbol):
    s = symbol.upper().replace("#", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    platforms = [
        (f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100", "Binance 🟡", f"BINANCE:{s}"),
        (f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100", "MEXC 🟢", f"MEXC:{s}")
    ]
    
    for url, name, tv_sym in platforms:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                cols = ['t','o','h','l','c','v','ct','q','n','tb','tq','i'] if "binance" in url else ['t','o','h','l','c','v','ct','q']
                df = pd.DataFrame(r.json(), columns=cols[:len(r.json()[0])]).astype(float)
                return df, s, name, f"https://www.tradingview.com/chart/?symbol={tv_sym}"
        except: continue
    return None, s, None, None

def calculate_trade_params(df):
    cp = df['c'].iloc[-1]
    ema = df['c'].ewm(span=20).mean().iloc[-1]
    side = "LONG 🚀" if cp > ema else "SHORT 📉"
    
    if side == "LONG 🚀":
        tp1, tp2 = cp * 1.02, cp * 1.05
        sl = df['l'].iloc[-15:].min() * 0.985
    else:
        tp1, tp2 = cp * 0.98, cp * 0.95
        sl = df['h'].iloc[-15:].max() * 1.015
    return side, cp, round(tp1, 4), round(tp2, 4), round(sl, 4)

# --- [ 4. نظام الدفع VIP ] ---
def create_oxapay_bill(uid, amount):
    url = "https://api.oxapay.com/merchants/request"
    data = {"merchant": OXAPAY_KEY, "amount": amount, "currency": "USDT", "description": str(uid), "callbackUrl": f"{WEBHOOK_URL}/payment/callback"}
    try:
        res = requests.post(url, json=data).json()
        return res.get("payLink")
    except: return None

@app.route('/payment/callback', methods=['POST'])
def payment_callback():
    data = request.json
    if data and data.get('status') in ['paid', 'confirmed']:
        uid = str(data.get('description'))
        if uid in db["users"]:
            db["vip_list"].append(uid)
            save_db()
            bot.send_message(uid, "👑 **مبروك! تم تفعيل اشتراك VIP تلقائياً.**\nستصلك الآن 6 توصيات ذهبية يومياً.")
    return "OK", 200

# --- [ 5. واجهة المستخدم والأزرار ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"][uid] = {"free_count": 0}; save_db()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔍 المحلل الذكي", "👑 تفعيل الـ VIP (50$)", "👤 حسابي", "📞 الدعم")
    bot.send_message(m.chat.id, "🏛 **إمبراطورية رادار القابضة**\nجاهز للتحليل وصيد التوصيات.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.chat.id)
    status = "👑 VIP" if uid in db["vip_list"] else "🆓 مجاني"
    count = db["users"].get(uid, {}).get("free_count", 0)
    msg = (f"👤 **بيانات الحساب**\n━━━━━━━━━━━━━━\n"
           f"🏆 الحالة: {status}\n"
           f"📊 التحليل المجاني المستهلك: `{count}/5`\n━━━━━━━━━━━━━━")
    bot.send_message(m.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👑 تفعيل الـ VIP (50$)")
def vip_gate(m):
    msg = "💎 **مميزات اشتراك الـ VIP:**\n\n✅ 6 توصيات (أهداف + وقف + دخول) يومياً.\n✅ تحليل لا محدود للعملات.\n✅ شارت مباشر لكل صفقة.\n\n**اختر وسيلة الدفع (50$ شهرياً):**"
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ دفع تلقائي وتفعيل فوري", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("📥 دفع يدوي (تحويل محفظة)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, msg, reply_markup=mk, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_payment_choice(call):
    uid = str(call.message.chat.id)
    if call.data == "pay_manual":
        bot.send_message(uid, f"📥 **الدفع اليدوي:**\nقم بتحويل **50$** USDT (TRC20) للمحفظة:\n\n`{MY_USDT_WALLET}`\n\nثم أرسل صورة التحويل للدعم الفني.")
    elif call.data == "pay_auto":
        link = create_oxapay_bill(uid, 50)
        if link:
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("دفع 50$ الآن 💳", url=link))
            bot.send_message(uid, "أدخل مبلغ 50$ في الرابط لإتمام التفعيل التلقائي:", reply_markup=mk)

# --- [ 6. المحلل الذكي (قيد الـ 5 تحليلات) ] ---
@bot.message_handler(func=lambda m: m.text == "🔍 المحلل الذكي")
def analysis_start(m):
    uid = str(m.chat.id)
    count = db["users"].get(uid, {}).get("free_count", 0)
    if uid not in db["vip_list"] and count >= 5:
        return bot.send_message(m.chat.id, "⚠️ انتهت محاولاتك المجانية (5/5).\nاشترك في VIP للتحليل بلا حدود.")
    
    msg = bot.send_message(m.chat.id, "📝 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, perform_analysis)

def perform_analysis(m):
    uid = str(m.chat.id)
    txt = m.text.upper().strip()
    df, fs, ex, chart = fetch_market_data(txt)
    
    if df is not None:
        side, entry, tp1, tp2, sl = calculate_trade_params(df)
        msg = (f"🏛 **تحليل الرادار لعملة {fs}**\n━━━━━━━━━━━━━━\n"
               f"📊 الإشارة: **{side}**\n📥 الدخول: `{entry}`\n🎯 هدف 1: `{tp1}`\n🎯 هدف 2: `{tp2}`\n🛑 الوقف: `{sl}`\n━━━━━━━━━━━━━━\n"
               f"📈 [عرض الشارت المباشر]({chart})")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown", disable_web_page_preview=False)
        if uid not in db["vip_list"]:
            db["users"][uid]["free_count"] += 1
            save_db()
    else: bot.send_message(m.chat.id, "❌ لم يتم العثور على البيانات.")

# --- [ 7. نظام التوصيات الـ 6 التلقائي ] ---
def auto_signals_engine():
    sent_count = 0
    curr_day = time.strftime("%d")
    while True:
        try:
            if time.strftime("%d") != curr_day: sent_count = 0; curr_day = time.strftime("%d")
            
            if sent_count < 6:
                ticker = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
                for item in sorted(ticker, key=lambda x: float(x['quoteVolume']), reverse=True)[:35]:
                    s = item['symbol']
                    if not s.endswith("USDT"): continue
                    df, fs, ex, chart = fetch_market_data(s)
                    if df is not None:
                        vol = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
                        if vol > 4.0: # شرط سيولة قوية جداً
                            side, entry, tp1, tp2, sl = calculate_trade_params(df)
                            msg = (f"💎 **توصية VIP رقم {sent_count+1}**\n━━━━━━━━━━━━━━\n"
                                   f"🪙 العملة: #{fs}\n🔥 انفجار سيولة: `{round(vol, 2)}x`\n\n"
                                   f"📥 الدخول: `{entry}`\n🎯 هدف 1: `{tp1}`\n🎯 هدف 2: `{tp2}`\n🛑 الوقف: `{sl}`\n━━━━━━━━━━━━━━\n"
                                   f"📈 [رابط الشارت والتحليل المباشر]({chart})")
                            for v_uid in db["vip_list"]:
                                try: bot.send_message(v_uid, msg, parse_mode="Markdown")
                                except: pass
                            sent_count += 1
                            time.sleep(3600 * 3) # فاصل 3 ساعات
            time.sleep(900)
        except: time.sleep(30)

@bot.message_handler(func=lambda m: m.text == "📞 الدعم")
def help_support(m):
    bot.send_message(m.chat.id, f"👤 لمراسلة الدعم وتأكيد الدفع اليدوي:\nآيدي المطور: `{OWNER_ID}`")

@app.route('/')
def health(): return "Radar Online 🏛"

if __name__ == "__main__":
    threading.Thread(target=auto_signals_engine, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
