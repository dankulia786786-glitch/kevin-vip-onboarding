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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID  = os.environ.get("OWNER_ID", "8957877294")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

VANTAGE_IMAGE = "https://raw.githubusercontent.com/dankulia786786-glitch/2.0-pm-gold-crm/main/WhatsApp%20iamge.jpg"
PUPRIME_IMAGE = "https://raw.githubusercontent.com/dankulia786786-glitch/2.0-pm-gold-crm/main/Pu%20Prime%20WhatsApp.jpg"

# Promo links (set these in Railway Variables, or edit here)
WHATSAPP_LINK = os.environ.get("WHATSAPP_LINK", "https://chat.whatsapp.com/IkmwitDmS5D3vWo8fN6Mhj")
PREMIUM_LINK  = os.environ.get("PREMIUM_LINK", "https://buy.stripe.com/7sY14mgvE90VgvteQp18c3c")

# Your signals channel — trades posted here get forwarded to all bot users
SIGNALS_CHANNEL_ID = os.environ.get("SIGNALS_CHANNEL_ID", "-1004447151625")

# ─── AUTH ─────────────────────────────────────────────────────────────────────
# Passwords are read from Railway env vars (never hardcoded in the public repo).
# Set DASH_PASS and DASH_PASS_TEAM in Railway Variables.
DASHBOARD_USERS = {
    os.environ.get("DASH_PASS", "change-me-owner"): "Owner",
    os.environ.get("DASH_PASS_TEAM", "change-me-team"): "Team",
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

# ─── DRIP MESSAGES ────────────────────────────────────────────────────────────
DRIP_MESSAGES = [
    # ===== PM / PREMIUM GROUP (10) =====
    "\U0001F6A8 <b>3 GOLD TRADES TODAY \u2014 ALL SMASHED TP</b>\n\n\nThe next ones are going out in the Premium Group only.\n\n\nIt's FREE to join with a Vantage account.\n\n\nDon't miss the next scalp \U0001F447",

    "\U0001F525 <b>A GOLD SIGNAL JUST DROPPED IN THE PREMIUM GROUP</b>\n\n\nYou're not in it yet.\n\n\nFix that in 20 seconds \U0001F447",

    "\U0001F4CA <b>OUR ANALYSIS WAS PERFECT AGAIN TODAY</b>\n\n\nMembers caught every move in the Premium Group.\n\n\nAnd you still haven't joined us.\n\n\nIt's free \u2014 complete your setup \U0001F447",

    "\u23F0 <b>QUICK SCALP GOLD TRADES GO OUT IN PREMIUM ONLY NOW</b>\n\n\nThe group trades are moving fast.\n\n\nGet the entries live, straight to your phone.\n\n\nJoin free in 20 seconds \U0001F447",

    "\U0001F6A8 <b>GOLD SIGNAL COMING IN THE PREMIUM GROUP SOON</b>\n\n\nBe ready.\n\n\nComplete your setup now so you don't miss it \U0001F447",

    "\U0001F525 <b>ANOTHER WEEK, ANOTHER RUN OF WINS</b>\n\n\nOur Premium members are eating good.\n\n\nFree gold signals, live entries, real results.\n\n\nStart in 20 seconds \U0001F447",

    "\U0001F4A1 <b>WHY MISS TRADES WHEN THE PREMIUM GROUP IS FREE?</b>\n\n\nLifetime access with a Vantage account.\n\n\nGold signals, quick scalps, and full support.\n\n\nComplete your setup \U0001F447",

    "\U0001F6A8 <b>THE PM GROUP JUST WENT LIVE WITH A SETUP</b>\n\n\nMembers are already in.\n\n\nYou've got 20 seconds to join them \U0001F447",

    "\U0001F4C8 <b>GOLD IS MOVING \u2014 AND SO IS THE PREMIUM GROUP</b>\n\n\nEvery entry shared live.\n\n\nDon't watch from the outside.\n\n\nJoin free \U0001F447",

    "\U0001F525 <b>YOUR FREE PREMIUM ACCESS IS WAITING</b>\n\n\nGold signals. Quick scalps. Live support.\n\n\nAll free with a Vantage account.\n\n\nFinish your setup in 20 seconds \U0001F447",

    # ===== ACCOUNT MANAGEMENT (10) =====
    "\U0001F4CA <b>TIRED OF WATCHING SIGNALS AND MISSING ENTRIES?</b>\n\n\nLet us trade it for you.\n\n\n\u2705 Start from \u00A3500 (we recommend \u00A31,000)\n\n\u2705 80% yours : 20% performance fee\n\n\u2705 No upfront fees \u2014 you only pay on profit\n\n\u2705 We target 65%+ monthly on GOLD & BTC\n\n\u2705 Full transparency \u2014 log in and watch every trade live\n\n\nReal clients, real results.\n\n\nComplete your setup to get started \U0001F447",

    "\U0001F4A1 <b>IN 2026, ONE INCOME ISN'T ENOUGH</b>\n\n\nAccount Management is the passive, consistent way to grow.\n\n\nWe trade, you keep 80%.\n\n\n\u2705 From \u00A3500, no upfront fees\n\n\u2705 You keep full control of your funds\n\n\u2705 Live verified results you can check yourself\n\n\nLet your money work while you work \U0001F447",

    "\U0001F4CA <b>REAL RESULTS, NOT SCREENSHOTS</b>\n\n\nOur managed clients are seeing serious growth on GOLD & BTC.\n\n\n\u2705 Start from \u00A3500\n\n\u2705 80:20 split in your favour\n\n\u2705 Only pay on profit\n\n\u2705 Log in and verify every trade yourself\n\n\nFull transparency, always \U0001F447",

    "\U0001F525 <b>LET US TRADE WHILE YOU LIVE YOUR LIFE</b>\n\n\nAccount Management is built for busy people.\n\n\n\u2705 Manual trading only, GOLD & BTC\n\n\u2705 Start \u00A3500 (recommended \u00A31,000)\n\n\u2705 We target 65%+ monthly\n\n\u2705 No upfront fees, only pay on profit\n\n\nComplete your setup to get started \U0001F447",

    "\U0001F4C8 <b>PASSIVE. CONSISTENT. TRANSPARENT.</b>\n\n\nThat's how our Account Management works.\n\n\n\u2705 You keep full control of your funds\n\n\u2705 We only trade \u2014 no access to your deposits or withdrawals\n\n\u2705 Monitor every trade live, anytime\n\n\nStart from \u00A3500 \U0001F447",

    "\U0001F4A1 <b>WHY TRY TO TIME THE MARKET YOURSELF?</b>\n\n\nOur team does it for you, live on your account.\n\n\n\u2705 80% yours : 20% performance fee\n\n\u2705 No upfront fees\n\n\u2705 65%+ monthly target\n\n\nProven results, full transparency \U0001F447",

    "\U0001F4CA <b>SERIOUS ABOUT GROWING YOUR ACCOUNT?</b>\n\n\nAccount Management does the work for you.\n\n\n\u2705 From \u00A3500 to start\n\n\u2705 We trade GOLD & BTC daily\n\n\u2705 London & New York sessions\n\n\u2705 You only pay on profit\n\n\nComplete your setup and let's talk \U0001F447",

    "\U0001F525 <b>YOUR MONEY SHOULD BE WORKING HARDER</b>\n\n\nManaged trading, done for you.\n\n\n\u2705 Start \u00A3500, recommended \u00A31,000\n\n\u2705 80:20 profit split in your favour\n\n\u2705 Live results you can verify\n\n\nUnder-promise, over-deliver \u2014 that's how we do it \U0001F447",

    "\U0001F4C8 <b>WANT CONSISTENT GROWTH WITHOUT THE STRESS?</b>\n\n\nLet our team manage it.\n\n\n\u2705 No upfront fees\n\n\u2705 Full fund control stays with you\n\n\u2705 Target 65%+ monthly on GOLD & BTC\n\n\nComplete your setup to get started \U0001F447",

    "\U0001F4A1 <b>PEOPLE TAKING ACTION ARE THE ONES WINNING IN 2026</b>\n\n\nAccount Management is the passive path.\n\n\n\u2705 From \u00A3500, no upfront fees\n\n\u2705 80% yours\n\n\u2705 Live verified results\n\n\nMake your move \U0001F447",
]

# ─── ENGAGEMENT QUESTIONS (every ~8h, friendly, get replies) ──────────────────
ENGAGEMENT_QUESTIONS = [
    "Yo 👋 did you trade today?\n\nWhat did you catch — gold, BTC, or forex?",
    "Quick one 👇\n\nGold today — you reckon it's going up or down this week?",
    "Be honest 😅\n\nDid you make profit or take a loss today?",
    "How's the trading going bro? 📈\n\nUp or down this week?",
    "You watching gold right now? 👀\n\nWhat's your bias — bullish or bearish?",
    "Did you catch that gold move today? 🔥\n\nOr did it get away from you?",
    "What's your account looking like this week? 💰\n\nGreen or red?",
    "Bitcoin's been moving 🪙\n\nYou in any positions right now?",
    "Real talk 👇\n\nWhat's the one thing holding your trading back right now?",
    "You trading solo or following signals? 🤔\n\nHow's it working out?",
    "Gold, Bitcoin or Forex — what's your favourite to trade? 📊\n\nTell me 👇",
    "How many trades did you take this week? 📈\n\nAnd how'd they go?",
    "If you could get ONE thing to level up your trading, what would it be? 💭",
    "You up or down on the month so far? 💰\n\nNo judgement 😄",
    "What broker are you on right now? 🤔\n\nHappy with it?",
    "Did you take the gold trade today? 🚨\n\nHow'd it play out?",
    "Be honest — are you trading with a plan, or winging it? 😅\n\nMost people wing it 👇",
    "What's your biggest trading win so far? 🔥\n\nDrop it below 👇",
]

ENGAGE_BUTTON = {"inline_keyboard": [
    [{"text": "💬 Message me", "url": "https://t.me/KevSupportTeam"}],
]}


JOIN_BUTTON = {"inline_keyboard": [
    [{"text": "✅ COMPLETE SETUP (20 sec)", "callback_data": "restart_onboarding"}],
    [{"text": "❗️ Live Support", "url": "https://t.me/Vantageadmins"}],
    [{"text": "📲 Join WhatsApp", "url": WHATSAPP_LINK},
     {"text": "💳 Premium Signals", "url": PREMIUM_LINK}],
]}

# ─── SPIN THE WHEEL ───────────────────────────────────────────────────────────
# Each prize: (emoji+label, weight, is_win, claim_line)
# weight = relative chance. Losers weighted higher so wins feel special.
SPIN_PRIZES = [
    ("🥇 FREE GOLD SIGNAL (VIP)", 10, True,
     "You've won a <b>FREE VIP Gold Signal</b>! 🥇"),
    ("🪙 FREE BITCOIN SIGNAL (VIP)", 10, True,
     "You've won a <b>FREE VIP Bitcoin Signal</b>! 🪙"),
    ("📚 FREE VANTAGE TRADING COURSE", 8, True,
     "You've unlocked the <b>FREE Vantage Trading Course</b>! 📚"),
    ("💰 150% DEPOSIT BONUS (New Clients)", 7, True,
     "You've won a <b>150% Deposit Bonus</b> for new clients! 💰"),
    ("🔁 50% REDEPOSIT BONUS (Lifetime)", 8, True,
     "You've won the <b>50% Lifetime Redeposit Bonus</b>! 🔁"),
    ("🛠 SMART TRADER TOOLS ACCESS", 7, True,
     "You've unlocked <b>Smart Trader Tools</b> access! 🛠"),
    ("😬 SO CLOSE — Spin Again Tomorrow", 25, False, ""),
    ("⏳ NOT THIS TIME — Try Again in 24h", 25, False, ""),
]

SPIN_COOLDOWN = 86400  # 24 hours
spin_state = {}        # user_id -> last_spin_timestamp

# Spinning wheel GIF (upload wheel.gif to your GitHub repo)
WHEEL_GIF = "https://raw.githubusercontent.com/dankulia786786-glitch/2.0-pm-gold-crm/main/wheel.gif"

def _weighted_spin():
    total = sum(w for _, w, _, _ in SPIN_PRIZES)
    r = random.uniform(0, total)
    upto = 0
    for prize in SPIN_PRIZES:
        upto += prize[1]
        if r <= upto:
            return prize
    return SPIN_PRIZES[-1]

def handle_spin(user_id, first_name, username):
    now = time.time()
    last = spin_state.get(str(user_id), 0)
    remaining = SPIN_COOLDOWN - (now - last)

    if remaining > 0:
        hrs = int(remaining // 3600)
        mins = int((remaining % 3600) // 60)
        send_to_user(user_id,
            "🎡 <b>You've already spun today!</b>\n\n"
            f"⏳ Come back in <b>{hrs}h {mins}m</b> for your next FREE spin.\n\n"
            "🔥 Tip: complete your setup so you can instantly claim anything you win!",
            keyboard={"inline_keyboard": [[{"text": "✅ Complete My Setup", "callback_data": "restart_onboarding"}]]}
        )
        return

    # Play the spinning wheel GIF (falls back to text if GIF unavailable)
    sent = send_animation_to_user(user_id, WHEEL_GIF, caption="🎡 <b>Spinning the wheel...</b>")
    if not sent:
        send_to_user(user_id, "🎡 <b>Spinning the wheel...</b>\n\n🔴🟡🟢🔵🟣")
    time.sleep(2.5)  # let the wheel "spin" before revealing

    label, weight, is_win, claim_line = _weighted_spin()
    spin_state[str(user_id)] = now

    if is_win:
        send_to_user(user_id,
            "🎉🎉🎉 <b>WINNER!</b> 🎉🎉🎉\n\n"
            f"The wheel landed on:\n\n🎁 <b>{label}</b>\n\n"
            f"{claim_line}\n\n"
            "⚡ <b>To CLAIM your prize:</b> complete your setup and join the PM — "
            "our team will activate it for you.\n\n"
            "⏳ Come back in 24h for another spin!",
            keyboard={"inline_keyboard": [[{"text": "🏆 CLAIM — Complete Setup", "callback_data": "restart_onboarding"}]]}
        )
        # Notify owner of a win
        notify_owner(
            f"🎡 <b>SPIN WIN</b>\n\n"
            f"👤 {first_name} (@{username})\n"
            f"🆔 <code>{user_id}</code>\n"
            f"🎁 Won: {label}"
        )
    else:
        send_to_user(user_id,
            f"🎡 The wheel landed on:\n\n<b>{label}</b>\n\n"
            "😅 Not a win this time — but every spin gets you closer!\n\n"
            "💡 Members who complete their setup get signals, bonuses & tools "
            "<b>every single day</b> — no luck required.\n\n"
            "⏳ Spin again in 24h!",
            keyboard={"inline_keyboard": [[{"text": "🔥 Get Daily Rewards — Join Free", "callback_data": "restart_onboarding"}]]}
        )


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

def send_animation_to_user(user_id, gif_url, caption=None):
    """Send an animated GIF (Telegram sendAnimation)."""
    try:
        payload = {"chat_id": user_id, "animation": gif_url}
        if caption:
            payload["caption"] = caption
            payload["parse_mode"] = "HTML"
        r = requests.post(f"{TELEGRAM_URL}/sendAnimation", json=payload, timeout=15)
        return r.json().get("ok", False)
    except Exception as e:
        logger.error(f"Animation error: {e}")
        return False

def notify_owner(text, keyboard=None):
    payload = {"chat_id": OWNER_ID, "text": text, "parse_mode": "HTML"}
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
    try:
        r = requests.post(f"{TELEGRAM_URL}/sendMessage", json=payload, timeout=10)
        data = r.json()
        if data.get("ok"):
            logger.info(f"✅ Owner notified (chat_id={OWNER_ID})")
            return data["result"]["message_id"]
        else:
            logger.error(f"❌ Owner notify FAILED: {data}  (OWNER_ID={OWNER_ID})")
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
        f"👋 <b>Welcome, {first_name}!</b>\n\n"
        "This is your gateway to 🏆 <b>VIP GOLD, BTC &amp; FOREX SIGNALS</b> — free for life.\n\n"
        "Here's what you unlock inside:\n\n"
        "✅ FREE VIP signals group (Gold • Bitcoin • Forex)\n\n"
        "✅ 150% deposit bonus for new accounts\n\n"
        "✅ 50% re-deposit bonus (lifetime)\n\n"
        "✅ Help opening a Vantage or PU Prime account\n\n"
        "✅ Direct 1-on-1 support whenever you're stuck\n\n"
        "👇 <b>Let's get you set up — pick the one that fits you:</b>",
        keyboard={"inline_keyboard": [
            [{"text": "✅ I already have a Vantage / PU Prime account", "callback_data": "have_account"}],
            [{"text": "🆕 I need to create an account", "callback_data": "create_account"}],
            [{"text": "💰 Claim my 150% + 50% bonus", "callback_data": "claim_bonus"}],
            [{"text": "💬 Stuck? Message me", "url": "https://t.me/KevSupportTeam"}],
        ]}
    )
    onboarding_state[user_id] = {"step": "main_menu", "first_name": first_name, "username": username}
    _add_step(user_id, "Started onboarding")

    # Log to chat history
    store_client_message(user_id, "▶️ Client started the bot (/start)", direction="event")
    store_client_message(user_id, "🤖 Bot: Welcome! Showed main menu.", direction="out")

    mid = notify_owner(
        f"🔔 <b>NEW LEAD STARTED THE BOT!</b>\n\n"
        f"👤 <b>Name:</b> {first_name}\n"
        f"📲 <b>Username:</b> @{username}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n\n"
        f"⏳ <b>Status:</b> Just started — at main menu...\n\n"
        f"💬 <i>Swipe/reply to THIS message to text them directly.</i>",
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

def _broker_choice(user_id, first_name, username, flow):
    """Show Vantage / PU Prime choice. flow = 'have' | 'bonus'."""
    send_to_user(user_id,
        "👇 <b>Which broker are you with?</b>\n\n"
        "Pick one and we'll guide you through the quick setup.",
        keyboard={"inline_keyboard": [
            [{"text": "🔵 Vantage", "callback_data": "broker_vantage"}],
            [{"text": "🔴 PU Prime", "callback_data": "broker_puprime"}],
            [{"text": "💬 Stuck? Message me", "url": "https://t.me/KevSupportTeam"}],
        ]}
    )
    onboarding_state[user_id] = {"step": "broker_choice", "flow": flow, "first_name": first_name, "username": username}

def handle_have_account(user_id, first_name, username):
    _add_step(user_id, "Has account - choosing broker")
    store_client_message(user_id, "Client tapped: I already have an account", direction="event")
    _broker_choice(user_id, first_name, username, "have")
    notify_owner(f"✅ <b>Lead has an account</b>\n👤 {first_name} (@{username})\n🆔 <code>{user_id}</code>\nChoosing broker...")

def handle_claim_bonus(user_id, first_name, username):
    _add_step(user_id, "Claiming bonus")
    store_client_message(user_id, "Client tapped: Claim bonus", direction="event")
    send_to_user(user_id,
        "💰 <b>CLAIM YOUR 150% + 50% BONUS</b>\n\n\n"
        "Here's what you get:\n\n"
        "✅ <b>150% deposit bonus</b> on new accounts\n\n"
        "✅ <b>50% re-deposit bonus</b> — for life\n\n\n"
        "Example: deposit <b>£500</b> → get <b>£750</b> on top → trade with <b>£1,250</b> 🔥\n\n\n"
        "First, let's link your account 👇"
    )
    _broker_choice(user_id, first_name, username, "bonus")
    notify_owner(f"💰 <b>Lead claiming bonus</b>\n👤 {first_name} (@{username})\n🆔 <code>{user_id}</code>")

def handle_create_account(user_id, first_name, username):
    _add_step(user_id, "Creating new account")
    store_client_message(user_id, "Client tapped: Create an account", direction="event")
    with users_lock:
        if str(user_id) in users_db:
            users_db[str(user_id)]["broker"] = "Vantage (new)"
            save_users(users_db)
    send_to_user(user_id,
        "🆕 <b>No account? No problem — let's get you set up in 30 seconds.</b>\n\n\n"
        "🔥 <b>JOIN THE BEST BROKER OF 2026</b>\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "1️⃣ <b>Create your account here</b> (takes 30s):\n"
        "https://vigco.co/QJrYVz\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "2️⃣ <b>Use these settings when signing up:</b>\n"
        "• Referral / IB: <b>58576</b>\n"
        "• Platform: <b>MT4 or MT5</b>\n"
        "• Account: <b>Standard STP</b>\n"
        "• Currency: <b>GBP or USD</b>\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "3️⃣ 💰 <b>Then we apply your 150% Deposit Bonus:</b>\n"
        "Deposit <b>£500</b> → get <b>£750</b> on top → trade with <b>£1,250</b> 🔥\n\n"
        "✅ Once your account's created, tap below 👇",
        keyboard={"inline_keyboard": [
            [{"text": "✅ ACCOUNT CREATED", "callback_data": "account_created"}],
            [{"text": "💬 Stuck? Message me", "url": "https://t.me/KevSupportTeam"}],
        ]}
    )
    onboarding_state[user_id] = {"step": "awaiting_created", "broker": "vantage", "first_name": first_name, "username": username}
    notify_owner(f"🆕 <b>Lead creating NEW account</b>\n👤 {first_name} (@{username})\n🆔 <code>{user_id}</code>")

def handle_account_created(user_id, first_name, username):
    _add_step(user_id, "New account created")
    store_client_message(user_id, "Client tapped: Account created", direction="event")
    _ask_for_details(user_id, first_name, username, "Vantage")
    onboarding_state[user_id] = {"step": "awaiting_account", "broker": "vantage", "first_name": first_name, "username": username}
    notify_owner(f"✅ <b>Lead created account - awaiting details</b>\n👤 {first_name} (@{username})\n🆔 <code>{user_id}</code>")

def _ask_for_details(user_id, first_name, username, broker_label):
    send_to_user(user_id,
        "🎉 <b>Almost there — you're getting FREE VIP access!</b>\n\n\n"
        "Please provide <b>ONE</b> of the following to verify your account:\n\n"
        f"✅ Your <b>{broker_label} MT4/MT5 number</b>\n\n"
        f"✅ Your <b>{broker_label} UID</b>\n\n"
        f"✅ Your <b>{broker_label} account email</b>\n\n\n"
        "👇 Just type it below and send.",
        keyboard={"inline_keyboard": [
            [{"text": "💬 Stuck? Message me", "url": "https://t.me/KevSupportTeam"}],
        ]}
    )

def handle_vantage(user_id, first_name, username):
    with users_lock:
        if str(user_id) in users_db:
            users_db[str(user_id)]["broker"] = "Vantage"
            save_users(users_db)
    _add_step(user_id, "Chose Vantage")

    # 1) Image FIRST
    send_photo_to_user(user_id, VANTAGE_IMAGE)
    # 2) Steps
    send_to_user(user_id,
        "✅ <b>Perfect — here's how to unlock your FREE lifetime VIP access.</b>\n\n"
        "Just follow these 4 quick steps 👇\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "1️⃣ <b>Log in to your Vantage account</b>\n"
        "https://secure.vantagemarkets.com/logout?lang=en_US\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "2️⃣ <b>Open the IB transfer form</b>\n"
        "https://secure.vantagemarkets.com/profile/transfer-ib-affiliate\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "3️⃣ <b>Enter these details exactly:</b>\n"
        "• Partnership Type: <b>IB</b>\n"
        "• IB Number: <b>58576</b>\n"
        "• Reason: <b>VIP</b>\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "4️⃣ <b>Close any open positions, then hit Submit.</b>\n\n"
        "✅ When you've submitted the form, tap the button below 👇"
    )
    # 3) DONE + Stuck buttons
    send_to_user(user_id,
        "🚨 <b>IMPORTANT</b>\n\n"
        "🚫 Close all open positions before the transfer.\n"
        "🚫 Wait for the confirmation email before placing new trades.",
        keyboard={"inline_keyboard": [
            [{"text": "✅ DONE, form submitted", "callback_data": "done_vantage"}],
            [{"text": "💬 Stuck? Message me", "url": "https://t.me/KevSupportTeam"}],
        ]}
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

    # 1) Image FIRST
    send_photo_to_user(user_id, PUPRIME_IMAGE)
    # 2) Steps
    send_to_user(user_id,
        "✅ <b>Perfect — here's how to unlock your FREE lifetime VIP access.</b>\n\n"
        "Just follow these 4 quick steps 👇\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "1️⃣ <b>Log in to your PU Prime portal</b>\n"
        "https://myaccount.puprime.com/home\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "2️⃣ <b>Open the IB transfer form</b>\n"
        "https://myaccount.puprime.com/profile/transfer-ib-affiliate\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "3️⃣ <b>Enter these details exactly:</b>\n"
        "• Partnership Type: <b>IB</b>\n"
        "• IB Number: <b>50151</b>\n"
        "• Reason: <b>VIP</b>\n\n"
        "━━━━━━━━━━━━━━━\n\n"
        "4️⃣ <b>Close any open positions, then hit Submit.</b>\n\n"
        "✅ When you've submitted the form, tap the button below 👇"
    )
    # 3) DONE + Stuck buttons
    send_to_user(user_id,
        "🚨 <b>IMPORTANT</b>\n\n"
        "🚫 Close all open positions before the transfer.\n"
        "🚫 Wait for the confirmation email before placing new trades.",
        keyboard={"inline_keyboard": [
            [{"text": "✅ DONE, form submitted", "callback_data": "done_puprime"}],
            [{"text": "💬 Stuck? Message me", "url": "https://t.me/KevSupportTeam"}],
        ]}
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
    store_client_message(user_id, "✅ Client tapped: DONE (IB transfer completed)", direction="event")
    store_client_message(user_id, "🤖 Bot: Asked for MT4/MT5 / UID / email.", direction="out")

    broker_label = "Vantage" if broker == "vantage" else "PU Prime"
    _ask_for_details(user_id, first_name, username, broker_label)
    onboarding_state[user_id] = {"step": "awaiting_account", "broker": broker, "first_name": first_name, "username": username}
    mid = notify_owner(
        f"✅ <b>Lead clicked DONE</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n\n"
        f"⏳ Status: Waiting for MT4/MT5 / UID / email...\n\n"
        f"<i>↩️ Reply to THIS message to send them a message</i>"
    )
    if mid:
        reply_map[str(mid)] = str(user_id)

def handle_account_number(user_id, first_name, username, account_number, broker):
    broker_name = "Vantage" if broker == "vantage" else "PU Prime"
    if "@" in account_number:
        detail_type = "Email"
    elif account_number.isdigit():
        detail_type = "MT4/MT5"
    else:
        detail_type = "UID"
    _add_step(user_id, f"Submitted {detail_type}: {account_number}")

    # Log to chat history
    store_client_message(user_id, f"🔢 Client entered {detail_type}: {account_number}", direction="event")
    store_client_message(user_id, "🤖 Bot: Details received! Team will verify and activate your access shortly. Welcome! 🏆", direction="out")

    with users_lock:
        if str(user_id) in users_db:
            users_db[str(user_id)]["completed"]   = True
            users_db[str(user_id)]["mt5_account"] = account_number
            save_users(users_db)

    send_to_user(user_id,
        "▓▓▓▓▓ <b>100% complete</b> ✅\n\n"
        "✅ <b>Details received!</b>\n\n"
        "Our team will verify your account and activate your FREE Premium Group access shortly.\n\n"
        "🏆 <b>Welcome to Gold PM Group!</b>\n\n"
        "Our team will be in touch with you very soon. 🙌\n\n"
        "🎡 <b>BONUS:</b> You've unlocked the <b>Daily Spin</b>! Spin every 24h to win "
        "free signals, bonuses & tools 👇",
        keyboard={"inline_keyboard": [[{"text": "🎡 SPIN THE WHEEL", "callback_data": "spin_wheel"}]]}
    )
    mid = notify_owner(
        f"🏆 <b>NEW VIP CLIENT COMPLETE!</b>\n\n"
        f"👤 Name: {first_name}\n"
        f"📲 Username: @{username}\n"
        f"🆔 User ID: <code>{user_id}</code>\n"
        f"🏦 Broker: {broker_name}\n"
        f"📋 {detail_type}: <b>{account_number}</b>\n\n"
        f"<i>↩️ Reply to THIS message to send them a message</i>"
    )
    if mid:
        reply_map[str(mid)] = str(user_id)
    onboarding_state.pop(user_id, None)

# ─── CHANNEL POST FORWARDING ──────────────────────────────────────────────────
CHANNEL_HOOKS = [
    "🔥 <b>THIS JUST DROPPED IN THE PM — YOU MISSED IT!</b>\n\nComplete your 20-second setup to catch the next one 👇",
    "🚨 <b>LIVE FROM THE PM GROUP — members are already on it!</b>\n\nYou're missing these. Finish your setup in 20 seconds 👇",
    "💰 <b>ANOTHER ONE JUST WENT OUT TO PM MEMBERS!</b>\n\nThis could've been you. Complete your free setup now 👇",
    "⚡ <b>PM MEMBERS GOT THIS SECONDS AGO.</b>\n\nStop missing out — 20-second setup and you're in 👇",
    "📈 <b>JUST POSTED IN THE PM — did you catch it?</b>\n\nGet every signal live. Finish your setup 👇",
]

def forward_channel_post_to_users(post):
    """Copy a channel post to every bot user with a FOMO hook + buttons."""
    from_chat_id = post.get("chat", {}).get("id")
    message_id   = post.get("message_id")
    if not from_chat_id or not message_id:
        return

    hook = random.choice(CHANNEL_HOOKS)

    with users_lock:
        uids = list(users_db.keys())

    logger.info(f"📢 Forwarding channel post to {len(uids)} users...")
    sent = 0
    for uid in uids:
        # skip blocked users
        udata = users_db.get(uid, {})
        if udata.get("blocked"):
            continue
        try:
            # 1) copy the actual trade/screenshot (no "forwarded from" tag)
            requests.post(f"{TELEGRAM_URL}/copyMessage", json={
                "chat_id": uid,
                "from_chat_id": from_chat_id,
                "message_id": message_id,
            }, timeout=10)
            # 2) send the hook + buttons underneath
            send_to_user(uid, hook, keyboard=JOIN_BUTTON)
            sent += 1
            time.sleep(0.05)  # stay under Telegram rate limits (~30/sec)
        except Exception as e:
            logger.error(f"Forward to {uid} failed: {e}")
    logger.info(f"📢 Channel post forwarded to {sent} users.")

# ─── DRIP SCHEDULER ───────────────────────────────────────────────────────────
MAX_DRIP_DAYS = 30
# Plan B: engagement questions often (~8h), promo ads rarely (~20h).
# Each user gets their own random next-times so nothing is clustered.
PROMO_MIN_GAP = 18 * 3600   # ~18h
PROMO_MAX_GAP = 24 * 3600   # ~24h
QUESTION_MIN_GAP = 7 * 3600  # ~7h
QUESTION_MAX_GAP = 10 * 3600 # ~10h

def drip_scheduler():
    logger.info("✅ DRIP SCHEDULER STARTED (questions ~8h, promos ~20h)")
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

                # ── ENGAGEMENT QUESTION (every ~8h) ──
                next_q = data.get("next_question")
                if next_q is None:
                    with users_lock:
                        users_db[uid]["next_question"] = now + random.uniform(QUESTION_MIN_GAP, QUESTION_MAX_GAP)
                        save_users(users_db)
                elif now >= next_q:
                    q_count = data.get("question_count", 0)
                    q = ENGAGEMENT_QUESTIONS[q_count % len(ENGAGEMENT_QUESTIONS)]
                    if send_to_user(uid, q, keyboard=ENGAGE_BUTTON):
                        due_count += 1
                        with users_lock:
                            users_db[uid]["question_count"] = q_count + 1
                            users_db[uid]["next_question"]  = time.time() + random.uniform(QUESTION_MIN_GAP, QUESTION_MAX_GAP)
                            save_users(users_db)
                        logger.info(f"💬 Question #{q_count+1} sent to {uid}")

                # ── PROMO AD (every ~20h) ──
                next_drip = data.get("next_drip")
                if next_drip is None:
                    with users_lock:
                        users_db[uid]["next_drip"] = now + random.uniform(PROMO_MIN_GAP, PROMO_MAX_GAP)
                        save_users(users_db)
                elif now >= next_drip:
                    count = data.get("drip_count", 0)
                    msg = DRIP_MESSAGES[count % len(DRIP_MESSAGES)]
                    if send_to_user(uid, msg, keyboard=JOIN_BUTTON):
                        due_count += 1
                        with users_lock:
                            users_db[uid]["last_drip"]  = time.time()
                            users_db[uid]["drip_count"] = count + 1
                            users_db[uid]["next_drip"]  = time.time() + random.uniform(PROMO_MIN_GAP, PROMO_MAX_GAP)
                            save_users(users_db)
                        logger.info(f"✅ Promo #{count+1} sent to {uid}")

            logger.info(f"[Drip cycle #{cycle}] Complete. {due_count} messages sent.")

        except Exception as e:
            logger.error(f"Drip scheduler error: {e}")
        time.sleep(600)  # check every 10 min


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

        # ── CHANNEL POST FORWARDING ──
        # When a new post appears in your signals channel, copy it to every
        # user who started the bot, with a FOMO hook + buttons.
        if "channel_post" in update:
            post = update["channel_post"]
            chat_id = str(post.get("chat", {}).get("id", ""))
            if chat_id == str(SIGNALS_CHANNEL_ID):
                threading.Thread(
                    target=forward_channel_post_to_users,
                    args=(post,), daemon=True
                ).start()
            return jsonify({"ok": True})

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

            # ── BLOCKED USER CHECK — silently ignore button taps ──
            if is_blocked(username):
                logger.info(f"🚫 Blocked user tapped button (ignored): @{username}")
                return jsonify({"ok": True})

            # If user not in DB (e.g. multi-worker / after restart), register
            # them SILENTLY so their record exists — but do NOT re-send the
            # welcome message. We still process the button they actually tapped.
            if str(user_id) not in users_db:
                with users_lock:
                    users_db[str(user_id)] = {
                        "name": name,
                        "username": username,
                        "started_at": time.time(),
                        "completed": False,
                        "last_drip": time.time(),
                        "drip_count": 0,
                        "broker": None,
                        "mt5_account": None,
                        "steps": [],
                        "last_seen": time.time(),
                    }
                    save_users(users_db)

            if data == "have_account":
                handle_have_account(user_id, name, username)
            elif data == "create_account":
                handle_create_account(user_id, name, username)
            elif data == "claim_bonus":
                handle_claim_bonus(user_id, name, username)
            elif data == "account_created":
                handle_account_created(user_id, name, username)
            elif data == "broker_vantage":
                handle_vantage(user_id, name, username)
            elif data == "broker_puprime":
                handle_puprime(user_id, name, username)
            elif data == "done_vantage":
                handle_done(user_id, name, username, "vantage")
            elif data == "done_puprime":
                handle_done(user_id, name, username, "puprime")
            elif data == "restart_onboarding":
                handle_start(user_id, name, username)
            elif data == "spin_wheel":
                handle_spin(user_id, name, username)
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

        if text.strip().startswith("/spin"):
            handle_spin(user_id, name, username)
            return jsonify({"ok": True})

        state = onboarding_state.get(user_id, {})
        if state.get("step") == "awaiting_account" and text.strip():
            handle_account_number(user_id, name, username, text.strip(), state.get("broker", "unknown"))
            return jsonify({"ok": True})

        # If user is in DB, chose a broker, clicked DONE but state was lost
        # (multi-worker / restart) and they type their MT5 number, email, or UID —
        # detect it and handle it.
        _txt = text.strip()
        is_number = _txt.isdigit() and len(_txt) >= 4
        is_email = "@" in _txt and "." in _txt
        is_uid = _txt.isalnum() and 4 <= len(_txt) <= 20
        looks_like_account = is_number or is_email or is_uid
        if looks_like_account:
            uid_data = users_db.get(str(user_id), {})
            broker = (uid_data.get("broker") or "").lower()
            if broker and not uid_data.get("completed"):
                broker_key = "vantage" if broker == "vantage" else "puprime"
                logger.info(f"Auto-detecting account detail from {user_id}: {_txt}")
                handle_account_number(user_id, name, username, _txt, broker_key)
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
        f"PM Gold Onboarding Bot is running! ✅\n"
        f"Total leads: {total} | Completed: {completed} | Pending: {total - completed}\n"
        f"Dashboard: /dashboard"
    )


# ─── AUTO WEBHOOK SETUP ───────────────────────────────────────────────────────
def setup_webhook():
    """Automatically register the webhook with Telegram on startup."""
    # Wait a moment for the server to come up
    time.sleep(5)
    # Railway provides the public domain in this env var
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    if not domain:
        logger.error("❌ RAILWAY_PUBLIC_DOMAIN not set — cannot register webhook automatically.")
        return
    webhook_url = f"https://{domain}/telegram_update"
    try:
        r = requests.post(
            f"{TELEGRAM_URL}/setWebhook",
            json={
                "url": webhook_url,
                "drop_pending_updates": True,
                "allowed_updates": ["message", "callback_query", "channel_post"],
            },
            timeout=10,
        )
        if r.json().get("ok"):
            logger.info(f"✅ Webhook set successfully: {webhook_url}")
        else:
            logger.error(f"❌ Webhook setup failed: {r.json()}")
    except Exception as e:
        logger.error(f"❌ Webhook setup error: {e}")

# Launch webhook setup in the background so it runs under gunicorn too
threading.Thread(target=setup_webhook, daemon=True).start()


if __name__ == "__main__":
    # Background threads already started above via start_background_threads()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
