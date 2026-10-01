import os
from flask import Flask, request
import telebot
from telebot import types
import json

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    TOKEN = "123456789:TEST"

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
    if request.data:
        bot.process_new_updates([types.Update.de_json(request.data.decode("utf-8"))])
    return "ok", 200

@app.route("/api/withdraw", methods=['POST'])
def api_withdraw():
    data=request.json; uid=str(data.get('user_id')); amount=int(data.get('amount',0))
    method=data.get('method'); wallet=data.get('wallet'); db=load()
    if amount<230: return {"ok":False,"msg":"Minimum 230"}
    if uid not in db or db[uid]['bal']<amount: return {"ok":False,"msg":"Balance কম"}
    db[uid]['bal']-=amount; save(db)
    try: bot.send_message(ADMIN_ID, f"💸 WITHDRAW\nUser:{uid}\nAmount:{amount}\nMethod:{method}\nWallet:{wallet}")
    except: pass
    return {"ok":True}

@bot.message_handler(commands=['start'])
def start(m):
    db=load(); uid=str(m.from_user.id); args=m.text.split(); ref=args[1] if len(args)>1 else None
    if uid not in db:
        db[uid]={"bal":0,"refs":0}
        if ref and ref in db and ref!=uid:
            db[ref]["bal"]+=22; db[ref]["refs"]+=1
            try: bot.send_message(ref, "🎉 New Referral +22 ৳")
            except: pass
    save(db); total=len(db)
    markup=types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Open Earning App", web_app=types.WebAppInfo(url="https://project-earning-bot-web.vercel.app/web/")))
    bot.send_message(m.chat.id, f"💰 Project Earning\n\n💵 Balance: {db[uid]['bal']} ৳\n👥 Refs: {db[uid]['refs']}\n🌍 Total: {total} জন", reply_markup=markup)

@bot.message_handler(commands=['users'])
def users(m):
    db=load(); bot.send_message(m.chat.id, f"👥 Total Users: {len(db)} জন")
