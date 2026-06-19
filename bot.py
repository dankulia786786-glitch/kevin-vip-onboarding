import os
import json
import logging
import requests
import threading
import time
import random
import hashlib
from functools import wraps
from flask import Flask, request, jsonify, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8808650060:AAGdfZbA_n5PHds59OL9iI5fVkkhCWGivP8")
OWNER_ID  = os.environ.get("OWNER_ID", "6838959359")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

VANTAGE_IMAGE = "https://raw.githubusercontent.com/dankulia786786-glitch/kevin-vip-onboarding/main/WhatsApp%20Image%202026-06-12%20at%2012.36.03.jpeg"
PUPRIME_IMAGE = "https://raw.githubusercontent.com/dankulia786786-glitch/kevin-vip-onboarding/main/WhatsApp%20Image%202026-06-12%20at%2014.49.01.jpeg"

# ─── AUTH ─────────────────────────────────────────────────────────────────────
DASHBOARD_USERS = {
    "Mobile0208@": "Kevin",
    "Admin123":    "Team"
}

def check_auth(username, password):
    return DASHBOARD_USERS.get(password) is not None

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response("Login required", 401,
                {'WWW-Authenticate': 'Basic realm="Kevin VIP CRM"'})
        return f(*args, **kwargs)
    return decorated

# ─── PERSISTENT STORAGE ───────────────────────────────────────────────────────
DATA_DIR       = "/data"
USERS_FILE     = "/data/vip_users.json"
BROADCAST_FILE = "/data/broadcasts.json"
users_lock     = threading.Lock()

def load_users():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Load users error: {e}")
    return {}

def save_users(users):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
    except Exception as e:
        logger.error(f"Save users error: {e}")

