import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات الأساسية ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v130_final.json"
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

# --- [ 3. محرك التحليل الفني (المثلثات، OB، RSI) ] ---
def analyze_crypto_logic(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
    try:
        r = requests.get(url, timeout=10).json()
        df = pd.DataFrame(r, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        p = df['c'].iloc[-1]
        vol_avg = df['v'].rolling(20).mean().iloc[-1]
        
        # استراتيجية المثلث والقمم (فريم 10 ساعات)
        high_10 = df['h'].rolling(10).max().iloc[-2]
        low_10 = df['l'].rolling(10).min().iloc[-2]
        
        # شرط السيولة المرن
        is_breakout = p > high_10 and df['v'].iloc[-1] > (vol_avg * 1.1)
        is_breakdown = p < low_10 and df['v'].iloc[-1] > (vol_avg * 1.1)
        
        # الأوردر بلوك (OB)
        is_ob_bullish = (df['l'].iloc[-2] < df['l'].iloc[-3]) and (df['c'].iloc[-1] > df['h'].iloc[-2])
        is_ob_bearish = (df['h'].iloc[-2] > df['h'].iloc[-3]) and (df['c'].iloc[-1] < df['l'].iloc[-2])
        
        # حساب RSI
        rsi = 100 - (100 / (1 + (df['c'].diff().where(df['c'].diff() > 0, 0).rolling(14).mean() / 
                                 -df['c'].diff().where(df['c'].diff() < 0, 0).rolling(14).mean()))).iloc[-1]

        if is_breakout and (is_ob_bullish or rsi > 52):
            return {"side": "LONG 🚀", "price": p, "target": p*1.04, "stop": p*0.975}
        elif is_breakdown and (is_ob_bearish or rsi < 48):
            return {"side": "SHORT 📉", "price": p, "target": p*0.96, "stop": p*1.025}
    except: return None

# --- [ 4. نظام الرادار (مسح جميع العملات) ] ---
def scanner_engine():
    while True:
        try:
            if db.get("last_reset") != time.strftime("%Y-%m-%d"):
                db["vip_daily_count"], db["last_reset"] = {}, time.strftime("%Y-%m-%d")
                save_db()

            ex_info = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
            symbols = [s['symbol'] for s in ex_info['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
            
            for s in symbols:
                res = analyze_crypto_logic(s)
                if res:
                    msg = (f"🏛 **توصية رادار قناص**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{s}\n📊 الإشارة: **{res['side']}**\n━━━━━━━━━━━━━━\n"
                           f"💰 الدخول: `{res['price']}`\n🎯 الهدف: `{round(res['target'], 4)}`\n"
                           f"🛡️ الوقف: `{round(res['stop'], 4)}` \n━━━━━━━━━━━━━━\n"
                           f"🔗 [عرض الشارت](https://www.tradingview.com/chart/?symbol=BINANCE:{s})")
                    
                    for uid in db["users"]:
                        uid_s = str(uid)
                        is_vip = db["vip"].get(uid_s, 0) > time.time()
                        if is_vip:
                            if db["vip_daily_count"].get(uid_s, 0) < 6:
                                try: bot.send_message(uid, msg, parse_mode="Markdown"); db["vip_daily_count"][uid_s] = db["vip_daily_count"].get(uid_s, 0) + 1
                                except: pass
                        elif db["free_used"].get(uid_s, 0) < 3:
                            try: bot.send_message(uid, "🎁 **توصية مجانية:**\n" + msg, parse_mode="Markdown"); db["free_used"][uid_s] = db["free_used"].get(uid_s, 0) + 1
                            except: pass
                    save_db()
                time.sleep(0.3) 
            time.sleep(60)
        except: time.sleep(20)

# --- [ 5. نظام الدفع (Oxapay + اليدوي) ] ---
@app.route('/payment/webhook', methods=['POST'])
def oxapay_webhook():
    data = request.json
    if data and data.get('status') in ['confirmed', 'paid']:
        uid = data.get('description')
        if uid:
            db["vip"][str(uid)] = time.time() + (30 * 86400)
            save_db()
            bot.send_message(int(uid), "✅ **تم تفعيل اشتراك VIP آلياً بنجاح!**")
    return "OK", 200

def create_pay_link(chat_id):
    try:
        payload = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': str(chat_id), 'callbackUrl': f"{RENDER_URL}/payment/webhook"}
        return requests.post("https://api.oxapay.com/merchants/request", json=payload, timeout=10).json().get('payLink')
    except: return None

# --- [ 6. واجهة التفاعل (المحلل + الأوامر) ] ---
@bot.message_handler(commands=['start'])
def start_bot(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    welcome_msg = ("🏛 **أهلاً بك في رادار القابضة V130**\n\nأقوى منظومة تتبع ذكية لاقتناص الفرص وتحليل العملات آلياً.\n\n"
                   "💡 **كيف تستخدم البوت؟**\n"
                   "1. التوصيات تصلك آلياً هنا فور صدورها.\n"
                   "2. أرسل اسم أي عملة (مثلاً: BTC) وسيقوم المحلل بفحصها لك فوراً.\n\n"
                   "🚀 ابقَ متيقظاً، الصيد القادم وشيك!")
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True).add("👤 حسابي", "💎 تفعيل VIP")
    bot.send_message(m.chat.id, welcome_msg, reply_markup=mk, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def acc_info(m):
    uid = str(m.chat.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    st = "VIP 👑" if is_vip else "مجاني 🆓"
    txt = f"👤 **حسابك:**\n🆔: `{uid}`\n🌟 الحالة: {st}\n"
    txt += f"📅 توصيات اليوم: {db['vip_daily_count'].get(uid, 0)}/6" if is_vip else f"🎁 متبقي لك: {3 - db['free_used'].get(uid, 0)} توصيات مجانية."
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text == "💎 تفعيل VIP")
def vip_pay(m):
    mk = types.InlineKeyboardMarkup()
    p_link = create_pay_link(m.chat.id)
    if p_link: mk.add(types.InlineKeyboardButton("⚡ دفع آلي (50$)", url=p_link))
    mk.add(types.InlineKeyboardButton("💳 إرسال إيصال يدوي", callback_data="manual_up"))
    bot.send_message(m.chat.id, "انضم للـ VIP واحصل على 6 توصيات قناصة يومياً.", reply_markup=mk)

# --- [ المحلل الذكي عند الطلب ] ---
@bot.message_handler(func=lambda m: len(m.text) >= 3 and len(m.text) <= 10 and m.text not in ["👤 حسابي", "💎 تفعيل VIP"])
def handle_analyzer(m):
    sym = m.text.upper().replace("#", "")
    if not sym.endswith("USDT"): sym += "USDT"
    bot.send_message(m.chat.id, f"🔍 جاري فحص عملة {sym}...")
    res = analyze_crypto_logic(sym)
    if res:
        msg = (f"🏛 **تحليل المحلل الذكي - {sym}**\n━━━━━━━━━━━━━━\n"
               f"📊 الإشارة الحالية: **{res['side']}**\n━━━━━━━━━━━━━━\n"
               f"💰 الدخول: `{res['price']}`\n🎯 الهدف: `{round(res['target'], 4)}`\n🛡️ الوقف: `{round(res['stop'], 4)}` \n━━━━━━━━━━━━━━\n"
               f"📈 إدارة مخاطر صارمة.")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, f"❌ عملة {sym} في منطقة تذبذب حالياً، لا توجد إشارة واضحة.")

@bot.callback_query_handler(func=lambda c: c.data == "manual_up")
def man_p(c):
    bot.send_message(c.message.chat.id, f"حول 50$ لـ:\n`{MY_WALLET}`\nوأرسل صورة الإيصال.")
    bot.register_next_step_handler(c.message, process_man)

def process_man(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل", callback_data=f"v_act_{m.chat.id}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"إيصال: `{m.chat.id}`", reply_markup=mk)
        bot.send_message(m.chat.id, "⏳ جاري المراجعة...")

@bot.callback_query_handler(func=lambda c: c.data.startswith("v_act_"))
def adm_c(c):
    tid = c.data.split("_")[2]
    db["vip"][tid] = time.time() + (30 * 86400); save_db()
    bot.send_message(int(tid), "✅ مبروك! تم تفعيل اشتراكك.")
    bot.answer_callback_query(c.id, "تم التفعيل")

# --- [ 7. التشغيل ] ---
if __name__ == "__main__":
    threading.Thread(target=scanner_engine, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
