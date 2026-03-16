import requests, telebot, time, json, os, threading
import pandas as pd
import numpy as np
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والربط ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_final_v200.json"
RENDER_URL = "https://tawsiaaat1111.onrender.com" 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. إدارة قاعدة البيانات ] ---
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

# --- [ 3. محرك التحليل الاحترافي (المؤشرات + السيولة) ] ---
def analyze_master_engine(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10).json()
        df = pd.DataFrame(r, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        
        cp = df['c'].iloc[-1]
        # أ) المتوسطات الأسية EMA
        ema_fast = df['c'].ewm(span=12).mean()
        ema_slow = df['c'].ewm(span=26).mean()
        
        # ب) مؤشر MACD
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=9).mean()
        
        # ج) مؤشر السيولة (Volume Flow)
        vol_now = df['v'].iloc[-1]
        vol_avg = df['v'].rolling(20).mean().iloc[-1]
        liq_flow = vol_now / (vol_avg + 1e-10)
        
        # د) مؤشر RSI
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / (loss.iloc[-1] + 1e-10))))

        # --- قرار الدخول (صعود / هبوط / تذبذب) ---
        side = "WAIT ⏳"
        status = "تذبذب عرضي ⚖️"
        
        # سيولة قوية تبدأ من 1.2x
        is_liquid = liq_flow > 1.2
        
        if cp > ema_fast.iloc[-1] and macd.iloc[-1] > signal_line.iloc[-1] and rsi > 50:
            side = "LONG 🚀"
            status = "صعودي قوي 🔥" if is_liquid else "صعودي ضعيف 📈"
        elif cp < ema_fast.iloc[-1] and macd.iloc[-1] < signal_line.iloc[-1] and rsi < 50:
            side = "SHORT 📉"
            status = "هبوطي قوي 📉" if is_liquid else "هبوطي ضعيف 📉"

        return {
            "p": cp, "side": side, "status": status, 
            "rsi": round(rsi, 1), "liq": round(liq_flow, 2),
            "t": cp*1.035 if "LONG" in side else cp*0.965,
            "s": cp*0.975 if "LONG" in side else cp*1.025
        }
    except: return None

# --- [ 4. الرادار الشامل (مسح كل العملات) ] ---
def run_global_scanner():
    while True:
        try:
            if db.get("last_reset") != time.strftime("%Y-%m-%d"):
                db["vip_daily_count"], db["last_reset"] = {}, time.strftime("%Y-%m-%d")
                save_db()

            symbols = [s['symbol'] for s in requests.get("https://api.binance.com/api/v3/exchangeInfo").json()['symbols'] if s['symbol'].endswith('USDT')]
            
            for s in symbols:
                res = analyze_master_engine(s)
                # الرادار يرسل التوصية آلياً فقط إذا كانت السيولة والاتجاه "قوي"
                if res and "WAIT" not in res['side'] and res['liq'] > 1.5:
                    msg = (f"🏛 **توصية رادار القابضة**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{s}\n📊 الإشارة: **{res['side']}**\n"
                           f"🌊 السيولة: `{res['liq']}x` | RSI: `{res['rsi']}`\n━━━━━━━━━━━━━━\n"
                           f"💰 دخول: `{res['p']}`\n🎯 هدف: `{round(res['t'], 4)}`\n🛡️ وقف: `{round(res['s'], 4)}` \n━━━━━━━━━━━━━━")
                    
                    for uid in db["users"]:
                        u_s = str(uid)
                        is_vip = db["vip"].get(u_s, 0) > time.time()
                        if is_vip and db["vip_daily_count"].get(u_s, 0) < 6:
                            try: bot.send_message(uid, msg, parse_mode="Markdown"); db["vip_daily_count"][u_s] += 1
                            except: pass
                        elif not is_vip and db["free_used"].get(u_s, 0) < 3:
                            try: bot.send_message(uid, "🎁 **توصية مجانية:**\n" + msg, parse_mode="Markdown"); db["free_used"][u_s] += 1
                            except: pass
                    save_db()
                time.sleep(0.15)
            time.sleep(60)
        except: time.sleep(20)

# --- [ 5. واجهة المستخدم والمحلل الشخصي ] ---
@bot.message_handler(commands=['start'])
def welcome_user(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"].append(uid); save_db(); bot.send_message(OWNER_ID, f"🔔 مستخدم جديد: `{uid}`")
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True).add("👤 حسابي", "💎 تفعيل VIP")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V200**\n\nأرسل اسم أي عملة (BTC, SOL, OP) وسأقوم بتحليل السيولة والمؤشرات فوراً.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_status(m):
    uid = str(m.chat.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    st = "VIP 👑" if is_vip else "مجاني 🆓"
    bot.send_message(m.chat.id, f"👤 **حسابك:** {st}\n🆔: `{uid}`\n📈 توصيات اليوم: {db['vip_daily_count'].get(uid, 0)}/6")

@bot.message_handler(func=lambda m: len(m.text) >= 2 and len(m.text) <= 10 and m.text not in ["👤 حسابي", "💎 تفعيل VIP"])
def manual_analyst(m):
    sym = m.text.upper().replace("#", "").replace("USDT", "") + "USDT"
    bot.send_message(m.chat.id, f"🔍 جاري تحليل {sym} عبر أقوى المؤشرات...")
    res = analyze_master_engine(sym)
    if res:
        msg = (f"🏛 **تقرير المحلل الذكي: {sym}**\n━━━━━━━━━━━━━━\n"
               f"📊 الاتجاه: **{res['status']}**\n"
               f"🌊 السيولة: `{res['liq']}x`\n"
               f"📈 مؤشر RSI: `{res['rsi']}`\n━━━━━━━━━━━━━━\n"
               f"🎯 الإشارة: **{res['side']}**\n"
               f"💰 سعر الدخول: `{res['p']}`\n✅ الهدف: `{round(res['t'], 4)}`\n❌ الوقف: `{round(res['s'], 4)}`\n━━━━━━━━━━━━━━")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "❌ لم أتمكن من العثور على العملة، تأكد من الرمز الصحيح.")

# --- [ 6. نظام الدفع والويب هوك ] ---
@app.route('/payment/webhook', methods=['POST'])
def handle_pay():
    data = request.json
    if data and data.get('status') in ['confirmed', 'paid']:
        uid = data.get('description')
        if uid:
            db["vip"][str(uid)] = time.time() + (30*86400); save_db()
            bot.send_message(int(uid), "✅ تم تفعيل اشتراك VIP بنجاح!"); bot.send_message(OWNER_ID, f"💰 اشتراك جديد: `{uid}`")
    return "OK", 200

@bot.message_handler(func=lambda m: m.text == "💎 تفعيل VIP")
def pay_request(m):
    p = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': str(m.chat.id), 'callbackUrl': f"{RENDER_URL}/payment/webhook"}
    link = requests.post("https://api.oxapay.com/merchants/request", json=p).json().get('payLink')
    if link:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⚡ دفع آلي (50$)", url=link))
        bot.send_message(m.chat.id, "💎 **مميزات VIP:**\n✅ 6 توصيات قوية يومياً\n✅ تحليل شامل للسيولة\n✅ أهداف دقيقة بنسبة نجاح عالية", reply_markup=mk)

# --- [ التشغيل النهائي ] ---
if __name__ == "__main__":
    threading.Thread(target=run_global_scanner, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
