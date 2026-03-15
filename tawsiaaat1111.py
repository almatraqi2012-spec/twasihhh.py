import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والتحصين ] ---
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_master_db.json"
RENDER_URL = "https://tawsiaaat1111.onrender.com" 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. محرك إدارة البيانات ] ---
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

# --- [ 3. المحلل الخارق (صعود وهبوط + قوة الاتجاه) ] ---
def analyze_crypto_v160(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10).json()
        df = pd.DataFrame(r, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        
        cp = df['c'].iloc[-1]
        ema_8 = df['c'].ewm(span=8).mean().iloc[-1]
        ema_21 = df['c'].ewm(span=21).mean().iloc[-1]
        
        # رصد الانفجار السعري والقيعان (7 ساعات)
        h7 = df['h'].rolling(7).max().iloc[-2]
        l7 = df['l'].rolling(7).min().iloc[-2]
        
        # مؤشر القوة النسبية RSI
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))

        # منطق الـ LONG (صعود)
        if cp > ema_8 and cp > h7 and rsi > 48:
            return {"side": "LONG 🚀", "p": cp, "t": cp*1.035, "s": cp*0.97, "power": "قوي 🔥"}
        # منطق الـ SHORT (هبوط)
        elif cp < ema_8 and cp < l7 and rsi < 52:
            return {"side": "SHORT 📉", "p": cp, "t": cp*0.965, "s": cp*1.03, "power": "عالي ⚡"}
        return None
    except: return None

# --- [ 4. الرادار الشامل لجميع العملات ] ---
def run_scanner():
    while True:
        try:
            if db.get("last_reset") != time.strftime("%Y-%m-%d"):
                db["vip_daily_count"], db["last_reset"] = {}, time.strftime("%Y-%m-%d")
                save_db()

            # جلب كل عملات USDT (بينانس تغطي 90% من عملات MEXC أيضاً)
            all_s = [s['symbol'] for s in requests.get("https://api.binance.com/api/v3/exchangeInfo").json()['symbols'] if s['symbol'].endswith('USDT')]
            
            for s in all_s:
                res = analyze_crypto_v160(s)
                if res:
                    msg = (f"🏛 **رادار القابضة - قناص الفرص**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{s}\n📊 الإشارة: **{res['side']}**\n💪 القوة: {res['power']}\n━━━━━━━━━━━━━━\n"
                           f"💰 الدخول: `{res['p']}`\n🎯 الهدف: `{round(res['t'], 4)}`\n🛡️ الوقف: `{round(res['s'], 4)}` \n━━━━━━━━━━━━━━\n"
                           f"🔗 [عرض الشارت](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
                    
                    for uid in db["users"]:
                        u_s = str(uid)
                        is_vip = db["vip"].get(u_s, 0) > time.time()
                        if is_vip and db["vip_daily_count"].get(u_s, 0) < 6:
                            bot.send_message(uid, msg, parse_mode="Markdown")
                            db["vip_daily_count"][u_s] = db["vip_daily_count"].get(u_s, 0) + 1
                        elif not is_vip and db["free_used"].get(u_s, 0) < 3:
                            bot.send_message(uid, "🎁 **توصية مجانية:**\n" + msg, parse_mode="Markdown")
                            db["free_used"][u_s] = db["free_used"].get(u_s, 0) + 1
                    save_db()
                time.sleep(0.1) # سرعة مسح خارقة
            time.sleep(40)
        except: time.sleep(10)

# --- [ 5. نظام الدفع والاشتراك المطور ] ---
@app.route('/payment/webhook', methods=['POST'])
def webhook_handler():
    data = request.json
    if data and data.get('status') in ['confirmed', 'paid']:
        uid = data.get('description')
        if uid:
            db["vip"][str(uid)] = time.time() + (30*86400)
            save_db()
            bot.send_message(int(uid), "👑 **مبروك! تم تفعيل اشتراك VIP بنجاح.**\nستصلك الآن أقوى الفرص آلياً.")
            bot.send_message(OWNER_ID, f"💰 **عملية دفع ناجحة!**\nالمستخدم: `{uid}` قام بالاشتراك.")
    return "OK", 200

# --- [ 6. واجهة الأوامر والمحلل الشخصي ] ---
@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: 
        db["users"].append(uid); save_db()
        bot.send_message(OWNER_ID, f"🔔 **مستخدم جديد انضم للبوت:** `{uid}`")
    
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في رادار القابضة V160**\n\nأنا أراقب **جميع العملات** في السوق الآن (Binance & MEXC).\n\n🔹 **التوصيات:** تصلك آلياً.\n🔹 **المحلل:** أرسل اسم أي عملة (مثال: BTC) لتحليلها فوراً.", 
                     reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("👤 حسابي", "💎 تفعيل VIP"))

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    uid = str(m.chat.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    txt = f"👤 **حسابك:** {'VIP 👑' if is_vip else 'مجاني 🆓'}\n🆔: `{uid}`\n📈 توصيات اليوم: {db['vip_daily_count'].get(uid, 0)}/6"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: len(m.text) >= 2 and len(m.text) <= 10 and m.text not in ["👤 حسابي", "💎 تفعيل VIP"])
def quick_analyst(m):
    sym = m.text.upper().replace("#", "")
    if not sym.endswith("USDT"): sym += "USDT"
    bot.send_message(m.chat.id, f"🔍 جاري فحص {sym} في جميع المنصات...")
    res = analyze_crypto_v160(sym)
    if res:
        bot.send_message(m.chat.id, f"🏛 **تقرير العملة {sym}**\n━━━━━━━━━━━━━━\nالإشارة: **{res['side']}**\nالقوة: {res['power']}\n━━━━━━━━━━━━━━\n💰 دخول: `{res['p']}`\n🎯 هدف: `{round(res['t'], 4)}` \n🛡️ وقف: `{round(res['s'], 4)}`", parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, f"⚠️ عملة {sym} في منطقة عرضية حالياً. لا يُنصح بالدخول الآن.")

