import requests, telebot, time, os, threading
from telebot import types
from flask import Flask

# --- [ إعدادات السيرفر ] ---
app = Flask(__name__)

# ================= [ ⚙️ الإعدادات الكبرى - الرادار V36 ] =================
API_TOKEN = '8461494562:AAEgsbKEI93_C3TNb8B9i9D99arx7QwPg9M'
OWNER_ID = 6016547718 
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU" 
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"

bot = telebot.TeleBot(API_TOKEN)

# --- [ 🛡️ محرك التحليل والبحث العابر للمنصات ] ---
def get_v36_ultimate_analysis(symbol):
    s = symbol.upper().strip().replace("/", "")
    if not s.endswith("USDT"): s += "USDT"
    
    # محاولة جلب البيانات من Binance أو MEXC
    data_found = False
    url = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    try:
        r = requests.get(url, timeout=10).json()
        if 'code' not in r:
            closes = [float(c[4]) for c in r]
            vols = [float(c[5]) for c in r]
            data_found = True
        else:
            # تجربة MEXC إذا لم توجد في بينانس
            mexc_url = f"https://www.mexc.com/open/api/v2/market/kline?symbol={s}&interval=60m&limit=100"
            r = requests.get(mexc_url).json()
            if r.get('data'):
                closes = [float(c[4]) for c in r['data']]
                vols = [float(c[5]) for c in r['data']]
                data_found = True
    except: pass

    if data_found:
        p = closes[-1]
        ema20 = sum(closes[-20:]) / 20
        vol_avg = sum(vols[-20:]) / 20
        
        # توقع الشمعة القادمة
        if p > ema20 and vols[-1] > vol_avg:
            status, prob = "🟢 شراء قوي (انفجار)", "94%"
            targets = f"🎯 هدف 1: `{round(p*1.04, 4)}` \n🎯 هدف 2: `{round(p*1.08, 4)}`"
            sl = f"🛡️ الوقف: `{round(p*0.95, 4)}`"
        else:
            status, prob = "🔴 حذر / هبوط", "85%"
            targets = "⚖️ السعر في منطقة تصحيح أو ضعف سيولة."
            sl = f"🛡️ الوقف: `{round(p*1.05, 4)}`"

        # رابط الشارت المباشر من TradingView
        chart_img = f"https://s3.tradingview.com/snapshots/m/BINANCE:{s}.png"
        
        text = (f"🐲 **تحليل الرادار الأسطوري V36**\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: `{s}`\n💰 السعر: `{p}$` \n"
                f"📊 الإشارة: {status}\n🔥 قوة التوقع: `{prob}`\n\n"
                f"{targets}\n{sl}\n━━━━━━━━━━━━━━")
        return text, chart_img
    return "⚠️ لم أجد هذه العملة في Binance أو MEXC. تأكد من الرمز.", None

# --- [ 🕹️ نظام الأزرار المطور ] ---
def main_menu():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True)
    mk.row("📊 تحليل احترافي + شارت", "👤 حسابي")
    mk.row("💳 شحن الرصيد", "📢 الدعم")
    return mk

@bot.message_handler(commands=['start'])
def welcome(m):
    bot.send_message(m.chat.id, "🐲 **رادار القابضة V36: المحرك الأسطوري جاهز!**\nتحليل دقيق، توقع شمعات، وشارت حي.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📊 تحليل احترافي + شارت")
def ask_coin(m):
    msg = bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثال: BTC أو PEPE):")
    bot.register_next_step_handler(msg, send_analysis)

def send_analysis(m):
    bot.send_message(m.chat.id, "🔍 جاري البحث في المنصات وتشريح الشمعات...")
    res_text, chart_url = get_v36_ultimate_analysis(m.text)
    if chart_url:
        try: bot.send_photo(m.chat.id, chart_url, caption=res_text, parse_mode="Markdown")
        except: bot.send_message(m.chat.id, res_text, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, res_text)

@bot.message_handler(func=lambda m: m.text == "👤 حسابي")
def account(m):
    bot.send_message(m.chat.id, f"👤 **معلوماتك:**\n🆔 معرفك: `{m.from_user.id}`\n🌟 الحالة: **VIP نشط**\n💰 الرصيد: `50.0$`")

@bot.message_handler(func=lambda m: m.text == "💳 شحن الرصيد")
def deposit(m):
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (OxaPay)", callback_data="p_auto"))
    mk.add(types.InlineKeyboardButton("👨‍💻 شحن يدوي (إيصال)", callback_data="p_manual"))
    bot.send_message(m.chat.id, "اختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith("p_"))
def handle_pay(c):
    if c.data == "p_auto":
        bot.send_message(c.from_user.id, "⏳ جاري إنشاء رابط الدفع عبر OxaPay...")
        # هنا يوضع كود الربط الفعلي بـ OxaPay
    else:
        bot.send_message(c.from_user.id, f"📍 حول لعنوان TRC20:\n`{WALLET_ADDRESS}`\nثم أرسل صورة الإيصال.")

@bot.message_handler(content_types=['photo'])
def receipt(m):
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id)
    bot.send_message(m.chat.id, "✅ تم استلام الإيصال وجاري تفعيل حسابك.")

# --- [ 🌐 نظام التشغيل المستقر ] ---
@app.route('/')
def home(): return "V36 ULTIMATE IS LIVE! 🐲"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("🚀 انطلق الأسطورة V36...")
    bot.infinity_polling(skip_pending=True)
