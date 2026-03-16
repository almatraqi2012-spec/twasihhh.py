import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والتحصين ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_USDT_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" # محفظتك اليدوية
WEBHOOK_URL = "https://tawsiaaat1111.onrender.com" 
DB_FILE = "radar_empire_v400.json"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. إدارة البيانات ] ---
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

# --- [ 3. محرك جلب جميع العملات (Global Scanner) ] ---
def get_all_symbols():
    # جلب كل العملات من بينانس
    b_symbols = []
    try:
        res = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
        b_symbols = [s['symbol'] for s in res['symbols'] if s['status'] == 'TRADING' and s['symbol'].endswith('USDT')]
    except: pass
    
    # جلب كل العملات من مكسيك (MEXC)
    m_symbols = []
    try:
        res = requests.get("https://api.mexc.com/api/v3/exchangeInfo").json()
        m_symbols = [s['symbol'] for s in res['symbols'] if s['symbol'].endswith('USDT')]
    except: pass
    
    return list(set(b_symbols + m_symbols))

# --- [ 4. محرك التحليل والاستراتيجية الفنية ] ---
def analyze_crypto(symbol):
    s = symbol.upper().strip()
    # تجربة بينانس أولاً
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    ex_name = "Binance 🟡"
    chart_provider = "BINANCE"
    
    r = requests.get(url, timeout=5)
    if r.status_code != 200: # تجربة مكسيك إذا فشلت بينانس
        url = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
        ex_name = "MEXC 🟢"
        chart_provider = "MEXC"
        r = requests.get(url, timeout=5)
        
    if r.status_code == 200:
        data = r.json()
        df = pd.DataFrame(data, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        cp = df['c'].iloc[-1]
        ema20 = df['c'].ewm(span=20).mean().iloc[-1]
        vol_avg = df['v'].rolling(20).mean().iloc[-1]
        liq = df['v'].iloc[-1] / (vol_avg + 1e-10)
        
        # تحليل الاتجاه (صعود/هبوط)
        side = "LONG 🚀" if cp > ema20 else "SHORT 📉"
        chart_url = f"https://www.tradingview.com/chart/?symbol={chart_provider}:{s}"
        
        return {"p": cp, "side": side, "liq": round(liq, 2), "sym": s, "ex": ex_name, "chart": chart_url}
    return None

# --- [ 5. رادار التوصيات التلقائي (الذي يمسح كل العملات) ] ---
def auto_signal_engine():
    while True:
        try:
            all_coins = get_all_symbols()
            for s in all_coins:
                # فلترة أولية لجودة العملة (يمكن إضافة شروط حجم التداول هنا)
                res = analyze_crypto(s)
                if res and res['liq'] > 3.0: # تنبيه عند انفجار السيولة 3 أضعاف
                    msg = (f"🏛 **توصية رادار آلية**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{res['sym']} | {res['ex']}\n"
                           f"📊 الإشارة: **{res['side']}**\n"
                           f"🌊 قوة السيولة: `{res['liq']}x`\n━━━━━━━━━━━━━━\n"
                           f"💰 السعر الحالي: `{res['p']}`\n"
                           f"🎯 الهدف المتوقع: `{round(res['p']*1.05 if 'LONG' in res['side'] else res['p']*0.95, 5)}` \n"
                           f"━━━━━━━━━━━━━━\n📈 [عرض الشارت المباشر]({res['chart']})")
                    
                    for uid in db["users"]:
                        try: bot.send_message(uid, msg, parse_mode="Markdown", disable_web_page_preview=True)
                        except: pass
                time.sleep(0.5) # حماية من الحظر
            time.sleep(300)
        except: time.sleep(10)

# --- [ 6. نظام المحفظة والدفع والشحن ] ---
@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"][uid] = {"balance": 0, "status": "Free"}; save_db()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔍 تحليل عملة", "💳 المحفظة والشحن", "👑 تفعيل VIP", "📞 الدعم")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V400**\nالنظام الشامل لجميع عملات Binance & MEXC مفعل.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "💳 المحفظة والشحن")
def wallet_panel(m):
    uid = str(m.chat.id)
    msg = (f"💳 **بيانات محفظتك**\n━━━━━━━━━━━━━━\n"
           f"💵 رصيدك: `{db['users'][uid]['balance']}$` USDT\n━━━━━━━━━━━━━━\n"
           f"📥 **شحن يدوي (مباشر):**\n`{MY_USDT_WALLET}`\n"
           f"⚠️ أرسل الإثبات للدعم بعد التحويل.\n━━━━━━━━━━━━━━\n"
           f"⚡ **شحن تلقائي (فوري):**")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⚡ شحن 10$ تلقائي", callback_data="pay_10"))
    bot.send_message(m.chat.id, msg, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
def handle_pay(call):
    # كود الربط مع Oxapay (كما في النسخ السابقة)
    bot.answer_callback_query(call.id, "جاري إنشاء رابط الدفع...")
    # ... (تكملة دالة الدفع الآلي)

# --- [ التشغيل النهائي ] ---
if __name__ == "__main__":
    threading.Thread(target=auto_signal_engine, daemon=True).start()
    bot.infinity_polling()
