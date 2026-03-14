import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. إعدادات السيرفر والبوت ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v90_final.json"

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

# --- [ 3. محرك الرادار والتحليل الفني (المثلثات والأوردر بلوك) ] ---
def analyze_crypto(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
    try:
        r = requests.get(url, timeout=10).json()
        df = pd.DataFrame(r, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        p = df['c'].iloc[-1]
        vol_avg = df['v'].rolling(20).mean().iloc[-1]
        
        # استراتيجية المثلث الصاعد (Ascending Triangle)
        high_15 = df['h'].rolling(15).max().iloc[-2]
        is_breakout = p > high_15 and df['v'].iloc[-1] > (vol_avg * 1.2)
        
        # استراتيجية الأوردر بلوك (Order Block)
        is_bullish_ob = (df['l'].iloc[-2] < df['l'].iloc[-3]) and (df['c'].iloc[-1] > df['h'].iloc[-2])
        
        rsi = 100 - (100 / (1 + (df['c'].diff().where(df['c'].diff() > 0, 0).rolling(14).mean() / 
                                 -df['c'].diff().where(df['c'].diff() < 0, 0).rolling(14).mean()))).iloc[-1]

        if is_breakout and is_bullish_ob and 50 < rsi < 70:
            return {"side": "LONG 🚀", "price": p, "target": p*1.05, "stop": df['l'].iloc[-5], "strategy": "مثلث صاعد + OB"}
        elif p < df['l'].rolling(15).min().iloc[-2] and rsi < 40:
            return {"side": "SHORT 📉", "price": p, "target": p*0.95, "stop": df['h'].iloc[-5], "strategy": "كسر هيكلي بيعي"}
    except: return None

# --- [ 4. نظام المسح والبث التلقائي ] ---
def scanner_loop():
    while True:
        try:
            # إعادة ضبط العداد اليومي
            if db.get("last_reset") != time.strftime("%Y-%m-%d"):
                db["vip_daily_count"], db["last_reset"] = {}, time.strftime("%Y-%m-%d")
                save_db()

            symbols = [s['symbol'] for s in requests.get("https://api.binance.com/api/v3/exchangeInfo").json()['symbols'] if s['symbol'].endswith('USDT')][:100] # نراقب أعلى 100 عملة سيولة
            for s in symbols:
                res = analyze_crypto(s)
                if res:
                    msg = (f"🏛 **رادار القابضة - إشارة قناص**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{s}\n📊 الإشارة: **{res['side']}**\n💡 الاستراتيجية: {res['strategy']}\n"
                           f"━━━━━━━━━━━━━━\n💰 الدخول: `{res['price']}`\n🎯 الهدف: `{round(res['target'], 4)}`\n🛡️ الوقف: `{round(res['stop'], 4)}` \n"
                           f"━━━━━━━━━━━━━━\n🔗 [الشارت المباشر](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
                    
                    for uid in db["users"]:
                        uid_s = str(uid)
                        is_vip = db["vip"].get(uid_s, 0) > time.time()
                        if is_vip and db["vip_daily_count"].get(uid_s, 0) < 6:
                            bot.send_message(uid, msg, parse_mode="Markdown")
                            db["vip_daily_count"][uid_s] = db["vip_daily_count"].get(uid_s, 0) + 1
                        elif not is_vip and db["free_used"].get(uid_s, 0) < 3:
                            bot.send_message(uid, "🎁 **توصية مجانية:**\n" + msg, parse_mode="Markdown")
                            db["free_used"][uid_s] = db["free_used"].get(uid_s, 0) + 1
                    save_db()
                time.sleep(1)
        except: pass
        time.sleep(300)

# --- [ 5. نظام الدفع والاشتراك (القلب النابض) ] ---
@app.route('/payment/webhook', methods=['POST'])
def oxapay_webhook():
    data = request.json
    if data and data.get('status') in ['confirmed', 'paid']:
        uid = data.get('description')
        if uid:
            db["vip"][str(uid)] = time.time() + (30 * 86400)
            save_db()
            bot.send_message(int(uid), "✅ **تم تفعيل اشتراك VIP آلياً بنجاح!** استمتع بالتوصيات.")
    return "OK", 200

def create_invoice(chat_id):
    try:
        res = requests.post("https://api.oxapay.com/merchants/request", json={
            'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': str(chat_id),
            'callbackUrl': 'https://' + request.host + '/payment/webhook'
        }).json()
        return res.get('payLink')
    except: return None

# --- [ 6. أوامر التفاعل مع المستخدم ] ---
@bot.message_handler(commands=['start'])
def start_cmd(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("👤 حسابي", "💎 تفعيل VIP")
    bot.send_message(m.chat.id, "🏛 **رادار القابضة V90**\n\nأنا أراقب السوق الآن بحثاً عن المثلثات والأوردر بلوك. سأرسل لك التوصيات هنا تلقائياً.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_account(m):
    uid = str(m.chat.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    st = "VIP 👑" if is_vip else "مجاني 🆓"
    txt = f"🆔 آيدي: `{uid}`\n🌟 الحالة: {st}\n📈 توصيات اليوم: {db['vip_daily_count'].get(uid, 0)}/6"
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text == "💎 تفعيل VIP")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup()
    pay_url = create_invoice(m.chat.id)
    if pay_url: mk.add(types.InlineKeyboardButton("⚡ دفع آلي (50$)", url=pay_url))
    mk.add(types.InlineKeyboardButton("💳 إرسال إيصال يدوي", callback_data="manual_pay"))
    bot.send_message(m.chat.id, "اختر طريقة الدفع لتفعيل VIP لمدة 30 يوم:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "manual_pay")
def manual_p(c):
    bot.send_message(c.message.chat.id, f"📌 حول 50$ (USDT.TRC20):\n`{MY_WALLET}`\nثم أرسل صورة الإيصال هنا.")
    bot.register_next_step_handler(c.message, process_receipt)

def process_receipt(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل", callback_data=f"activate_{m.chat.id}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"🔔 إيصال من `{m.chat.id}`", reply_markup=mk)
        bot.send_message(m.chat.id, "⏳ تم استلام الإيصال، انتظر التفعيل.")
    else: bot.send_message(m.chat.id, "⚠️ أرسل صورة فقط.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("activate_"))
def admin_activate(c):
    target = c.data.split("_")[1]
    db["vip"][target] = time.time() + (30 * 86400); save_db()
    bot.send_message(int(target), "✅ تم تفعيل حسابك من قبل الإدارة.")
    bot.answer_callback_query(c.id, "تم التفعيل")

# --- [ 7. التشغيل النهائي ] ---
if __name__ == "__main__":
    threading.Thread(target=scanner_loop, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
