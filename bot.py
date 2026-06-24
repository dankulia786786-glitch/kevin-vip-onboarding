import os
import json
import logging
import requests
import threading
import time
import random
from functools import wraps
from flask import Flask, request, jsonify, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8808650060:AAFNftKGNOtFeQTB3h26x-wVWUtXwS2fxh8")
OWNER_ID  = os.environ.get("OWNER_ID", "6838959359")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

VANTAGE_IMAGE = "https://raw.githubusercontent.com/dankulia786786-glitch/kevin-vip-onboarding/main/WhatsApp%20Image%202026-06-12%20at%2012.36.03.jpeg"
PUPRIME_IMAGE = "https://raw.githubusercontent.com/dankulia786786-glitch/kevin-vip-onboarding/main/WhatsApp%20Image%202026-06-12%20at%2014.49.01.jpeg"

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

DATA_DIR       = "/data"
USERS_FILE     = "/data/vip_users.json"
BROADCAST_FILE = "/data/broadcasts.json"
MESSAGES_FILE  = "/data/messages.json"
UNREAD_FILE    = "/data/unread.json"
NOTES_FILE     = "/data/notes.json"
users_lock     = threading.Lock()
messages_lock  = threading.Lock()
unread_lock    = threading.Lock()
notes_lock     = threading.Lock()

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

