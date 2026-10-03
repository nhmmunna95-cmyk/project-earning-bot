import os, json, threading, datetime, time
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot import types

TOKEN = os.environ.get("BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://project-earning-bot-web.vercel.app/")
ADMIN_IDS = [8630373069]
DB_FILE = "/tmp/db.json"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
CORS(app)
lock = threading.Lock()

def load():
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except: return {}
def save(d):
    with lock:
        with open(DB_FILE, "w") as f: json.dump(d, f)
def get_today(): return datetime.date.today().isoformat()

REWARDS = {"welcome": 50, "main": 20, "payment": 20, "giveaway": 20, "fb": 20, "yt": 20, "official": 20}

@app.route("/")
def home(): return "Bot Running!"

@app.route("/api/balance")
def api_balance():
    uid = str(request.args.get('user_id'))
    db = load()
    user = db.get(uid, {"bal": 0, "refs": 0, "ads_today": 0, "last_ad_date": "", "tasks": []})
    if user.get("last_ad_date")!= get_today():
        user["ads_today"] = 0; user["last_ad_date"] = get_today(); db[uid] = user; save(db)
    return jsonify({"bal": user['bal'], "refs": user['refs'], "total": len(db), "ads_today": user.get("ads_today",0), "tasks": user.get("tasks",[])})

@app.route("/api/add_balance", methods=['POST'])
def api_add_balance():
    data = request.json; uid = str(data.get('user_id')); amount = 10
    db = load()
    if uid not in db: db[uid] = {"bal": 0, "refs": 0, "ads_today": 0, "last_ad_date": get_today(), "tasks": []}
    user = db[uid]
    if user.get("last_ad_date")!= get_today(): user["ads_today"] = 0; user["last_ad_date"] = get_today()
    if data.get("type") == "ad":
        if user.get("ads_today",0) >= 10: return jsonify({"ok": False, "msg": "Daily 10 Ads Limit!"})
        user["ads_today"] += 1
    user['bal'] += amount; user["last_ad_date"] = get_today(); save(db)
    return jsonify({"ok": True, "new_bal": user['bal'], "ads_today": user["ads_today"]})

@app.route("/api/task", methods=['POST'])
def api_task():
    data = request.json; uid = str(data.get('user_id')); task = data.get('task')
    db = load()
    if uid not in db: db[uid] = {"bal": 0, "refs": 0, "ads_today": 0, "last_ad_date": "", "tasks": []}
    if task in db[uid].get("tasks", []): return jsonify({"ok": False, "msg": "Already Done!"})
    reward = REWARDS.get(task, 20)
    if task in ["fb", "yt", "welcome", "giveaway", "official"]:
        db[uid]["bal"] += reward; db[uid].setdefault("tasks", []).append(task); save(db)
        return jsonify({"ok": True, "reward": reward})
    try:
        channel = "@ProjectEarnig" if task == "main" else "@Projectpayments"
        member = bot.get_chat_member(channel, int(uid))
        if member.status in ['member', 'administrator', 'creator']:
            db[uid]["bal"] += reward; db[uid].setdefault("tasks", []).append(task); save(db)
            return jsonify({"ok": True, "reward": reward})
        else: return jsonify({"ok": False, "msg": f"Please Join {channel} First!"})
    except Exception as e:
        print(f"Check Error: {e}"); return jsonify({"ok": False, "msg": f"Bot কে {channel} এ Admin বানাও!"})

@app.route("/api/withdraw", methods=['POST'])
def api_withdraw():
    data = request.json; uid = str(data.get('user_id')); amount = int(data.get('amount', 0)); method = data.get('method'); wallet = data.get('wallet')
    db = load()
    if amount < 500: return jsonify({"ok": False, "msg": "Minimum 500 ৳ Required"})
    if uid not in db or db[uid]['bal'] < amount: return jsonify({"ok": False, "msg": "Balance কম"})
    db[uid]['bal'] -= amount; save(db)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}_{amount}"), types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}_{amount}"))
    try:
        for admin in ADMIN_IDS:
            bot.send_message(admin, f"💸 WITHDRAW\nUser: {uid}\nAmount: {amount}৳\nMethod: {method}\nWallet: {wallet}\nBal: {db[uid]['bal']}৳", reply_markup=markup)
    except: pass
    return jsonify({"ok": True})

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(c):
    if c.from_user.id not in ADMIN_IDS: return
    parts = c.data.split("_"); action, uid, amount = parts[0], parts[1], parts[2]
    if action == "approve":
        try: bot.send_message(uid, f"✅ {amount}৳ Withdraw Approved!"); bot.edit_message_text(f"✅ Approved {amount}৳ for {uid}", c.message.chat.id, c.message.message_id)
        except: pass
    elif action == "reject":
        db = load(); db[uid]['bal'] += int(amount); save(db)
        try: bot.send_message(uid, f"❌ {amount}৳ Rejected, Refunded!"); bot.edit_message_text(f"❌ Rejected {amount}৳ for {uid}", c.message.chat.id, c.message.message_id)
        except: pass