@bot.message_handler(func=lambda m: m.text == "💎 تفعيل VIP")
def pay_btn(m):
    p = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': str(m.chat.id), 'callbackUrl': f"{RENDER_URL}/payment/webhook"}
    link = requests.post("https://api.oxapay.com/merchants/request", json=p).json().get('payLink')
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⚡ دفع آلي سريع (50$)", url=link))
    bot.send_message(m.chat.id, "💎 **اشتراك VIP (30 يوم)**\n\n✅ 6 توصيات يومية قناصة.\n✅ تحليل جميع العملات.\n✅ دعم فني وأهداف دقيقة.", reply_markup=mk)

if __name__ == "__main__":
    threading.Thread(target=run_scanner, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والتحصين ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_master_db.json"
RENDER_URL = "https://tawsiaaat1111.onrender.com" 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. محرك إدارة البيانات ] ---
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

# --- [ 3. المحلل الخارق (صعود وهبوط + قوة الاتجاه) ] ---
def analyze_crypto_v160(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10).json()
        df = pd.DataFrame(r, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        
        cp = df['c'].iloc[-1]
        ema_8 = df['c'].ewm(span=8).mean().iloc[-1]
        ema_21 = df['c'].ewm(span=21).mean().iloc[-1]
        
        # رصد الانفجار السعري والقيعان (7 ساعات)
        h7 = df['h'].rolling(7).max().iloc[-2]
        l7 = df['l'].rolling(7).min().iloc[-2]
        
        # مؤشر القوة النسبية RSI
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1])))

        # منطق الـ LONG (صعود)
        if cp > ema_8 and cp > h7 and rsi > 48:
            return {"side": "LONG 🚀", "p": cp, "t": cp*1.035, "s": cp*0.97, "power": "قوي 🔥"}
        # منطق الـ SHORT (هبوط)
        elif cp < ema_8 and cp < l7 and rsi < 52:
            return {"side": "SHORT 📉", "p": cp, "t": cp*0.965, "s": cp*1.03, "power": "عالي ⚡"}
        return None
    except: return None

