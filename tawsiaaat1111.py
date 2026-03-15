import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والروابط ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_v100_database.json"
# ملاحظة: استبدل الرابط أدناه برابط تطبيقك على Render ليتم تفعيل الدفع التلقائي
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

# --- [ 3. محرك الرادار (المثلثات والسيولة) ] ---
def analyze_market_v100(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=50"
    try:
        r = requests.get(url, timeout=10).json()
        df = pd.DataFrame(r, columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float)
        p = df['c'].iloc[-1]
        vol_avg = df['v'].rolling(20).mean().iloc[-1]
        
        # استراتيجية كسر المثلث والقمم
        high_max = df['h'].rolling(15).max().iloc[-2]
        is_breakout = p > high_max and df['v'].iloc[-1] > (vol_avg * 1.25)
        
        # استراتيجية الأوردر بلوك (OB)
        is_ob_bullish = (df['l'].iloc[-2] < df['l'].iloc[-3]) and (df['c'].iloc[-1] > df['high'].iloc[-2])
        
        rsi = 100 - (100 / (1 + (df['c'].diff().where(df['c'].diff() > 0, 0).rolling(14).mean() / 
                                 -df['c'].diff().where(df['c'].diff() < 0, 0).rolling(14).mean()))).iloc[-1]

        if is_breakout and is_ob_bullish and 50 < rsi < 72:
            return {"side": "LONG 🚀", "price": p, "target": p*1.05, "stop": df['l'].iloc[-5]}
        elif p < df['l'].rolling(15).min().iloc[-2] and rsi < 42:
            return {"side": "SHORT 📉", "price": p, "target": p*0.95, "stop": df['h'].iloc[-5]}
    except: return None

# --- [ 4. نظام المسح والبث الذكي ] ---
def start_radar_system():
    while True:
        try:
            # تصفير العداد اليومي للـ VIP
            today = time.strftime("%Y-%m-%d")
            if db.get("last_reset") != today:
                db["vip_daily_count"] = {}
                db["last_reset"] = today
                save_db()

            # جلب كل العملات من بينانس
            all_symbols = [s['symbol'] for s in requests.get("https://api.binance.com/api/v3/exchangeInfo").json()['symbols'] if s['symbol'].endswith('USDT') and s['status'] == 'TRADING']
            
            for s in all_symbols[:150]: # مسح أفضل 150 عملة سيولة لضمان السرعة والجودة
                signal = analyze_market_v100(s)
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
                            count = db["vip_daily_count"].get(u_str, 0)
                            if count < 6: # حد الـ 6 توصيات يومياً
                                try: bot.send_message(user_id, msg, parse_mode="Markdown"); db["vip_daily_count"][u_str] = count + 1
                                except: pass
                        else:
                            free_c = db["free_used"].get(u_str, 0)
                            if free_c < 3: # حد الـ 3 توصيات مجانية مدى الحياة
                                try: bot.send_message(user_id, "🎁 **توصية مجانية:**\n" + msg, parse_mode="Markdown"); db["free_used"][u_str] = free_c + 1
                                except: pass
                    save_db()
                time.sleep(0.5)
        except: time.sleep(10)

# --- [ 5. نظام الدفع التلقائي (Webhook) ] ---
@app.route('/payment/webhook', methods=['POST'])
def webhook_listener():
    data = request.json
    if data and data.get('status') in ['confirmed', 'paid']:
        uid = data.get('description')
        if uid:
            db["vip"][str(uid)] = time.time() + (30 * 86400) # إضافة 30 يوم
            save_db()
            try: bot.send_message(int(uid), "✅ **مبروك! تم تفعيل اشتراك VIP بنجاح.**\nستصلك الآن أقوى 6 توصيات يومياً.")
            except: pass
    return "OK", 200

def get_payment_link(chat_id):
    try:
        payload = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': str(chat_id), 'callbackUrl': f"{RENDER_URL}/payment/webhook"}
        r = requests.post("https://api.oxapay.com/merchants/request", json=payload, timeout=10).json()
        return r.get('payLink')
    except: return None

# --- [ 6. أوامر البوت والتفاعل ] ---
@bot.message_handler(commands=['start'])
def welcome_msg(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: db["users"].append(uid); save_db()
    
    welcome_text = (
        "🏛 **أهلاً بك في رادار القابضة V100**\n\n"
        "أقوى منظومة تتبع ذكية لاقتناص فرص التداول. نحن نرصد **تحركات السيولة الكبرى** ونمنحك نقاط دخول دقيقة بأهداف واقعية.\n\n"
        "🚀 **التوصيات ستصلك آلياً هنا فور صدورها.. ابقَ متيقظاً!**"
    )
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("👤 حسابي", "💎 تفعيل VIP")
    bot.send_message(m.chat.id, welcome_text, reply_markup=mk, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.chat.id)
    is_vip = db["vip"].get(uid, 0) > time.time()
    status = "VIP 👑" if is_vip else "مجاني 🆓"
    txt = f"👤 **تفاصيل حسابك:**\n🆔 آيدي: `{uid}`\n🌟 الحالة: {status}\n"
    if is_vip: txt += f"📅 توصيات اليوم: {db['vip_daily_count'].get(uid, 0)}/6"
    else: txt += f"🎁 متبقي لك: {3 - db['free_used'].get(uid, 0)} توصيات مجانية."
    bot.send_message(m.chat.id, txt)

@bot.message_handler(func=lambda m: m.text == "💎 تفعيل VIP")
def vip_menu(m):
    mk = types.InlineKeyboardMarkup()
    p_link = get_payment_link(m.chat.id)
    if p_link: mk.add(types.InlineKeyboardButton("⚡ دفع آلي سريع (50$)", url=p_link))
    mk.add(types.InlineKeyboardButton("💳 إرسال إيصال يدوي", callback_data="manual"))
    bot.send_message(m.chat.id, "انضم للـ VIP واحصل على 6 توصيات قناصة يومياً مختارة بأعلى معايير الدقة.", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "manual")
def manual_pay(c):
    bot.send_message(c.message.chat.id, f"📌 حول 50$ (USDT.TRC20):\n`{MY_WALLET}`\nثم أرسل صورة الإيصال هنا.")
    bot.register_next_step_handler(c.message, check_receipt)

def check_receipt(m):
    if m.photo:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ تفعيل الحساب", callback_data=f"adm_act_{m.chat.id}"))
        bot.send_photo(OWNER_ID, m.photo[-1].file_id, caption=f"إيصال جديد من: `{m.chat.id}`", reply_markup=mk)
        bot.send_message(m.chat.id, "⏳ جاري مراجعة الإيصال من قبل الإدارة..")

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_act_"))
def admin_confirm(c):
    tid = c.data.split("_")[2]
    db["vip"][tid] = time.time() + (30 * 86400); save_db()
    bot.send_message(int(tid), "✅ تم تفعيل اشتراك VIP الخاص بك بنجاح!")
    bot.answer_callback_query(c.id, "تم التفعيل بنجاح")

# --- [ 7. التشغيل النهائي ] ---
if __name__ == "__main__":
    threading.Thread(target=start_radar_system, daemon=True).start()
    threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
