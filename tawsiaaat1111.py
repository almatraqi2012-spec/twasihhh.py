import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_final_production.json"
RENDER_URL = "https://tawsiaaat1111.onrender.com" 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. إدارة البيانات ] ---
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

# --- [ 3. محرك التحليل (المؤشرات والسيولة) ] ---
def analyze_crypto_core(symbol):
    s = symbol.upper().strip()
    if not s.endswith("USDT"): s += "USDT"
    
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return None
        df = pd.DataFrame(r.json(), columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        
        cp = df['c'].iloc[-1]
        ema = df['c'].ewm(span=20).mean().iloc[-1]
        # السيولة: حجم التداول الحالي مقارنة بالمتوسط
        liq = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
        # RSI
        delta = df['c'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean().iloc[-1]
        loss = -delta.where(delta < 0, 0).rolling(14).mean().iloc[-1]
        rsi = 100 - (100 / (1 + (gain / (loss + 1e-10))))

        side = "LONG 🚀" if cp > ema and rsi > 50 else "SHORT 📉"
        return {"p": cp, "side": side, "rsi": round(rsi, 1), "liq": round(liq, 2), "sym": s}
    except: return None

# --- [ 4. نظام الرادار (التوصيات التلقائية) ] ---
def automated_scanner():
    while True:
        try:
            # إعادة تصفير العداد اليومي
            if db.get("last_reset") != time.strftime("%Y-%m-%d"):
                db["vip_daily_count"], db["last_reset"] = {}, time.strftime("%Y-%m-%d")
                save_db()

            # جلب العملات ومسحها
            ex = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
            symbols = [s['symbol'] for s in ex['symbols'] if s['symbol'].endswith('USDT')][:150] # مسح أول 150 عملة لسرعة الاستجابة
            
            for s in symbols:
                res = analyze_crypto_core(s)
                # شرط التوصية التلقائية: سيولة عالية (أكبر من 2.0x)
                if res and res['liq'] > 2.0:
                    msg = (f"🏛 **توصية رادار آلية**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{res['sym']}\n📊 الإشارة: **{res['side']}**\n"
                           f"🌊 السيولة: `{res['liq']}x` | RSI: `{res['rsi']}`\n━━━━━━━━━━━━━━\n"
                           f"💰 دخول: `{res['p']}`\n🎯 الهدف: `{round(res['p']*1.04 if 'LONG' in res['side'] else res['p']*0.96, 4)}` \n━━━━━━━━━━━━━━")
                    
                    for uid in db["users"]:
                        u_s = str(uid)
                        is_vip = db["vip"].get(u_s, 0) > time.time()
                        if is_vip and db["vip_daily_count"].get(u_s, 0) < 6:
                            try: bot.send_message(uid, msg, parse_mode="Markdown"); db["vip_daily_count"][u_s] = db["vip_daily_count"].get(u_s, 0) + 1
                            except: pass
                        elif not is_vip and db["free_used"].get(u_s, 0) < 3:
                            try: bot.send_message(uid, "🎁 **توصية مجانية:**\n" + msg, parse_mode="Markdown"); db["free_used"][u_s] = db["free_used"].get(u_s, 0) + 1
                            except: pass
                    save_db()
                time.sleep(0.2)
            time.sleep(60)
        except: time.sleep(10)

# --- [ 5. المحلل الشخصي عند الطلب ] ---
@bot.message_handler(func=lambda m: m.text not in ["👤 حسابي", "💎 تفعيل VIP", "/start"])
def manual_lookup(m):
    text = m.text.upper().strip()
    bot.send_message(m.chat.id, f"🔍 جاري تحليل {text}...")
    res = analyze_crypto_core(text)
    if res:
        msg = (f"🏛 **نتائج تحليل: {res['sym']}**\n━━━━━━━━━━━━━━\n"
               f"💰 السعر: `{res['p']}`\n📊 الاتجاه: **{res['side']}**\n"
               f"🌊 السيولة: `{res['liq']}x` | RSI: `{res['rsi']}`\n━━━━━━━━━━━━━━\n"
               f"🎯 هدف مقترح: `{round(res['p']*1.03 if 'LONG' in res['side'] else res['p']*0.97, 4)}` ")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "❌ لم أجد بيانات لهذه العملة. تأكد من الرمز (مثلاً: BTC أو SOL).")

# --- [ 6. الأوامر ونظام VIP ] ---
@bot.message_handler(commands=['start'])
def welcome(m):
    if str(m.chat.id) not in db["users"]: db["users"].append(str(m.chat.id)); save_db()
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True).add("👤 حسابي", "💎 تفعيل VIP")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V202**\nأرسل اسم أي عملة لتحليلها، أو انتظر التوصيات الآلية القوية هنا.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    uid = str(m.chat.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    bot.send_message(m.chat.id, f"👤 حسابك: {'VIP 👑' if is_vip else 'مجاني 🆓'}\n🆔: `{uid}`")

@app.route('/payment/webhook', methods=['POST'])
def pay_web():
    data = request.json
    if data and data.get('status') in ['confirmed', 'paid']:
        uid = data.get('description')
        if uid: db["vip"][str(uid)] = time.time() + (30*86400); save_db(); bot.send_message(int(uid), "✅ تم تفعيل VIP!")
    return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=automated_scanner, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
