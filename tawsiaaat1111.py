import requests, telebot, time, json, os, datetime
from telebot import types
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home(): return "Radar is Online!"

def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()
# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAF3PnajVvXjzL1-aC8RxJwHmP5ahmTIvcs'
OWNER_ID = '6016547718'
WALLET_ADDRESS = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
DB_FILE = "final_db.json"

bot = telebot.TeleBot(API_TOKEN)

# --- [ إدارة البيانات ] ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                data = json.load(f)
                if "usage" not in data: data["usage"] = {}
                if "vip" not in data: data["vip"] = {OWNER_ID: 9999999999}
                return data
        except: pass
    return {"vip": {OWNER_ID: 9999999999}, "usage": {}}

db = load_db()

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump(db, f)

def check_access(uid):
    now = time.time()
    today = datetime.date.today().isoformat()

    # ضمان وجود سجل للمستخدم
    if uid not in db["usage"] or not isinstance(db["usage"][uid], dict):
        db["usage"][uid] = {"count": 0, "last_reset": today, "total_free": 0}
        save_db()

    # 1. فحص الـ VIP (هل مشترك؟ وهل الوقت لم ينتهِ؟)
    if uid in db["vip"] and db["vip"][uid] > now:
        # نظام الـ 5 محاولات اليومية للمشترك
        if db["usage"][uid].get("last_reset") != today:
            db["usage"][uid]["count"] = 0
            db["usage"][uid]["last_reset"] = today
            save_db()

        if db["usage"][uid]["count"] < 5:
            return True, "ok"
        else:
            return False, "daily_limit"

    # 2. إذا كان مشتركاً وانتهت مدة الشهر (30 يوم)
    elif uid in db["vip"] and db["vip"][uid] <= now:
        return False, "expired"

    # 3. المستخدم المجاني (5 محاولات للأبد)
    else:
        if db["usage"][uid].get("total_free", 0) < 5:
            return True, "free_ok"
        else:
            return False, "need_sub"

# --- [ محرك التحليل ] ---
def get_pro_analysis(symbol):
    try:
        symbol = symbol.upper().replace("/", "").strip()
        if not symbol.endswith("USDT"): symbol += "USDT"

        source = "BINANCE"
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
        res = requests.get(url, timeout=5).json()

        if isinstance(res, dict) and (res.get('code') == -1121 or 'msg' in res):
            source = "MEXC"
            url = f"https://api.mexc.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
            res = requests.get(url, timeout=5).json()

        # قراءة البيانات
        closes = [float(c[4]) for c in res]
        highs = [float(c[2]) for c in res]
        lows = [float(c[3]) for c in res]
        volumes = [float(c[5]) for c in res]  # إضافة بيانات الفوليوم

        live_price = closes[-1]
        avg_volume = sum(volumes[-20:]) / 20  # متوسط الفوليوم لآخر 20 شمعة
        current_volume = volumes[-1]

        # حساب RSI
        sma = sum(closes[-20:]) / 20
        gains = sum([max(0, closes[i] - closes[i-1]) for i in range(-14, 0)])
        losses = sum([max(0, closes[i-1] - closes[i]) for i in range(-14, 0)])
        rsi = 100 - (100 / (1 + (gains/losses if losses != 0 else 1)))

        # تحليل قوة السيولة (Volume Analysis)
        vol_status = "💎 سيولة عالية" if current_volume > avg_volume else "⚠️ سيولة ضعيفة"

        # منطق الإشارات المطور
        highest, lowest = max(highs), min(lows)
        
        if live_price <= lowest * 1.01 and rsi < 35:
            s, t = "🚀 شراء (قاع مؤكد)", "📈 ارتداد قوي مدعوم بالسيولة" if current_volume > avg_volume else "📈 ارتداد ضعيف"
            tg, sl = live_price * 1.03, lowest * 0.98  # أهداف واقعية 3%
        elif live_price >= highest * 0.99 or rsi > 70:
            s, t = "⚠️ بيع (قمة)", "📉 تصحيح متوقع"
            tg, sl = live_price * 0.97, highest * 1.02
        elif current_volume > avg_volume * 1.5 and live_price > sma:
            s, t = "🔥 انفجار سعري", "✅ دخول سيولة ضخمة الآن"
            tg, sl = live_price * 1.05, live_price * 0.97
        else:
            s, t = "⚖️ تذبذب", "⏳ انتظر إشارة أقوى"
            tg, sl = sma, live_price * 0.98

        return (f"🏛 **رادار القابضة** | `{source}`\n━━━━━━━━━━━━━━\n"
                f"🪙 العملة: #{symbol}\n💰 السعر: `{live_price:.4f}`\n"
                f"📊 RSI: {rsi:.1f} | {vol_status}\n━━━━━━━━━━━━━━\n"
                f"💡 الإشارة: **{s}**\n📌 التوجه: {t}\n━━━━━━━━━━━━━━\n"
                f"🎯 الهدف: `{tg:.4f}`\n🛡️ الوقف: `{sl:.4f}`\n"
                f"🔗 [الشارت المباشر](https://www.tradingview.com/chart/?symbol={source}:{symbol})")
    except Exception as e:
        return None
