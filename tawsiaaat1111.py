import telebot, threading, time, asyncio, requests, random, os
from telebot import types
from telethon import TelegramClient, functions, types as tl_types
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest
from telethon.tl.types import UserStatusRecently, UserStatusOnline
from telethon.errors import *

# ================= [ ⚙️ الإعدادات المركزية ] ================
BOT_TOKEN = "8574116889:AAE39BjBYZbk8ps5dg3Ix9yIVC7cIx5B_cg"
MY_API_ID = 23269382
MY_API_HASH = 'fe19c565fb4378bd5128885428ff8e26'
ADMIN_ID = 6016547718
OXAPAY_KEY = "CE8H0F-ISXBD2-RXHALY-KZXUZU"
MY_WALLET = "TLtLuhkU2kkkR1Wz1TtrBTpoNRTNviYpsA"
PRICE_PER_MEMBER = 0.04 

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ================= [ 🛠️ وظائف البيانات ] ================

def get_balance(uid):
    file = f"bal_{uid}.txt"
    if not os.path.exists(file): return 0.0
    with open(file, 'r') as f:
        try: return float(f.read())
        except: return 0.0

def update_balance(uid, amount):
    bal = get_balance(uid) + amount
    with open(f"bal_{uid}.txt", 'w') as f: f.write(str(round(bal, 2)))

def get_army(uid):
    return [f for f in os.listdir('.') if f.startswith(f"sess_{uid}_") and f.endswith('.session')]

# ================= [ 📱 الأزرار الرئيسية ] ================

def main_markup():
    mk = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    mk.add("⚔️ بدء الهجوم (قوة التحدي)", "➕ إضافة حساب للجيش")
    mk.add("💰 شحن الرصيد", "👤 حسابي")
    mk.add("🗑️ حذف حساب", "📊 إحصائيات النظام")
    return mk

@bot.message_handler(commands=['start'])
def start_cmd(m):
    bot.clear_step_handler_by_chat_id(m.chat.id)
    bot.send_message(m.chat.id, "🐲 **مرحباً بك في منصة دراجون V36 - كود التحدي**\nنظام الجر القسري الفعلي نشط الآن.", reply_markup=main_markup())

# ================= [ ⚔️ خوارزمية التحدي (الجر الفعلي) ] ================

async def dragon_challenge_engine(army, src, trg, target_count, uid):
    success = 0
    scout_sess = army[0].replace('.session','')
    scout = TelegramClient(scout_sess, MY_API_ID, MY_API_HASH)
    
    try:
        await scout.connect()
        # سحب كمية ضخمة لضمان الوصول للعدد المطلوب رغم الخصوصية
        targets = []
        async for u in scout.iter_participants(src, limit=target_count * 25):
            if u.username and not u.bot:
                if isinstance(u.status, (UserStatusRecently, UserStatusOnline)):
                    targets.append(u)
        await scout.disconnect()
    except Exception as e:
        return bot.send_message(uid, f"❌ خطأ رادار المصدر: {e}")

    if not targets:
        return bot.send_message(uid, "❌ المصدر فارغ من الأعضاء النشطين.")

    bot.send_message(uid, f"⚔️ **بدأ التحدي! الهدف: إضافة {target_count} عضو فعلياً.**")

    # حلقة الجر القسري - لا تتوقف إلا باكتمال العدد
    for target in targets:
        if success >= target_count: break
        
        # تبديل حساب الجيش تلقائياً عند كل محاولة
        current_sess = army[success % len(army)].replace('.session','')
        client = TelegramClient(current_sess, MY_API_ID, MY_API_HASH)
        
        try:
            await client.connect()
            # محاولة الانضمام الصامت للكروب الهدف
            try: await client(JoinChannelRequest(trg))
            except: pass
            
            # --- سطر الجر الفعلي ---
            await client(InviteToChannelRequest(trg, [target]))
            
            # احتساب النجاح والخصم فقط عند الإضافة الفعلية
            success += 1
            update_balance(uid, -PRICE_PER_MEMBER)
            bot.send_message(uid, f"✅ [{success}/{target_count}] تم الجر: `@{target.username}`")
            
            await client.disconnect()
            await asyncio.sleep(random.randint(15, 30)) # فاصل حماية
            
        except (UserPrivacyRestrictedError, UserAlreadyParticipantError, UserBannedInChannelError):
            await client.disconnect() # تجاوز الخصوصية بصمت والانتقال لليوزر التالي
            continue
        except PeerFloodError:
            await client.disconnect() # الحساب تعب، الخوارزمية تنتقل للحساب التالي فوراً
            continue
        except Exception:
            await client.disconnect()
            continue

    bot.send_message(uid, f"🏁 **تمت المهمة بنجاح!**\n✅ الأعضاء المضافين فعلياً: `{success}`\n💰 الرصيد المتبقي: `{get_balance(uid)}$`")

