import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v150_final.json"
RENDER_URL = "https://tawsiaaat1111.onrender.com" 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"vip": {}, "free_used": {}, "vip_daily_count": {}, "users": [], "last_reset": time.strftime("%Y-%m-%d")}

db = load_db()
def save_db():
    try:
        with open(DB_FILE, 'w') as f: json.dump(db, f)
    except: pass

# --- [ 3. محرك التحليل الخارق (صعود وهبوط) ] ---
def analyze_market_ultra(symbol):
    # نستخدم فريم الساعة (1h) مع 100 شمعة لتحليل أدق
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10).json()
        df = pd.DataFrame(r, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        
        current_p = df['c'].iloc[-1]
        ema_20 = df['c'].ewm(span=20, adjust=False).mean().iloc[-1]
        recent_high = df['h'].rolling(7).max().iloc[-2]
        recent_low = df['l'].rolling(7).min().iloc[-2]
        
        # حساب RSI للزخم
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))

        # --- [ منطق الصعود LONG ] ---
        if current_p > ema_20 and current_p >= recent_high and rsi > 45:
            return {"side": "LONG 🚀", "price": current_p, "target": current_p * 1.03, "stop": current_p * 0.97}
            
        # --- [ منطق الهبوط SHORT ] ---
        elif current_p < ema_20 and current_p <= recent_low and rsi < 55:
            return {"side": "SHORT 📉", "price": current_p, "target": current_p * 0.97, "stop": current_p * 1.03}
        
        return None
    except: return None

# --- [ 4. نظام المسح الشامل (كل العملات) ] ---
def start_full_scanner():
    while True:
        try:
            # تصفير العداد اليومي
            if db.get("last_reset") != time.strftime("%Y-%m-%d"):
                db["vip_daily_count"], db["last_reset"] = {}, time.strftime("%Y-%m-%d")
                save_db()

            # جلب كل العملات المتاحة
            symbols = [s['symbol'] for s in requests.get("https://api.binance.com/api/v3/exchangeInfo").json()['symbols'] if s['symbol'].endswith('USDT')]
            
            for s in symbols:
                res = analyze_market_ultra(s)
                if res:
                    msg = (f"🏛 **رادار القابضة - إشارة مؤكدة**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{s}\n📊 الإشارة: **{res['side']}**\n━━━━━━━━━━━━━━\n"
                           f"💰 الدخول: `{res['price']}`\n🎯 الهدف: `{round(res['target'], 4)}`\n🛡️ الوقف: `{round(res['stop'], 4)}` \n━━━━━━━━━━━━━━\n"
                           f"🔗 [الشارت المباشر](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
                    
                    for user in db["users"]:
                        u_s = str(user)
                        is_vip = db["vip"].get(u_s, 0) > time.time()
                        if is_vip and db["vip_daily_count"].get(u_s, 0) < 6:
                            bot.send_message(user, msg, parse_mode="Markdown")
                            db["vip_daily_count"][u_s] = db["vip_daily_count"].get(u_s, 0) + 1
                        elif not is_vip and db["free_used"].get(u_s, 0) < 3:
                            bot.send_message(user, "🎁 **توصية مجانية:**\n" + msg, parse_mode="Markdown")
                            db["free_used"][u_s] = db["free_used"].get(u_s, 0) + 1
                    save_db()
                time.sleep(0.1) # مسح سريع جداً
            time.sleep(30)
        except: time.sleep(10)

# --- [ 5. واجهة المستخدم والمحلل ] ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V150 جاهز!**\n\nأنا أراقب **جميع العملات** الآن. أرسل اسم أي عملة لتحليلها فوراً، أو انتظر التوصيات الآلية.", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("👤 حسابي", "💎 تفعيل VIP"))

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.chat.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    txt = f"👤 حسابك: {'VIP 👑' if is_vip else 'مجاني 🆓'}\n🆔: `{uid}`\nتوصيات اليوم: {db['vip_daily_count'].get(uid, 0)}/6"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: len(m.text) >= 2 and len(m.text) <= 10 and m.text not in ["👤 حسابي", "💎 تفعيل VIP"])
def manual_anal(m):
    sym = m.text.upper().replace("#", "")
    if not sym.endswith("USDT"): sym += "USDT"
    bot.send_message(m.chat.id, f"🔍 جاري تحليل {sym}...")
    res = analyze_market_ultra(sym)
    if res:
        msg = (f"🏛 **تحليل {sym}**\n━━━━━━━━━━━━━━\n"
               f"📊 الإشارة: **{res['side']}**\n💰 الدخول: `{res['price']}`\n🎯 الهدف: `{round(res['target'], 4)}` \n━━━━━━━━━━━━━━")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, f"⚠️ عملة {sym} لا تعطي إشارة دخول واضحة حالياً. يفضل مراقبة عملة أخرى.")

# --- [ نظام الدفع ] ---
@app.route('/payment/webhook', methods=['POST'])
def webh():
    data = request.json
    if data and data.get('status') in ['confirmed', 'paid']:
        uid = data.get('description')
        if uid: db["vip"][str(uid)] = time.time() + (30*86400); save_db(); bot.send_message(int(uid), "✅ تم تفعيل VIP!")
    return "OK", 200

def get_link(cid):
    p = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': str(cid), 'callbackUrl': f"{RENDER_URL}/payment/webhook"}
    try: return requests.post("https://api.oxapay.com/merchants/request", json=p).json().get('payLink')
    except: return None

@bot.message_handler(func=lambda m: m.text == "💎 تفعيل VIP")
def pay_v(m):
    mk = types.InlineKeyboardMarkup()
    link = get_link(m.chat.id)
    if link: mk.add(types.InlineKeyboardButton("⚡ دفع آلي (50$)", url=link))
    bot.send_message(m.chat.id, "اختر طريقة تفعيل VIP لمدة 30 يوم:", reply_markup=mk)

# --- [ التشغيل ] ---
if __name__ == "__main__":
    threading.Thread(target=start_full_scanner, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
