import telebot
from telebot import types
import json, os, threading
from flask import Flask

TOKEN = "8801646866:AAGviA32a8Lnkcb_KAKokM800qNfhI_LLLM"
ADMIN_ID = 8630373069

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

DB_FILE = "db.json"
if not os.path.exists(DB_FILE):
    with open(DB_FILE,"w") as f: json.dump({}, f)
def load():
    try:
        with open(DB_FILE,"r") as f: return json.load(f)
    except: return {}
def save(d):
    with open(DB_FILE,"w") as f: json.dump(d,f)

@app.route("/")
def home(): return "Bot Running!"

@bot.message_handler(commands=['start'])
def start(m):
    db=load(); uid=str(m.from_user.id)
    ref=m.text.split()[1] if len(m.text.split())>1 else None
    if uid not in db:
        db[uid]={"bal":0,"refs":0,"tasks":{}}
        if ref and ref in db and ref!=uid:
            db[ref]["bal"]+=22; db[ref]["refs"]+=1
            try: bot.send_message(ref, f"🎉 New Refer! +22 Taka")
            except: pass
        save(db)
    MINI_APP_URL = "https://project-earning-bot.vercel.app"
    markup=types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Open Earning App", web_app=types.WebAppInfo(url=MINI_APP_URL)))
    markup.add(types.InlineKeyboardButton("📢 Main Channel", url="https://t.me/ProjectEarnig"))
    markup.add(types.InlineKeyboardButton("💳 Payment Proof", url="https://t.me/Projectpayments"))
    bot.send_message(m.chat.id, f"💰 Project Earning\n\n👋 Hello {m.from_user.first_name}!\n\nTask 70 | Refer 22 Unlimited | Ad 7\nWithdraw 230 Taka\n\nOpen App 👇", reply_markup=markup)

def run_bot(): bot.infinity_polling()
def run_flask(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
if __name__=="__main__":
    threading.Thread(target=run_bot).start()
    run_flask()
