import requests, telebot, time, os, threading, json
from datetime import datetime, timedelta
from telebot import types
from flask import Flask

app = Flask(__name__)

# ================= [ ⚙️ الإعدادات الكبرى ] =================
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "radar_users.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ 💾 إدارة قاعدة البيانات ] ---
def load_db():
    if not os.path.exists(DB_FILE): return {}
    with open(DB_FILE, 'r') as f: return json.load(f)

def save_db(db):
    with open(DB_FILE, 'w') as f: json.dump(db, f)

# --- [ 🛡️ محرك التحليل الرباعي + السيولة ] ---
def get_v36_advanced_analysis(symbol):
    s = symbol.upper().strip().replace("/", "")
    if not s.endswith("USDT"): s += "USDT"
    
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10).json()
        closes = [float(c[4]) for c in r]
        vols = [float(c[5]) for c in r]
        highs = [float(c[2]) for c in r]
        lows = [float(c[3]) for c in r]
        
        p = closes[-1]
        # 1. المتوسط المتحرك (EMA)
        ema = sum(closes[-20:]) / 20
        # 2. قوة السيولة (Volume Force)
        vol_avg = sum(vols[-20:]) / 20
        # 3. مؤشر القوة النسبية المبسط (RSI)
        up = sum([max(0, closes[i] - closes[i-1]) for i in range(-14, 0)])
        down = sum([max(0, closes[i-1] - closes[i]) for i in range(-14, 0)])
        rsi = 100 - (100 / (1 + (up/down if down != 0 else 1)))
        
        # منطق التوقع (واقعي ومنطقي)
        if p > ema and vols[-1] > vol_avg and rsi < 70:
            status, pred = "🟢 صعود قوي (اختراق سيولة)", "🚀 الشمعة القادمة: خضراء صاعدة"
            t1, t2, sl = p*1.035, p*1.075, p*0.955
        elif p < ema and vols[-1] > vol_avg:
            status, pred = "🔴 هبوط (ضغط بيعي)", "📉 الشمعة القادمة: حمراء هابطة"
            t1, t2, sl = p*0.965, p*0.925, p*1.045
        else:
            status, pred = "🟡 تذبذب (منطقة حيرة)", "⚖️ لا توجد إشارة واضحة حالياً"
            t1, t2, sl = "---", "---", "---"

        chart = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        res = (f"🐲 **نتائج الرادار V36 الأسطوري**\n━━━━━━━━━━━━━━\n"
               f"🪙 العملة: `{s}` | 💰 السعر: `{p}$` \n"
               f"📊 الإشارة: **{status}**\n🔮 التوقع: `{pred}`\n"
               f"🌡️ مؤشر RSI: `{round(rsi, 2)}` | 🌊 السيولة: `{ 'عالية' if vols[-1]>vol_avg else 'ضعيفة' }` \n\n"
               f"🎯 أهداف: `{round(t1,4) if t1!='---' else '---'}` | `{round(t2,4) if t2!='---' else '---'}`\n"
               f"🛡️ الوقف: `{round(sl,4) if sl!='---' else '---'}`\n━━━━━━━━━━━━━━")
        return res, chart
    except: return "⚠️ عذراً، العملة غير موجودة أو هناك ضغط.", None

# --- [ 🕹️ إدارة المشتركين والقيود ] ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    db = load_db()
    if uid not in db:
        db[uid] = {"sub": False, "exp": None, "free_uses": 0, "daily_count": 0, "last_date": str(datetime.now().date())}
        save_db(db)
    
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("📊 تحليل العملات 📈", "👤 حسابي")
    mk.row("💳 اشتراك (تلقائي/يدوي)", "📢 دعم الرادار")
    bot.send_message(m.chat.id, "🐲 **أهلاً بك في رادار القابضة V36**\n\nنظام التحليل المتطور القائم على السيولة والمؤشرات الحقيقية.", reply_markup=mk)

@bot.message_handler(func=lambda m: m.text == "📊 تحليل العملات 📈")
def check_and_ask(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    today = str(datetime.now().date())
    
    if u['last_date'] != today: u['daily_count'] = 0; u['last_date'] = today; save_db(db)

    if u['sub']:
        if datetime.now() > datetime.strptime(u['exp'], '%Y-%m-%d'):
            u['sub'] = False; save_db(db)
            return bot.send_message(m.chat.id, "❌ انتهى اشتراكك الشهري، يرجى التجديد.")
        if u['daily_count'] >= 5:
            return bot.send_message(m.chat.id, "⚠️ وصلت للحد اليومي (5 عملات). المحاولة القادمة غداً.")
    else:
        if u['free_uses'] >= 5:
            return bot.send_message(m.chat.id, "❌ انتهى حدك المجاني (5 عملات مدى الحياة). يرجى الاشتراك بـ 50$.")

    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC):")
    bot.register_next_step_handler(msg, process_analysis)

def process_analysis(m):
    uid = str(m.from_user.id); db = load_db()
    res, chart = get_v36_advanced_analysis(m.text)
    if chart:
        if db[uid]['sub']: db[uid]['daily_count'] += 1
        else: db[uid]['free_uses'] += 1
        save_db(db)
        bot.send_photo(m.chat.id, chart, caption=res, parse_mode="Markdown")
    else: bot.send_message(m.chat.id, res)

@bot.message_handler(func=lambda m: m.text == "💳 اشتراك (تلقائي/يدوي)")
def payment_options(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ دفع تلقائي (OxaPay)", callback_data="pay_auto"))
    mk.add(types.InlineKeyboardButton("👨‍💻 دفع يدوي (إيصال)", callback_data="pay_manual"))
    bot.send_message(m.chat.id, "اختر طريقة الاشتراك المفضلة (50$ شهر):", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def handle_payment(c):
    uid = str(c.from_user.id)
    if c.data == "pay_auto":
        payload = {'merchant': OXAPAY_KEY, 'amount': 50, 'currency': 'USD', 'description': uid}
        try:
            r = requests.post("https://api.oxapay.com/merchants/request", json=payload).json()
            if r.get('payLink'):
                bot.send_message(uid, f"🔗 [رابط الدفع التلقائي الآمن]({r['payLink']})\nسيتم تفعيل حسابك فور الدفع.", parse_mode="Markdown")
        except: bot.send_message(uid, "⚠️ البوابة الآلية متوقفة، استخدم الدفع اليدوي.")
    else:
        bot.send_message(uid, f"📍 حول الاشتراك لعنوان TRC20:\n`{WALLET_ADDRESS}`\n\nثم أرسل صورة الإيصال هنا.")

@bot.message_handler(content_types=['photo'])
def forward_receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم إرسال الإيصال للمالك. سيتم تفعيل حسابك يدوياً خلال دقائق.")

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def my_acc(m):
    uid = str(m.from_user.id); db = load_db(); u = db[uid]
    status = f"✅ VIP (ينتهي في: {u['exp']})" if u['sub'] else "👤 مجاني"
    limit = f"{u['daily_count']}/5 اليوم" if u['sub'] else f"{u['free_uses']}/5 مدى الحياة"
    bot.send_message(m.chat.id, f"👤 **بروفايلك:**\n🆔 معرفك: `{uid}`\n🛡️ الحالة: {status}\n📊 الاستهلاك: {limit}")

# --- [ تشغيل السيرفر ] ---
@app.route('/')
def home(): return "V36 TITAN IS ALIVE! 🐲"

if __name__ == "__main__":
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))), daemon=True).start()
    bot.infinity_polling(skip_pending=True)