def load_broadcasts():
    try:
        if os.path.exists(BROADCAST_FILE):
            with open(BROADCAST_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_broadcasts(data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(BROADCAST_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Save broadcasts error: {e}")

users_db = load_users()
onboarding_state = {}
reply_map        = {}

# ─── DRIP MESSAGES ────────────────────────────────────────────────────────────
DRIP_MESSAGES = [
    "⚡ <b>FREE Gold signal firing soon — don't miss it!</b>\n\nJoin our FREE PM signals group and get every signal direct to your phone.\n\n👇 Complete your FREE setup — takes 2 minutes!",
    "💰 <b>Our members just made £134 on Gold — FOR FREE!</b>\n\nYou're one step away from joining our FREE VIP signals group.\n\n👇 Complete your FREE setup and never miss a trade again!",
    "🔥 <b>Gold is moving RIGHT NOW!</b>\n\nOur FREE PM group members are already positioned. Don't get left behind.\n\n👇 Join FREE — takes 2 minutes!",
    "🏆 <b>100% FREE access to daily Gold & Bitcoin signals.</b>\n\nNo subscription. No hidden fees. Completely FREE forever.\n\n👇 Complete your FREE setup now!",
    "📈 <b>We hit TP2 on Gold today — members are up £200+</b>\n\nAll signals are sent FREE to our PM group every single day.\n\n👇 Join FREE today and start receiving signals immediately!",
    "⚠️ <b>You're missing FREE Gold signals every day!</b>\n\nOur community is growing fast — don't get left behind.\n\n👇 Complete your FREE setup in 2 minutes!",
    "🎯 <b>FREE Gold & Bitcoin signals — daily, every day.</b>\n\nPlus a 50% deposit bonus for life — completely FREE and uncapped.\n\n👇 Claim your FREE access now!",
    "💎 <b>VIP access. Premium signals. 100% FREE.</b>\n\nWe're sending another Gold signal soon. Will you be in the group?\n\n👇 Complete your FREE setup now and join the team!",
]

JOIN_BUTTON = {"inline_keyboard": [[{"text": "👉 JOIN FREE NOW 👈", "callback_data": "restart_onboarding"}]]}

# ─── CORE SEND FUNCTIONS ──────────────────────────────────────────────────────
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

def send_photo_to_user(user_id, photo_url, caption=None):
    try:
        payload = {"chat_id": user_id, "photo": photo_url}
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "HTML"
        requests.post(f"{TELEGRAM_URL}/sendPhoto", json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Photo error: {e}")

def send_video_to_user(user_id, video_url, caption=None):
    try:
        payload = {"chat_id": user_id, "video": video_url}
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "HTML"
        requests.post(f"{TELEGRAM_URL}/sendVideo", json=payload, timeout=15)
    except Exception as e:
        logger.error(f"Video error: {e}")

def notify_owner(text, keyboard=None):
    payload = {"chat_id": OWNER_ID, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
    try:
        r = requests.post(f"{TELEGRAM_URL}/sendMessage", json=payload, timeout=10)
        data = r.json()
        if data.get("ok"):
            return data["result"]["message_id"]
    except Exception as e:
        logger.error(f"Owner notify error: {e}")
    return None

def forward_to_owner(user_id, name, username, text):
    msg = (
        f"📩 <b>Message from client:</b>\n\n"
        f"👤 Name: {name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"💬 Message: {text}\n\n"
        f"<i>↩️ Reply to THIS message to respond to them</i>"
    )
    mid = notify_owner(msg)
    if mid:
        reply_map[str(mid)] = str(user_id)

# ─── ONBOARDING HANDLERS ──────────────────────────────────────────────────────
def handle_start(user_id, first_name, username):
    with users_lock:
        existing = users_db.get(str(user_id), {})
        users_db[str(user_id)] = {
            "name":        first_name,
            "username":    username,
            "started_at":  existing.get("started_at", time.time()),
            "completed":   existing.get("completed", False),
            "last_drip":   time.time(),
            "drip_count":  existing.get("drip_count", 0),
            "broker":      existing.get("broker"),
            "mt5_account": existing.get("mt5_account"),
            "steps":       existing.get("steps", []),
        }
        save_users(users_db)

    send_to_user(user_id,
        f"👋 <b>Welcome, {first_name} | GOLD SIGNALS 🔔</b>\n\n"
        "Get <b>FREE</b> access to:\n"
        "✅ VIP Gold Signals — <b>FREE</b>\n"
        "✅ 50% Deposit Bonus for Life — <b>FREE & Uncapped</b>\n"
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
    _add_step(user_id, "Started onboarding")

    mid = notify_owner(
        f"🔔 <b>New Lead Started Onboarding!</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"⏳ Status: Choosing broker...\n\n"
        f"<i>↩️ Reply to THIS message to send them a message</i>",
    )
    if mid:
        reply_map[str(mid)] = str(user_id)

def _add_step(user_id, step_text):
    with users_lock:
        if str(user_id) in users_db:
            steps = users_db[str(user_id)].get("steps", [])
            steps.append({"text": step_text, "time": time.time()})
            users_db[str(user_id)]["steps"] = steps
            save_users(users_db)

def handle_vantage(user_id, first_name, username):
    with users_lock:
        if str(user_id) in users_db:
            users_db[str(user_id)]["broker"] = "Vantage"
            save_users(users_db)
    _add_step(user_id, "Chose Vantage")

    send_to_user(user_id,
        "🚀 <b>Complete the steps below to activate your FREE Premium Group access.</b> (Takes 10s)\n\n"
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
    mid = notify_owner(
        f"📊 <b>Lead chose Vantage</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"⏳ Status: Completing IB transfer steps...\n\n"
        f"<i>↩️ Reply to THIS message to send them a message</i>"
    )
    if mid:
        reply_map[str(mid)] = str(user_id)

def handle_puprime(user_id, first_name, username):
    with users_lock:
        if str(user_id) in users_db:
            users_db[str(user_id)]["broker"] = "PU Prime"
            save_users(users_db)
    _add_step(user_id, "Chose PU Prime")

    send_to_user(user_id,
        "🚀 <b>Complete the steps below to activate your FREE Premium Group access.</b> (Takes 10s)\n\n"
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
    mid = notify_owner(
        f"📊 <b>Lead chose PU Prime</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"⏳ Status: Completing IB transfer steps...\n\n"
        f"<i>↩️ Reply to THIS message to send them a message</i>"
    )
    if mid:
        reply_map[str(mid)] = str(user_id)

def handle_done(user_id, first_name, username, broker):
    _add_step(user_id, "Clicked DONE")
    send_to_user(user_id,
        "🎉 <b>Almost there — you're getting FREE access!</b>\n\n"
        "Please enter your MT4/MT5 Account Number below.\n\n"
        "👇 This will be used to verify your account and activate your FREE Premium Group access."
    )
    onboarding_state[user_id] = {"step": "awaiting_account", "broker": broker, "first_name": first_name, "username": username}
    mid = notify_owner(
        f"✅ <b>Lead clicked DONE</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"⏳ Status: Waiting for MT4/MT5 account number...\n\n"
        f"<i>↩️ Reply to THIS message to send them a message</i>"
    )
    if mid:
        reply_map[str(mid)] = str(user_id)

def handle_account_number(user_id, first_name, username, account_number, broker):
    broker_name = "Vantage" if broker == "vantage" else "PU Prime"
    _add_step(user_id, f"Submitted MT5: {account_number}")

    with users_lock:
        if str(user_id) in users_db:
            users_db[str(user_id)]["completed"]   = True
            users_db[str(user_id)]["mt5_account"] = account_number
            save_users(users_db)

    send_to_user(user_id,
        "✅ <b>Account number received!</b>\n\n"
        "Our team will verify your account and activate your FREE Premium Group access shortly.\n\n"
        "🏆 Welcome to Kevin's Gold Signals VIP!\n\n"
        "Our team will be in touch with you very soon. 🙌"
    )
    mid = notify_owner(
        f"🏆 <b>NEW VIP CLIENT COMPLETE!</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n"
        f"🏦 Broker: {broker_name}\n"
        f"📋 MT4/MT5 Account: <b>{account_number}</b>\n\n"
        f"<i>↩️ Reply to THIS message to send them a message</i>"
    )
    if mid:
        reply_map[str(mid)] = str(user_id)
    onboarding_state.pop(user_id, None)

# ─── DRIP SCHEDULER ───────────────────────────────────────────────────────────
MAX_DRIP_DAYS = 30
DRIP_INTERVAL = 86400  # 24 hours

def drip_scheduler():
    logger.info("Drip scheduler started")
    while True:
        try:
            now = time.time()
            with users_lock:
                snapshot = dict(users_db)

            for uid, data in snapshot.items():
                if data.get("completed"):
                    continue
                started = data.get("started_at", now)
                if now - started > MAX_DRIP_DAYS * 86400:
                    continue
                last_drip = data.get("last_drip", 0)
                if now - last_drip < DRIP_INTERVAL:
                    continue

                # Random spread — don't send all at once
                time.sleep(random.uniform(5, 120))

                count = data.get("drip_count", 0)
                msg   = DRIP_MESSAGES[count % len(DRIP_MESSAGES)]
                ok    = send_to_user(uid, msg, keyboard=JOIN_BUTTON)
                if ok:
                    with users_lock:
                        users_db[uid]["last_drip"]  = time.time()
                        users_db[uid]["drip_count"] = count + 1
                        save_users(users_db)
                    logger.info(f"Drip #{count+1} sent to {uid}")

        except Exception as e:
            logger.error(f"Drip error: {e}")
        time.sleep(300)

# ─── FORWARD TP TO INCOMPLETE LEADS ─────────────────────────────────────────
last_tp_forward = {}
tp_forward_lock = threading.Lock()

@app.route("/forward_tp", methods=["POST"])
def forward_tp():
    """Receives profit card image from signals bot and forwards to all incomplete leads"""
    try:
        close_type = request.form.get("close_type", "TP1")
        pair       = request.form.get("pair", "XAUUSD")
        profit_str = request.form.get("profit_str", "")
        image_file = request.files.get("image")

        # Dedup — only forward once per TP type per hour
        dedup_key = f"{pair}_{close_type}"
        now = time.time()
        with tp_forward_lock:
            if now - last_tp_forward.get(dedup_key, 0) < 3600:
                return jsonify({"status": "duplicate_ignored"})
            last_tp_forward[dedup_key] = now

        pair_name = "GOLD" if pair == "XAUUSD" else "BITCOIN"
        tp_labels = {
            "TP1": f"TP1 just smashed on {pair_name}!",
            "TP2": f"TP2 just smashed on {pair_name}!",
            "TP3": f"ALL targets hit on {pair_name}!",
        }
        tp_label = tp_labels.get(close_type, f"{close_type} hit on {pair_name}!")

        caption = (
            f"🔥 <b>{tp_label}</b>\n\n"
            f"Our FREE members just made <b>{profit_str}</b> — <b>FOR FREE!</b>\n\n"
            f"You missed this signal. Don't miss the next one.\n\n"
            f"👇 <b>Join FREE now — takes 2 minutes!</b>"
        )

        image_bytes = image_file.read() if image_file else None

        with users_lock:
            snapshot = dict(users_db)

        sent = 0
        for uid, udata in snapshot.items():
            if udata.get("completed"):
                continue
            # Max 2 TP forwards per day per user
            tp_count_today = udata.get("tp_forward_today", 0)
            last_tp_day    = udata.get("last_tp_forward_day", "")
            today_str      = __import__("datetime").date.today().isoformat()
            if last_tp_day != today_str:
                tp_count_today = 0
            if tp_count_today >= 2:
                continue

            time.sleep(random.uniform(0.3, 2))

            try:
                if image_bytes:
                    files   = {"photo": ("result.jpg", image_bytes, "image/jpeg")}
                    payload = {
                        "chat_id":    uid,
                        "caption":    caption,
                        "parse_mode": "HTML",
                        "reply_markup": json.dumps(JOIN_BUTTON)
                    }
                    r = requests.post(f"{TELEGRAM_URL}/sendPhoto",
                                      files=files, data=payload, timeout=15)
                    ok = r.json().get("ok", False)
                else:
                    ok = send_to_user(uid, caption, keyboard=JOIN_BUTTON)

                if ok:
                    with users_lock:
                        users_db[uid]["tp_forward_today"]   = tp_count_today + 1
                        users_db[uid]["last_tp_forward_day"] = today_str
                        save_users(users_db)
                    sent += 1
            except Exception as e:
                logger.error(f"TP forward error for {uid}: {e}")

        logger.info(f"TP forward sent to {sent} incomplete leads")
        return jsonify({"status": "ok", "sent": sent})
    except Exception as e:
        logger.error(f"forward_tp error: {e}")
        return jsonify({"status": "error"}), 500


# ─── TELEGRAM WEBHOOK ─────────────────────────────────────────────────────────
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
            stored   = onboarding_state.get(user_id, {})
            username = stored.get("username", username)

            if data == "broker_vantage":
                handle_vantage(user_id, name, username)
            elif data == "broker_puprime":
                handle_puprime(user_id, name, username)
            elif data == "done_vantage":
                handle_done(user_id, name, username, "vantage")
            elif data == "done_puprime":
                handle_done(user_id, name, username, "puprime")
            elif data == "restart_onboarding":
                handle_start(user_id, name, username)
            return jsonify({"ok": True})

        message = update.get("message", {})
        if not message:
            return jsonify({"ok": True})

        user     = message.get("from", {})
        user_id  = str(user.get("id"))
        name     = user.get("first_name", "Friend")
        username = user.get("username", "no username")
        text     = message.get("text", "")

        if user_id == str(OWNER_ID):
            reply_to = message.get("reply_to_message", {})
            if reply_to:
                replied_mid = str(reply_to.get("message_id", ""))
                client_id   = reply_map.get(replied_mid)
                if client_id:
                    send_to_user(client_id, f"💬 <b>Message from Kevin:</b>\n\n{text}")
                    notify_owner("✅ Your reply was sent to the client.")
                else:
                    notify_owner("⚠️ Could not find that client.")
            return jsonify({"ok": True})

        if text.strip() == "/start":
            handle_start(user_id, name, username)
            return jsonify({"ok": True})

        state = onboarding_state.get(user_id, {})
        if state.get("step") == "awaiting_account" and text.strip():
            handle_account_number(user_id, name, username, text.strip(), state.get("broker", "unknown"))
            return jsonify({"ok": True})

        forward_to_owner(user_id, name, username, text)

    except Exception as e:
        logger.error(f"Update error: {e}")
    return jsonify({"ok": True})

# ─── CRM DASHBOARD ────────────────────────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kevin VIP CRM</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #fff; min-height: 100vh; }
.header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px 30px; border-bottom: 2px solid #d4af37; display: flex; align-items: center; justify-content: space-between; }
.header h1 { font-size: 22px; color: #d4af37; }
.header .subtitle { font-size: 13px; color: #888; margin-top: 4px; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; padding: 24px 30px; }
.stat-card { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4e; text-align: center; }
.stat-card .number { font-size: 36px; font-weight: bold; color: #d4af37; }
.stat-card .label { font-size: 13px; color: #888; margin-top: 6px; }
.stat-card.green .number { color: #00dc50; }
.stat-card.red .number { color: #ff4444; }
.stat-card.blue .number { color: #4a90e2; }
.section { padding: 0 30px 30px; }
.section-title { font-size: 16px; font-weight: bold; color: #d4af37; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.broadcast-box { background: #1a1a2e; border-radius: 12px; padding: 20px; border: 1px solid #2a2a4e; margin-bottom: 24px; }
.broadcast-box textarea { width: 100%; background: #0f0f1a; border: 1px solid #2a2a4e; border-radius: 8px; color: #fff; padding: 12px; font-size: 14px; resize: vertical; min-height: 80px; }
.broadcast-box input[type=text] { width: 100%; background: #0f0f1a; border: 1px solid #2a2a4e; border-radius: 8px; color: #fff; padding: 10px 12px; font-size: 14px; margin-top: 10px; }
.btn { padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer; font-size: 14px; font-weight: bold; transition: all 0.2s; }
.btn-gold { background: #d4af37; color: #000; }
.btn-gold:hover { background: #f0c840; }
.btn-red { background: #c0392b; color: #fff; }
.btn-green { background: #27ae60; color: #fff; }
.btn-blue { background: #2980b9; color: #fff; }
.btn:hover { opacity: 0.85; transform: translateY(-1px); }
.btn-row { display: flex; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
table { width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 12px; overflow: hidden; }
th { background: #d4af37; color: #000; padding: 12px 16px; text-align: left; font-size: 13px; }
td { padding: 12px 16px; border-bottom: 1px solid #2a2a4e; font-size: 13px; color: #ccc; vertical-align: middle; }
tr:hover td { background: #1e1e35; }
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: bold; }
.badge-green { background: #1a3a2a; color: #00dc50; border: 1px solid #00dc50; }
.badge-orange { background: #3a2a1a; color: #f39c12; border: 1px solid #f39c12; }
.badge-blue { background: #1a2a3a; color: #4a90e2; border: 1px solid #4a90e2; }
.steps-list { font-size: 11px; color: #888; }
.msg-input { display: flex; gap: 8px; margin-top: 8px; }
.msg-input input { flex: 1; background: #0f0f1a; border: 1px solid #2a2a4e; border-radius: 6px; color: #fff; padding: 6px 10px; font-size: 12px; }
.search-bar { width: 100%; background: #1a1a2e; border: 1px solid #2a2a4e; border-radius: 8px; color: #fff; padding: 10px 14px; font-size: 14px; margin-bottom: 16px; }
.filter-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.filter-tab { padding: 6px 16px; border-radius: 20px; border: 1px solid #2a2a4e; background: #1a1a2e; color: #888; cursor: pointer; font-size: 13px; }
.filter-tab.active { background: #d4af37; color: #000; border-color: #d4af37; font-weight: bold; }
.toast { position: fixed; bottom: 30px; right: 30px; background: #00dc50; color: #000; padding: 12px 20px; border-radius: 8px; font-weight: bold; display: none; z-index: 999; }
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>👑 Kevin VIP CRM Dashboard</h1>
    <div class="subtitle">Gold Signals — Lead Management System</div>
  </div>
  <div style="text-align:right; font-size:13px; color:#888;">
    <div id="clock"></div>
    <div style="margin-top:4px;">Auto-refreshes every 60s</div>
  </div>
</div>

<div class="stats" id="stats">
  <div class="stat-card"><div class="number" id="s-total">-</div><div class="label">Total Leads</div></div>
  <div class="stat-card green"><div class="number" id="s-done">-</div><div class="label">✅ Completed</div></div>
  <div class="stat-card red"><div class="number" id="s-pending">-</div><div class="label">⏳ Pending</div></div>
  <div class="stat-card blue"><div class="number" id="s-vantage">-</div><div class="label">🔵 Vantage</div></div>
  <div class="stat-card blue"><div class="number" id="s-puprime">-</div><div class="label">🔴 PU Prime</div></div>
</div>

<div class="section">
  <div class="section-title">📢 Broadcast Message</div>
  <div class="broadcast-box">
    <div style="font-size:13px; color:#888; margin-bottom:10px;">Send a message, testimonial, or promotion to ALL pending leads (1 per day limit applies)</div>
    <textarea id="bc-text" placeholder="Type your message here... e.g. 🔥 We just hit TP3 on Gold — members made £420 for FREE today! Don't miss the next one 👇"></textarea>
    <input type="text" id="bc-media" placeholder="Optional: Paste image or video URL (leave blank for text only)" />
    <div class="btn-row">
      <button class="btn btn-gold" onclick="sendBroadcast('all')">📢 Send to ALL Pending</button>
      <button class="btn btn-blue" onclick="sendBroadcast('no_broker')">Send to Not Started</button>
      <button class="btn btn-green" onclick="sendBroadcast('vantage')">Send to Vantage Only</button>
      <button class="btn btn-red" onclick="sendBroadcast('puprime')">Send to PU Prime Only</button>
    </div>
  </div>

  <div class="section-title">👥 All Leads</div>
  <input class="search-bar" type="text" id="search" placeholder="🔍 Search by name, username or MT5..." onkeyup="filterTable()" />
  <div class="filter-tabs">
    <div class="filter-tab active" onclick="setFilter('all', this)">All</div>
    <div class="filter-tab" onclick="setFilter('completed', this)">✅ Completed</div>
    <div class="filter-tab" onclick="setFilter('pending', this)">⏳ Pending</div>
    <div class="filter-tab" onclick="setFilter('Vantage', this)">🔵 Vantage</div>
    <div class="filter-tab" onclick="setFilter('PU Prime', this)">🔴 PU Prime</div>
  </div>
  <table id="leads-table">
    <thead>
      <tr>
        <th>#</th>
        <th>Name</th>
        <th>Username</th>
        <th>Broker</th>
        <th>MT5 Account</th>
        <th>Status</th>
        <th>Steps</th>
        <th>Drip #</th>
        <th>Message</th>
      </tr>
    </thead>
    <tbody id="leads-body">
      <tr><td colspan="9" style="text-align:center; color:#888; padding:30px;">Loading...</td></tr>
    </tbody>
  </table>
</div>

<div class="toast" id="toast"></div>

<script>
let allLeads = [];
let currentFilter = 'all';

function showToast(msg, color='#00dc50') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = color;
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3000);
}

function setFilter(f, el) {
  currentFilter = f;
  document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  renderTable(allLeads);
}

function filterTable() {
  renderTable(allLeads);
}

function renderTable(leads) {
  const search = document.getElementById('search').value.toLowerCase();
  const tbody  = document.getElementById('leads-body');
  let filtered = leads.filter(l => {
    const matchSearch = !search ||
      (l.name || '').toLowerCase().includes(search) ||
      (l.username || '').toLowerCase().includes(search) ||
      (l.mt5_account || '').toLowerCase().includes(search);
    const matchFilter =
      currentFilter === 'all' ||
      (currentFilter === 'completed' && l.completed) ||
      (currentFilter === 'pending' && !l.completed) ||
      (currentFilter === l.broker);
    return matchSearch && matchFilter;
  });

  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:#888;padding:30px;">No leads found</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map((l, i) => {
    const status = l.completed
      ? '<span class="badge badge-green">✅ Complete</span>'
      : '<span class="badge badge-orange">⏳ Pending</span>';
    const broker = l.broker
      ? `<span class="badge badge-blue">${l.broker}</span>`
      : '<span style="color:#555">—</span>';
    const steps = (l.steps || []).map(s => `<div>• ${s.text}</div>`).join('') || '—';
    const mt5   = l.mt5_account || '<span style="color:#555">—</span>';
    const uname = l.username && l.username !== 'no username'
      ? `<a href="https://t.me/${l.username}" target="_blank" style="color:#4a90e2">@${l.username}</a>`
      : `<span style="color:#555">No username</span>`;

    return `<tr data-id="${l.user_id}">
      <td>${i+1}</td>
      <td><b>${l.name || '—'}</b></td>
      <td>${uname}</td>
      <td>${broker}</td>
      <td>${mt5}</td>
      <td>${status}</td>
      <td><div class="steps-list">${steps}</div></td>
      <td style="text-align:center">${l.drip_count || 0}</td>
      <td>
        <div class="msg-input">
          <input type="text" id="msg-${l.user_id}" placeholder="Send message..." />
          <button class="btn btn-blue" style="padding:6px 12px;font-size:12px" onclick="sendMsg('${l.user_id}')">Send</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

async function loadLeads() {
  try {
    const r = await fetch('/api/leads');
    const data = await r.json();
    allLeads = data.leads || [];

    document.getElementById('s-total').textContent   = data.total;
    document.getElementById('s-done').textContent    = data.completed;
    document.getElementById('s-pending').textContent = data.pending;
    document.getElementById('s-vantage').textContent = data.vantage;
    document.getElementById('s-puprime').textContent = data.puprime;

    renderTable(allLeads);
  } catch(e) {
    console.error(e);
  }
}

async function sendMsg(uid) {
  const text = document.getElementById('msg-' + uid).value.trim();
  if (!text) return;
  const r = await fetch('/api/message', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_id: uid, text})
  });
  const d = await r.json();
  if (d.ok) { showToast('✅ Message sent!'); document.getElementById('msg-' + uid).value = ''; }
  else showToast('❌ Failed to send', '#e74c3c');
}

async function sendBroadcast(target) {
  const text  = document.getElementById('bc-text').value.trim();
  const media = document.getElementById('bc-media').value.trim();
  if (!text) { showToast('Please write a message first', '#e74c3c'); return; }
  if (!confirm(`Send to ${target === 'all' ? 'ALL pending' : target} leads?`)) return;
  const r = await fetch('/api/broadcast', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text, media_url: media, target})
  });
  const d = await r.json();
  showToast(`✅ Broadcast sent to ${d.sent} leads!`);
}

function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent = now.toLocaleTimeString('en-GB', {
    hour:'2-digit', minute:'2-digit', second:'2-digit', timeZone:'Europe/London'
  }) + ' UK';
}

loadLeads();
setInterval(loadLeads, 60000);
setInterval(updateClock, 1000);
updateClock();
</script>
</body>
</html>"""


@app.route("/dashboard")
@requires_auth
def dashboard():
    return DASHBOARD_HTML


@app.route("/api/leads")
@requires_auth
def api_leads():
    with users_lock:
        snapshot = dict(users_db)
    leads = []
    for uid, d in snapshot.items():
        leads.append({
            "user_id":     uid,
            "name":        d.get("name", ""),
            "username":    d.get("username", ""),
            "broker":      d.get("broker", ""),
            "mt5_account": d.get("mt5_account", ""),
            "completed":   d.get("completed", False),
            "drip_count":  d.get("drip_count", 0),
            "steps":       d.get("steps", []),
            "started_at":  d.get("started_at", 0),
        })
    leads.sort(key=lambda x: x["started_at"], reverse=True)
    total     = len(leads)
    completed = sum(1 for l in leads if l["completed"])
    vantage   = sum(1 for l in leads if l.get("broker") == "Vantage")
    puprime   = sum(1 for l in leads if l.get("broker") == "PU Prime")
    return jsonify({
        "leads":     leads,
        "total":     total,
        "completed": completed,
        "pending":   total - completed,
        "vantage":   vantage,
        "puprime":   puprime,
    })


@app.route("/api/message", methods=["POST"])
@requires_auth
def api_message():
    data    = request.get_json(force=True)
    user_id = data.get("user_id")
    text    = data.get("text", "")
    if not user_id or not text:
        return jsonify({"ok": False})
    ok = send_to_user(user_id, f"💬 <b>Message from Kevin:</b>\n\n{text}")
    return jsonify({"ok": ok})


@app.route("/api/broadcast", methods=["POST"])
@requires_auth
def api_broadcast():
    data      = request.get_json(force=True)
    text      = data.get("text", "")
    media_url = data.get("media_url", "")
    target    = data.get("target", "all")

    with users_lock:
        snapshot = dict(users_db)

    sent = 0
    for uid, udata in snapshot.items():
        if udata.get("completed"):
            continue
        broker = udata.get("broker", "")
        if target == "vantage"   and broker != "Vantage":  continue
        if target == "puprime"   and broker != "PU Prime": continue
        if target == "no_broker" and broker:               continue

        time.sleep(random.uniform(0.5, 3))

        if media_url:
            if any(ext in media_url.lower() for ext in [".mp4", ".mov", ".avi"]):
                send_video_to_user(uid, media_url, caption=text)
            else:
                send_photo_to_user(uid, media_url, caption=text)
        else:
            send_to_user(uid, text, keyboard=JOIN_BUTTON)

        with users_lock:
            users_db[uid]["last_drip"] = time.time()
            save_users(users_db)
        sent += 1

    # Log broadcast
    broadcasts = load_broadcasts()
    broadcasts.append({"time": time.time(), "text": text[:100], "sent": sent, "target": target})
    save_broadcasts(broadcasts[-50:])

    return jsonify({"ok": True, "sent": sent})


# ─── HEALTH ───────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    with users_lock:
        total     = len(users_db)
        completed = sum(1 for u in users_db.values() if u.get("completed"))
    return (
        f"Kevin VIP Onboarding Bot is running! ✅\n"
        f"Total leads: {total} | Completed: {completed} | Pending: {total - completed}\n"
        f"Dashboard: /dashboard"
    )


if __name__ == "__main__":
    threading.Thread(target=drip_scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
