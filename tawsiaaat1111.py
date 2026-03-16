import requests, telebot, time, json, os, threading
import pandas as pd
from telebot import types
from flask import Flask, request

# --- [ الإعدادات ] ---
API_TOKEN = '8461494562:AAEQGbNessZGroYrttf5_gDRsVfNJ2j_6MI'
OWNER_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
DB_FILE = "radar_global_final.json"
RENDER_URL = "https://tawsiaaat1111.onrender.com" 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- [ محرك جلب البيانات المزدوج (Binance & MEXC) ] ---
def get_data(symbol):
    s = symbol.upper().replace("#", "").strip()
    if not s.endswith("USDT"): s += "USDT"
    
    # محاولة جلب البيانات من بينانس أولاً
    url_binance = f"https://api.binance.com/api/v3/klines?symbol={s}&interval=1h&limit=100"
    # محاولة جلب البيانات من مكسيك كبديل أو كإضافة
    url_mexc = f"https://api.mexc.com/api/v3/klines?symbol={s}&interval=60m&limit=100"
    
    try:
        r = requests.get(url_binance, timeout=5)
        if r.status_code == 200:
            return pd.DataFrame(r.json(), columns=['t','o','h','l','c','v','ct','q','n','tb','tq','i']).astype(float), s, "Binance 🟡"
        
        # إذا فشلت بينانس، نجرب مكسيك (للعملات الجديدة والميمز)
        r = requests.get(url_mexc, timeout=5)
        if r.status_code == 200:
            return pd.DataFrame(r.json(), columns=['t','o','h','l','c','v','ct','q']).astype(float), s, "MEXC 🟢"
            
        return None, s, None
    except:
        return None, s, None

# --- [ محرك التحليل الاحترافي ] ---
def analyze_crypto_v210(symbol):
    df, full_name, exchange = get_data(symbol)
    if df is None: return None
    
    cp = df['c'].iloc[-1]
    # تحليل الهيكل (متوسطات + سيولة + RSI)
    ema20 = df['c'].ewm(span=20).mean().iloc[-1]
    ema50 = df['c'].ewm(span=50).mean().iloc[-1]
    vol_ratio = df['v'].iloc[-1] / (df['v'].rolling(20).mean().iloc[-1] + 1e-10)
    
    # منطق RSI
    delta = df['c'].diff()
    rsi = 100 - (100 / (1 + (delta.where(delta > 0, 0).rolling(14).mean().iloc[-1] / 
                             (-delta.where(delta < 0, 0).rolling(14).mean().iloc[-1] + 1e-10))))

    # تحديد الإشارة بناءً على تقاطع المتوسطات والسيولة
    if cp > ema20 and rsi > 55:
        side = "LONG 🚀 (صعود)"
    elif cp < ema20 and rsi < 45:
        side = "SHORT 📉 (هبوط)"
    else:
        side = "تذبذب ⚖️ (انتظار)"

    return {"p": cp, "side": side, "rsi": round(rsi, 1), "liq": round(vol_ratio, 2), "sym": full_name, "ex": exchange}

# --- [ الرادار الشامل - يمسح المنصتين ] ---
def scanner_engine():
    while True:
        try:
            # جلب قائمة العملات من بينانس (كمرجع أساسي للسيولة)
            ex = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
            symbols = [s['symbol'] for s in ex['symbols'] if s['symbol'].endswith('USDT')][:100]
            
            for s in symbols:
                res = analyze_crypto_v210(s)
                # إرسال تلقائي فقط للفرص "القوية" (سيولة عالية + اتجاه واضح)
                if res and res['liq'] > 2.5 and "تذبذب" not in res['side']:
                    msg = (f"🏛 **رادار القابضة - فرصة ذهبية**\n━━━━━━━━━━━━━━\n"
                           f"🪙 العملة: #{res['sym']}\n🏦 المنصة: {res['ex']}\n"
                           f"📊 الإشارة: **{res['side']}**\n🌊 السيولة: `{res['liq']}x`\n━━━━━━━━━━━━━━\n"
                           f"💰 دخول: `{res['p']}`\n🎯 الهدف: `{round(res['p']*1.05 if 'LONG' in res['side'] else res['p']*0.95, 4)}` \n━━━━━━━━━━━━━━")
                    
                    # إرسال لكل المستخدمين (مع مراعاة حدود VIP)
                    # (هنا يوضع كود الإرسال كما في النسخ السابقة)
                    pass
                time.sleep(0.2)
            time.sleep(60)
        except: time.sleep(10)

# --- [ معالجة الرسائل ] ---
@bot.message_handler(func=lambda m: m.text not in ["👤 حسابي", "💎 تفعيل VIP", "/start"])
def handle_manual(m):
    user_input = m.text.upper().strip()
    bot.send_message(m.chat.id, f"📡 جاري مسح Binance & MEXC للبحث عن {user_input}...")
    
    res = analyze_crypto_v210(user_input)
    if res:
        msg = (f"🏛 **نتائج الرادار المزدوج: {res['sym']}**\n"
               f"━━━━━━━━━━━━━━\n"
               f"🏦 المصدر: {res['ex']}\n"
               f"💰 السعر: `{res['p']}`\n"
               f"📊 الإشارة: **{res['side']}**\n"
               f"🌊 السيولة: `{res['liq']}x` | RSI: `{res['rsi']}`\n"
               f"━━━━━━━━━━━━━━\n"
               f"🎯 الهدف: `{round(res['p']*1.03 if 'LONG' in res['side'] else res['p']*0.97, 4)}` \n"
               f"❌ الوقف: `{round(res['p']*0.97 if 'LONG' in res['side'] else res['p']*1.03, 4)}` ")
        bot.send_message(m.chat.id, msg, parse_mode="Markdown")
    else:
        bot.send_message(m.chat.id, "❌ لم يتم العثور على العملة في Binance أو MEXC. تأكد من الرمز.")

if __name__ == "__main__":
    threading.Thread(target=scanner_engine, daemon=True).start()
    bot.infinity_polling()
