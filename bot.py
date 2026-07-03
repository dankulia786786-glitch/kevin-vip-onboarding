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
MESSAGES_FILE  = "/data/messages.json"
UNREAD_FILE    = "/data/unread.json"
NOTES_FILE     = "/data/notes.json"
BLOCKED_FILE   = "/data/blocked.json"
users_lock     = threading.Lock()
messages_lock  = threading.Lock()
unread_lock    = threading.Lock()
notes_lock     = threading.Lock()
blocked_lock   = threading.Lock()

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


def load_blocked():
    try:
        if os.path.exists(BLOCKED_FILE):
            with open(BLOCKED_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_blocked(data):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(BLOCKED_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Save blocked error: {e}")

def is_blocked(username):
    """Check if a username is on the blocked list (case-insensitive)."""
    if not username or username == "no username":
        return False
    uname = username.lower().lstrip("@").strip()
    with blocked_lock:
        blocked = load_blocked()
    return uname in [b.lower().lstrip("@").strip() for b in blocked]

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
    # Mark as unread if incoming
    if direction == "in":
        with unread_lock:
            unread = load_unread()
            unread[uid] = unread.get(uid, 0) + 1
            save_unread(unread)
    # Update last_seen for incoming messages
    if direction == "in":
        with users_lock:
            if uid in users_db:
                users_db[uid]["last_seen"] = time.time()
                save_users(users_db)

users_db = load_users()
onboarding_state = {}
reply_map        = {}
processed_callbacks = {}   # dedup: callback_query_id -> timestamp
callback_lock       = threading.Lock()

# ─── DRIP MESSAGES ────────────────────────────────────────────────────────────
DRIP_MESSAGES = [
    "⏰ <b>Gold signal expected in the next 10 minutes!</b>\n\nOur PM group gets the entry, the chart, and the TP result the second it happens — completely FREE.\n\nDon't watch from the sidelines.\n\n❓ Need a hand? Message: @Kevsupportteam\n\n👇 JOIN THE PM NOW 👇",
    "💰 <b>GOLD JUST SMASHED TP — members banked profit FOR FREE!</b>\n\nWhile you were outside the group, our PM members had the entry, the SL, the TP — all sent straight to their phone.\n\nThis happens multiple times a day.\n\n❓ Stuck? Message: @Kevsupportteam\n\n👇 Complete your FREE setup now",
    "🪙 <b>Bitcoin signal incoming — get it before it moves.</b>\n\nWe trade Gold AND Bitcoin in the same FREE group, including weekend BTC setups when most signal groups go quiet.\n\nYou're one step from being inside.\n\n❓ Questions? @Kevsupportteam\n\n👇 JOIN THE PM NOW",
    "📊 <b>You started but never finished setting up.</b>\n\nMembers inside the group are getting up to 12+ signals a day across Gold and Bitcoin — all FREE if you've got a Vantage or PU Prime account.\n\nTakes 2 minutes to unlock.\n\n❓ Need help? @Kevsupportteam\n\n👇 Finish your FREE setup",
    "✅ <b>ALL TARGETS HIT on today's Gold trade!</b>\n\nFull profits secured by everyone already inside the PM group. Every entry, every TP, every chart — sent live, completely FREE.\n\nThis is what waiting is costing you.\n\n❓ Help: @Kevsupportteam\n\n👇 JOIN FREE NOW",
    "🔥 <b>Live signal dropping shortly on Gold or Bitcoin.</b>\n\nWe're not a once-a-day group — members get multiple high quality setups daily, weekends included.\n\nNo subscription. No catch. Just complete the free setup once.\n\n❓ @Kevsupportteam if you're stuck\n\n👇 Complete setup",
    "💎 <b>FREE access. Up to 12+ signals a day. Gold + Bitcoin.</b>\n\nWeekend Bitcoin trades when most groups go silent. 50% deposit bonus for life on top.\n\nAll it takes is finishing what you started.\n\n❓ Message: @Kevsupportteam\n\n👇 JOIN THE PM NOW",
    "🚨 <b>Your spot is still open — but not guaranteed.</b>\n\nYou clicked start but didn't complete the steps. Members already inside are getting Gold and Bitcoin signals around the clock, completely FREE.\n\n❓ Need support? @Kevsupportteam\n\n👇 Finish your FREE setup before it closes",
    "📈 <b>Bitcoin and Gold both moving today.</b>\n\nOur PM group covers both markets, every day — including weekends when most traders are asleep on opportunities.\n\nFree for anyone with a Vantage or PU Prime account.\n\n❓ @Kevsupportteam\n\n👇 JOIN FREE NOW",
    "🏆 <b>Another TP smashed — full profits locked in for members.</b>\n\nThe chart, the entry, the result — it's all shared live inside the PM group the second it happens.\n\nYou're missing it right now.\n\n❓ Help: @Kevsupportteam\n\n👇 Complete your FREE setup",
    "⚡ <b>Setup taking shape on Gold — signal could fire any minute.</b>\n\nGet it the second it's live by finishing your FREE access. Takes under 2 minutes.\n\n❓ Questions? @Kevsupportteam\n\n👇 JOIN THE PM NOW",
    "🎯 <b>12+ signals a day. Gold, Bitcoin, and weekend BTC trades.</b>\n\nAll 100% FREE with a Vantage or PU Prime account — no subscription required.\n\nYou're so close to being inside.\n\n❓ @Kevsupportteam\n\n👇 Finish your FREE setup now",
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
        is_new = str(user_id) not in users_db
        users_db[str(user_id)] = {
            "name":        first_name,
            "username":    username,
            "started_at":  existing.get("started_at", time.time()),
            "completed":   existing.get("completed", False),
            # Only reset last_drip for brand new users, not returning ones
            "last_drip":   existing.get("last_drip", time.time()) if not is_new else time.time(),
            "drip_count":  existing.get("drip_count", 0),
            "broker":      existing.get("broker"),
            "mt5_account": existing.get("mt5_account"),
            "steps":       existing.get("steps", []),
            "last_seen":   time.time(),  # Always update last_seen
        }
        save_users(users_db)

    send_to_user(user_id,
        f"👋 <b>Welcome, {first_name} | GOLD SIGNALS 🔔</b>\n\n"
        "▓░░░░ <b>20% complete</b>\n\n"
        "🚀 <b>Let's get you set up.</b>\n"
        "⏱️ Takes less than 20 seconds to complete.\n\n"
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

    # Log to chat history
    store_client_message(user_id, "▶️ Client started the bot (/start)", direction="event")
    store_client_message(user_id, "🤖 Bot: Welcome! Please choose your broker — Vantage or PU Prime.", direction="out")

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
        "▓▓░░░ <b>40% complete</b>\n\n"
        "🚀 <b>Complete the steps below to activate your FREE Premium Group access.</b> (Takes 10s)\n\n"
        "1️⃣ Log-in to your Vantage client portal:\n👇\n"
        "https://secure.vantagemarkets.com/logout?lang=en_US\n\n"
        "2️⃣ After Log-in, Please click link below & Fill the Form 📋\n👇\n"
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

    # Log to chat history
    store_client_message(user_id, "🔵 Client tapped: Vantage", direction="event")
    store_client_message(user_id, "🤖 Bot: Sent Vantage IB transfer instructions (IB Code: 58576). Waiting for DONE.", direction="out")

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
        "▓▓░░░ <b>40% complete</b>\n\n"
        "🚀 <b>Complete the steps below to activate your FREE Premium Group access.</b> (Takes 10s)\n\n"
        "1️⃣ Log in to your PU Prime Client Portal\n👇\n"
        "https://myaccount.puprime.com/home\n\n"
        "2️⃣ After Log-in, Please click link below & Open the IB Transfer Form\n👇\n"
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

    # Log to chat history
    store_client_message(user_id, "🔴 Client tapped: PU Prime", direction="event")
    store_client_message(user_id, "🤖 Bot: Sent PU Prime IB transfer instructions (IB Code: 50151). Waiting for DONE.", direction="out")

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

    # Log to chat history
    store_client_message(user_id, "✅ Client tapped: DONE (IB transfer completed)", direction="event")
    store_client_message(user_id, "🤖 Bot: Please enter your MT4/MT5 account number.", direction="out")

    send_to_user(user_id,
        "▓▓▓▓░ <b>80% complete</b>\n\n"
        "🎉 <b>Almost there — you're getting FREE access!</b>\n\n"
        "Please provide ONE of the following to verify your account:\n\n"
        "✅ Your MT4/MT5 Account Number\n"
        "  — or —\n"
        "✅ Your account email\n"
        "  — or —\n"
        "✅ Your account UID\n\n"
        "👇 Just type it below and send."
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

    # Log to chat history
    store_client_message(user_id, f"🔢 Client entered MT5 number: {account_number}", direction="event")
    store_client_message(user_id, "🤖 Bot: Account received! Team will verify and activate your access shortly. Welcome! 🏆", direction="out")

    with users_lock:
        if str(user_id) in users_db:
            users_db[str(user_id)]["completed"]   = True
            users_db[str(user_id)]["mt5_account"] = account_number
            save_users(users_db)

    send_to_user(user_id,
        "▓▓▓▓▓ <b>100% complete</b> ✅\n\n"
        "✅ <b>Details received!</b>\n\n"
        "Our team will verify your account and activate your FREE Premium Group access shortly.\n\n"
        "🏆 Welcome to Gold PM Group!\n\n"
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
DRIP_INTERVAL = 25200  # 7 hours (within your 6-8 hour target)

def drip_scheduler():
    logger.info("✅ DRIP SCHEDULER THREAD STARTED")
    cycle = 0
    while True:
        cycle += 1
        try:
            now = time.time()
            with users_lock:
                snapshot = dict(users_db)

            pending_count = sum(1 for d in snapshot.values() if not d.get("completed"))
            logger.info(f"[Drip cycle #{cycle}] Checking {pending_count} pending leads...")

            due_count = 0
            for uid, data in snapshot.items():
                if data.get("completed"):
                    continue
                started = data.get("started_at", now)
                if now - started > MAX_DRIP_DAYS * 86400:
                    continue
                last_drip = data.get("last_drip", 0)
                if now - last_drip < DRIP_INTERVAL:
                    continue

                due_count += 1
                time.sleep(random.uniform(5, 30))

                count = data.get("drip_count", 0)
                msg   = DRIP_MESSAGES[count % len(DRIP_MESSAGES)]
                ok    = send_to_user(uid, msg, keyboard=JOIN_BUTTON)
                if ok:
                    with users_lock:
                        users_db[uid]["last_drip"]  = time.time()
                        users_db[uid]["drip_count"] = count + 1
                        save_users(users_db)
                    logger.info(f"✅ Drip #{count+1} sent to {uid}")
                else:
                    logger.error(f"❌ Drip FAILED to send to {uid}")

            logger.info(f"[Drip cycle #{cycle}] Complete. {due_count} leads were due and processed.")

        except Exception as e:
            logger.error(f"Drip scheduler error: {e}")
        time.sleep(300)


def start_background_threads():
    """Called at import time so it works under gunicorn AND direct python run."""
    threading.Thread(target=drip_scheduler, daemon=True).start()
    logger.info("Background threads launched (drip scheduler)")

start_background_threads()

# ─── FORWARD TP TO INCOMPLETE LEADS ─────────────────────────────────────────
last_tp_forward = {}
tp_forward_lock = threading.Lock()

@app.route("/forward_tp", methods=["POST"])
def forward_tp():
    try:
        close_type = request.form.get("close_type", "TP1")
        pair       = request.form.get("pair", "XAUUSD")
        profit_str = request.form.get("profit_str", "")
        image_file = request.files.get("image")

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
                        "chat_id":      uid,
                        "caption":      caption,
                        "parse_mode":   "HTML",
                        "reply_markup": json.dumps(JOIN_BUTTON)
                    }
                    r  = requests.post(f"{TELEGRAM_URL}/sendPhoto", files=files, data=payload, timeout=15)
                    ok = r.json().get("ok", False)
                else:
                    ok = send_to_user(uid, caption, keyboard=JOIN_BUTTON)

                if ok:
                    with users_lock:
                        users_db[uid]["tp_forward_today"]    = tp_count_today + 1
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
            cq_id    = str(cq.get("id", ""))

            # ── DEDUP: ignore if we've already processed this exact callback ──
            now_ts = time.time()
            with callback_lock:
                # Clean out old entries (older than 5 min)
                for k in [k for k, t in processed_callbacks.items() if now_ts - t > 300]:
                    processed_callbacks.pop(k, None)
                # Dedup key combines user + action so a genuine re-tap later still works,
                # but Telegram's instant retry of the SAME callback id is blocked
                dedup_key = f"{user_id}_{data}"
                if cq_id and cq_id in processed_callbacks:
                    return jsonify({"ok": True})
                # Also block same user+action within 3 seconds (double-tap / retry)
                last = processed_callbacks.get(dedup_key, 0)
                if now_ts - last < 3:
                    return jsonify({"ok": True})
                if cq_id:
                    processed_callbacks[cq_id] = now_ts
                processed_callbacks[dedup_key] = now_ts

            try:
                requests.post(f"{TELEGRAM_URL}/answerCallbackQuery",
                              json={"callback_query_id": cq["id"]}, timeout=5)
            except Exception:
                pass
            stored   = onboarding_state.get(user_id, {})
            username = stored.get("username", username)

            # ── BLOCKED USER CHECK — silently ignore button taps ──
            if is_blocked(username):
                logger.info(f"🚫 Blocked user tapped button (ignored): @{username}")
                return jsonify({"ok": True})

            # If user not in DB at all (e.g. after restart), register them first
            if str(user_id) not in users_db:
                handle_start(user_id, name, username)
                return jsonify({"ok": True})

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

        # ── BLOCKED USER CHECK — silently ignore all messages ──
        if user_id != str(OWNER_ID) and is_blocked(username):
            logger.info(f"🚫 Blocked user messaged (ignored): @{username}")
            return jsonify({"ok": True})

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
                    notify_owner("⚠️ Could not find that client.")
            return jsonify({"ok": True})

        # ── Always store every client message first, no matter what ──
        if text.strip():
            store_client_message(user_id, text.strip(), direction="in")

        # ── Auto-register if not in DB (catches edge cases) ──
        if str(user_id) not in users_db and text.strip():
            handle_start(user_id, name, username)
            return jsonify({"ok": True})

        if text.strip().startswith("/start"):
            handle_start(user_id, name, username)
            return jsonify({"ok": True})

        state = onboarding_state.get(user_id, {})
        if state.get("step") == "awaiting_account" and text.strip():
            handle_account_number(user_id, name, username, text.strip(), state.get("broker", "unknown"))
            return jsonify({"ok": True})

        # If user is in DB, chose a broker, clicked DONE but state was lost (server restart)
        # accept their verification detail (number, email, or UID)
        t = text.strip()
        looks_like_account = (
            (t.isdigit() and len(t) >= 5) or           # MT5 number
            ("@" in t and "." in t) or                  # email
            (len(t) >= 5 and len(t) <= 40 and " " not in t)  # UID / account ref
        )
        if looks_like_account:
            uid_data = users_db.get(str(user_id), {})
            broker = (uid_data.get("broker") or "").lower()
            if broker and not uid_data.get("completed"):
                broker_key = "vantage" if broker == "vantage" else "puprime"
                logger.info(f"Auto-detecting account detail from {user_id}: {t}")
                handle_account_number(user_id, name, username, t, broker_key)
                return jsonify({"ok": True})

        forward_to_owner(user_id, name, username, text)

    except Exception as e:
        logger.error(f"Update error: {e}")
    return jsonify({"ok": True})


# ─── CRM DASHBOARD ────────────────────────────────────────────────────────────
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>Kevin VIP CRM</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #fff; min-height: 100vh; }

/* HEADER */
.header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 14px 20px; border-bottom: 2px solid #d4af37; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.header h1 { font-size: 18px; color: #d4af37; }
.header .subtitle { font-size: 12px; color: #888; margin-top: 2px; }
.header-right { text-align: right; font-size: 12px; color: #888; }

/* STATS */
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; padding: 16px 20px; }
.stat-card { background: #1a1a2e; border-radius: 10px; padding: 14px; border: 1px solid #2a2a4e; text-align: center; }
.stat-card .number { font-size: 28px; font-weight: bold; color: #d4af37; }
.stat-card .label { font-size: 11px; color: #888; margin-top: 4px; }
.stat-card.green .number { color: #00dc50; }
.stat-card.red .number { color: #ff4444; }
.stat-card.blue .number { color: #4a90e2; }

/* SECTION */
.section { padding: 0 20px 24px; }
.section-title { font-size: 15px; font-weight: bold; color: #d4af37; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }

/* BROADCAST */
.broadcast-box { background: #1a1a2e; border-radius: 12px; padding: 16px; border: 1px solid #2a2a4e; margin-bottom: 20px; }
.broadcast-box textarea { width: 100%; background: #0f0f1a; border: 1px solid #2a2a4e; border-radius: 8px; color: #fff; padding: 10px; font-size: 13px; resize: vertical; min-height: 70px; }
.broadcast-box input[type=text] { width: 100%; background: #0f0f1a; border: 1px solid #2a2a4e; border-radius: 8px; color: #fff; padding: 8px 10px; font-size: 13px; margin-top: 8px; }
.btn { padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer; font-size: 13px; font-weight: bold; transition: all 0.2s; }
.btn-gold { background: #d4af37; color: #000; }
.btn-gold:hover { background: #f0c840; }
.btn-red { background: #c0392b; color: #fff; }
.btn-green { background: #27ae60; color: #fff; }
.btn-blue { background: #2980b9; color: #fff; }
.btn:hover { opacity: 0.88; transform: translateY(-1px); }
.btn-row { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }

/* SEARCH & FILTERS */
.search-bar { width: 100%; background: #1a1a2e; border: 1px solid #2a2a4e; border-radius: 8px; color: #fff; padding: 9px 12px; font-size: 13px; margin-bottom: 12px; }
.filter-tabs { display: flex; gap: 6px; margin-bottom: 14px; flex-wrap: wrap; }
.filter-tab { padding: 5px 14px; border-radius: 20px; border: 1px solid #2a2a4e; background: #1a1a2e; color: #888; cursor: pointer; font-size: 12px; }
.filter-tab.active { background: #d4af37; color: #000; border-color: #d4af37; font-weight: bold; }

/* CARDS (mobile-first layout) */
.leads-grid { display: flex; flex-direction: column; gap: 12px; }
.lead-card {
  background: #1a1a2e;
  border: 1px solid #2a2a4e;
  border-radius: 12px;
  padding: 14px;
  position: relative;
}
.lead-card:hover { border-color: #d4af37; }
.lead-card-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 10px; }
.lead-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.lead-name { font-size: 15px; font-weight: bold; color: #fff; }
.online-dot { width: 8px; height: 8px; border-radius: 50%; background: #555; display: inline-block; flex-shrink: 0; }
.online-dot.online { background: #00dc50; box-shadow: 0 0 6px #00dc50; }
.last-seen { font-size: 11px; color: #666; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 10px; font-weight: bold; }
.badge-green { background: #1a3a2a; color: #00dc50; border: 1px solid #00dc50; }
.badge-orange { background: #3a2a1a; color: #f39c12; border: 1px solid #f39c12; }
.badge-blue { background: #1a2a3a; color: #4a90e2; border: 1px solid #4a90e2; }

/* PROGRESS TICKS */
.progress-ticks { display: flex; gap: 5px; margin: 8px 0; align-items: center; }
.tick { width: 22px; height: 22px; border-radius: 50%; border: 2px solid #333; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #555; transition: all 0.3s; flex-shrink: 0; }
.tick.done { border-color: #00dc50; background: #00dc50; color: #000; }
.tick-label { font-size: 10px; color: #666; margin-left: 6px; }

/* UNREAD BADGE */
.unread-badge { background: #e74c3c; color: #fff; border-radius: 50%; width: 18px; height: 18px; font-size: 10px; font-weight: bold; display: inline-flex; align-items: center; justify-content: center; margin-left: 4px; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.2); } }

/* ACTION BUTTONS ROW */
.lead-actions { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; align-items: center; }
.btn-chat { background: #6c3483; color: #fff; padding: 5px 10px; border-radius: 6px; border: none; cursor: pointer; font-size: 11px; font-weight: bold; display: flex; align-items: center; gap: 4px; }
.btn-chat:hover { background: #8e44ad; }
.btn-handled { background: transparent; border: 1px solid #555; color: #888; padding: 4px 8px; border-radius: 6px; cursor: pointer; font-size: 11px; }
.btn-handled.active { border-color: #00dc50; color: #00dc50; background: #1a3a2a; }
.quick-input { flex: 1; min-width: 120px; background: #0f0f1a; border: 1px solid #2a2a4e; border-radius: 6px; color: #fff; padding: 5px 8px; font-size: 12px; }
.btn-send-quick { background: #2980b9; color: #fff; border: none; border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: bold; cursor: pointer; }

/* NOTES */
.notes-area { width: 100%; background: #0f0f1a; border: 1px solid #2a2a4e; border-radius: 6px; color: #aaa; padding: 6px 8px; font-size: 11px; resize: none; min-height: 42px; margin-top: 8px; font-family: inherit; }
.notes-area:focus { border-color: #d4af37; outline: none; color: #fff; }
.notes-saved { font-size: 10px; color: #00dc50; display: none; margin-top: 2px; }

/* TOAST */
.toast { position: fixed; bottom: 20px; right: 20px; background: #00dc50; color: #000; padding: 10px 18px; border-radius: 8px; font-weight: bold; display: none; z-index: 9999; font-size: 13px; max-width: 90vw; }

/* CHAT PANEL */
#chat-overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.75); z-index: 1000;
  align-items: center; justify-content: center; padding: 12px;
}
#chat-overlay.open { display: flex; }
#chat-panel {
  background: #1a1a2e; border: 1px solid #d4af37;
  border-radius: 16px; width: 100%; max-width: 520px;
  max-height: 90vh; display: flex; flex-direction: column; overflow: hidden;
}
#chat-header {
  background: linear-gradient(135deg, #16213e, #1a1a2e);
  padding: 14px 16px; border-bottom: 1px solid #2a2a4e;
  display: flex; align-items: center; justify-content: space-between;
}
#chat-header .chat-name { font-size: 15px; font-weight: bold; color: #d4af37; }
#chat-header .chat-sub  { font-size: 11px; color: #888; margin-top: 2px; }
#chat-close { background: none; border: none; color: #888; font-size: 22px; cursor: pointer; }
#chat-close:hover { color: #fff; }
#chat-messages {
  flex: 1; overflow-y: auto; padding: 14px;
  display: flex; flex-direction: column; gap: 8px; min-height: 200px;
}
#chat-messages::-webkit-scrollbar { width: 3px; }
#chat-messages::-webkit-scrollbar-thumb { background: #2a2a4e; border-radius: 3px; }
.chat-bubble { max-width: 82%; padding: 9px 13px; border-radius: 14px; font-size: 13px; line-height: 1.5; word-break: break-word; }
.chat-bubble.in { background: #0f0f1a; border: 1px solid #2a2a4e; color: #ddd; align-self: flex-start; border-bottom-left-radius: 4px; }
.chat-bubble.out { background: #d4af37; color: #000; align-self: flex-end; border-bottom-right-radius: 4px; }
.chat-bubble.event { background: #1a2a1a; border: 1px solid #2a4a2a; color: #7ec87e; align-self: center; font-size: 11px; padding: 5px 10px; border-radius: 20px; max-width: 95%; text-align: center; }
.bubble-time { font-size: 10px; opacity: 0.55; margin-top: 3px; text-align: right; }
.chat-empty { text-align: center; color: #555; font-size: 13px; margin: auto; padding: 20px; }
#chat-input-area { padding: 12px 14px; border-top: 1px solid #2a2a4e; display: flex; gap: 8px; background: #16213e; }
#chat-input { flex: 1; background: #0f0f1a; border: 1px solid #2a2a4e; border-radius: 8px; color: #fff; padding: 9px 12px; font-size: 13px; outline: none; }
#chat-input:focus { border-color: #d4af37; }
#chat-file-btn { background: #2a2a4e; color: #fff; border: 1px solid #3a3a6e; border-radius: 8px; padding: 9px 12px; font-size: 15px; cursor: pointer; display: flex; align-items: center; }
#chat-file-btn:hover { background: #3a3a6e; }
#chat-send-btn { background: #d4af37; color: #000; border: none; border-radius: 8px; padding: 9px 16px; font-weight: bold; cursor: pointer; font-size: 13px; white-space: nowrap; }
#chat-send-btn:hover { background: #f0c840; }

/* DESKTOP TABLE (hidden on mobile) */
@media (min-width: 900px) {
  .leads-grid { display: none; }
  .leads-table-wrap { display: block; }
}
@media (max-width: 899px) {
  .leads-table-wrap { display: none; }
  .leads-grid { display: flex; }
  .stats { grid-template-columns: repeat(3, 1fr); }
  .section { padding: 0 12px 20px; }
  .header { padding: 12px 14px; }
}
.leads-table-wrap table { width: 100%; border-collapse: collapse; background: #1a1a2e; border-radius: 12px; overflow: hidden; }
.leads-table-wrap th { background: #d4af37; color: #000; padding: 10px 12px; text-align: left; font-size: 12px; }
.leads-table-wrap td { padding: 10px 12px; border-bottom: 1px solid #2a2a4e; font-size: 12px; color: #ccc; vertical-align: middle; }
.leads-table-wrap tr:hover td { background: #1e1e35; }
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>👑 Kevin VIP CRM</h1>
    <div class="subtitle">Gold Signals — Lead Management</div>
  </div>
  <div class="header-right">
    <div id="clock"></div>
    <div style="margin-top:2px;font-size:11px;">Auto-refresh 30s</div>
  </div>
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
    <div style="font-size:12px;color:#888;margin-bottom:8px;">Send to ALL pending leads (1 per day limit)</div>
    <textarea id="bc-text" placeholder="e.g. BITCOIN SMASHED TP1 ✅✅✅ Our members just made +£103 FOR FREE! You missed this — complete your FREE setup now!"></textarea>
    <div style="display:flex;gap:8px;margin-top:8px;align-items:center;flex-wrap:wrap">
      <label id="bc-file-label" style="display:flex;align-items:center;gap:6px;background:#1e1e35;border:1px solid #2a2a4e;border-radius:8px;padding:7px 12px;cursor:pointer;font-size:12px;color:#aaa;">
        📎 Attach Image / Video
        <input type="file" id="bc-file" accept="image/*,video/*" style="display:none" onchange="bcFileSelected()" />
      </label>
      <span id="bc-file-name" style="font-size:11px;color:#888"></span>
      <button id="bc-clear-file" onclick="bcClearFile()" style="display:none;background:none;border:none;color:#e74c3c;cursor:pointer;font-size:12px">✕ Remove</button>
    </div>
    <div class="btn-row">
      <button class="btn btn-gold" onclick="sendBroadcast('all')">📢 All Pending</button>
      <button class="btn" style="background:#8e44ad;color:#fff" onclick="resetDrips()" title="Reset drip timer — all pending leads will get next message within 12 hours">🔄 Restart Drips</button>
      <button class="btn btn-blue" onclick="sendBroadcast('no_broker')">Not Started</button>
      <button class="btn btn-green" onclick="sendBroadcast('vantage')">Vantage Only</button>
      <button class="btn btn-red" onclick="sendBroadcast('puprime')">PU Prime Only</button>
    </div>
  </div>

  <div class="section-title">🚫 Blocked Users</div>
  <div class="broadcast-box">
    <div style="font-size:12px;color:#888;margin-bottom:8px;">Paste usernames (one per line, with or without @). Blocked users are silently ignored — they can't start the bot, get no messages, and never enter your leads.</div>
    <textarea id="blocked-text" placeholder="@baduser1&#10;@baduser2&#10;spammer3" style="min-height:60px"></textarea>
    <div class="btn-row">
      <button class="btn" style="background:#c0392b;color:#fff" onclick="saveBlocked()">🚫 Save Blocked List</button>
      <span id="blocked-count" style="font-size:12px;color:#888;align-self:center"></span>
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

  <!-- MOBILE CARDS -->
  <div class="leads-grid" id="leads-grid"></div>

  <!-- DESKTOP TABLE -->
  <div class="leads-table-wrap">
    <table>
      <thead><tr>
        <th>#</th><th>Name</th><th>Username</th><th>Broker</th><th>MT5</th>
        <th>Status</th><th>Progress</th><th>Last Seen</th><th>Drip</th><th>Chat</th><th>Quick Send</th>
      </tr></thead>
      <tbody id="leads-tbody"></tbody>
    </table>
  </div>
</div>

<!-- CHAT PANEL -->
<div id="chat-overlay" onclick="closeChatOnOverlay(event)">
  <div id="chat-panel">
    <div id="chat-header">
      <div>
        <div class="chat-name" id="chat-title">Chat</div>
        <div class="chat-sub" id="chat-sub"></div>
      </div>
      <button id="chat-close" onclick="closeChat()">✕</button>
    </div>
    <div id="chat-messages"><div class="chat-empty">Loading...</div></div>
    <div id="chat-input-area">
      <input type="text" id="chat-input" placeholder="Type a message..." onkeydown="if(event.key==='Enter') sendChatMsg()" />
      <label id="chat-file-btn" title="Send image/file">
        📎<input type="file" id="chat-file-input" accept="image/*,video/*,.pdf,.doc,.docx" style="display:none" onchange="sendChatFile()" />
      </label>
      <button id="chat-send-btn" onclick="sendChatMsg()">Send ✈️</button>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let allLeads   = [];
let allUnread  = {};
let allNotes   = {};
let currentFilter = 'all';
let activeChatUserId = null;
let activeChatName   = null;
let chatPollInterval = null;
const STEPS = ['Started','Broker','Done','MT5','Complete'];

// ── DESKTOP NOTIFICATIONS ──
function requestNotifPerm() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
}
function showDesktopNotif(title, body) {
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification(title, { body, icon: '' });
  }
}

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
  renderAll(allLeads);
}

function filterLeads() { renderAll(allLeads); }

function getFiltered() {
  const search = (document.getElementById('search').value || '').toLowerCase();
  return allLeads.filter(l => {
    const ms = !search ||
      (l.name||'').toLowerCase().includes(search) ||
      (l.username||'').toLowerCase().includes(search) ||
      (l.mt5_account||'').toLowerCase().includes(search);
    const mf = currentFilter==='all' ||
      (currentFilter==='completed' && l.completed) ||
      (currentFilter==='pending' && !l.completed) ||
      (currentFilter===l.broker);
    return ms && mf;
  });
}

function getProgress(l) {
  const steps = (l.steps||[]).map(s=>s.text);
  return [
    steps.some(s=>s.includes('Started')),
    steps.some(s=>s.includes('Chose')),
    steps.some(s=>s.includes('DONE')),
    steps.some(s=>s.includes('MT5')||s.includes('Submitted')),
    !!l.completed
  ];
}

function ticksHtml(l) {
  const prog = getProgress(l);
  return prog.map((done,i) =>
    `<div class="tick ${done?'done':''}" title="${STEPS[i]}">${done?'✓':''}` +
    `<title>${STEPS[i]}</title></div>`
  ).join('');
}

function lastSeenHtml(l) {
  if (!l.last_seen) return '<span style="color:#555">—</span>';
  const diff = Date.now()/1000 - l.last_seen;
  const isOnline = diff < 300;
  let label;
  if (diff < 60)       label = 'Just now';
  else if (diff < 3600) label = Math.floor(diff/60) + 'm ago';
  else if (diff < 86400) label = Math.floor(diff/3600) + 'h ago';
  else                  label = Math.floor(diff/86400) + 'd ago';
  return `<span class="online-dot ${isOnline?'online':''}" style="display:inline-block;margin-right:4px"></span><span class="last-seen">${label}</span>`;
}

function chatBtnHtml(l) {
  const uid = l.user_id;
  const esc = (l.name||'Client').replace(/'/g,"\\'").replace(/"/g,'&quot;');
  const uname = (l.username||'').replace(/'/g,"\\'");
  const unread = allUnread[uid] || 0;
  const badge  = unread > 0 ? `<span class="unread-badge">${unread}</span>` : '';
  return `<button class="btn-chat" onclick="openChat('${uid}','${esc}','${uname}')">💬${badge}</button>`;
}

function renderAll(leads) {
  const filtered = getFiltered(leads);
  renderCards(filtered);
  renderTable(filtered);
}

function renderCards(filtered) {
  const grid = document.getElementById('leads-grid');
  if (!filtered.length) {
    grid.innerHTML = '<div style="text-align:center;color:#888;padding:30px">No leads found</div>';
    return;
  }
  grid.innerHTML = filtered.map((l,i) => {
    const uid   = l.user_id;
    const esc   = (l.name||'Client').replace(/'/g,"\\'").replace(/"/g,'&quot;');
    const uname = (l.username||'').replace(/'/g,"\\'");
    const unread = allUnread[uid]||0;
    const badge  = unread>0?`<span class="unread-badge">${unread}</span>`:'';
    const prog   = getProgress(l);
    const note   = allNotes[uid]||'';
    const isOnline = l.last_seen && (Date.now()/1000 - l.last_seen < 300);

    return `<div class="lead-card" id="card-${uid}">
      <div class="lead-card-top">
        <div>
          <div class="lead-name-row">
            <span class="online-dot ${isOnline?'online':''}"></span>
            <span class="lead-name">${l.name||'—'}</span>
            ${l.broker?`<span class="badge badge-blue">${l.broker}</span>`:''}
            ${l.completed?'<span class="badge badge-green">✅ Done</span>':'<span class="badge badge-orange">⏳ Pending</span>'}
          </div>
          <div style="font-size:11px;color:#666;margin-top:3px">
            ${l.username&&l.username!=='no username'?`<a href="https://t.me/${l.username}" target="_blank" style="color:#4a90e2">@${l.username}</a>`:'No username'}
            ${l.mt5_account?` &bull; MT5: ${l.mt5_account}`:''}
          </div>
          <div style="font-size:11px;color:#666;margin-top:2px">${lastSeenHtml(l)}</div>
        </div>
        <div style="font-size:11px;color:#555;text-align:right">Drip: ${l.drip_count||0}</div>
      </div>
      <div class="progress-ticks">
        ${prog.map((done,idx)=>`<div class="tick ${done?'done':''}" title="${STEPS[idx]}">${done?'✓':idx+1}</div>`).join('')}
        <span class="tick-label">${STEPS.filter((_,i)=>prog[i]).length}/5 steps</span>
      </div>
      <div class="lead-actions">
        <button class="btn-chat" onclick="openChat('${uid}','${esc}','${uname}')">💬 Chat ${badge}</button>
        <button class="btn-handled ${l.handled?'active':''}" onclick="toggleHandled('${uid}',this)">${l.handled?'✅ Handled':'Mark handled'}</button>
        <input class="quick-input" type="text" id="qi-${uid}" placeholder="Quick send..." onkeydown="if(event.key==='Enter')sendQuick('${uid}')" />
        <button class="btn-send-quick" onclick="sendQuick('${uid}')">Send</button>
      </div>
      <textarea class="notes-area" id="note-${uid}" placeholder="Add a private note... (auto-saves)" onblur="saveNote('${uid}')" onkeydown="if(event.ctrlKey&&event.key==='Enter')saveNote('${uid}')">${note}</textarea>
      <div class="notes-saved" id="note-saved-${uid}">✅ Saved</div>
    </div>`;
  }).join('');
}

function renderTable(filtered) {
  const tbody = document.getElementById('leads-tbody');
  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="11" style="text-align:center;color:#888;padding:24px">No leads found</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map((l,i) => {
    const uid  = l.user_id;
    const prog = getProgress(l);
    const note = allNotes[uid]||'';
    const uname = l.username&&l.username!=='no username'
      ? `<a href="https://t.me/${l.username}" target="_blank" style="color:#4a90e2">@${l.username}</a>`
      : '<span style="color:#555">No username</span>';
    const esc   = (l.name||'Client').replace(/'/g,"\\'").replace(/"/g,'&quot;');
    const uesc  = (l.username||'').replace(/'/g,"\\'");
    const unread = allUnread[uid]||0;
    const badge  = unread>0?`<span class="unread-badge">${unread}</span>`:'';
    return `<tr>
      <td>${i+1}</td>
      <td><b>${l.name||'—'}</b><br><span style="font-size:10px;color:#666">${lastSeenHtml(l)}</span></td>
      <td>${uname}</td>
      <td>${l.broker?`<span class="badge badge-blue">${l.broker}</span>`:'<span style="color:#555">—</span>'}</td>
      <td>${l.mt5_account||'<span style="color:#555">—</span>'}</td>
      <td>${l.completed?'<span class="badge badge-green">✅ Done</span>':'<span class="badge badge-orange">⏳ Pending</span>'}</td>
      <td><div class="progress-ticks">${prog.map((done,idx)=>`<div class="tick ${done?'done':''}" title="${STEPS[idx]}">${done?'✓':idx+1}</div>`).join('')}</div></td>
      <td>${lastSeenHtml(l)}</td>
      <td>${l.drip_count||0}</td>
      <td><button class="btn-chat" onclick="openChat('${uid}','${esc}','${uesc}')">💬 ${badge}</button>
          <button class="btn-handled ${l.handled?'active':''}" style="margin-top:4px" onclick="toggleHandled('${uid}',this)">${l.handled?'✅':'Mark done'}</button></td>
      <td>
        <div style="display:flex;gap:4px;margin-bottom:4px">
          <input class="quick-input" style="min-width:100px" type="text" id="qi-${uid}" placeholder="Send..." onkeydown="if(event.key==='Enter')sendQuick('${uid}')" />
          <button class="btn-send-quick" onclick="sendQuick('${uid}')">Send</button>
        </div>
        <textarea class="notes-area" id="note-dt-${uid}" style="min-height:32px" placeholder="Note..." onblur="saveNote('${uid}',true)">${note}</textarea>
        <div class="notes-saved" id="note-saved-dt-${uid}">✅ Saved</div>
      </td>
    </tr>`;
  }).join('');
}

async function loadLeads() {
  try {
    const [lr, ur, nr] = await Promise.all([
      fetch('/api/leads').then(r=>r.json()),
      fetch('/api/unread').then(r=>r.json()),
      fetch('/api/notes').then(r=>r.json()),
    ]);
    const prevLeads = allLeads.map(l=>l.user_id);
    allLeads  = lr.leads || [];
    allUnread = ur.unread || {};
    allNotes  = nr.notes || {};

    document.getElementById('s-total').textContent   = lr.total;
    document.getElementById('s-done').textContent    = lr.completed;
    document.getElementById('s-pending').textContent = lr.pending;
    document.getElementById('s-vantage').textContent = lr.vantage;
    document.getElementById('s-puprime').textContent = lr.puprime;

    // Desktop notification for new leads
    const newLeads = allLeads.filter(l => !prevLeads.includes(l.user_id));
    newLeads.forEach(l => showDesktopNotif('New Lead! 🔔', l.name + ' just started the bot'));

    // Notify for unread messages
    Object.entries(allUnread).forEach(([uid, count]) => {
      if (count > 0) {
        const lead = allLeads.find(l => l.user_id === uid);
        if (lead) showDesktopNotif('New message 💬', (lead.name||'Client') + ' sent you a message');
      }
    });

    renderAll(allLeads);
  } catch(e) { console.error(e); }
}

async function sendQuick(uid) {
  const inp  = document.getElementById('qi-' + uid);
  const inp2 = document.getElementById('qi-' + uid); // same element in both views
  const text = inp ? inp.value.trim() : '';
  if (!text) return;
  const r = await fetch('/api/message', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({user_id: uid, text})
  });
  const d = await r.json();
  if (d.ok) { showToast('✅ Sent!'); if(inp) inp.value=''; }
  else showToast('❌ Failed', '#e74c3c');
}

async function sendMsg(uid) { return sendQuick(uid); }

async function toggleHandled(uid, btn) {
  const r = await fetch('/api/handled', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({user_id: uid})
  });
  const d = await r.json();
  if (d.ok) {
    const isNow = d.handled;
    btn.classList.toggle('active', isNow);
    btn.textContent = isNow ? '✅ Handled' : 'Mark handled';
  }
}

async function saveNote(uid, isDesktop) {
  const elId = isDesktop ? 'note-dt-' + uid : 'note-' + uid;
  const savedId = isDesktop ? 'note-saved-dt-' + uid : 'note-saved-' + uid;
  const el = document.getElementById(elId);
  if (!el) return;
  const note = el.value;
  await fetch('/api/note', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({user_id: uid, note})
  });
  allNotes[uid] = note;
  const savedEl = document.getElementById(savedId);
  if (savedEl) { savedEl.style.display='block'; setTimeout(()=>savedEl.style.display='none', 2000); }
}

async function loadBlocked() {
  try {
    const r = await fetch('/api/blocked');
    const d = await r.json();
    const list = d.blocked || [];
    document.getElementById('blocked-text').value = list.map(u => '@' + u).join('\n');
    document.getElementById('blocked-count').textContent = list.length + ' blocked';
  } catch(e) {}
}

async function saveBlocked() {
  const usernames = document.getElementById('blocked-text').value;
  const r = await fetch('/api/blocked', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({usernames})
  });
  const d = await r.json();
  if (d.ok) {
    showToast('🚫 Blocked list saved — ' + d.count + ' users blocked');
    document.getElementById('blocked-count').textContent = d.count + ' blocked';
    document.getElementById('blocked-text').value = (d.blocked||[]).map(u => '@' + u).join('\n');
  } else {
    showToast('❌ Failed to save', '#e74c3c');
  }
}

async function resetDrips() {
  if (!confirm('Reset drip timer for ALL pending leads? They will each receive the next drip message within 12 hours.')) return;
  const r = await fetch('/api/reset_drips', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
  const d = await r.json();
  if (d.ok) showToast('✅ Drip reset for ' + d.reset + ' pending leads! Messages will send within 12 hours.');
  else showToast('❌ Failed', '#e74c3c');
}

function bcFileSelected() {
  const fi = document.getElementById('bc-file');
  const nameEl = document.getElementById('bc-file-name');
  const clearBtn = document.getElementById('bc-clear-file');
  const label = document.getElementById('bc-file-label');
  if (fi.files[0]) {
    nameEl.textContent = fi.files[0].name;
    clearBtn.style.display = 'inline';
    label.style.borderColor = '#00dc50';
    label.style.color = '#00dc50';
  }
}

function bcClearFile() {
  document.getElementById('bc-file').value = '';
  document.getElementById('bc-file-name').textContent = '';
  document.getElementById('bc-clear-file').style.display = 'none';
  const label = document.getElementById('bc-file-label');
  label.style.borderColor = '#2a2a4e';
  label.style.color = '#aaa';
}

async function sendBroadcast(target) {
  const text = document.getElementById('bc-text').value.trim();
  const fileInput = document.getElementById('bc-file');
  const file = fileInput.files[0];
  if (!text) { showToast('Write a message first', '#e74c3c'); return; }
  if (!confirm('Send to ' + (target==='all'?'ALL pending':target) + ' leads?')) return;

  showToast('📤 Sending...', '#2980b9');

  const fd = new FormData();
  fd.append('text', text);
  fd.append('target', target);
  if (file) fd.append('image', file);

  const r = await fetch('/api/broadcast_file', {method:'POST', body: fd});
  const d = await r.json();
  if (d.ok) {
    showToast('✅ Broadcast sent to ' + d.sent + ' leads!');
    bcClearFile();
  } else {
    showToast('❌ Failed to send', '#e74c3c');
  }
}

// ── CHAT PANEL ──
function openChat(uid, name, username) {
  activeChatUserId = uid;
  activeChatName   = name;
  document.getElementById('chat-title').textContent = '💬 ' + name;
  document.getElementById('chat-sub').textContent   = username ? '@'+username : 'No username';
  document.getElementById('chat-overlay').classList.add('open');
  document.getElementById('chat-input').value = '';
  // Mark as read
  fetch('/api/mark_read', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid})});
  allUnread[uid] = 0;
  loadChatMessages();
  if (chatPollInterval) clearInterval(chatPollInterval);
  chatPollInterval = setInterval(loadChatMessages, 6000);
}

function closeChat() {
  document.getElementById('chat-overlay').classList.remove('open');
  activeChatUserId = null;
  if (chatPollInterval) { clearInterval(chatPollInterval); chatPollInterval = null; }
}

function closeChatOnOverlay(e) {
  if (e.target === document.getElementById('chat-overlay')) closeChat();
}

async function loadChatMessages() {
  if (!activeChatUserId) return;
  try {
    const r = await fetch('/api/chat/' + activeChatUserId);
    const d = await r.json();
    renderChatMessages(d.messages || []);
  } catch(e) {}
}

function formatTime(ts) {
  const d = new Date(ts*1000);
  return d.toLocaleString('en-GB',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'short'});
}

function renderChatMessages(messages) {
  const box = document.getElementById('chat-messages');
  if (!messages.length) {
    box.innerHTML = '<div class="chat-empty">No messages yet.<br>When this client messages the bot you will see them here.</div>';
    return;
  }
  const wasAtBottom = box.scrollHeight - box.clientHeight <= box.scrollTop + 40;
  box.innerHTML = messages.map(m =>
    `<div class="chat-bubble ${m.direction}">
      ${escHtml(m.text)}
      <div class="bubble-time">${formatTime(m.time)}</div>
    </div>`
  ).join('');
  if (wasAtBottom || messages.length <= 5) box.scrollTop = box.scrollHeight;
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

async function sendChatMsg() {
  const input = document.getElementById('chat-input');
  const text  = input.value.trim();
  if (!text || !activeChatUserId) return;
  input.value = '';
  const r = await fetch('/api/message', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({user_id: activeChatUserId, text})
  });
  const d = await r.json();
  if (d.ok) { await loadChatMessages(); }
  else { showToast('❌ Failed', '#e74c3c'); input.value = text; }
}

async function sendChatFile() {
  const fi = document.getElementById('chat-file-input');
  const file = fi.files[0];
  if (!file || !activeChatUserId) return;
  showToast('📤 Sending...', '#2980b9');
  const fd = new FormData();
  fd.append('user_id', activeChatUserId);
  fd.append('file', file);
  try {
    const r = await fetch('/api/send_file', {method:'POST', body:fd});
    const d = await r.json();
    if (d.ok) { showToast('✅ File sent!'); await loadChatMessages(); }
    else showToast('❌ Failed to send file', '#e74c3c');
  } catch(e) { showToast('❌ Error', '#e74c3c'); }
  fi.value = '';
}

function updateClock() {
  const now = new Date();
  document.getElementById('clock').textContent = now.toLocaleTimeString('en-GB',{
    hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:'Europe/London'
  }) + ' UK';
}

requestNotifPerm();
loadLeads();
loadBlocked();
setInterval(loadLeads, 30000);
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
            "last_seen":   d.get("last_seen", 0),
            "handled":     d.get("handled", False),
        })
    leads.sort(key=lambda x: x["started_at"], reverse=True)
    total     = len(leads)
    completed = sum(1 for l in leads if l["completed"])
    vantage   = sum(1 for l in leads if l.get("broker") == "Vantage")
    puprime   = sum(1 for l in leads if l.get("broker") == "PU Prime")
    return jsonify({"leads": leads, "total": total, "completed": completed,
                    "pending": total - completed, "vantage": vantage, "puprime": puprime})


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
    uid  = str(data.get("user_id", ""))
    note = data.get("note", "")
    if uid:
        with notes_lock:
            notes = load_notes()
            notes[uid] = note
            save_notes(notes)
    return jsonify({"ok": True})


@app.route("/api/handled", methods=["POST"])
@requires_auth
def api_handled():
    uid = str(request.get_json(force=True).get("user_id", ""))
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
    return jsonify({"messages": msgs.get(str(user_id), []), "user_id": user_id})


@app.route("/api/send_file", methods=["POST"])
@requires_auth
def api_send_file():
    user_id = request.form.get("user_id")
    file    = request.files.get("file")
    if not user_id or not file:
        return jsonify({"ok": False})
    try:
        file_bytes = file.read()
        fname      = file.filename.lower()
        mime       = file.mimetype or ""
        if mime.startswith("image/") or any(fname.endswith(x) for x in [".jpg",".jpeg",".png",".gif",".webp"]):
            r = requests.post(f"{TELEGRAM_URL}/sendPhoto",
                files={"photo": (file.filename, file_bytes, mime)},
                data={"chat_id": user_id}, timeout=20)
        elif mime.startswith("video/") or any(fname.endswith(x) for x in [".mp4",".mov",".avi"]):
            r = requests.post(f"{TELEGRAM_URL}/sendVideo",
                files={"video": (file.filename, file_bytes, mime)},
                data={"chat_id": user_id}, timeout=30)
        else:
            r = requests.post(f"{TELEGRAM_URL}/sendDocument",
                files={"document": (file.filename, file_bytes, mime)},
                data={"chat_id": user_id}, timeout=20)
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
    text    = data.get("text", "")
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

    broadcasts = load_broadcasts()
    broadcasts.append({"time": time.time(), "text": text[:100], "sent": sent, "target": target})
    save_broadcasts(broadcasts[-50:])

    return jsonify({"ok": True, "sent": sent})


@app.route("/api/broadcast_file", methods=["POST"])
@requires_auth
def api_broadcast_file():
    text      = request.form.get("text", "")
    target    = request.form.get("target", "all")
    image     = request.files.get("image")

    if not text:
        return jsonify({"ok": False, "sent": 0})

    image_bytes = image.read() if image else None
    mime        = image.mimetype if image else "image/jpeg"
    fname       = image.filename if image else "image.jpg"

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

        time.sleep(random.uniform(0.5, 2))

        try:
            if image_bytes:
                is_video = mime.startswith("video/") or any(fname.lower().endswith(x) for x in [".mp4",".mov",".avi"])
                if is_video:
                    r = requests.post(f"{TELEGRAM_URL}/sendVideo",
                        files={"video": (fname, image_bytes, mime)},
                        data={"chat_id": uid, "caption": text, "parse_mode": "HTML",
                              "reply_markup": json.dumps(JOIN_BUTTON)}, timeout=30)
                else:
                    r = requests.post(f"{TELEGRAM_URL}/sendPhoto",
                        files={"photo": (fname, image_bytes, mime)},
                        data={"chat_id": uid, "caption": text, "parse_mode": "HTML",
                              "reply_markup": json.dumps(JOIN_BUTTON)}, timeout=20)
                ok = r.json().get("ok", False)
            else:
                ok = send_to_user(uid, text, keyboard=JOIN_BUTTON)

            if ok:
                with users_lock:
                    users_db[uid]["last_drip"] = time.time()
                    save_users(users_db)
                sent += 1
        except Exception as e:
            logger.error(f"broadcast_file error for {uid}: {e}")

    broadcasts = load_broadcasts()
    broadcasts.append({"time": time.time(), "text": text[:100], "sent": sent, "target": target})
    save_broadcasts(broadcasts[-50:])

    return jsonify({"ok": True, "sent": sent})


@app.route("/api/blocked", methods=["GET"])
@requires_auth
def api_get_blocked():
    with blocked_lock:
        return jsonify({"blocked": load_blocked()})


@app.route("/api/blocked", methods=["POST"])
@requires_auth
def api_set_blocked():
    data = request.get_json(force=True)
    raw  = data.get("usernames", "")
    # Accept newline or comma separated
    names = []
    for chunk in raw.replace(",", "\n").split("\n"):
        u = chunk.strip().lstrip("@").strip()
        if u:
            names.append(u)
    # Deduplicate case-insensitively, preserve order
    seen = set()
    clean = []
    for u in names:
        if u.lower() not in seen:
            seen.add(u.lower())
            clean.append(u)
    with blocked_lock:
        save_blocked(clean)
    logger.info(f"Blocked list updated: {len(clean)} usernames")
    return jsonify({"ok": True, "blocked": clean, "count": len(clean)})


@app.route("/api/reset_drips", methods=["POST"])
@requires_auth
def api_reset_drips():
    with users_lock:
        count = 0
        for uid, udata in users_db.items():
            if not udata.get("completed"):
                users_db[uid]["last_drip"] = 0
                count += 1
        save_users(users_db)
    logger.info(f"Reset drip timers for {count} pending leads")
    return jsonify({"ok": True, "reset": count})


@app.route("/forward_signal", methods=["POST"])
def forward_signal():
    """Receives entry signal text from signals bot and forwards to all incomplete leads"""
    try:
        signal_text = request.form.get("signal_text", "")
        pair        = request.form.get("pair", "XAUUSD")
        if not signal_text:
            return jsonify({"status": "no_text"})

        pair_name = "GOLD" if pair == "XAUUSD" else "BITCOIN"
        caption = (
            f"{signal_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🔒 <b>This signal was sent FREE to our PM group.</b>\n\n"
            f"You\'re missing every signal like this one.\n\n"
            f"👇 <b>Complete your FREE setup — takes 2 minutes!</b>\n\n"
            f"❓ Need help? Message: @KevSupportTeam"
        )

        with users_lock:
            snapshot = dict(users_db)

        sent = 0
        for uid, udata in snapshot.items():
            if udata.get("completed"):
                continue
            time.sleep(random.uniform(0.3, 1.5))
            try:
                ok = send_to_user(uid, caption, keyboard=JOIN_BUTTON)
                if ok:
                    sent += 1
            except Exception as e:
                logger.error(f"forward_signal error for {uid}: {e}")

        logger.info(f"Signal forwarded to {sent} incomplete leads")
        return jsonify({"status": "ok", "sent": sent})
    except Exception as e:
        logger.error(f"forward_signal error: {e}")
        return jsonify({"status": "error"}), 500


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
    # Background threads already started above via start_background_threads()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
