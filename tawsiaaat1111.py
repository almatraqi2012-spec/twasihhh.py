import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والتحصين ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_USDT_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" # محفظتك للتحويل اليدوي
WEBHOOK_URL = "https://tawsiaaat1111.onrender.com" 
DB_FILE = "radar_empire_v500.json"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. إدارة قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"users": {}, "vip": {}, "last_reset": time.strftime("%Y-%m-%d")}

db = load_db()
def save_db():
    try:
        with open(DB_FILE, 'w') as f: json.dump(db, f)
    except: pass

# --- [ 3. محرك جلب البيانات الذكي (إصلاح مشكلة عدم العثور) ] ---
def fetch_market_data(symbol):
    # تنظيف الاسم تماماً لضمان القبول في بينانس ومكسيك
    s = symbol.upper().replace("#", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # محاولة بينانس أولاً
    b_url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(b_url, timeout=10)
        if r.status_code == 200:
            df = pd.DataFrame(r.json(), columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
            return df, s, "Binance 🟡", f"https://www.tradingview.com/chart/?symbol=BINANCE:{s}"
    except: pass

    # محاولة مكسيك (MEXC) ثانياً
    m_url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
    try:
        r = requests.get(m_url, timeout=10)
        if r.status_code == 200:
            df = pd.DataFrame(r.json(), columns=['t','o','h','l','c','v','ct','q']).astype(float)
            return df, s, "MEXC 🟢", f"https://www.tradingview.com/chart/?symbol=MEXC:{s}"
    except: pass
    
    return None, s, None, None

# --- [ 4. نظام الشحن والدفع (تلقائي + يدوي) ] ---
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

# --- [ 5. واجهة المستخدم والميزات ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"][uid] = {"balance": 0, "status": "Free"}; save_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔍 محلل ذكي", "💳 المحفظة والشحن", "👑 VIP", "📞 الدعم")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V500**\nأرسل اسم أي عملة (مثلاً BTC) للتحليل المزدوج.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💳 المحفظة والشحن")
def wallet_section(m):
    uid = str(m.chat.id)
    balance = db["users"][uid]["balance"]
    msg = (f"💳 **محفظتك الرقمية**\n━━━━━━━━━━━━━━\n"
           f"💵 الرصيد: `{balance}$` USDT\n━━━━━━━━━━━━━━\n"
           f"📥 **شحن يدوي (مباشر لك):**\n`{MY_USDT_WALLET}`\n"
           f"⚠️ أرسل صورة التحويل للدعم الفني.\n━━━━━━━━━━━━━━\n"
           f"⚡ **شحن تلقائي (فوري):**")
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⚡ شحن تلقائي 10$", callback_data="pay_10"))
    bot.send_message(m.chat.id, msg, parse_mode="Markdown", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_pay(call):
    amount = int(call.data.split("_")[1])
    link = create_oxapay_bill(call.message.chat.id, amount)
    if link: bot.send_message(call.message.chat.id, f"🔗 [اضغط هنا لإتمام الشحن الآلي {amount}$]({link})", parse_mode="Markdown")

# --- [ 6. المحلل الشخصي + التوصيات الآلية ] ---
@bot.message_handler(func=lambda m: m.text == "🔍 محلل ذكي")
def ask_analysis(m):
    bot.send_message(m.chat.id, "📝 أرسل رمز العملة (مثال: SOL):")
    bot.register_next_step_handler(m, run_analysis)

def run_analysis(m):
    txt = m.text.upper().strip()
    wait = bot.send_message(m.chat.id, f"📡 جاري مسح Binance & MEXC للبحث عن {txt}...")
    df, fs, ex, chart = fetch_market_data(txt)
    
    if df is not None:
        cp = df['c'].iloc[-1]
        vol = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
        side = "LONG 🚀" if cp > df['c'].ewm(span=20).mean().iloc[-1] else "SHORT 📉"
        msg = (f"🏛 **نتائج الرادار لعملة: {fs}**\n━━━━━━━━━━━━━━\n"
               f"🏦 المنصة: {ex}\n📊 الإشارة: **{side}** | السعر: `{cp}`\n"
               f"🌊 السيولة: `{round(vol, 2)}x`\n━━━━━━━━━━━━━━\n"
               f"📈 [عرض الشارت والتحليل المباشر]({chart})")
        bot.edit_message_text(msg, m.chat.id, wait.message_id, parse_mode="Markdown", disable_web_page_preview=False)
    else:
        bot.edit_message_text(f"❌ لم يتم العثور على `{txt}` في أي منصة. تأكد من الرمز الصحيح.", m.chat.id, wait.message_id)

# --- [ 7. محرك الرادار (التوصيات التلقائية لجميع العملات) ] ---
def auto_radar():
    while True:
        try:
            # مسح عملات بينانس الأعلى تداولاً لضمان توصيات حقيقية
            ticker = requests.get("https://api.binance.com/api/v3/ticker/24hr").json()
            for item in sorted(ticker, key=lambda x: float(x['quoteVolume']), reverse=True)[:50]:
                s = item['symbol']
                if not s.endswith("USDT"): continue
                df, fs, ex, chart = fetch_market_data(s)
                if df is not None:
                    vol_ratio = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
                    if vol_ratio > 3.0: # تنبيه عند انفجار السيولة 3 أضعاف
                        msg = (f"🏛 **توصية رادار آلية**\n━━━━━━━━━━━━━━\n"
                               f"🪙 العملة: #{fs} | {ex}\n🌊 السيولة: `{round(vol_ratio, 2)}x`\n"
                               f"📈 [تحقق من الفرصة الآن]({chart})")
                        for uid in db["users"]:
                            try: bot.send_message(uid, msg, parse_mode="Markdown")
                            except: pass
            time.sleep(600)
        except: time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=auto_radar, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
