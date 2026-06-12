import os
import json
import logging
import requests
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8808650060:AAGdfZbA_n5PHds59OL9iI5fVkkhCWGivP8")
OWNER_ID  = os.environ.get("OWNER_ID", "8842842151")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

VANTAGE_IMAGE = "https://raw.githubusercontent.com/dankulia786786-glitch/kevin-vip-onboarding/main/WhatsApp%20Image%202026-06-12%20at%2012.36.03.jpeg"
PUPRIME_IMAGE = "https://raw.githubusercontent.com/dankulia786786-glitch/kevin-vip-onboarding/main/WhatsApp%20Image%202026-06-12%20at%2014.49.01.jpeg"

onboarding_state = {}

def send_to_user(user_id, text, keyboard=None):
    payload = {"chat_id": user_id, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
    try:
        r = requests.post(f"{TELEGRAM_URL}/sendMessage", json=payload, timeout=10)
        return r.json().get("ok", False)
    except Exception as e:
        logger.error(f"Send error: {e}")
        return False

def send_photo_to_user(user_id, photo_url):
    try:
        requests.post(f"{TELEGRAM_URL}/sendPhoto",
                      json={"chat_id": user_id, "photo": photo_url}, timeout=10)
    except Exception as e:
        logger.error(f"Photo error: {e}")

def notify_owner(text):
    try:
        requests.post(f"{TELEGRAM_URL}/sendMessage",
                      json={"chat_id": OWNER_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        logger.error(f"Owner notify error: {e}")

def handle_start(user_id, first_name, username):
    send_to_user(user_id,
        f"👋 <b>Welcome, {first_name} | GOLD SIGNALS 🔔</b>\n\n"
        "Get access to:\n"
        "✅ VIP Gold Signals\n"
        "✅ 150% Deposit Bonus\n"
        "✅ Free Vantage Trading Course\n\n"
        "⏱ Takes less than 2 minutes to complete.\n\n"
        "👇 Tap below to get started."
    )
    send_to_user(user_id,
        "🚀 Let's get you set up.\n\n"
        "Please select the broker you're currently using so we can guide you "
        "through the correct setup process.\n\n"
        "👇 Choose your broker below:",
        keyboard={"inline_keyboard": [
            [{"text": "🔵 Vantage", "callback_data": "broker_vantage"}],
            [{"text": "🔴 PU Prime", "callback_data": "broker_puprime"}]
        ]}
    )
    onboarding_state[user_id] = {"step": "broker_choice", "first_name": first_name, "username": username}

    # Notify Kevin immediately when someone starts
    notify_owner(
        f"🔔 <b>New Lead Started Onboarding!</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"⏳ Status: Choosing broker...\n"
        f"💬 Chat with them: https://t.me/user?id={user_id}"
    )

def handle_vantage(user_id, first_name, username):
    send_to_user(user_id,
        "🚀 <b>Complete the steps below to activate your Premium Group access.</b> (Takes 10s)\n\n"
        "1️⃣ Log-in to your Vantage client portal:\n👇\n"
        "https://secure.vantagemarkets.com/logout?lang=en_US\n\n"
        "2️⃣ Fill the Form 📋\n👇\n"
        "https://secure.vantagemarkets.com/profile/transfer-ib-affiliate\n\n"
        "3️⃣ Enter the following details exactly as shown:\n"
        "✅ Partnership Type: IB\n"
        "✅ IB Code: <b>58576</b>\n"
        "✅ Reason: PM\n\n"
        "👇 Step-by-step guide below:"
    )
    send_photo_to_user(user_id, VANTAGE_IMAGE)
    send_to_user(user_id,
        "🚨 <b>IMPORTANT</b>\n\n"
        "🚫 Please close all open positions before initiating the transfer.\n"
        "🚫 Wait for the confirmation email before placing any new trades.\n\n"
        "👇 Once completed, click the button below.",
        keyboard={"inline_keyboard": [[{"text": "✅ DONE", "callback_data": "done_vantage"}]]}
    )
    onboarding_state[user_id] = {"step": "awaiting_done", "broker": "vantage", "first_name": first_name, "username": username}

    notify_owner(
        f"📊 <b>Lead chose Vantage</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"⏳ Status: Completing IB transfer steps...\n"
        f"💬 Chat with them: https://t.me/user?id={user_id}"
    )

def handle_puprime(user_id, first_name, username):
    send_to_user(user_id,
        "🚀 <b>Complete the steps below to activate your Premium Group access.</b> (Takes 10s)\n\n"
        "1️⃣ Log in to your PU Prime Client Portal\n👇\n"
        "https://myaccount.puprime.com/home\n\n"
        "2️⃣ Open the IB Transfer Form\n👇\n"
        "https://myaccount.puprime.com/profile/transfer-ib-affiliate\n\n"
        "3️⃣ Enter the following details exactly as shown:\n"
        "✅ Partnership Type: IB\n"
        "✅ IB Code: <b>50151</b>\n"
        "✅ Reason: PM\n\n"
        "👇 Step-by-step guide below:"
    )
    send_photo_to_user(user_id, PUPRIME_IMAGE)
    send_to_user(user_id,
        "🚨 <b>IMPORTANT</b>\n\n"
        "🚫 Please close all open positions before initiating the transfer.\n"
        "🚫 Wait for the confirmation email before placing any new trades.\n\n"
        "👇 Once completed, click the button below.",
        keyboard={"inline_keyboard": [[{"text": "✅ DONE", "callback_data": "done_puprime"}]]}
    )
    onboarding_state[user_id] = {"step": "awaiting_done", "broker": "puprime", "first_name": first_name, "username": username}

    notify_owner(
        f"📊 <b>Lead chose PU Prime</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"⏳ Status: Completing IB transfer steps...\n"
        f"💬 Chat with them: https://t.me/user?id={user_id}"
    )

def handle_done(user_id, first_name, username, broker):
    send_to_user(user_id,
        "🎉 <b>Almost done!</b>\n\n"
        "Please enter your MT4/MT5 Account Number below.\n\n"
        "👇 This will be used to verify your account and activate your Premium Group access."
    )
    onboarding_state[user_id] = {"step": "awaiting_account", "broker": broker, "first_name": first_name, "username": username}

    notify_owner(
        f"✅ <b>Lead clicked DONE</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"⏳ Status: Waiting for MT4/MT5 account number...\n"
        f"💬 Chat with them: https://t.me/user?id={user_id}"
    )

def handle_account_number(user_id, first_name, username, account_number, broker):
    broker_name = "Vantage" if broker == "vantage" else "PU Prime"
    send_to_user(user_id,
        "✅ <b>Account number received!</b>\n\n"
        "Our team will verify your account and activate your Premium Group access shortly.\n\n"
        "🏆 Welcome to Kevin's Gold Signals VIP!"
    )
    notify_owner(
        f"🏆 <b>NEW VIP CLIENT COMPLETE!</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n"
        f"🏦 Broker: {broker_name}\n"
        f"📋 MT4/MT5 Account: <b>{account_number}</b>\n\n"
        f"💬 Reply directly: https://t.me/user?id={user_id}"
    )
    onboarding_state.pop(user_id, None)

@app.route("/telegram_update", methods=["POST"])
def telegram_update():
    try:
        update = request.get_json(force=True)

        if "callback_query" in update:
            cq       = update["callback_query"]
            user     = cq.get("from", {})
            user_id  = str(user.get("id"))
            name     = user.get("first_name", "Friend")
            username = user.get("username", "no username")
            data     = cq.get("data", "")
            try:
                requests.post(f"{TELEGRAM_URL}/answerCallbackQuery",
                              json={"callback_query_id": cq["id"]}, timeout=5)
            except Exception:
                pass

            # Get stored username if available
            stored = onboarding_state.get(user_id, {})
            username = stored.get("username", username)

            if data == "broker_vantage":
                handle_vantage(user_id, name, username)
            elif data == "broker_puprime":
                handle_puprime(user_id, name, username)
            elif data == "done_vantage":
                handle_done(user_id, name, username, "vantage")
            elif data == "done_puprime":
                handle_done(user_id, name, username, "puprime")
            return jsonify({"ok": True})

        message = update.get("message", {})
        if not message:
            return jsonify({"ok": True})

        user     = message.get("from", {})
        user_id  = str(user.get("id"))
        name     = user.get("first_name", "Friend")
        username = user.get("username", "no username")
        text     = message.get("text", "")

        if text.strip() == "/start":
            handle_start(user_id, name, username)
            return jsonify({"ok": True})

        state = onboarding_state.get(user_id, {})
        if state.get("step") == "awaiting_account" and text.strip():
            handle_account_number(user_id, name, username, text.strip(), state.get("broker", "unknown"))
            return jsonify({"ok": True})

        # Any other message — forward to Kevin
        notify_owner(
            f"📩 <b>Message from bot user:</b>\n\n"
            f"👤 Name: {name}\n"
            f"📲 Username: @{username}\n"
            f"🆔 User ID: <code>{user_id}</code>\n"
            f"💬 Message: {text}\n\n"
            f"Reply directly: https://t.me/user?id={user_id}"
        )
    except Exception as e:
        logger.error(f"Update error: {e}")
    return jsonify({"ok": True})

@app.route("/", methods=["GET"])
def health():
    return "Kevin VIP Onboarding Bot is running! ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
