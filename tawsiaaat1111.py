import requests, telebot, time, json, os, threading, datetime
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ 1. الإعدادات والتحصين ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_USDT_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA" 
WEBHOOK_URL = "https://tawsiaaat1111.onrender.com" 
DB_FILE = "radar_global_final_v10.json"

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ 2. إدارة قاعدة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"users": {}, "vip_list": {}}

db = load_db()
def save_db():
    try:
        with open(DB_FILE, 'w') as f: json.dump(db, f, indent=4)
    except: pass

# --- [ 3. محرك التحقق ] ---
def is_vip(uid):
    uid = str(uid)
    if uid in db["vip_list"]:
        exp = datetime.datetime.strptime(db["vip_list"][uid], '%Y-%m-%d')
        return datetime.datetime.now() < exp
    return False

# --- [ 4. قائمة الأزرار الرئيسية ] ---
def main_menu():
    m = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي", "📞 الدعم الفني")
    return m

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.chat.id)
    if uid not in db["users"]: 
        db["users"][uid] = {"free_total": 0, "daily_analysis": 0}
    save_db()
    bot.send_message(uid, "🏛 **مرحباً بك في رادار القابضة**\nأقوى نظام لتحليل وتوصيات الكريبتو.", reply_markup=main_menu())

# --- [ 5. اشتراك VIP (الأزرار التي طلبتها) ] ---
@bot.message_handler(func=lambda m: m.text == "👑 اشتراك VIP")
def vip_section(m):
    text = (f"💎 **باقة VIP الإمبراطورية**\n\n"
            f"✅ 6 تحليلات يدوية يومياً.\n"
            f"✅ 6 توصيات آلية (أقوى فرص السوق).\n"
            f"✅ اشتراك كامل لمدة 30 يوم.\n\n"
            f"💰 السعر: **50$ USDT**")
    
    # الأزرار المطلوبة (تلقائي ويدوي)
    mk = types.InlineKeyboardMarkup(row_width=1)
    # زر التفعيل التلقائي يفتح رابط OxaPay فوراً
    pay_url = f"https://oxapay.com/pay/50/USDT/{m.chat.id}"
    mk.add(types.InlineKeyboardButton("⚡ تفعيل تلقائي (OxaPay)", url=pay_url))
    # زر التفعيل اليدوي يرسل "طلب" للبوت لاستقبال صورة
    mk.add(types.InlineKeyboardButton("📥 تفعيل يدوي (إرسال إيصال)", callback_data="manual_payment"))
    
    bot.send_message(m.chat.id, text, reply_markup=mk, parse_mode="Markdown")

# --- [ 6. معالجة استجابة الأزرار (Callback) ] ---
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    uid = str(call.message.chat.id)
    if call.data == "manual_payment":
        bot.send_message(uid, f"📥 **قسم التفعيل اليدوي**\n\nقم بتحويل مبلغ **50$** (USDT TRC20) للمحفظة:\n`{MY_USDT_WALLET}`\n\nثم أرسل **صورة الإيصال** هنا في الشات وسنقوم بتفعيلك فوراً.")

# --- [ 7. المحلل الذكي (التحكم بـ 6 عملات) ] ---
@bot.message_handler(func=lambda m: m.text == "🔍 المحلل الذكي")
def analysis_gate(m):
    uid = str(m.chat.id)
    user_data = db["users"].get(uid, {"free_total": 0, "daily_analysis": 0})
    
    if not is_vip(uid):
        if user_data.get("free_total", 0) >= 5:
            return bot.send_message(uid, "⚠️ انتهت محاولاتك المجانية (5/5). اشترك الآن للفتح.")
    else:
        if user_data.get("daily_analysis", 0) >= 6:
            return bot.send_message(uid, "🚫 اكتملت حصتك اليومية (6/6). انتظر للغد.")

    msg = bot.send_message(uid, "📝 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, run_analysis)

def run_analysis(m):
    uid = str(m.chat.id)
    if m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي", "📞 الدعم الفني"]: return
    
    symbol = m.text.upper().replace("#", "").strip()
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}USDT&interval=1h&limit=100"
        r = requests.get(url).json()
        df = pd.DataFrame(r).astype(float)
        cp = df[4].iloc[-1]
        ema = df[4].ewm(span=20).mean().iloc[-1]
        side = "LONG 🚀" if cp > ema else "SHORT 📉"
        
        bot.send_message(uid, f"🏛 **تحليل {symbol}**\n━━━━━━━━\nالإشارة: {side}\nالسعر: `{cp}`\n━━━━━━━━")
        
        # تحديث العدادات
        if is_vip(uid): db["users"][uid]["daily_analysis"] += 1
        else: db["users"][uid]["free_total"] += 1
        save_db()
    except:
        bot.send_message(uid, "❌ عملة غير صحيحة.")

# --- [ 8. استقبال الإيصالات والرسائل ] ---
@bot.message_handler(content_types=['photo', 'text'])
def support_handler(m):
    uid = str(m.chat.id)
    # حماية الأوامر
    if m.text and (m.text.startswith('/') or m.text in ["🔍 المحلل الذكي", "👑 اشتراك VIP", "👤 حسابي", "📞 الدعم الفني"]): return
    if uid == str(OWNER_ID): return

    if m.content_type == 'photo':
        bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
        bot.send_message(OWNER_ID, f"🖼 **إيصال دفع جديد!**\nالآيدي: `{uid}`\nللتفعيل: `/activate {uid}`")
        bot.send_message(uid, "✅ تم إرسال الإيصال للإدارة للمراجعة.")
    else:
        bot.send_message(OWNER_ID, f"📩 رسالة دعم من `{uid}`: {m.text}")
        bot.send_message(uid, "✅ تم استلام رسالتك.")

# --- [ 9. أوامر المالك ] ---
@bot.message_handler(commands=['activate'])
def admin_activate(m):
    if str(m.chat.id) == str(OWNER_ID):
        try:
            target = m.text.split()[1]
            exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            db["vip_list"][target] = exp; save_db()
            bot.send_message(target, f"👑 تم تفعيل VIP بنجاح حتى: {exp}")
            bot.send_message(OWNER_ID, f"✅ تم تفعيل {target}")
        except: pass

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def account(m):
    uid = str(m.chat.id)
    status = "👑 VIP" if is_vip(uid) else "🆓 مجاني"
    daily = db["users"].get(uid, {}).get("daily_analysis", 0) if is_vip(uid) else db["users"].get(uid, {}).get("free_total", 0)
    bot.send_message(uid, f"👤 **بياناتك:**\nالحالة: {status}\nالاستهلاك اليومي: {daily}/6")

@bot.message_handler(func=lambda m: m.text == "📞 الدعم الفني")
def support(m):
    bot.send_message(m.chat.id, "👋 أرسل استفسارك وسنقوم بالرد عليك فوراً.")

# --- [ محرك تصفير العداد اليومي ] ---
def reset_loop():
    while True:
        now = datetime.datetime.now()
        if now.hour == 0 and now.minute == 0:
            for u in db["users"]: db["users"][u]["daily_analysis"] = 0
            save_db()
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=reset_loop, daemon=True).start()
    bot.infinity_polling()
