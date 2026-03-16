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
DB_FILE = "radar_empire_v520.json" # نسخة مطورة

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. إدارة قاعدة البيانات المحلية (JSON) ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"users": {}, "vip": {}, "last_reset": time.strftime("%Y-%m-%d")}

db = load_db()
def save_db():
    try:
        with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)
    except: pass

# --- [ 3. محرك جلب البيانات الذكي ] ---
def fetch_market_data(symbol):
    s = symbol.upper().replace("#", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # محاولة بينانس
    b_url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(b_url, timeout=10)
        if r.status_code == 200:
            df = pd.DataFrame(r.json(), columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
            return df, s, "Binance 🟡", f"https://www.tradingview.com/chart/?symbol=BINANCE:{s}"
    except: pass

    # محاولة مكسيك
    m_url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
    try:
        r = requests.get(m_url, timeout=10)
        if r.status_code == 200:
            df = pd.DataFrame(r.json(), columns=['t','o','h','l','c','v','ct','q']).astype(float)
            return df, s, "MEXC 🟢", f"https://www.tradingview.com/chart/?symbol=MEXC:{s}"
    except: pass
    
    return None, s, None, None

# --- [ 4. نظام الشحن والدفع ] ---
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
        uid = data.get('description')
        amount = float(data.get('amount'))
        if uid in db["users"]:
            db["users"][uid]["balance"] += amount
            save_db()
            bot.send_message(uid, f"✅ تم الشحن التلقائي! رصيدك الجديد: `{db['users'][uid]['balance']}$`")
    return "OK", 200

# --- [ 5. واجهة المستخدم ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"][uid] = {"balance": 0, "status": "Free"}; save_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔍 محلل ذكي", "📊 توصيات الرادار", "💳 المحفظة", "👑 VIP")
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في إمبراطورية رادار القابضة V520**\nأقوى نظام تحليل ومسح للسيولة في بينانس ومكسيك.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💳 المحفظة")
def wallet_section(m):
    uid = str(m.chat.id)
    balance = db["users"][uid]["balance"]
    msg = (f"💳 **محفظتك الرقمية**\n━━━━━━━━━━━━━━\n"
           f"💵 الرصيد: `{balance}$` USDT\n━━━━━━━━━━━━━━\n"
           f"📥 **شحن يدوي:**\n`{MY_USDT_WALLET}`\n"
           f"⚠️ أرسل صورة التحويل للدعم.\n━━━━━━━━━━━━━━\n"
           f"⚡ **شحن تلقائي فوري:**")
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⚡ شحن تلقائي 10$", callback_data="pay_10"))
    bot.send_message(m.chat.id, msg, parse_mode="Markdown", reply_markup=mk)

# --- [ 6. المحلل الذكي (إصلاح كامل للأهداف) ] ---
@bot.message_handler(func=lambda m: m.text == "🔍 محلل ذكي")
def ask_analysis(m):
    bot.send_message(m.chat.id, "📝 أرسل اسم العملة (مثل BTC):")
    bot.register_next_step_handler(m, run_analysis)

def run_analysis(m):
    txt = m.text.upper().strip()
    wait = bot.send_message(m.chat.id, f"📡 جاري تحليل {txt} في جميع المنصات...")
    df, fs, ex, chart = fetch_market_data(txt)
    
    if df is not None:
        cp = df['c'].iloc[-1]
        ema = df['c'].ewm(span=20).mean().iloc[-1]
        vol_ratio = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
        
        # حساب الأهداف والوقف
        side = "LONG 🚀" if cp > ema else "SHORT 📉"
        if side == "LONG 🚀":
            tp1, tp2 = cp * 1.015, cp * 1.04
            sl = df['l'].iloc[-10:].min() * 0.99
        else:
            tp1, tp2 = cp * 0.985, cp * 0.96
            sl = df['h'].iloc[-10:].max() * 1.01

        msg = (f"🏛 **نتائج تحليل رادار القابضة**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: #{fs} | {ex}\n📊 الإشارة: **{side}**\n"
               f"🌊 السيولة: `{round(vol_ratio, 2)}x`\n━━━━━━━━━━━━━━\n"
               f"📥 **سعر الدخول:** `{cp}`\n"
               f"🎯 **هدف 1:** `{round(tp1, 4)}`\n"
               f"🎯 **هدف 2:** `{round(tp2, 4)}`\n"
               f"🛑 **الوقف:** `{round(sl, 4)}`\n━━━━━━━━━━━━━━\n"
               f"📈 [التحليل المباشر على TradingView]({chart})")
        bot.edit_message_text(msg, m.chat.id, wait.message_id, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        bot.edit_message_text(f"❌ لم أجد `{txt}`. تأكد من الرمز.", m.chat.id, wait.message_id)

# --- [ 7. محرك الرادار التلقائي (صائد السيولة) ] ---
def auto_radar():
    while True:
        try:
            ticker = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
            # مسح أعلى 30 عملة سيولة
            for item in sorted(ticker, key=lambda x: float(x['quoteVolume']), reverse=True)[:30]:
                s = item['symbol']
                if not s.endswith("USDT"): continue
                df, fs, ex, chart = fetch_market_data(s)
                if df is not None:
                    vol_ratio = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
                    # تنبيه عند انفجار السيولة (أكثر من 4 أضعاف المعدل)
                    if vol_ratio > 4.0:
                        cp = df['c'].iloc[-1]
                        msg = (f"🚨 **تنبيه انفجار سيولة (رادار القابضة)**\n━━━━━━━━━━━━━━\n"
                               f"🪙 العملة: #{fs}\n🌊 قوة الانفجار: `{round(vol_ratio, 2)}x`\n"
                               f"💵 السعر الحالي: `{cp}`\n━━━━━━━━━━━━━━\n"
                               f"📈 [اقتناص الفرصة الآن]({chart})")
                        for uid in list(db["users"].keys()):
                            try: bot.send_message(uid, msg, parse_mode="Markdown")
                            except: pass
            time.sleep(900) # مسح كل 15 دقيقة
        except: time.sleep(30)

@app.route('/')
def home(): return "Radar Empire V520 is Active! 🏛"

if __name__ == "__main__":
    # تشغيل الرادار التلقائي في خلفية الكود
    threading.Thread(target=auto_radar, daemon=True).start()
    # تشغيل استقبال الرسائل
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    # تشغيل سيرفر Flask لمنع الانهيار (Crash)
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
    
