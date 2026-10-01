import os
from flask import Flask, request
import telebot
from telebot import types
import json

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

ADMIN_ID = 8630373069
DB_FILE = "/tmp/db.json"

def load():
    try:
        with open(DB_FILE, "r") as f: return json.load(f)
    except: return {}
def save(d):
    with open(DB_FILE, "w") as f: json.dump(d,f)

@app.route("/")
def home(): return "Bot Running!"

@app.route(f"/{TOKEN}", methods=['POST'])
def webhook():
    bot.process_new_updates([types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

@app.route("/api/withdraw", methods=['POST'])
def api_withdraw():
    data = request.json
    uid = str(data.get('user_id'))
    amount = int(data.get('amount', 0))
    method = data.get('method')
    wallet = data.get('wallet')
    db=load()
    if amount < 230:
        return {"ok": False, "msg": "Minimum 230"}
    if uid not in db or db[uid]['bal'] < amount:
        return {"ok": False, "msg": "Balance কম"}
    db[uid]['bal'] -= amount
    save(db)
    try:
        bot.send_message(ADMIN_ID, f"💸 NEW WITHDRAW\n\n👤 User: {uid}\n💰 Amount: {amount}\n💳 Method: {method}\n🔢 Wallet: {wallet}")
    except: pass
    return {"ok": True}

@bot.message_handler(commands=['start'])
def start(m):
    db=load(); uid=str(m.from_user.id)
    args=m.text.split()
    ref=args[1] if len(args)>1 else None
    if uid not in db:
        db[uid]={"bal":0,"refs":0}
        if ref and ref in db and ref!=uid:
            db[ref]["bal"]+=22; db[ref]["refs"]+=1
            try: bot.send_message(ref, "🎉 New Referral! +22")
            except: pass
        save(db)

    total_users = len(db)
    MINI_APP_URL="https://project-earning-bot.vercel.app/web/"
    markup=types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Open App", web_app=types.WebAppInfo(url=MINI_APP_URL)))
    markup.add(types.InlineKeyboardButton("📊 Total Users", callback_data="show_users"))

    bot.send_message(m.chat.id,
        f"💰 Project Earning Bot\n\n"
        f"💵 Balance: {db[uid]['bal']}\n"
        f"👥 Your Refs: {db[uid]['refs']}\n\n"
        f"🌍 Total Bot Users: {total_users} জন\n\n"
        f"Commands:\n/users - Total users\n/withdraw - Withdraw",
        reply_markup=markup)

@bot.message_handler(commands=['users', 'stats'])
def show_users(m):
    db=load()
    total = len(db)
    bot.send_message(m.chat.id, f"📊 Bot Statistics\n\n👥 Total Users: {total} জন\n\nসবাই বট ব্যবহার করছে! 🚀")

@bot.callback_query_handler(func=lambda c: c.data=="show_users")
def callback_users(c):
    db=load()
    total = len(db)
    bot.answer_callback_query(c.id, f"👥 Total Users: {total} জন")

@bot.message_handler(commands=['broadcast'])
def broadcast(m):
    if m.from_user.id!=ADMIN_ID: return
    text=m.text.replace("/broadcast","").strip()
    if not text:
        bot.send_message(m.chat.id, "ব্যবহার: /broadcast মেসেজ")
        return
    db=load(); c=0
    for uid in db:
        try: bot.send_message(uid, f"📢 NOTICE\n\n{text}"); c+=1
        except: pass
    bot.send_message(m.chat.id, f"✅ {c} জনকে পাঠানো হয়েছে")

@bot.message_handler(commands=['withdraw'])
def withdraw(m):
    db=load(); bal=db.get(str(m.from_user.id), {}).get('bal',0)
    bot.send_message(m.chat.id, f"💰 Balance: {bal}\nMini App থেকে 230+ হলে Withdraw")