# ================= [ 🛡️ إدارة الجيش ] ================

@bot.message_handler(func=lambda m: m.text == "➕ إضافة حساب للجيش")
def add_acc(m):
    msg = bot.send_message(m.chat.id, "📱 أرسل رقم الهاتف (مثال: +967...):")
    bot.register_next_step_handler(msg, process_phone)

def process_phone(m):
    phone = m.text.replace(' ','')
    sess_id = f"sess_{m.chat.id}_{phone.replace('+','')}"
    client = TelegramClient(sess_id, MY_API_ID, MY_API_HASH)
    async def get_code():
        await client.connect()
        try:
            res = await client.send_code_request(phone)
            return res.phone_code_hash, True
        except Exception as e: return str(e), False
        finally: await client.disconnect()
    
    h, ok = asyncio.run(get_code())
    if ok:
        msg = bot.send_message(m.chat.id, "📩 أرسل كود التحقق:")
        bot.register_next_step_handler(msg, process_otp, phone, h, sess_id)
    else: bot.send_message(m.chat.id, f"❌ خطأ: {h}")

def process_otp(m, ph, h, sess):
    otp = m.text.strip()
    client = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    async def sign():
        await client.connect()
        try:
            await client.sign_in(ph, otp, phone_code_hash=h)
            return "OK", False
        except SessionPasswordNeededError: return "2FA", True
        except Exception as e: return str(e), False
        finally: await client.disconnect()

    res, need_2fa = asyncio.run(sign())
    if res == "OK": bot.send_message(m.chat.id, "✅ تم إضافة الحساب للجيش!")
    elif need_2fa:
        msg = bot.send_message(m.chat.id, "🔐 أرسل كلمة السر (2FA):")
        bot.register_next_step_handler(msg, lambda ms: asyncio.run(sign_2fa(ms, sess)))
    else: bot.send_message(m.chat.id, f"❌ فشل: {res}")

async def sign_2fa(m, sess):
    cl = TelegramClient(sess, MY_API_ID, MY_API_HASH)
    await cl.connect()
    try:
        await cl.sign_in(password=m.text)
        bot.send_message(m.chat.id, "✅ تم الربط بنجاح!")
    except Exception as e: bot.send_message(m.chat.id, f"❌ خطأ: {e}")
    finally: await cl.disconnect()

# ================= [ 💰 نظام الشحن (المطور) ] ================

@bot.message_handler(func=lambda m: m.text == "💰 شحن الرصيد")
def pay_menu(m):
    mk = types.InlineKeyboardMarkup(row_width=1)
    mk.add(types.InlineKeyboardButton("⚡ شحن آلي (Oxapay)", callback_data="auto_p"),
           types.InlineKeyboardButton("💳 شحن يدوي (إيصال)", callback_data="manual_p"))
    bot.send_message(m.chat.id, "⬇️ اختر وسيلة الشحن:", reply_markup=mk)

@bot.callback_query_handler(func=lambda call: call.data in ["auto_p", "manual_p"])
def handle_pay_click(call):
    bot.answer_callback_query(call.id)
    if call.data == "auto_p":
        msg = bot.send_message(call.message.chat.id, "💰 أدخل المبلغ بالدولار:")
        bot.register_next_step_handler(msg, oxa_exec)
    elif call.data == "manual_p":
        bot.send_message(call.message.chat.id, f"💳 حول لمفظتنا:\n`{MY_WALLET}`\nثم أرسل صورة الإيصال هنا.")