# --- [ 4. الرادار الشامل لجميع العملات ] ---
def run_scanner():
    while True:
        try:
            if db.get("last_reset") != time.strftime("%Y-%m-%d"):
                db["vip_daily_count"], db["last_reset"] = {}, time.strftime("%Y-%m-%d")
                save_db()

            # جلب كل عملات USDT (بينانس تغطي 90% من عملات MEXC أيضاً)
            all_s = [s['symbol'] for s in requests.get("https://api.binance.com/api/v3/exchangeInfo").json()['symbols'] if s['symbol'].endswith('USDT')]
            
            for s in all_s:
                res = analyze_crypto_v160(s)
                if res:
                    msg = (f"🏛 **رادار القابضة - قناص الفرص**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{s}\n📊 الإشارة: **{res['side']}**\n💪 القوة: {res['power']}\n━━━━━━━━━━━━━━\n"
                           f"💰 الدخول: `{res['p']}`\n🎯 الهدف: `{round(res['t'], 4)}`\n🛡️ الوقف: `{round(res['s'], 4)}` \n━━━━━━━━━━━━━━\n"
                           f"🔗 [عرض الشارت](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
                    
                    for uid in db["users"]:
                        u_s = str(uid)
                        is_vip = db["vip"].get(u_s, 0) > time.time()
                        if is_vip and db["vip_daily_count"].get(u_s, 0) < 6:
                            bot.send_message(uid, msg, parse_mode="Markdown")
                            db["vip_daily_count"][u_s] = db["vip_daily_count"].get(u_s, 0) + 1
                        elif not is_vip and db["free_used"].get(u_s, 0) < 3:
                            bot.send_message(uid, "🎁 **توصية مجانية:**\n" + msg, parse_mode="Markdown")
                            db["free_used"][u_s] = db["free_used"].get(u_s, 0) + 1
                    save_db()
                time.sleep(0.1) # سرعة مسح خارقة
            time.sleep(40)
        except: time.sleep(10)

# --- [ 5. نظام الدفع والاشتراك المطور ] ---
@app.route('/payment/webhook', methods=['POST'])
def webhook_handler():
    data = request.json
    if data and data.get('status') in ['confirmed', 'paid']:
        uid = data.get('description')
        if uid:
            db["vip"][str(uid)] = time.time() + (30*86400)
            save_db()
            bot.send_message(int(uid), "👑 **مبروك! تم تفعيل اشتراك VIP بنجاح.**\nستصلك الآن أقوى الفرص آلياً.")
            bot.send_message(OWNER_ID, f"💰 **عملية دفع ناجحة!**\nالمستخدم: `{uid}` قام بالاشتراك.")
    return "OK", 200

# --- [ 6. واجهة الأوامر والمحلل الشخصي ] ---
@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: 
        db["users"].append(uid); save_db()
        bot.send_message(OWNER_ID, f"🔔 **مستخدم جديد انضم للبوت:** `{uid}`")
    
    bot.send_message(m.chat.id, "🏛 **مرحباً بك في رادار القابضة V160**\n\nأنا أراقب **جميع العملات** في السوق الآن (Binance & MEXC).\n\n🔹 **التوصيات:** تصلك آلياً.\n🔹 **المحلل:** أرسل اسم أي عملة (مثال: BTC) لتحليلها فوراً.", 
                     reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("👤 حسابي", "💎 تفعيل VIP"))

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def info(m):
    uid = str(m.chat.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    txt = f"👤 **حسابك:** {'VIP 👑' if is_vip else 'مجاني 🆓'}\n🆔: `{uid}`\n📈 توصيات اليوم: {db['vip_daily_count'].get(uid, 0)}/6"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: len(m.text) >= 2 and len(m.text) <= 10 and m.text not in ["👤 حسابي", "💎 تفعيل VIP"])
def quick_analyst(m):
    sym = m.text.upper().replace("#", "")
    if not sym.endswith("USDT"): sym += "USDT"
    bot.send_message(m.chat.id, f"🔍 جاري فحص {sym} في جميع المنصات...")
    res = analyze_crypto_v160(sym)
    if res:
        bot.send_message(m.chat.id, f"🏛 **تقرير العملة {sym}**\n━━━━━━━━━━━━━━\nالإشارة: **{res['side']}**\nالقوة: {res['power']}\n━━━━━━━━━━━━━━\n💰 دخول: `{res['p']}`\n🎯 هدف: `{round(res['t'], 4)}` \n🛡️ وقف: `{round(res['s'], 4)}`", parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, f"⚠️ عملة {sym} في منطقة عرضية حالياً. لا يُنصح بالدخول الآن.")

@bot.message_handler(func=lambda m: m.text == "💎 تفعيل VIP")
def pay_btn(m):
    p = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': str(m.chat.id), 'callbackUrl': f"{RENDER_URL}/payment/webhook"}
    link = requests.post("https://api.oxapay.com/merchants/request", json=p).json().get('payLink')
    mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("⚡ دفع آلي سريع (50$)", url=link))
    bot.send_message(m.chat.id, "💎 **اشتراك VIP (30 يوم)**\n\n✅ 6 توصيات يومية قناصة.\n✅ تحليل جميع العملات.\n✅ دعم فني وأهداف دقيقة.", reply_markup=mk)

if __name__ == "__main__":
    threading.Thread(target=run_scanner, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