@bot.message_handler(commands=['start'])
def start(m):
    db = load(); uid = str(m.from_user.id); args = m.text.split(); ref = args[1] if len(args) > 1 else None
    if uid not in db: db[uid] = {"bal": 0, "refs": 0, "ads_today": 0, "last_ad_date": "", "tasks": []}
    if ref and ref in db and ref!= uid and "referred_by" not in db[uid]:
        db[ref]["bal"] += 22; db[ref]["refs"] += 1; db[uid]["referred_by"] = ref
        try: bot.send_message(ref, f"🎉 New Refer +22৳ from {m.from_user.first_name}")
        except: pass
    save(db)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Open Earning App", web_app=types.WebAppInfo(url=WEB_APP_URL)))
    bot.send_message(m.chat.id, f"💰 Project Earning\n💵 Balance: {db[uid]['bal']}৳\n👥 Refs: {db[uid]['refs']}\n🌍 Total: {len(db)} জন", reply_markup=markup)

@bot.message_handler(commands=['balance'])
def balance_cmd(m):
    db = load(); uid = str(m.from_user.id); user = db.get(uid, {"bal": 0, "refs": 0})
    bot.send_message(m.chat.id, f"💰 আপনার ব্যালেন্স: {user.get('bal',0)}৳\n👥 রেফার: {user.get('refs',0)} জন")

@bot.message_handler(commands=['tasks'])
def tasks_cmd(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📋 Open Tasks", web_app=types.WebAppInfo(url=WEB_APP_URL)))
    bot.send_message(m.chat.id, "📋 টাস্ক কমপ্লিট করতে App ওপেন করুন:", reply_markup=markup)

@bot.message_handler(commands=['refer'])
def refer_cmd(m):
    uid = str(m.from_user.id)
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={uid}"
    bot.send_message(m.chat.id, f"👥 আপনার রেফার লিংক:\n{link}\n\nপ্রতি রেফারে 22৳ পাবেন!")

@bot.message_handler(commands=['withdraw'])
def withdraw_cmd(m):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💸 Withdraw", web_app=types.WebAppInfo(url=WEB_APP_URL)))
    bot.send_message(m.chat.id, "💸 Minimum Withdraw 500৳\nApp থেকে Withdraw করুন:", reply_markup=markup)

# --- NOTICE / BROADCAST SYSTEM ---
@bot.message_handler(commands=['notice', 'broadcast'])
def broadcast_cmd(m):
    if m.from_user.id not in ADMIN_IDS:
        bot.send_message(m.chat.id, "⛔ Admin Only!")
        return
    msg = m.text.replace("/notice", "").replace("/broadcast", "").strip()
    if not msg:
        bot.send_message(m.chat.id, "ব্যবহার: /notice আপনার মেসেজ\n\nযেমন:\n/notice আজ রাত ৮টায় পেমেন্ট দেওয়া হবে")
        return
    db = load()
    total = len(db)
    bot.send_message(m.chat.id, f"📢 {total} জনকে Notice পাঠানো হচ্ছে...")
    sent = 0
    for uid in list(db.keys()):
        try:
            bot.send_message(uid, f"📢 **NOTICE**\n\n{msg}\n\n- Project Earning Team")
            sent += 1
            time.sleep(0.05)
        except: pass
    bot.send_message(m.chat.id, f"✅ {sent}/{total} জনকে Notice পাঠানো সম্পন্ন!")

@bot.message_handler(commands=['users'])
def users_cmd(m):
    if m.from_user.id not in ADMIN_IDS: return
    db = load()
    bot.send_message(m.chat.id, f"👥 Total Users: {len(db)} জন")

def run_bot():
    try:
        bot.set_my_commands([
            types.BotCommand("start", "🚀 Bot Start করুন"),
            types.BotCommand("balance", "💰 ব্যালেন্স চেক করুন"),
            types.BotCommand("tasks", "📋 টাস্ক কমপ্লিট করুন"),
            types.BotCommand("refer", "👥 রেফার করুন"),
            types.BotCommand("withdraw", "💸 উইথড্র করুন"),
            types.BotCommand("notice", "📢 সবাইকে নোটিশ (Admin)"),
            types.BotCommand("users", "👥 Total User (Admin)")
        ])
    except: pass
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