def load_messages():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(MESSAGES_FILE):
            with open(MESSAGES_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Load messages error: {e}")
    return {}

def save_messages(msgs):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(MESSAGES_FILE, "w") as f:
            json.dump(msgs, f)
    except Exception as e:
        logger.error(f"Save messages error: {e}")

def load_unread():
    try:
        if os.path.exists(UNREAD_FILE):
            with open(UNREAD_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_unread(data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(UNREAD_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Save unread error: {e}")

def load_notes():
    try:
        if os.path.exists(NOTES_FILE):
            with open(NOTES_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_notes(data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(NOTES_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Save notes error: {e}")

def store_client_message(user_id, text, direction="in"):
    uid = str(user_id)
    with messages_lock:
        msgs = load_messages()
        if uid not in msgs:
            msgs[uid] = []
        msgs[uid].append({
            "text":      text,
            "direction": direction,
            "time":      time.time()
        })
        msgs[uid] = msgs[uid][-200:]
        save_messages(msgs)
    if direction == "in":
        with unread_lock:
            unread = load_unread()
            unread[uid] = unread.get(uid, 0) + 1
            save_unread(unread)
    if direction == "in":
        with users_lock:
            if uid in users_db:
                users_db[uid]["last_seen"] = time.time()
                save_users(users_db)

users_db = load_users()
onboarding_state = {}
reply_map        = {}

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

def _add_step(user_id, step_text):
    with users_lock:
        if str(user_id) in users_db:
            steps = users_db[str(user_id)].get("steps", [])
            steps.append({"text": step_text, "time": time.time()})
            users_db[str(user_id)]["steps"] = steps
            save_users(users_db)

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
            "last_seen":   existing.get("last_seen", time.time()),
        }
        save_users(users_db)

    # SINGLE message — straight to broker choice
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
    store_client_message(user_id, "▶️ Client started the bot (/start)", direction="event")
    store_client_message(user_id, "🤖 Bot: Please choose your broker.", direction="out")

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
    store_client_message(user_id, "🔵 Client tapped: Vantage", direction="event")
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
    store_client_message(user_id, "🔴 Client tapped: PU Prime", direction="event")
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
    store_client_message(user_id, "✅ Client tapped: DONE", direction="event")
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
    store_client_message(user_id, f"🔢 MT5: {account_number}", direction="event")
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

MAX_DRIP_DAYS = 30
DRIP_INTERVAL = 86400

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
                time.sleep(random.uniform(5, 120))
                count = data.get("drip_count", 0)
                msg   = DRIP_MESSAGES[count % len(DRIP_MESSAGES)]
                ok    = send_to_user(uid, msg, keyboard=JOIN_BUTTON)
                if ok:
                    with users_lock:
                        users_db[uid]["last_drip"]  = time.time()
                        users_db[uid]["drip_count"] = count + 1
                        save_users(users_db)
        except Exception as e:
            logger.error(f"Drip error: {e}")
        time.sleep(300)

last_tp_forward = {}
tp_forward_lock = threading.Lock()

@app.route("/forward_tp", methods=["POST"])
def forward_tp():
    try:
        close_type = request.form.get("close_type", "TP1")
        pair       = request.form.get("pair", "XAUUSD")
        profit_str = request.form.get("profit_str", "")
        image_file = request.files.get("image")
        dedup_key  = f"{pair}_{close_type}"
        now = time.time()
        with tp_forward_lock:
            if now - last_tp_forward.get(dedup_key, 0) < 3600:
                return jsonify({"status": "duplicate_ignored"})
            last_tp_forward[dedup_key] = now
        pair_name = "GOLD" if pair == "XAUUSD" else "BITCOIN"
        tp_labels = {"TP1": f"TP1 just smashed on {pair_name}!", "TP2": f"TP2 just smashed on {pair_name}!", "TP3": f"ALL targets hit on {pair_name}!"}
        caption = (
            f"🔥 <b>{tp_labels.get(close_type, close_type+' hit!')}</b>\n\n"
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
            today_str = __import__("datetime").date.today().isoformat()
            if udata.get("last_tp_forward_day") == today_str and udata.get("tp_forward_today", 0) >= 2:
                continue
            time.sleep(random.uniform(0.3, 2))
            try:
                if image_bytes:
                    files   = {"photo": ("result.jpg", image_bytes, "image/jpeg")}
                    payload = {"chat_id": uid, "caption": caption, "parse_mode": "HTML", "reply_markup": json.dumps(JOIN_BUTTON)}
                    r  = requests.post(f"{TELEGRAM_URL}/sendPhoto", files=files, data=payload, timeout=15)
                    ok = r.json().get("ok", False)
                else:
                    ok = send_to_user(uid, caption, keyboard=JOIN_BUTTON)
                if ok:
                    with users_lock:
                        users_db[uid]["tp_forward_today"]    = udata.get("tp_forward_today", 0) + 1
                        users_db[uid]["last_tp_forward_day"] = today_str
                        save_users(users_db)
                    sent += 1
            except Exception as e:
                logger.error(f"TP forward error: {e}")
        return jsonify({"status": "ok", "sent": sent})
    except Exception as e:
        logger.error(f"forward_tp error: {e}")
        return jsonify({"status": "error"}), 500

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
                requests.post(f"{TELEGRAM_URL}/answerCallbackQuery", json={"callback_query_id": cq["id"]}, timeout=5)
            except Exception:
                pass
            stored   = onboarding_state.get(user_id, {})
            username = stored.get("username", username)
            if data == "broker_vantage":       handle_vantage(user_id, name, username)
            elif data == "broker_puprime":     handle_puprime(user_id, name, username)
            elif data == "done_vantage":       handle_done(user_id, name, username, "vantage")
            elif data == "done_puprime":       handle_done(user_id, name, username, "puprime")
            elif data == "restart_onboarding": handle_start(user_id, name, username)
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
                    store_client_message(client_id, text, direction="out")
                    notify_owner("✅ Your reply was sent to the client.")
                else:
                    notify_owner("⚠️ Could not find that client. Ask them to send a message first.")
            return jsonify({"ok": True})

        if text.strip():
            store_client_message(user_id, text.strip(), direction="in")

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

@app.route("/api/leads")
@requires_auth
def api_leads():
    with users_lock:
        snapshot = dict(users_db)
    leads = []
    for uid, d in snapshot.items():
        leads.append({"user_id": uid, "name": d.get("name",""), "username": d.get("username",""), "broker": d.get("broker",""), "mt5_account": d.get("mt5_account",""), "completed": d.get("completed",False), "drip_count": d.get("drip_count",0), "steps": d.get("steps",[]), "started_at": d.get("started_at",0), "last_seen": d.get("last_seen",0), "handled": d.get("handled",False)})
    leads.sort(key=lambda x: x["started_at"], reverse=True)
    total=len(leads); completed=sum(1 for l in leads if l["completed"]); vantage=sum(1 for l in leads if l.get("broker")=="Vantage"); puprime=sum(1 for l in leads if l.get("broker")=="PU Prime")
    return jsonify({"leads": leads, "total": total, "completed": completed, "pending": total-completed, "vantage": vantage, "puprime": puprime})

@app.route("/api/unread")
@requires_auth
def api_unread():
    with unread_lock:
        return jsonify({"unread": load_unread()})

@app.route("/api/mark_read", methods=["POST"])
@requires_auth
def api_mark_read():
    uid = request.get_json(force=True).get("user_id")
    if uid:
        with unread_lock:
            unread = load_unread()
            unread.pop(str(uid), None)
            save_unread(unread)
    return jsonify({"ok": True})

@app.route("/api/notes")
@requires_auth
def api_notes():
    with notes_lock:
        return jsonify({"notes": load_notes()})

@app.route("/api/note", methods=["POST"])
@requires_auth
def api_note():
    data = request.get_json(force=True)
    uid  = str(data.get("user_id",""))
    note = data.get("note","")
    if uid:
        with notes_lock:
            notes = load_notes()
            notes[uid] = note
            save_notes(notes)
    return jsonify({"ok": True})

@app.route("/api/handled", methods=["POST"])
@requires_auth
def api_handled():
    uid = str(request.get_json(force=True).get("user_id",""))
    if uid:
        with users_lock:
            if uid in users_db:
                users_db[uid]["handled"] = not users_db[uid].get("handled", False)
                save_users(users_db)
                return jsonify({"ok": True, "handled": users_db[uid]["handled"]})
    return jsonify({"ok": False})

@app.route("/api/chat/<user_id>")
@requires_auth
def api_chat(user_id):
    with messages_lock:
        msgs = load_messages()
    return jsonify({"messages": msgs.get(str(user_id),[]), "user_id": user_id})

@app.route("/api/send_file", methods=["POST"])
@requires_auth
def api_send_file():
    user_id = request.form.get("user_id")
    file    = request.files.get("file")
    if not user_id or not file:
        return jsonify({"ok": False})
    try:
        file_bytes = file.read()
        fname = file.filename.lower()
        mime  = file.mimetype or ""
        if mime.startswith("image/") or any(fname.endswith(x) for x in [".jpg",".jpeg",".png",".gif",".webp"]):
            r = requests.post(f"{TELEGRAM_URL}/sendPhoto", files={"photo":(file.filename,file_bytes,mime)}, data={"chat_id":user_id}, timeout=20)
        elif mime.startswith("video/") or any(fname.endswith(x) for x in [".mp4",".mov",".avi"]):
            r = requests.post(f"{TELEGRAM_URL}/sendVideo", files={"video":(file.filename,file_bytes,mime)}, data={"chat_id":user_id}, timeout=30)
        else:
            r = requests.post(f"{TELEGRAM_URL}/sendDocument", files={"document":(file.filename,file_bytes,mime)}, data={"chat_id":user_id}, timeout=20)
        ok = r.json().get("ok", False)
        if ok:
            store_client_message(user_id, f"[📎 File: {file.filename}]", direction="out")
        return jsonify({"ok": ok})
    except Exception as e:
        logger.error(f"send_file error: {e}")
        return jsonify({"ok": False})

@app.route("/api/message", methods=["POST"])
@requires_auth
def api_message():
    data    = request.get_json(force=True)
    user_id = data.get("user_id")
    text    = data.get("text","")
    if not user_id or not text:
        return jsonify({"ok": False})
    ok = send_to_user(user_id, f"💬 <b>Message from Kevin:</b>\n\n{text}")
    if ok:
        store_client_message(user_id, text, direction="out")
    return jsonify({"ok": ok})

@app.route("/api/broadcast", methods=["POST"])
@requires_auth
def api_broadcast():
    data      = request.get_json(force=True)
    text      = data.get("text","")
    media_url = data.get("media_url","")
    target    = data.get("target","all")
    with users_lock:
        snapshot = dict(users_db)
    sent = 0
    for uid, udata in snapshot.items():
        if udata.get("completed"): continue
        broker = udata.get("broker","")
        if target=="vantage" and broker!="Vantage": continue
        if target=="puprime" and broker!="PU Prime": continue
        if target=="no_broker" and broker: continue
        time.sleep(random.uniform(0.5,3))
        if media_url:
            if any(ext in media_url.lower() for ext in [".mp4",".mov",".avi"]):
                send_video_to_user(uid, media_url, caption=text)
            else:
                send_photo_to_user(uid, media_url, caption=text)
        else:
            send_to_user(uid, text, keyboard=JOIN_BUTTON)
        with users_lock:
            users_db[uid]["last_drip"] = time.time()
            save_users(users_db)
        sent += 1
    broadcasts = load_broadcasts()
    broadcasts.append({"time": time.time(), "text": text[:100], "sent": sent, "target": target})
    save_broadcasts(broadcasts[-50:])
    return jsonify({"ok": True, "sent": sent})

@app.route("/dashboard")
@requires_auth
def dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kevin VIP CRM</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#fff;min-height:100vh}
.header{background:linear-gradient(135deg,#1a1a2e,#16213e);padding:14px 20px;border-bottom:2px solid #d4af37;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
.header h1{font-size:18px;color:#d4af37}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;padding:16px 20px}
.stat-card{background:#1a1a2e;border-radius:10px;padding:14px;border:1px solid #2a2a4e;text-align:center}
.stat-card .number{font-size:28px;font-weight:bold;color:#d4af37}
.stat-card .label{font-size:11px;color:#888;margin-top:4px}
.stat-card.green .number{color:#00dc50}
.stat-card.red .number{color:#ff4444}
.stat-card.blue .number{color:#4a90e2}
.section{padding:0 20px 24px}
.section-title{font-size:15px;font-weight:bold;color:#d4af37;margin-bottom:12px}
.broadcast-box{background:#1a1a2e;border-radius:12px;padding:16px;border:1px solid #2a2a4e;margin-bottom:20px}
.broadcast-box textarea{width:100%;background:#0f0f1a;border:1px solid #2a2a4e;border-radius:8px;color:#fff;padding:10px;font-size:13px;resize:vertical;min-height:70px}
.broadcast-box input[type=text]{width:100%;background:#0f0f1a;border:1px solid #2a2a4e;border-radius:8px;color:#fff;padding:8px 10px;font-size:13px;margin-top:8px}
.btn{padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:13px;font-weight:bold;transition:all 0.2s}
.btn-gold{background:#d4af37;color:#000}
.btn-red{background:#c0392b;color:#fff}
.btn-green{background:#27ae60;color:#fff}
.btn-blue{background:#2980b9;color:#fff}
.btn-row{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.search-bar{width:100%;background:#1a1a2e;border:1px solid #2a2a4e;border-radius:8px;color:#fff;padding:9px 12px;font-size:13px;margin-bottom:12px}
.filter-tabs{display:flex;gap:6px;margin-bottom:14px;flex-wrap:wrap}
.filter-tab{padding:5px 14px;border-radius:20px;border:1px solid #2a2a4e;background:#1a1a2e;color:#888;cursor:pointer;font-size:12px}
.filter-tab.active{background:#d4af37;color:#000;border-color:#d4af37;font-weight:bold}
.leads-grid{display:flex;flex-direction:column;gap:12px}
.lead-card{background:#1a1a2e;border:1px solid #2a2a4e;border-radius:12px;padding:14px;position:relative}
.lead-card:hover{border-color:#d4af37}
.badge{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10px;font-weight:bold}
.badge-green{background:#1a3a2a;color:#00dc50;border:1px solid #00dc50}
.badge-orange{background:#3a2a1a;color:#f39c12;border:1px solid #f39c12}
.badge-blue{background:#1a2a3a;color:#4a90e2;border:1px solid #4a90e2}
.progress-ticks{display:flex;gap:5px;margin:8px 0;align-items:center}
.tick{width:22px;height:22px;border-radius:50%;border:2px solid #333;display:flex;align-items:center;justify-content:center;font-size:10px;color:#555}
.tick.done{border-color:#00dc50;background:#00dc50;color:#000}
.unread-badge{background:#e74c3c;color:#fff;border-radius:50%;width:18px;height:18px;font-size:10px;font-weight:bold;display:inline-flex;align-items:center;justify-content:center;margin-left:4px}
.lead-actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;align-items:center}
.btn-chat{background:#6c3483;color:#fff;padding:5px 10px;border-radius:6px;border:none;cursor:pointer;font-size:11px;font-weight:bold}
.btn-chat:hover{background:#8e44ad}
.btn-handled{background:transparent;border:1px solid #555;color:#888;padding:4px 8px;border-radius:6px;cursor:pointer;font-size:11px}
.btn-handled.active{border-color:#00dc50;color:#00dc50;background:#1a3a2a}
.quick-input{flex:1;min-width:120px;background:#0f0f1a;border:1px solid #2a2a4e;border-radius:6px;color:#fff;padding:5px 8px;font-size:12px}
.btn-send-quick{background:#2980b9;color:#fff;border:none;border-radius:6px;padding:5px 10px;font-size:12px;font-weight:bold;cursor:pointer}
.notes-area{width:100%;background:#0f0f1a;border:1px solid #2a2a4e;border-radius:6px;color:#aaa;padding:6px 8px;font-size:11px;resize:none;min-height:42px;margin-top:8px;font-family:inherit}
.toast{position:fixed;bottom:20px;right:20px;background:#00dc50;color:#000;padding:10px 18px;border-radius:8px;font-weight:bold;display:none;z-index:9999;font-size:13px}
#chat-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:1000;align-items:center;justify-content:center;padding:12px}
#chat-overlay.open{display:flex}
#chat-panel{background:#1a1a2e;border:1px solid #d4af37;border-radius:16px;width:100%;max-width:520px;max-height:90vh;display:flex;flex-direction:column;overflow:hidden}
#chat-header{background:linear-gradient(135deg,#16213e,#1a1a2e);padding:14px 16px;border-bottom:1px solid #2a2a4e;display:flex;align-items:center;justify-content:space-between}
#chat-header .chat-name{font-size:15px;font-weight:bold;color:#d4af37}
#chat-close{background:none;border:none;color:#888;font-size:22px;cursor:pointer}
#chat-messages{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;min-height:200px}
.chat-bubble{max-width:82%;padding:9px 13px;border-radius:14px;font-size:13px;line-height:1.5;word-break:break-word}
.chat-bubble.in{background:#0f0f1a;border:1px solid #2a2a4e;color:#ddd;align-self:flex-start}
.chat-bubble.out{background:#d4af37;color:#000;align-self:flex-end}
.chat-bubble.event{background:#1a2a1a;border:1px solid #2a4a2a;color:#7ec87e;align-self:center;font-size:11px;padding:5px 10px;border-radius:20px;max-width:95%;text-align:center}
.bubble-time{font-size:10px;opacity:0.55;margin-top:3px;text-align:right}
.chat-empty{text-align:center;color:#555;font-size:13px;margin:auto;padding:20px}
#chat-input-area{padding:12px 14px;border-top:1px solid #2a2a4e;display:flex;gap:8px;background:#16213e}
#chat-input{flex:1;background:#0f0f1a;border:1px solid #2a2a4e;border-radius:8px;color:#fff;padding:9px 12px;font-size:13px;outline:none}
#chat-input:focus{border-color:#d4af37}
#chat-send-btn{background:#d4af37;color:#000;border:none;border-radius:8px;padding:9px 16px;font-weight:bold;cursor:pointer;font-size:13px}
</style>
</head>
<body>
<div class="header">
  <div><h1>👑 Kevin VIP CRM</h1><div style="font-size:12px;color:#888">Gold Signals — Lead Management</div></div>
  <div style="text-align:right;font-size:12px;color:#888"><div id="clock"></div><div style="margin-top:2px">Auto-refresh 30s</div></div>
</div>
<div class="stats">
  <div class="stat-card"><div class="number" id="s-total">-</div><div class="label">Total</div></div>
  <div class="stat-card green"><div class="number" id="s-done">-</div><div class="label">✅ Done</div></div>
  <div class="stat-card red"><div class="number" id="s-pending">-</div><div class="label">⏳ Pending</div></div>
  <div class="stat-card blue"><div class="number" id="s-vantage">-</div><div class="label">🔵 Vantage</div></div>
  <div class="stat-card blue"><div class="number" id="s-puprime">-</div><div class="label">🔴 PU Prime</div></div>
</div>
<div class="section">
  <div class="section-title">📢 Broadcast Message</div>
  <div class="broadcast-box">
    <textarea id="bc-text" placeholder="e.g. We just hit TP3 on Gold — members made £420 for FREE today!"></textarea>
    <input type="text" id="bc-media" placeholder="Optional: image or video URL" />
    <div class="btn-row">
      <button class="btn btn-gold" onclick="sendBroadcast('all')">📢 All Pending</button>
      <button class="btn btn-blue" onclick="sendBroadcast('no_broker')">Not Started</button>
      <button class="btn btn-green" onclick="sendBroadcast('vantage')">Vantage Only</button>
      <button class="btn btn-red" onclick="sendBroadcast('puprime')">PU Prime Only</button>
    </div>
  </div>
  <div class="section-title">👥 All Leads</div>
  <input class="search-bar" type="text" id="search" placeholder="🔍 Search name, username, MT5..." onkeyup="filterLeads()" />
  <div class="filter-tabs">
    <div class="filter-tab active" onclick="setFilter('all',this)">All</div>
    <div class="filter-tab" onclick="setFilter('completed',this)">✅ Done</div>
    <div class="filter-tab" onclick="setFilter('pending',this)">⏳ Pending</div>
    <div class="filter-tab" onclick="setFilter('Vantage',this)">🔵 Vantage</div>
    <div class="filter-tab" onclick="setFilter('PU Prime',this)">🔴 PU Prime</div>
  </div>
  <div class="leads-grid" id="leads-grid"></div>
</div>
<div id="chat-overlay" onclick="closeChatOnOverlay(event)">
  <div id="chat-panel">
    <div id="chat-header">
      <div><div class="chat-name" id="chat-title">Chat</div><div style="font-size:11px;color:#888" id="chat-sub"></div></div>
      <button id="chat-close" onclick="closeChat()">✕</button>
    </div>
    <div id="chat-messages"><div class="chat-empty">Loading...</div></div>
    <div id="chat-input-area">
      <input type="text" id="chat-input" placeholder="Type a message..." onkeydown="if(event.key==='Enter')sendChatMsg()" />
      <button id="chat-send-btn" onclick="sendChatMsg()">Send ✈️</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
let allLeads=[],allUnread={},allNotes={},currentFilter='all',activeChatUserId=null,chatPollInterval=null;
const STEPS=['Started','Broker','Done','MT5','Complete'];
function showToast(msg,color='#00dc50'){const t=document.getElementById('toast');t.textContent=msg;t.style.background=color;t.style.display='block';setTimeout(()=>t.style.display='none',3000)}
function setFilter(f,el){currentFilter=f;document.querySelectorAll('.filter-tab').forEach(t=>t.classList.remove('active'));el.classList.add('active');renderAll()}
function filterLeads(){renderAll()}
function getFiltered(){const s=(document.getElementById('search').value||'').toLowerCase();return allLeads.filter(l=>{const ms=!s||(l.name||'').toLowerCase().includes(s)||(l.username||'').toLowerCase().includes(s)||(l.mt5_account||'').toLowerCase().includes(s);const mf=currentFilter==='all'||(currentFilter==='completed'&&l.completed)||(currentFilter==='pending'&&!l.completed)||(currentFilter===l.broker);return ms&&mf})}
function getProgress(l){const steps=(l.steps||[]).map(s=>s.text);return[steps.some(s=>s.includes('Started')),steps.some(s=>s.includes('Chose')),steps.some(s=>s.includes('DONE')),steps.some(s=>s.includes('MT5')||s.includes('Submitted')),!!l.completed]}
function lastSeenHtml(l){if(!l.last_seen)return'<span style="color:#555">—</span>';const diff=Date.now()/1000-l.last_seen;const isOnline=diff<300;let label;if(diff<60)label='Just now';else if(diff<3600)label=Math.floor(diff/60)+'m ago';else if(diff<86400)label=Math.floor(diff/3600)+'h ago';else label=Math.floor(diff/86400)+'d ago';return`<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${isOnline?'#00dc50':'#555'};margin-right:4px"></span><span style="font-size:11px;color:#666">${label}</span>`}
function renderAll(){const f=getFiltered();const grid=document.getElementById('leads-grid');if(!f.length){grid.innerHTML='<div style="text-align:center;color:#888;padding:30px">No leads found</div>';return}grid.innerHTML=f.map(l=>{const uid=l.user_id;const esc=(l.name||'Client').replace(/'/g,"\\'").replace(/"/g,'&quot;');const uname=(l.username||'').replace(/'/g,"\\'");const unread=allUnread[uid]||0;const badge=unread>0?`<span class="unread-badge">${unread}</span>`:'';const prog=getProgress(l);const note=allNotes[uid]||'';return`<div class="lead-card"><div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:10px"><div><div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><span style="font-size:15px;font-weight:bold">${l.name||'—'}</span>${l.broker?`<span class="badge badge-blue">${l.broker}</span>`:''} ${l.completed?'<span class="badge badge-green">✅ Done</span>':'<span class="badge badge-orange">⏳ Pending</span>'}</div><div style="font-size:11px;color:#666;margin-top:3px">${l.username&&l.username!=='no username'?`<a href="https://t.me/${l.username}" target="_blank" style="color:#4a90e2">@${l.username}</a>`:'No username'}${l.mt5_account?' • MT5: '+l.mt5_account:''}</div><div style="font-size:11px;color:#666;margin-top:2px">${lastSeenHtml(l)}</div></div><div style="font-size:11px;color:#555">Drip: ${l.drip_count||0}</div></div><div class="progress-ticks">${prog.map((done,idx)=>`<div class="tick ${done?'done':''}" title="${STEPS[idx]}">${done?'✓':idx+1}</div>`).join('')}<span style="font-size:10px;color:#666;margin-left:6px">${STEPS.filter((_,i)=>prog[i]).length}/5 steps</span></div><div class="lead-actions"><button class="btn-chat" onclick="openChat('${uid}','${esc}','${uname}')">💬 Chat ${badge}</button><button class="btn-handled ${l.handled?'active':''}" onclick="toggleHandled('${uid}',this)">${l.handled?'✅ Handled':'Mark handled'}</button><input class="quick-input" type="text" id="qi-${uid}" placeholder="Quick send..." onkeydown="if(event.key==='Enter')sendQuick('${uid}')" /><button class="btn-send-quick" onclick="sendQuick('${uid}')">Send</button></div><textarea class="notes-area" id="note-${uid}" placeholder="Add a private note..." onblur="saveNote('${uid}')">${note}</textarea></div>`}).join('')}
async function loadLeads(){try{const[lr,ur,nr]=await Promise.all([fetch('/api/leads').then(r=>r.json()),fetch('/api/unread').then(r=>r.json()),fetch('/api/notes').then(r=>r.json())]);allLeads=lr.leads||[];allUnread=ur.unread||{};allNotes=nr.notes||{};document.getElementById('s-total').textContent=lr.total;document.getElementById('s-done').textContent=lr.completed;document.getElementById('s-pending').textContent=lr.pending;document.getElementById('s-vantage').textContent=lr.vantage;document.getElementById('s-puprime').textContent=lr.puprime;renderAll()}catch(e){console.error(e)}}
async function sendQuick(uid){const inp=document.getElementById('qi-'+uid);const text=inp?inp.value.trim():'';if(!text)return;const r=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid,text})});const d=await r.json();if(d.ok){showToast('✅ Sent!');if(inp)inp.value=''}else showToast('❌ Failed','#e74c3c')}
async function toggleHandled(uid,btn){const r=await fetch('/api/handled',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid})});const d=await r.json();if(d.ok){btn.classList.toggle('active',d.handled);btn.textContent=d.handled?'✅ Handled':'Mark handled'}}
async function saveNote(uid){const el=document.getElementById('note-'+uid);if(!el)return;await fetch('/api/note',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid,note:el.value})})}
async function sendBroadcast(target){const text=document.getElementById('bc-text').value.trim();const media=document.getElementById('bc-media').value.trim();if(!text){showToast('Write a message first','#e74c3c');return}if(!confirm('Send to '+target+' leads?'))return;const r=await fetch('/api/broadcast',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,media_url:media,target})});const d=await r.json();showToast('✅ Sent to '+d.sent+' leads!')}
function openChat(uid,name,username){activeChatUserId=uid;document.getElementById('chat-title').textContent='💬 '+name;document.getElementById('chat-sub').textContent=username?'@'+username:'No username';document.getElementById('chat-overlay').classList.add('open');fetch('/api/mark_read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid})});allUnread[uid]=0;loadChatMessages();if(chatPollInterval)clearInterval(chatPollInterval);chatPollInterval=setInterval(loadChatMessages,6000)}
function closeChat(){document.getElementById('chat-overlay').classList.remove('open');activeChatUserId=null;if(chatPollInterval){clearInterval(chatPollInterval);chatPollInterval=null}}
function closeChatOnOverlay(e){if(e.target===document.getElementById('chat-overlay'))closeChat()}
async function loadChatMessages(){if(!activeChatUserId)return;try{const r=await fetch('/api/chat/'+activeChatUserId);const d=await r.json();renderChatMessages(d.messages||[])}catch(e){}}
function renderChatMessages(messages){const box=document.getElementById('chat-messages');if(!messages.length){box.innerHTML='<div class="chat-empty">No messages yet.</div>';return}const wasAtBottom=box.scrollHeight-box.clientHeight<=box.scrollTop+40;box.innerHTML=messages.map(m=>`<div class="chat-bubble ${m.direction}">${escHtml(m.text)}<div class="bubble-time">${new Date(m.time*1000).toLocaleString('en-GB',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'short'})}</div></div>`).join('');if(wasAtBottom||messages.length<=5)box.scrollTop=box.scrollHeight}
function escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
async function sendChatMsg(){const input=document.getElementById('chat-input');const text=input.value.trim();if(!text||!activeChatUserId)return;input.value='';const r=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:activeChatUserId,text})});const d=await r.json();if(d.ok)await loadChatMessages();else{showToast('❌ Failed','#e74c3c');input.value=text}}
function updateClock(){document.getElementById('clock').textContent=new Date().toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:'Europe/London'})+' UK'}
loadLeads();setInterval(loadLeads,30000);setInterval(updateClock,1000);updateClock();
</script>
</body>
</html>"""

@app.route("/", methods=["GET"])
def health():
    with users_lock:
        total=len(users_db); completed=sum(1 for u in users_db.values() if u.get("completed"))
    return f"Kevin VIP Onboarding Bot is running! ✅\nTotal leads: {total} | Completed: {completed} | Pending: {total-completed}\nDashboard: /dashboard"

if __name__ == "__main__":
    threading.Thread(target=drip_scheduler, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
