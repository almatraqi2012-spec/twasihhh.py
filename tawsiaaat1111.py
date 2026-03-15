import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والروابط ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v110_final.json"
RENDER_URL = "https://tawsiaaat1111.onrender.com" 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. إدارة قاعدة البيانات والاشتراكات ] ---
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

# --- [ 3. محرك التحليل الذكي (المثلثات والسيولة) ] ---
def analyze_market_v110(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
    try:
        r = requests.get(url, timeout=10).json()
        df = pd.DataFrame(r, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        p = df['c'].iloc[-1]
        vol_avg = df['v'].rolling(20).mean().iloc[-1]
        
        # استراتيجية كسر المثلث والقمم (فريم 10 ساعات لسرعة الالتقاط)
        high_10 = df['h'].rolling(10).max().iloc[-2]
        low_10 = df['l'].rolling(10).min().iloc[-2]
        
        # شرط السيولة المرن (1.1) لضمان عدم تفويت الفرص
        is_breakout = p > high_10 and df['v'].iloc[-1] > (vol_avg * 1.1)
        is_breakdown = p < low_10 and df['v'].iloc[-1] > (vol_avg * 1.1)
        
        # استراتيجية الأوردر بلوك (OB) - تأكيد الدخول المؤسسي
        is_ob_bullish = (df['l'].iloc[-2] < df['l'].iloc[-3]) and (df['c'].iloc[-1] > df['h'].iloc[-2])
        is_ob_bearish = (df['h'].iloc[-2] > df['h'].iloc[-3]) and (df['c'].iloc[-1] < df['l'].iloc[-2])
        
        rsi = 100 - (100 / (1 + (df['c'].diff().where(df['c'].diff() > 0, 0).rolling(14).mean() / 
                                 -df['c'].diff().where(df['c'].diff() < 0, 0).rolling(14).mean()))).iloc[-1]

        # قرار الدخول (دمج المثلث مع OB لضمان الواقعية)
        if is_breakout and (is_ob_bullish or rsi > 55):
            return {"side": "LONG 🚀", "price": p, "target": p*1.04, "stop": p*0.97}
        elif is_breakdown and (is_ob_bearish or rsi < 45):
            return {"side": "SHORT 📉", "price": p, "target": p*0.96, "stop": p*1.03}
    except: return None

# --- [ 4. نظام المسح الشامل (كل العملات) ] ---
def start_radar_system():
    while True:
        try:
            today = time.strftime("%Y-%m-%d")
            if db.get("last_reset") != today:
                db["vip_daily_count"], db["last_reset"] = {}, today
                save_db()

            # جلب كل العملات مقابل USDT بلا استثناء
            ex_info = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
            all_symbols = [s['symbol'] for s in ex_info['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
            
            for s in all_symbols:
                signal = analyze_market_v110(s)
                if signal:
                    msg = (f"🏛 **رادار القابضة - إشارة قناص**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{s}\n📊 الإشارة: **{signal['side']}**\n"
                           f"━━━━━━━━━━━━━━\n💰 الدخول: `{signal['price']}`\n🎯 الهدف: `{round(signal['target'], 4)}`\n"
                           f"🛡️ الوقف: `{round(signal['stop'], 4)}` \n━━━━━━━━━━━━━━\n"
                           f"🔗 [عرض الشارت المباشر](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
                    
                    for user_id in db["users"]:
                        u_str = str(user_id)
                        is_vip = db["vip"].get(u_str, 0) > time.time()
                        if is_vip:
                            if db["vip_daily_count"].get(u_str, 0) < 6:
                                try: bot.send_message(user_id, msg, parse_mode="Markdown"); db["vip_daily_count"][u_str] = db["vip_daily_count"].get(u_str, 0) + 1
                                except: pass
                        elif db["free_used"].get(u_str, 0) < 3:
                            try: bot.send_message(user_id, "🎁 **توصية مجانية:**\n" + msg, parse_mode="Markdown"); db["free_used"][u_str] = db["free_used"].get(u_str, 0) + 1
                            except: pass
                    save_db()
                time.sleep(0.25) # سرعة مسح عالية لتغطية كل السوق
            time.sleep(60)
        except: time.sleep(10)

# --- [ 5. نظام الدفع التلقائي واليدوي ] ---
@app.route('/payment/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data and data.get('status') in ['confirmed', 'paid']:
        uid = data.get('description')
        if uid:
            db["vip"][str(uid)] = time.time() + (30 * 86400)
            save_db()
            bot.send_message(int(uid), "✅ **تم تفعيل اشتراك VIP بنجاح لمدة 30 يوم!**")
    return "OK", 200

def get_pay_link(chat_id):
    try:
        payload = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': str(chat_id), 'callbackUrl': f"{RENDER_URL}/payment/webhook"}
        return requests.post("https://api.oxapay.com/merchants/request", json=payload, timeout=10).json().get('payLink')
    except: return None

# --- [ 6. واجهة التفاعل ] ---
@bot.message_handler(commands=['start'])
def welcome(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    welcome_text = (f"🏛 **أهلاً بك في رادار القابضة V110**\n\nأقوى منظومة تتبع ذكية لاقتناص فرص التداول. نحن نرصد **تحركات السيولة الكبرى** ونمنحك نقاط دخول دقيقة بأهداف واقعية.\n\n"
                    f"🚀 **التوصيات ستصلك آلياً هنا فور صدورها.. ابقَ متيقظاً!**")
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True).add("👤 حسابي", "💎 تفعيل VIP")
    bot.send_message(m.chat.id, welcome_text, reply_markup=mk, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def account(m):
    uid = str(m.chat.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    st = "VIP 👑" if is_vip else "مجاني 🆓"
    txt = f"👤 **تفاصيل حسابك:**\n🆔 آيدي: `{uid}`\n🌟 الحالة: {st}\n"
    txt += f"📅 توصيات اليوم: {db['vip_daily_count'].get(uid, 0)}/6" if is_vip else f"🎁 متبقي لك: {3 - db['free_used'].get(uid, 0)} توصيات مجانية."
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text == "💎 تفعيل VIP")
def vip(m):
    mk = types.InlineKeyboardMarkup()
    link = get_pay_link(m.chat.id)
    if link: mk.add(types.InlineKeyboardButton("⚡ دفع آلي سريع (50$)", url=link))
    mk.add(types.InlineKeyboardButton("💳 إرسال إيصال يدوي", callback_data="manual"))
    bot.send_message(m.chat.id, "انضم للـ VIP واحصل على 6 توصيات قناصة يومياً مختارة بأعلى معايير الدقة.", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "manual")
def manual(c):
    bot.send_message(c.message.chat.id, f"📌 حول 50$ (USDT.TRC20):\n`{MY_WALLET}`\nأرسل صورة الإيصال هنا.")
    bot.register_next_step_handler(c.message, check)

def check(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل", callback_data=f"act_{m.chat.id}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"إيصال من: `{m.chat.id}`", reply_markup=mk)
        bot.send_message(m.chat.id, "⏳ جاري المراجعة...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("act_"))
def confirm(c):
    tid = c.data.split("_")[1]
    db["vip"][tid] = time.time() + (30 * 86400); save_db()
    bot.send_message(int(tid), "✅ تم تفعيل حسابك!"); bot.answer_callback_query(c.id, "تم")

if __name__ == "__main__":
    threading.Thread(target=start_radar_system, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