def oxa_exec(m):
    try:
        amt = float(m.text)
        res = requests.post("https://api.oxapay.com/merchants/request", json={'merchant': OXAPAY_KEY, 'amount': amt, 'currency': 'USD', 'description': str(m.chat.id)}).json()
        if res.get('payLink'):
            mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("💳 صفحة الدفع", url=res['payLink']))
            bot.send_message(m.chat.id, f"✅ تم إنشاء فاتورة بـ {amt}$", reply_markup=mk)
            threading.Thread(target=watch_oxa, args=(res.get('trackId'), m.chat.id, amt)).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ في المبلغ.")

def watch_oxa(tid, uid, amt):
    for _ in range(15):
        time.sleep(60)
        try:
            r = requests.post("https://api.oxapay.com/merchants/inquiry", json={'merchant': OXAPAY_KEY, 'trackId': tid}).json()
            if r.get('status') in ['Paid', 'Confirmed']:
                update_balance(uid, amt); bot.send_message(uid, f"🎉 تم الشحن آلياً: {amt}$"); break
        except: continue

@bot.message_handler(content_types=['photo'])
def handle_receipt(m):
    if m.chat.id != ADMIN_ID:
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ 5$", callback_data=f"adm_5_{m.chat.id}"),
                                             types.InlineKeyboardButton("✏️ مخصص", callback_data=f"adm_cus_{m.chat.id}"))
        bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=f"إيصال من: `{m.chat.id}`", reply_markup=mk)
        bot.reply_to(m, "⏳ جارٍ المراجعة...")

@bot.callback_query_handler(func=lambda c: c.data.startswith('adm_'))
def admin_action(c):
    bot.answer_callback_query(c.id)
    d = c.data.split('_')
    uid = int(d[2])
    if d[1] == "cus":
        m = bot.send_message(ADMIN_ID, "أدخل المبلغ للشحن:")
        bot.register_next_step_handler(m, lambda ms: [update_balance(uid, float(ms.text)), bot.send_message(uid, f"🎁 تم شحن {ms.text}$")])
    else:
        update_balance(uid, float(d[1]))
        bot.send_message(uid, f"🎁 تم شحن {d[1]}$")
    bot.edit_message_caption("✅ تم الإجراء", c.message.chat.id, c.message.message_id)

# ================= [ 🏁 بدء الهجوم ] ================

@bot.message_handler(func=lambda m: m.text == "⚔️ بدء الهجوم (قوة التحدي)")
def init_attack(m):
    army = get_army(m.chat.id)
    if not army: return bot.send_message(m.chat.id, "❌ جيشك فارغ!")
    msg = bot.send_message(m.chat.id, "📡 يوزر المصدر:")
    bot.register_next_step_handler(msg, get_src)

def get_src(m):
    src = m.text.replace('@','')
    msg = bot.send_message(m.chat.id, "🎯 يوزر مجموعتك:")
    bot.register_next_step_handler(msg, get_trg, src)

def get_trg(m, src):
    trg = m.text.replace('@','')
    msg = bot.send_message(m.chat.id, "🔢 العدد الفعلي المطلوب:")
    bot.register_next_step_handler(msg, lambda ms: run_attack(ms, src, trg))

def run_attack(m, src, trg):
    try:
        num = int(m.text)
        if get_balance(m.chat.id) < (num * PRICE_PER_MEMBER): return bot.send_message(m.chat.id, "❌ رصيدك ناقص.")
        threading.Thread(target=lambda: asyncio.run(dragon_challenge_engine(get_army(m.chat.id), src, trg, num, m.chat.id))).start()
    except: bot.send_message(m.chat.id, "⚠️ خطأ في الرقم.")

# ================= [ 🚀 التشغيل ] ================

if __name__ == "__main__":
    print("🐲 Dragon Challenge V36 is Active...")
    try:
        bot.delete_webhook(drop_pending_updates=True)
        bot.infinity_polling()
    except Exception as e: print(f"❌ Error: {e}")