# --- [ الأوامر ] ---
@bot.message_handler(commands=['start'])
def start_cmd(m):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔍 تحليل عملة", "💎 حالة اشتراكي")
    markup.add("💳 بيانات الدفع (50$)", "👨‍💻 تفعيل الحساب")
    bot.send_message(m.chat.id, f"👋 أهلاً بك يا {m.from_user.first_name} في رادار القابضة!\nلديك 5 محاولات مجانية للأبد.", reply_markup=markup)

@bot.message_handler(commands=['activate'])
def admin_activate(m):
    if str(m.from_user.id) == OWNER_ID:
        try:
            tid = m.text.split()[1]
            # تفعيل لمدة 30 يوم من لحظة كتابة الأمر
            db["vip"][str(tid)] = time.time() + (30 * 86400)
            save_db()
            bot.send_message(OWNER_ID, f"✅ تم تفعيل `{tid}` لمدة 30 يوم.")
            bot.send_message(tid, "🌟 مبروك! تم تفعيل اشتراكك VIP لمدة 30 يوم بنجاح.")
        except:
            bot.send_message(OWNER_ID, "⚠️ اكتب: `/activate ID`")

user_state = {}

@bot.message_handler(func=lambda m: True)
def handle_messages(m):
    uid = str(m.from_user.id)

    if m.text == "🔍 تحليل عملة":
        can, reason = check_access(uid)
        if can:
            user_state[uid] = "waiting_coin"
            bot.send_message(m.chat.id, "🎯 أرسل رمز العملة (مثلاً: BTC):")
        else:
            if reason == "expired":
                bot.send_message(m.chat.id, "⚠️ انتهى اشتراكك الشهري. يرجى التجديد بـ 70$.")
            elif reason == "daily_limit":
                bot.send_message(m.chat.id, "❌ استهلكت حدك اليومي (5/5). حاول غداً.")
            else:
                bot.send_message(m.chat.id, "❌ انتهت الـ 5 محاولات المجانية. يرجى الاشتراك بـ 70$.")

    elif m.text == "💎 حالة اشتراكي":
        now = time.time()
        is_v = uid in db["vip"] and db["vip"][uid] > now
        if is_v:
            rem = int((db["vip"][uid] - now) / 86400)
            bot.send_message(m.chat.id, f"🌟 اشتراك VIP نشط\n⏳ متبقي: {rem} يوم\n📊 استهلاك اليوم: {db['usage'][uid]['count']}/5")
        elif uid in db["vip"] and db["vip"][uid] <= now:
            bot.send_message(m.chat.id, "⚠️ اشتراكك منتهي. يرجى التجديد.")
        else:
            total = db["usage"][uid].get("total_free", 0)
            bot.send_message(m.chat.id, f"👤 حساب عادي\n📊 محاولات مجانية متبقية: {5 - total}/5")

    elif m.text == "💳 بيانات الدفع (70$)":
        bot.send_message(m.chat.id, f"💳 الدفع USDT TRC20:\n`{WALLET_ADDRESS}`")

    elif m.text == "👨‍💻 تفعيل الحساب":
        user_state[uid] = "waiting_proof"
        bot.send_message(m.chat.id, "📝 أرسل الـ ID الخاص بك مع صورة اثبات الدفع هنا للتفعيل:")

    elif uid in user_state:
        st = user_state[uid]
        if st == "waiting_coin":
            res = get_pro_analysis(m.text)
            if res:
                # حسم المحاولة
                if uid in db["vip"] and db["vip"][uid] > time.time():
                    db["usage"][uid]["count"] += 1
                else:
                    db["usage"][uid]["total_free"] = db["usage"][uid].get("total_free", 0) + 1
                save_db()
                bot.send_message(m.chat.id, res, parse_mode="Markdown")
            else: bot.send_message(m.chat.id, "⚠️ رمز غير صحيح.")
        elif st == "waiting_proof":
            bot.send_message(OWNER_ID, f"🔔 طلب تفعيل من: `{uid}`")
            bot.send_message(m.chat.id, "✅ تم إرسال طلبك.")
        del user_state[uid]

bot.infinity_polling()
