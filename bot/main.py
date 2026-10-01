import os, json, threading, datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
from telebot import types

TOKEN = os.environ.get("BOT_TOKEN")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://project-earning-bot-web.vercel.app/web/")
ADMIN_ID = 8630373069
DB_FILE = "/tmp/db.json"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
CORS(app)

def load():
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except: return {}
def save(d):
    with open(DB_FILE, "w") as f: json.dump(d, f)
def get_today():
    return datetime.date.today().isoformat()

@app.route("/")
def home(): return "Bot Running on Railway!"

@app.route("/api/balance")
def api_balance():
    uid = str(request.args.get('user_id'))
    db = load()
    user = db.get(uid, {"bal": 0, "refs": 0, "ads_today": 0, "last_ad_date": "", "tasks": []})
    if user.get("last_ad_date")!= get_today():
        user["ads_today"] = 0
    return jsonify({"bal": user['bal'], "refs": user['refs'], "total": len(db), "ads_today": user.get("ads_today",0)})

@app.route("/api/add_balance", methods=['POST'])
def api_add_balance():
    data = request.json
    uid = str(data.get('user_id'))
    amount = int(data.get('amount', 0))
    db = load()
    if uid not in db: db[uid] = {"bal": 0, "refs": 0, "ads_today": 0, "last_ad_date": get_today(), "tasks": []}
    user = db[uid]
    if user.get("last_ad_date")!= get_today():
        user["ads_today"] = 0
        user["last_ad_date"] = get_today()
    if data.get("type") == "ad":
        if user.get("ads_today",0) >= 10:
            return jsonify({"ok": False, "msg": "Daily 10 Ads Limit Reached!"})
        user["ads_today"] += 1
    user['bal'] += amount
    user["last_ad_date"] = get_today()
    save(db)
    return jsonify({"ok": True, "new_bal": user['bal'], "ads_today": user["ads_today"]})

@app.route("/api/task", methods=['POST'])
def api_task():
    data = request.json
    uid = str(data.get('user_id'))
    task = data.get('task')
    db = load()
    if uid not in db: db[uid] = {"bal": 0, "refs": 0, "ads_today": 0, "last_ad_date": "", "tasks": []}
    if task in db[uid].get("tasks", []):
        return jsonify({"ok": False, "msg": "Already Done!"})
    db[uid]["bal"] += 10
    db[uid].setdefault("tasks", []).append(task)
    save(db)
    return jsonify({"ok": True})

@app.route("/api/withdraw", methods=['POST'])
def api_withdraw():
    data = request.json
    uid = str(data.get('user_id')); amount = int(data.get('amount', 0)); method = data.get('method'); wallet = data.get('wallet')
    db = load()
    if amount < 230: return jsonify({"ok": False, "msg": "Minimum 230 ৳"})
    if uid not in db or db[uid]['bal'] < amount: return jsonify({"ok": False, "msg": "Balance কম"})
    db[uid]['bal'] -= amount
    save(db)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{uid}_{amount}"),
               types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{uid}_{amount}"))
    try:
        bot.send_message(ADMIN_ID, f"💸 WITHDRAW REQUEST\n\nUser: {uid}\nAmount: {amount} ৳\nMethod: {method}\nWallet: {wallet}\nRemaining: {db[uid]['bal']} ৳", reply_markup=markup)
    except: pass
    return jsonify({"ok": True})

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(c):
    if c.from_user.id!= ADMIN_ID: return
    parts = c.data.split("_")
    action = parts[0]; uid = parts[1]; amount = parts[2]
    if action == "approve":
        try:
            bot.send_message(uid, f"✅ আপনার {amount}৳ Withdraw Approve হয়েছে! 24 ঘণ্টার মধ্যে পেমেন্ট পাবেন।")
            bot.edit_message_text(f"✅ Approved {amount}৳ for {uid}", c.message.chat.id, c.message.message_id)
        except: pass
    elif action == "reject":
        db = load()
        if uid in db:
            db[uid]['bal'] += int(amount)
            save(db)
        try:
            bot.send_message(uid, f"❌ আপনার {amount}৳ Withdraw Reject করা হয়েছে। টাকা Balance এ ফেরত দেওয়া হয়েছে।")
            bot.edit_message_text(f"❌ Rejected & Refunded {amount}৳ for {uid}", c.message.chat.id, c.message.message_id)
        except: pass

@bot.message_handler(commands=['start'])
def start(m):
    db = load(); uid = str(m.from_user.id); args = m.text.split(); ref = args[1] if len(args) > 1 else None
    if uid not in db:
        db[uid] = {"bal": 0, "refs": 0, "ads_today": 0, "last_ad_date": "", "tasks": []}
        if ref and ref in db and ref!= uid:
            db[ref]["bal"] += 22; db[ref]["refs"] += 1
            try: bot.send_message(ref, f"🎉 New Referral +22 ৳ From: {m.from_user.first_name}")
            except: pass
    save(db)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Open Earning App", web_app=types.WebAppInfo(url=WEB_APP_URL)))
    bot.send_message(m.chat.id, f"💰 Project Earning\n\n💵 Balance: {db[uid]['bal']} ৳\n👥 Refs: {db[uid]['refs']}\n🌍 Total: {len(db)} জন", reply_markup=markup)

# --- NEW NOTICE COMMAND ---
@bot.message_handler(commands=['notice'])
def notice(m):
    if m.from_user.id!= ADMIN_ID:
        bot.send_message(m.chat.id, "⛔ Only Admin can use this!")
        return
    msg = m.text.replace("/notice", "").strip()
    if not msg:
        bot.send_message(m.chat.id, "Usage:\n/notice আজ রাত 10 টায় পেমেন্ট দেওয়া হবে!")
        return
    db = load()
    bot.send_message(m.chat.id, f"📢 Sending notice to {len(db)} users...")
    sent = 0
    for uid in list(db.keys()):
        try:
            bot.send_message(uid, f"📢 NOTICE from Admin\n\n{msg}\n\n💰 Project Earning")
            sent += 1
        except:
            pass
    bot.send_message(m.chat.id, f"✅ Notice sent to {sent}/{len(db)} users")

@bot.message_handler(commands=['users'])
def users_cmd(m):
    if m.from_user.id == ADMIN_ID:
        db = load()
        bot.send_message(m.chat.id, f"👥 Total Users: {len(db)} জন")

def run_bot(): bot.infinity_polling()
if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
