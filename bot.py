import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from flask import Flask
import json
import time
import threading
import os
import uuid
import html
import re
from datetime import datetime, timedelta
from collections import defaultdict

# --- Telegram Latest Feature Check (CopyTextButton) ---
try:
    from telebot.types import CopyTextButton
    HAS_COPY_BTN = True
except ImportError:
    HAS_COPY_BTN = False

# ============================================================
#  কনফিগারেশন (Configuration)
# ============================================================
# 🌟 আপনার দেওয়া নতুন বট টোকেন এখানে আপডেট করা হয়েছে
TOKEN = "8634301352:AAHZ2Rmgy8qb5gYKyrQCtSTy9057k9eJZ90"
ADMIN_ID = 6901639746

# ── 2 Panel Configuration ──
PANELS = [
    {"url": "http://63.141.255.227", "key": "nxa_27c40799d4f104fd0649d098c843dab44d879bc2"},
    {"url": "http://63.141.255.227", "key": "nxa_2e85684bd380958ec3e895e63601b6af6d24819d"}
]

bot       = telebot.TeleBot(TOKEN, parse_mode=None)
DATA_FILE = "dxa_bot_advanced_v5.json"

active_polls      = {}
user_states       = {}
traffic_cooldowns = {}
number_cooldowns  = {}
data_lock         = threading.RLock()

user_last_service_info = {}

NUMBER_FETCH_COOLDOWN    = 5
TRAFFIC_COOLDOWN         = 10
NUMBER_ALLOCATION_COUNT  = 2
OTP_POLL_TIMEOUT         = 1200
RANGE_UPDATE_INTERVAL    = 30      # সেকেন্ড — live range group-এ পাঠানোর interval

# 🌟 গ্রুপে রেঞ্জ পুনরায় ফরওয়ার্ড করার কুলডাউন টাইম (৩০০ সেকেন্ড = ৫ মিনিট)
last_forwarded_ranges  = {}
RANGE_FORWARD_COOLDOWN = 300 

# ============================================================
#  SMS-based Service Detection
# ============================================================
SMS_SERVICE_PATTERNS = [
    ("whatsapp", ["your whatsapp code", "whatsapp code", "whatsapp"]),
    ("instagram", ["is your instagram code", "your instagram code", "instagram code", "instagram", "gdgcwrwhvm"]),
    ("facebook", ["votre code facebook", "is your facebook code", "your facebook code", "facebook code", "facebook", "h**q+fsn"]),
    ("telegram", ["telegram code", "login code telegram", "telegram"]),
    ("google", ["google verification", "your google code", "gmail", "google"]),
    ("tiktok", ["tiktok", "tik tok"]),
    ("twitter", ["twitter", "your x verification"]),
    ("snapchat", ["snapchat"]),
]

TARGET_SERVICES = {"facebook", "whatsapp", "instagram"}

def detect_service_from_sms(sms_text: str, app_name: str) -> str:
    sms_lower  = sms_text.lower()
    app_lower  = app_name.lower()
    combined   = sms_lower + " " + app_lower

    for service, patterns in SMS_SERVICE_PATTERNS:
        for pat in patterns:
            if pat in combined:
                return service
    return app_lower.strip()

# ============================================================
#  Premium Emoji Collection
# ============================================================
EMOJI_COLLECTION = {
    "facebook": "📘", "whatsapp": "💚", "telegram": "✈️", "instagram": "📷",
    "twitter": "𝕏", "google": "🔍", "gmail": "📧", "youtube": "🎬",
    "apple": "🍎", "microsoft": "💻", "tiktok": "🎵", "snapchat": "👻",
    "binance": "💰", "melbet": "🎰", "bkash": "💳", "rocket": "🚀",
    "nagad": "📲", "imo": "💭", "messenger": "💬", "linkedin": "🔷",
    "discord": "💜", "spotify": "🎶", "netflix": "🎬", "amazon": "📦",
    "uber": "🚗", "paypal": "💳", "cashapp": "💸", "venmo": "💵",
    "done": "✅", "cross": "❌", "warning": "⚠️", "time": "⏰",
    "waiting": "🔄", "message": "📩", "otp": "🔐", "number": "📞",
    "world": "🌐", "user": "👤", "bot": "🤖", "live": "🟢",
    "off": "🔴", "traffic": "📊", "chart": "📈", "star": "⭐",
    "crown": "👑", "diamond": "💎", "fire": "🔥", "sparkles": "✨",
    "globe": "🌍", "pin": "📌", "note": "📝", "gear": "⚙️",
    "link": "🔗", "plus": "➕", "trash": "🗑️", "gift": "🎁",
    "shield": "🛡️", "key": "🔑", "lock": "🔒", "bell": "🔔",
    "target": "🎯", "lightning": "⚡", "bulb": "💡", "tools": "🛠️",
    "package": "📦", "mega": "📢", "hi": "👋", "refresh": "🔄",
    "premium": "💫", "vip": "🌟", "ban": "🚫", "admin": "👮",
    "stats": "📉", "history": "📋", "search": "🔎", "health": "💊",
    "success": "🎉", "info": "ℹ️", "back": "◀️", "new": "🆕",
}

COUNTRY_CODE_MAP = {
    "togo": "TG", "ivory coast": "IV", "ghana": "GH", "nigeria": "NG",
    "senegal": "SN", "cameroon": "CM", "benin": "BJ", "mali": "ML",
    "guinea": "GN", "burkina faso": "BF", "niger": "NE", "congo": "CG",
    "kenya": "KE", "ethiopia": "ET", "tanzania": "TZ", "uganda": "UG",
    "rwanda": "RW", "zambia": "ZM", "zimbabwe": "ZW", "malawi": "MW",
    "mozambique": "MZ", "madagascar": "MG", "mauritius": "MU",
    "south africa": "ZA", "egypt": "EG", "morocco": "MA", "algeria": "DZ",
    "tunisia": "TN", "libya": "LY", "sudan": "SD", "somalia": "SO", 
    "djibouti": "DJ", "eritrea": "ER", "india": "IN", "pakistan": "PK", 
    "bangladesh": "BD", "indonesia": "ID", "philippines": "PH", "vietnam": "VN",
    "thailand": "TH", "malaysia": "MY", "myanmar": "MM", "cambodia": "KH", 
    "laos": "LA", "sri lanka": "LK", "nepal": "NP", "bhutan": "BT", 
    "maldives": "MV", "china": "CN", "russia": "RU", "ukraine": "UA",
    "brazil": "BR", "mexico": "MX", "colombia": "CO", "argentina": "AR", 
    "venezuela": "VE", "peru": "PE", "chile": "CL", "bolivia": "BO", 
    "ecuador": "EC", "usa": "US", "canada": "CA", "uk": "GB",
    "germany": "DE", "france": "FR", "spain": "ES", "italy": "IT", 
    "portugal": "PT", "netherlands": "NL", "belgium": "BE", "switzerland": "CH", 
    "austria": "AT", "poland": "PL", "czech": "CZ", "romania": "RO",
    "hungary": "HU", "bulgaria": "BG", "greece": "GR", "sweden": "SE", 
    "norway": "NO", "denmark": "DK", "finland": "FI", "turkey": "TR", 
    "israel": "IL", "iran": "IR", "iraq": "IQ", "saudi arabia": "SA",
    "uae": "AE", "kuwait": "KW", "qatar": "QA", "bahrain": "BH", 
    "oman": "OM", "yemen": "YE", "jordan": "JO", "lebanon": "LB", 
    "syria": "SY", "afghanistan": "AF", "uzbekistan": "UZ", "kazakhstan": "KZ",
    "australia": "AU", "new zealand": "NZ", "japan": "JP", "south korea": "KR", 
    "north korea": "KP", "taiwan": "TW", "hong kong": "HK", "singapore": "SG",
}

FLAG_MAP = {
    "TG": "🇹🇬", "IV": "🇨🇮", "GH": "🇬🇭", "NG": "🇳🇬",
    "SN": "🇸🇳", "CM": "🇨🇲", "BJ": "🇧জয়", "ML": "🇲🇱",
    "GN": "🇬🇳", "BF": "🇧🇫", "NE": "🇳🇪", "CG": "🇨🇬",
    "KE": "🇰🇪", "ET": "🇪🇹", "TZ": "🇹🇿", "UG": "🇺🇬",
    "RW": "🇷🇼", "ZM": "🇿🇲", "ZW": "🇿🇼", "MW": "🇲🇼",
    "MZ": "🇲🇿", "MG": "🇲🇬", "MU": "🇲🇺", "ZA": "🇿🇦",
    "EG": "🇪🇬", "MA": "🇲🇦", "DZ": "🇩🇿", "TN": "🇹🇳",
    "LY": "🇱🇾", "SD": "🇸🇩", "SO": "🇸🇴", "DJ": "🇩🇯",
    "ER": "🇪🇷", "IN": "🇮🇳", "PK": "🇵🇰", "BD": "🇧🇩",
    "ID": "🇮🇩", "PH": "🇵🇭", "VN": "🇻🇳", "TH": "🇹🇭",
    "MY": "🇲🇾", "MM": "🇲🇲", "KH": "🇰🇭", "LA": "🇱🇦",
    "LK": "🇱🇰", "NP": "🇳🇵", "BT": "🇧🇹", "MV": "🇲🇻",
    "CN": "🇨🇳", "RU": "🇷🇺", "UA": "🇺🇦", "BR": "🇧🇷",
    "MX": "🇲🇽", "CO": "🇨🇴", "AR": "🇦🇷", "VE": "🇻🇪",
    "PE": "🇵🇪", "CL": "🇨🇱", "BO": "🇧🇴", "EC": "🇪🇨",
    "US": "🇺🇸", "CA": "🇨🇦", "GB": "🇬🇧", "DE": "🇩🇪",
    "FR": "🇫🇷", "ES": "🇪🇸", "IT": "🇮🇹", "PT": "🇵🇹",
    "NL": "🇳🇱", "BE": "🇧🇪", "CH": "🇨🇭", "AT": "🇦🇹",
    "PL": "🇵🇱", "CZ": "🇨🇿", "RO": "🇷🇴", "HU": "🇭🇺",
    "BG": "🇧🇬", "GR": "🇬🇷", "SE": "🇸🇪", "NO": "🇳🇴",
    "DK": "🇩🇰", "FI": "🇫🇮", "TR": "🇹🇷", "IL": "🇮🇱",
    "IR": "🇮🇷", "IQ": "🇮🇶", "SA": "🇸🇦", "AE": "🇦🇪",
    "KW": "🇰🇼", "QA": "🇶🇦", "BH": "🇧🇭", "OM": "🇴🇲",
    "YE": "🇾🇪", "JO": "🇯🇴", "LB": "🇱🇧", "SY": "🇸🇾",
    "AF": "🇦🇫", "UZ": "🇺🇿", "KZ": "🇰🇿", "AU": "🇦🇺",
    "NZ": "🇳🇿", "JP": "🇯🇵", "KR": "🇰🇷", "KP": "🇰🇵",
    "TW": "🇹🇼", "HK": "🇭🇰", "SG": "🇸🇬",
}

# --- Flask Dummy Server for Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!", 200

def run_flask():
    app.run(host="0.0.0.0", port=10000)

def emo(keyword, default="✨"):
    if not keyword: return default
    kw = str(keyword).lower().strip()
    if kw in EMOJI_COLLECTION: return EMOJI_COLLECTION[kw]
    for key, val in EMOJI_COLLECTION.items():
        if len(key) >= 3 and key in kw: return val
    return default

def get_country_code(name):
    if not name: return "XX"
    key = name.lower().strip()
    if key in COUNTRY_CODE_MAP:
        return COUNTRY_CODE_MAP[key]
    return name[:2].upper()

def get_flag(name):
    if not name: return "🌍"
    code = get_country_code(name)
    return FLAG_MAP.get(code, "🌍")

# ============================================================
#  Data Management
# ============================================================
DEFAULT_DATA = {
    "users": {}, "services_data": {},
    "forward_groups": [{"chat_id": "-1002366117336", "buttons": []}],
    "main_otp_link": "https://t.me/anudh8448", "watermark": "THE white x",
    "force_join_enabled": False, "force_join_channels": [],
    "admins": [], "banned_users": [],
    "global_stats": {"total_otps": 0, "total_numbers": 0, "daily": {}}
}

def load_data():
    with data_lock:
        if not os.path.exists(DATA_FILE): return DEFAULT_DATA.copy()
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if not content: return DEFAULT_DATA.copy()
            data = json.loads(content)
            for key in ["force_join_enabled", "force_join_channels", "admins", "banned_users", "global_stats", "main_otp_link", "watermark"]:
                if key not in data: data[key] = DEFAULT_DATA[key]
            if "daily" not in data.get("global_stats", {}): data["global_stats"]["daily"] = {}
            for grp in data.get("forward_groups", []): grp.setdefault("buttons", [])
            return data
        except:
            return DEFAULT_DATA.copy()

def save_data(data):
    with data_lock:
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass

# ============================================================
#  Helper Functions
# ============================================================
def format_url(url):
    if url and not url.startswith(("http://", "https://", "tg://")): return "https://" + url
    return url

def today_str(): return datetime.now().strftime("%Y-%m-%d")

def extract_channel_username(url):
    if "t.me/" in url:
        parts = url.split("t.me/")
        if len(parts) > 1:
            username = parts[1].split("/")[0].split("?")[0]
            if not username.startswith("@"): username = "@" + username
            return username
    return ""

def is_admin(user_id):
    if user_id == ADMIN_ID: return True
    return user_id in load_data().get("admins", [])

def is_banned(user_id):
    if user_id == ADMIN_ID: return False
    return user_id in load_data().get("banned_users", [])

def check_force_join(user_id):
    if is_admin(user_id): return True
    data = load_data()
    if not data.get("force_join_enabled"): return True
    channels = data.get("force_join_channels", [])
    if not channels: return True
    for link in channels:
        chat_username = extract_channel_username(link)
        if not chat_username: continue
        try:
            member = bot.get_chat_member(chat_username, user_id)
            if member.status not in ["member", "administrator", "creator"]: return False
        except:
            pass
    return True

def register_user(from_user):
    data = load_data()
    uid = str(from_user.id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if uid not in data["users"]:
        data["users"][uid] = {"name": from_user.first_name or "", "username": from_user.username or "", "joined": now, "last_seen": now, "otp_count": 0, "number_count": 0, "history": []}
    else:
        data["users"][uid]["last_seen"] = now
        data["users"][uid]["name"] = from_user.first_name or data["users"][uid].get("name", "")
        data["users"][uid]["username"] = from_user.username or data["users"][uid].get("username", "")
    save_data(data)

def bump_stats(uid, kind):
    data = load_data()
    uid = str(uid)
    today = today_str()
    data["users"].setdefault(uid, {"name": "", "username": "", "joined": "", "last_seen": "", "otp_count": 0, "number_count": 0, "history": []})
    gs = data.setdefault("global_stats", {"total_otps": 0, "total_numbers": 0, "daily": {}})
    gs.setdefault("daily", {}).setdefault(today, {"otps": 0, "numbers": 0})
    if kind == "otp":
        data["users"][uid]["otp_count"] = data["users"][uid].get("otp_count", 0) + 1
        gs["total_otps"] = gs.get("total_otps", 0) + 1
        gs["daily"][today]["otps"] += 1
    elif kind == "number":
        data["users"][uid]["number_count"] = data["users"][uid].get("number_count", 0) + 1
        gs["total_numbers"] = gs.get("total_numbers", 0) + 1
        gs["daily"][today]["numbers"] += 1
    save_data(data)

def add_to_history(uid, entry):
    data = load_data()
    uid = str(uid)
    user = data["users"].setdefault(uid, {"history": []})
    history = user.setdefault("history", [])
    history.insert(0, entry)
    user["history"] = history[:10]
    save_data(data)

def safe_send(chat_id, text, reply_markup=None, message_id=None):
    try:
        if message_id:
            return bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=reply_markup)
        else:
            return bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=reply_markup)
    except:
        return None

def make_poll_state(chat_id, number_ids=None):
    active_polls[str(chat_id)] = {
        "active": True,
        "numbers": {num_id: True for num_id in (number_ids or [])}
    }

def cancel_poll_state(chat_id):
    active_polls[str(chat_id)] = {"active": False, "numbers": {}}

# ============================================================
#  Group Forward Helper
# ============================================================
def build_group_forward_markup(grp, copy_text_value, bot_link):
    markup = InlineKeyboardMarkup(row_width=2)
    if HAS_COPY_BTN:
        copy_btn = InlineKeyboardButton("📋 Copy", copy_text=CopyTextButton(text=str(copy_text_value)))
    else:
        copy_btn = InlineKeyboardButton("📋 Copy", callback_data=f"copyn|{copy_text_value}")

    custom_buttons = []
    for b in grp.get("buttons", []):
        if b.get("name") and b.get("url"):
            custom_buttons.append(InlineKeyboardButton(b["name"], url=format_url(b["url"])))

    if custom_buttons:
        markup.row(copy_btn, custom_buttons[0])
        for btn in custom_buttons[1:]:
            markup.add(btn)
    else:
        markup.add(copy_btn)
    return markup

def forward_range_to_groups(fwd_groups, watermark, service_name, country_name, rng_pattern, bot_link):
    flag         = get_flag(country_name)
    country_code = get_country_code(country_name)
    srv_emoji    = emo(service_name)
    now_str      = datetime.now().strftime("%H:%M:%S")

    msg_text = (
        f"VIP NUMBER CLUB ⚡  <b>{html.escape(watermark)}</b>\n"
        f"{flag} {country_code} [+{rng_pattern}] {srv_emoji} "
        f"{html.escape(service_name.title())} ({html.escape(country_name)}) {now_str}"
    )

    for grp in fwd_groups:
        grp_id_fwd = grp.get("chat_id")
        if not grp_id_fwd: continue
        rng_markup = build_group_forward_markup(grp, rng_pattern, bot_link)
        
        while True:
            try:
                bot.send_message(int(grp_id_fwd), msg_text, reply_markup=rng_markup, parse_mode="HTML")
                break
            except Exception as fwd_err:
                err_str = str(fwd_err)
                if "429" in err_str or "Too Many Requests" in err_str:
                    match = re.search(r'retry after (\d+)', err_str)
                    retry_after = int(match.group(1)) if match else 5
                    print(f"⏳ [429 FloodWait] Sleeping for {retry_after}s on group {grp_id_fwd}...")
                    time.sleep(retry_after + 1)
                else:
                    print(f"❌ [FWD] Range forward error ({grp.get('chat_id')}): {fwd_err}")
                    break

# ============================================================
#  User UI Functions
# ============================================================
def show_user_services(chat_id, message_id=None):
    data = load_data()
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for srv_id, srv in data.get("services_data", {}).items():
        has_ranges = any(len(cnt.get("ranges", {})) > 0 for cnt in srv.get("countries", {}).values())
        if has_ranges:
            buttons.append(InlineKeyboardButton(text=f"{emo(srv['name'])} {srv['name']}", callback_data=f"usr_s|{srv_id}"))
    if buttons: markup.add(*buttons)
    markup.row(InlineKeyboardButton("🔍 Custom Search", callback_data="find_number"), InlineKeyboardButton("📋 My History", callback_data="my_history"))
    text = f"{emo('star')} <b>AVAILABLE SERVICES</b> {emo('star')}\n━━━━━━━━━━━━━━━━━━\nChoose a service to get a virtual number\n━━━━━━━━━━━━━━━━━━\n{emo('lightning')} Fast • Secure • Reliable {emo('lightning')}"
    safe_send(chat_id, text, markup, message_id)

def show_user_countries(chat_id, srv_id, message_id=None):
    data = load_data()
    srv_data = data.get("services_data", {}).get(srv_id)
    if not srv_data: return
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for cnt_id, cnt in srv_data.get("countries", {}).items():
        if len(cnt.get("ranges", {})) > 0:
            buttons.append(InlineKeyboardButton(text=f"{get_flag(cnt['name'])} {cnt['name']}", callback_data=f"usr_c|{srv_id}|{cnt_id}"))
    if buttons: markup.add(*buttons)
    markup.add(InlineKeyboardButton("🔙 Back to Services", callback_data="back_to_user_services"))
    text = f"{emo('globe')} <b>SELECT COUNTRY</b> {emo('globe')}\n━━━━━━━━━━━━━━━━━━\n📱 Service: <code>{html.escape(srv_data['name'])}</code>\n\nChoose your country below:"
    safe_send(chat_id, text, markup, message_id)

def show_user_ranges(chat_id, srv_id, cnt_id, message_id=None):
    data = load_data()
    srv_data = data.get("services_data", {}).get(srv_id)
    cnt_data = srv_data.get("countries", {}).get(cnt_id) if srv_data else None
    if not cnt_data: return
    
    markup = InlineKeyboardMarkup(row_width=2)
    
    # 🌟 সমাধানের অংশ: র (raw) রেঞ্জ হাইড করে প্রফেশনাল 'Server 1, 2, 3' বাটন দেওয়া হয়েছে
    buttons = []
    for idx, (rng_id, rng_val) in enumerate(cnt_data.get("ranges", {}).items(), 1):
        buttons.append(InlineKeyboardButton(text=f"⚙️ Server {idx}", callback_data=f"usr_r|{srv_id}|{cnt_id}|{rng_id}"))
        
    if buttons: markup.add(*buttons)
    markup.add(InlineKeyboardButton("🔙 Back to Countries", callback_data=f"usr_s|{srv_id}"))
    text = (
        f"{emo('number')} <b>SELECT SERVER</b> {emo('number')}\n━━━━━━━━━━━━━━━━━━\n"
        f"{emo(srv_data['name'])} Service: <code>{html.escape(srv_data['name'])}</code>\n"
        f"{get_flag(cnt_data['name'])} Country: <code>{html.escape(cnt_data['name'])}</code>\n\n"
        f"Tap a server to allocate a number:"
    )
    safe_send(chat_id, text, markup, message_id)

def show_my_history(chat_id, uid, message_id=None):
    data = load_data()
    user = data.get("users", {}).get(str(uid), {})
    history = user.get("history", [])
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back to Services", callback_data="back_to_user_services"))
    if not history:
        text = f"{emo('history')} <b>MY OTP HISTORY</b>\n━━━━━━━━━━━━━━━━━━\nNo OTP history yet.\nGet a number to start!"
    else:
        text = f"{emo('history')} <b>MY LAST OTPs</b>\n━━━━━━━━━━━━━━━━━━\n"
        for i, h in enumerate(history[:10], 1):
            text += f"{i}. {emo(h.get('service'))} <code>{h.get('number')}</code> → <code>{h.get('otp')}</code> <i>({h.get('time')})</i>\n"
    safe_send(chat_id, text, markup, message_id)

def show_traffic_search(chat_id, message_id=None):
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Close", callback_data="close_menu"))
    text = (
        f"{emo('traffic')} <b>TRAFFIC CHECK</b> {emo('traffic')}\n━━━━━━━━━━━━━━━━━━\n"
        f"Type the service name to check live traffic\nExample: <code>WhatsApp</code>\n\n"
        f"📝 Note: Facebook = Instagram Range\nSend /cancel to stop"
    )
    if not message_id:
        msg = safe_send(chat_id, text, markup)
        if msg: bot.register_next_step_handler_by_chat_id(chat_id, process_api_traffic_search, msg.message_id)
    else:
        safe_send(chat_id, text, markup, message_id)
        bot.register_next_step_handler_by_chat_id(chat_id, process_api_traffic_search, message_id)

# ============================================================
#  Number Allocation Core (Controlled Loop System)
# ============================================================
def fetch_number(chat_id, service_info, msg_id, is_custom=False, retry=0):
    payload = {"range": service_info["range"], "format": "normal"}
    results = []

    active_panels = [p for p in PANELS if p["url"].startswith("http") and p.get("key")]

    for _ in range(NUMBER_ALLOCATION_COUNT):
        number_fetched = False
        for panel in active_panels:
            try:
                res = requests.post(
                    f"{panel['url']}/api/v1/numbers/get",
                    json=payload,
                    headers={"X-API-Key": panel["key"]},
                    timeout=7
                )
                data = res.json()
                if data.get("success") and data.get("number"):
                    results.append({
                        "number":     data.get("number"),
                        "number_id":  data.get("number_id"),
                        "panel_url":  panel["url"],
                        "panel_key":  panel["key"]
                    })
                    number_fetched = True
                    break
            except Exception as e:
                print(f"❌ [API ERROR] -> {e}")
                continue
        if not number_fetched: break

    final_numbers = results

    if not final_numbers:
        if retry < 1:
            time.sleep(1)
            fetch_number(chat_id, service_info, msg_id, is_custom, retry + 1)
            return
        markup = InlineKeyboardMarkup()
        if is_custom: markup.add(InlineKeyboardButton("❌ Close", callback_data="close_menu"))
        else: markup.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_user_services"))
        safe_send(chat_id, f"{emo('cross')} <b>Number out of stock in all panels.</b>", markup, msg_id)
        return

    data      = load_data()
    main_link = format_url(data.get("main_otp_link", "https://t.me/"))
    for _ in final_numbers: bump_stats(chat_id, "number")
    user_last_service_info[str(chat_id)] = service_info

    text   = f"{emo('number')} <b>Allocated {len(final_numbers)} Number(s)</b>"

    markup = InlineKeyboardMarkup(row_width=1)
    for num_data in final_numbers:
        num_str = f"+{str(num_data['number']).replace('+', '')}"
        if HAS_COPY_BTN: markup.add(InlineKeyboardButton(num_str, copy_text=CopyTextButton(text=num_str)))
        else: markup.add(InlineKeyboardButton(num_str, callback_data=f"copyn|{num_str}"))

    if is_custom:
        markup.add(InlineKeyboardButton("🔄 Change Number", callback_data=f"chgc|{service_info['range']}"))
    else:
        markup.add(InlineKeyboardButton("🔄 Change Number", callback_data=f"usr_r|{service_info['srv_id']}|{service_info['cnt_id']}|{service_info['id']}"))
        markup.add(InlineKeyboardButton("🌍 Change Country", callback_data=f"usr_s|{service_info['srv_id']}"))

    markup.add(InlineKeyboardButton("🔔 OTP View / OTP Group ↗", url=main_link))
    safe_send(chat_id, text, markup, msg_id)
    make_poll_state(chat_id, [nd["number_id"] for nd in final_numbers])

    for num_data in final_numbers:
        threading.Thread(
            target=poll_user_otp,
            args=(chat_id, num_data["number_id"], service_info, num_data["number"], msg_id, is_custom, num_data["panel_url"], num_data["panel_key"]),
            daemon=True
        ).start()

def poll_user_otp(chat_id, num_id, service_info, allocated_number, msg_id, is_custom, panel_url, panel_key):
    start    = time.time()
    disp_num = f"+{str(allocated_number).replace('+', '')}"
    clean_num = str(allocated_number).replace("+", "")

    while time.time() - start < OTP_POLL_TIMEOUT:
        poll_state = active_polls.get(str(chat_id), {"active": False, "numbers": {}})
        if not poll_state.get("active", False) or not poll_state.get("numbers", {}).get(num_id, False): break

        try:
            r = requests.get(
                f"{panel_url}/api/v1/numbers/{num_id}/sms",
                headers={"X-API-Key": panel_key},
                timeout=10
            ).json()

            if r.get("success") and r.get("otp"):
                poll_state = active_polls.get(str(chat_id), {"active": False, "numbers": {}})
                if isinstance(poll_state, dict):
                    poll_state.setdefault("numbers", {})[num_id] = False

                otp_code  = r["otp"]
                flag      = get_flag(service_info["country_name"])
                now_str   = datetime.now().strftime("%H:%M:%S")

                bump_stats(chat_id, "otp")
                add_to_history(chat_id, {"service": service_info["service_name"], "number": disp_num, "otp": otp_code, "time": now_str})

                data      = load_data()
                main_link = format_url(data.get("main_otp_link", "https://t.me/"))

                success_text = f"{flag} {html.escape(service_info['service_name'])} <code>{clean_num}</code>"

                markup = InlineKeyboardMarkup(row_width=1)
                if HAS_COPY_BTN: markup.add(InlineKeyboardButton(f"📋 {otp_code}", copy_text=CopyTextButton(text=str(otp_code))))
                else: markup.add(InlineKeyboardButton(f"📋 {otp_code}", callback_data=f"copyn|{otp_code}"))

                nav_buttons = []
                if is_custom:
                    nav_buttons.append(InlineKeyboardButton("🔄 New Number", callback_data=f"chgc|{service_info['range']}"))
                    nav_buttons.append(InlineKeyboardButton("📨 OTP Group",  url=main_link))
                    markup.row(*nav_buttons)
                    markup.add(InlineKeyboardButton("❌ Close", callback_data="close_menu"))
                else:
                    nav_buttons.append(InlineKeyboardButton("🔄 New Number", callback_data=f"usr_r|{service_info['srv_id']}|{service_info['cnt_id']}|{service_info['id']}"))
                    nav_buttons.append(InlineKeyboardButton("📨 OTP Group",  url=main_link))
                    markup.row(*nav_buttons)
                    markup.add(InlineKeyboardButton("🔙 Back", callback_data=f"usr_c|{service_info['srv_id']}|{service_info['cnt_id']}"))

                safe_send(chat_id, success_text, markup)

                fwd_groups = data.get("forward_groups", [])
                for grp in fwd_groups:
                    try:
                        grp_id_fwd = grp.get("chat_id")
                        if not grp_id_fwd: continue
                        otp_markup = build_group_forward_markup(grp, otp_code, main_link)
                        bot.send_message(int(grp_id_fwd), success_text, reply_markup=otp_markup, parse_mode="HTML")
                    except Exception as fwd_err:
                        print(f"[FWD] Group forward error ({grp.get('chat_id')}): {fwd_err}")
                return
        except: pass
        time.sleep(1)

    poll_state = active_polls.get(str(chat_id), {"active": False, "numbers": {}})
    if poll_state.get("active", False) and poll_state.get("numbers", {}).get(num_id, False):
        poll_state["numbers"][num_id] = False
        markup = InlineKeyboardMarkup()
        if is_custom: markup.add(InlineKeyboardButton("❌ Close", callback_data="close_menu"))
        else:         markup.add(InlineKeyboardButton("🔙 Back", callback_data="back_to_user_services"))
        safe_send(chat_id, f"{emo('time')} <b>Timeout!</b> No OTP received in 20 minutes.\nTry a different number.", markup)

# ============================================================
#  Admin Panel UI
# ============================================================
def get_admin_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🛠️ Manage Services",     callback_data="admin_manage_service"),
        InlineKeyboardButton("📢 Broadcast Message",    callback_data="admin_broadcast"),
        InlineKeyboardButton("🔗 Group Settings",       callback_data="admin_group_settings"),
        InlineKeyboardButton("📣 Force Join Settings",  callback_data="admin_force_join"),
    )
    return markup

def show_admin_panel(chat_id, message_id=None):
    data  = load_data()
    gs    = data.get("global_stats", {})
    today = today_str()
    td    = gs.get("daily", {}).get(today, {"otps": 0, "numbers": 0})
    text  = (
        f"{emo('crown')} <b>ADMIN PANEL</b> {emo('crown')}\n━━━━━━━━━━━━━━━━━━\n"
        f"📈 <b>TODAY</b> ({today})\n"
        f"🔢 Numbers: <code>{td['numbers']}</code>  🔐 OTPs: <code>{td['otps']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🌍 <b>Total All-Time</b>\n"
        f"🔢 Numbers: <code>{gs.get('total_numbers', 0)}</code>  🔐 OTPs: <code>{gs.get('total_otps', 0)}</code>\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    safe_send(chat_id, text, get_admin_menu(), message_id)

def get_force_join_menu():
    data        = load_data()
    is_enabled  = data.get("force_join_enabled", False)
    channels    = data.get("force_join_channels", [])
    status_text = "🟢 ENABLED" if is_enabled else "🔴 DISABLED"
    markup      = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton(f"Toggle: {status_text}", callback_data="toggle_force_join"))
    for idx, link in enumerate(channels):
        markup.add(InlineKeyboardButton(f"❌ Remove: {link}", callback_data=f"delfjc_{idx}"))
    markup.add(InlineKeyboardButton("➕ Add Channel",   callback_data="add_fjc"))
    markup.add(InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin"))
    return markup

def get_group_settings_menu():
    data    = load_data()
    markup  = InlineKeyboardMarkup(row_width=1)
    otp_link = data.get("main_otp_link", "")
    markup.add(InlineKeyboardButton("🔗 Set OTP Group Link", callback_data="set_main_otp_link"))
    if otp_link and otp_link != "https://t.me/":
        markup.add(InlineKeyboardButton("🗑️ Remove OTP Link", callback_data="del_main_otp_link"))
    markup.add(InlineKeyboardButton("➕ Add Forward Group", callback_data="add_fwd_group"))
    fwd_groups = data.get("forward_groups", [])
    if fwd_groups:
        markup.add(InlineKeyboardButton("── ADDED GROUPS ──", callback_data="ignore"))
        for grp in fwd_groups:
            btn_count = len(grp.get("buttons", []))
            markup.add(InlineKeyboardButton(f"⚙️ {grp['chat_id']} [{btn_count} Btns]", callback_data=f"editgrp_{grp['chat_id']}"))
    markup.add(InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin"))
    return markup

def show_admin_services(chat_id, message_id=None):
    data   = load_data()
    markup = InlineKeyboardMarkup(row_width=2)
    for srv_id, srv in data.get("services_data", {}).items():
        markup.add(InlineKeyboardButton(text=f"📁 {srv['name']}", callback_data=f"adm_s|{srv_id}"))
    markup.add(InlineKeyboardButton("➕ Add Service",   callback_data="add_srv"))
    markup.add(InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin"))
    safe_send(chat_id, f"{emo('gear')} <b>MANAGE SERVICES</b>\n━━━━━━━━━━━━━━━━━━\nSelect a service:", markup, message_id)

def show_admin_countries(chat_id, srv_id, message_id=None):
    data     = load_data()
    srv_data = data.get("services_data", {}).get(srv_id)
    if not srv_data: return
    markup   = InlineKeyboardMarkup(row_width=2)
    for cnt_id, cnt in srv_data.get("countries", {}).items():
        markup.add(InlineKeyboardButton(text=f"{get_flag(cnt['name'])} {cnt['name']}", callback_data=f"adm_c|{srv_id}|{cnt_id}"))
    markup.add(InlineKeyboardButton("➕ Add Country",    callback_data=f"add_cnt|{srv_id}"))
    markup.add(InlineKeyboardButton("🗑️ Delete Service", callback_data=f"del_srv|{srv_id}"))
    markup.add(InlineKeyboardButton("🔙 Back",           callback_data="admin_manage_service"))
    safe_send(chat_id, f"{emo('globe')} <b>Countries → {html.escape(srv_data['name'])}</b>\n━━━━━━━━━━━━━━━━━━\nSelect country:", markup, message_id)

def show_admin_ranges(chat_id, srv_id, cnt_id, message_id=None):
    data     = load_data()
    srv_data = data.get("services_data", {}).get(srv_id)
    cnt_data = srv_data.get("countries", {}).get(cnt_id) if srv_data else None
    if not cnt_data: return
    flag   = get_flag(cnt_data["name"])
    markup = InlineKeyboardMarkup(row_width=1)
    for rng_id, rng_val in cnt_data.get("ranges", {}).items():
        markup.add(InlineKeyboardButton(text=f"❌ {rng_val}", callback_data=f"del_rng|{srv_id}|{cnt_id}|{rng_id}"))
    markup.add(InlineKeyboardButton("➕ Add Range",       callback_data=f"add_rng|{srv_id}|{cnt_id}"))
    markup.add(InlineKeyboardButton("📥 Bulk Import",     callback_data=f"bulk_rng|{srv_id}|{cnt_id}"))
    markup.add(InlineKeyboardButton("🗑️ Delete Country",  callback_data=f"del_cnt|{srv_id}|{cnt_id}"))
    markup.add(InlineKeyboardButton("🔙 Back",            callback_data=f"adm_s|{srv_id}"))
    safe_send(chat_id, f"{flag} <b>Ranges → {html.escape(srv_data['name'])} → {html.escape(cnt_data['name'])}</b>\n━━━━━━━━━━━━━━━━━━\nTap ❌ to delete:", markup, message_id)

def show_edit_group_menu(chat_id, grp_id, message_id=None):
    data = load_data()
    grp  = next((g for g in data.get("forward_groups", []) if str(g["chat_id"]) == str(grp_id)), None)
    if not grp:
        safe_send(chat_id, f"{emo('link')} <b>Group Settings</b>", get_group_settings_menu(), message_id)
        return
    text   = f"⚙️ <b>MANAGE GROUP</b>\n━━━━━━━━━━━━━━━━━━\n📱 Chat ID: <code>{grp_id}</code>\n🔘 Buttons: {len(grp.get('buttons', []))}"
    markup = InlineKeyboardMarkup(row_width=1)
    for idx, btn in enumerate(grp.get("buttons", [])):
        markup.add(InlineKeyboardButton(f"❌ {btn['name']}", callback_data=f"delgrpbtn_{grp_id}_{idx}"))
    markup.add(InlineKeyboardButton("➕ Add Button",  callback_data=f"addgrpbtn_{grp_id}"))
    markup.add(InlineKeyboardButton("🗑️ Delete Group", callback_data=f"delfwd_{grp_id}"))
    markup.add(InlineKeyboardButton("🔙 Back",         callback_data="admin_group_settings"))
    safe_send(chat_id, text, markup, message_id)

# ============================================================
#  Command Handlers
# ============================================================
@bot.message_handler(commands=["start"])
def start_cmd(m):
    uid = m.from_user.id
    register_user(m.from_user)
    if is_banned(uid):
        bot.send_message(m.chat.id, f"{emo('ban')} <b>You are banned from using this bot.</b>", parse_mode="HTML")
        return
    data = load_data()
    if not check_force_join(uid):
        markup = InlineKeyboardMarkup()
        for link in data.get("force_join_channels", []):
            markup.add(InlineKeyboardButton("📢 Join Channel", url=link))
        markup.add(InlineKeyboardButton("✅ I've Joined", callback_data="check_join"))
        bot.send_message(m.chat.id, f"{emo('warning')} <b>Please join our channel first!</b>", reply_markup=markup, parse_mode="HTML")
        return

    welcome_text = (
        f"{emo('hi')} <b>Welcome to THE WHITE X Bot!</b>\n\n"
        f"🔐 Get virtual numbers & receive OTPs instantly\n"
        f"📊 Check live traffic for any service\n\n"
        f"Use the buttons below to get started."
    )
    main_kbd = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    main_kbd.add(KeyboardButton("📱 GET NUMBER"), KeyboardButton("📊 TRAFFIC"))
    main_kbd.add(KeyboardButton("New Number 🔁"))
    if is_admin(uid): main_kbd.add(KeyboardButton("⚙️ ADMIN PANEL"))
    bot.send_message(m.chat.id, welcome_text, reply_markup=main_kbd, parse_mode="HTML")

@bot.message_handler(commands=["help"])
def help_cmd(m):
    text = (
        f"{emo('info')} <b>BOT COMMANDS</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"📱 <b>GET NUMBER</b> — Get a virtual number\n"
        f"📊 <b>TRAFFIC</b> — Check live OTP traffic\n"
        f"📋 <b>MY HISTORY</b> — View your OTP history\n"
        f"🔁 <b>New Number 🔁</b> — Last range থেকে নতুন number নাও\n"
        f"/start — Restart the bot\n/help — Show this help\n/cancel — Cancel current operation\n"
        f"━━━━━━━━━━━━━━━━━━\n💡 <b>Tips:</b>\n"
        f"• Use Custom Search to enter any range manually\n"
        f"• Traffic Check shows which ranges have active OTPs\n"
        f"• New Number 🔁 instantly reuses your last range!"
    )
    bot.send_message(m.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=["cancel"])
def cancel_cmd(m):
    bot.clear_step_handler_by_chat_id(m.chat.id)
    cancel_poll_state(m.chat.id)
    bot.send_message(m.chat.id, f"{emo('cross')} <b>Cancelled.</b>", parse_mode="HTML")

@bot.message_handler(func=lambda m: True)
def text_handler(m):
    uid = m.from_user.id
    register_user(m.from_user)
    if is_banned(uid): return
    if not check_force_join(uid): return
    t = m.text

    if t == "📱 GET NUMBER": show_user_services(m.chat.id)
    elif t == "📊 TRAFFIC": show_traffic_search(m.chat.id)
    elif t == "⚙️ ADMIN PANEL" and is_admin(uid): show_admin_panel(m.chat.id)
    elif t == "New Number 🔁":
        last_info = user_last_service_info.get(str(uid))
        if not last_info:
            bot.send_message(m.chat.id, f"{emo('warning')} <b>কোনো পূর্বের range নেই!</b>\nপ্রথমে 📱 GET NUMBER থেকে একটি number নিন।", parse_mode="HTML")
            return
        now  = time.time()
        last = number_cooldowns.get(uid, 0)
        if now - last < NUMBER_FETCH_COOLDOWN:
            wait = int(NUMBER_FETCH_COOLDOWN - (now - last))
            bot.send_message(m.chat.id, f"{emo('time')} <b>⏳ {wait} সেকেন্ড অপেক্ষা করুন...</b>", parse_mode="HTML")
            return
        number_cooldowns[uid] = now
        cancel_poll_state(m.chat.id)
        is_custom = last_info.get("srv_id") is None
        
        # 🌟 সমাধানের অংশ: ইউজার ইন্টারফেসে র (raw) রেঞ্জ টেক্সট হাইড করা হয়েছে
        sent = bot.send_message(
            m.chat.id,
            f"{emo('waiting')} <b>নতুন number নেওয়া হচ্ছে...</b>\n📡 Service: <code>{html.escape(str(last_info.get('service_name', '')))}</code>",
            parse_mode="HTML"
        )
        threading.Thread(target=fetch_number, args=(m.chat.id, last_info, sent.message_id, is_custom), daemon=True).start()

# ============================================================
#  Callback Query Handler
# ============================================================
@bot.callback_query_handler(func=lambda c: True)
def query_handler(c):
    try: bot.answer_callback_query(c.id)
    except: pass
    bot.clear_step_handler_by_chat_id(c.message.chat.id)

    chat_id  = c.message.chat.id
    msg_id   = c.message.message_id
    user_id  = c.from_user.id
    data     = load_data()

    if is_banned(user_id): return
    if c.data in ("ignore", "none"): return
    if c.data == "close_menu":
        try: bot.delete_message(chat_id, msg_id)
        except: pass
        return

    if c.data == "check_join":
        if check_force_join(user_id):
            try: bot.delete_message(chat_id, msg_id)
            except: pass
            start_cmd(c.message)
        else:
            bot.answer_callback_query(c.id, "❌ Please join all channels first!", show_alert=True)
        return

    ADMIN_CALLBACKS = {
        "admin_broadcast", "admin_group_settings", "admin_force_join",
        "toggle_force_join", "add_fjc", "back_to_admin", "admin_manage_service",
        "set_main_otp_link", "del_main_otp_link", "add_fwd_group"
    }
    ADMIN_PREFIXES = ("adm_", "add_", "del_", "editgrp_", "addgrpbtn_", "delgrpbtn_", "delfwd_", "delfjc_", "bulk_rng|")
    is_admin_action = (c.data in ADMIN_CALLBACKS or any(c.data.startswith(p) for p in ADMIN_PREFIXES))
    if is_admin_action and not is_admin(user_id):
        safe_send(chat_id, f"{emo('warning')} <b>Access Denied!</b>", None, msg_id)
        return

    USER_PREFIXES = ("usr_s|", "usr_c|", "usr_r|", "chgc|")
    if (c.data in {"back_to_user_services", "find_number", "my_history"} or any(c.data.startswith(p) for p in USER_PREFIXES)):
        if not check_force_join(user_id): return

    if c.data == "back_to_user_services":
        cancel_poll_state(chat_id)
        show_user_services(chat_id, msg_id)

    elif c.data == "my_history": show_my_history(chat_id, user_id, msg_id)
    elif c.data.startswith("usr_s|"): show_user_countries(chat_id, c.data.split("|")[1], msg_id)
    elif c.data.startswith("copyn|"):
        num = c.data.split("|", 1)[1]
        try: 
            bot.answer_callback_query(c.id, text="📋 Sending copyable text...")
            bot.send_message(chat_id, f"<code>{num}</code>\n▲ ট্যাপ করে কপি করুন", parse_mode="HTML")
        except: pass

    elif c.data.startswith("usr_c|"):
        _, srv_id, cnt_id = c.data.split("|")
        show_user_ranges(chat_id, srv_id, cnt_id, msg_id)

    elif c.data == "find_number":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data="back_to_user_services"))
        safe_send(chat_id, f"{emo('note')} <b>Enter Custom Range:</b>\nExample: <code>99298XXX</code> or <code>8801</code>\n\nSend /cancel to stop", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, process_custom_range, msg_id)

    elif c.data.startswith("chgc|") or c.data.startswith("usr_r|"):
        is_custom = c.data.startswith("chgc|")
        if is_custom:
            custom_input = c.data.split("|")[1]
            service_info = {"id": f"custom_{custom_input}", "service_name": "Custom Search", "country_name": "Universal", "range": custom_input, "srv_id": None, "cnt_id": None}
        else:
            _, srv_id, cnt_id, rng_id = c.data.split("|")
            srv_data = data.get("services_data", {}).get(srv_id)
            cnt_data = srv_data.get("countries", {}).get(cnt_id) if srv_data else None
            rng_val  = cnt_data.get("ranges", {}).get(rng_id) if cnt_data else None
            if not rng_val: return
            service_info = {"id": rng_id, "srv_id": srv_id, "cnt_id": cnt_id, "service_name": srv_data["name"], "country_name": cnt_data["name"], "range": rng_val}

        now  = time.time()
        last = number_cooldowns.get(user_id, 0)
        if now - last < NUMBER_FETCH_COOLDOWN:
            wait = int(NUMBER_FETCH_COOLDOWN - (now - last))
            bot.answer_callback_query(c.id, f"⏳ Please wait {wait}s before getting another number.", show_alert=True)
            return
        number_cooldowns[user_id] = now
        cancel_poll_state(chat_id)
        msg_obj = safe_send(chat_id, f"{emo('waiting')} <b>Allocating number...</b>", None, msg_id)
        if msg_obj: threading.Thread(target=fetch_number, args=(chat_id, service_info, msg_obj.message_id, is_custom), daemon=True).start()

    elif c.data == "back_to_admin": show_admin_panel(chat_id, msg_id)
    elif c.data == "admin_manage_service": show_admin_services(chat_id, msg_id)
    elif c.data == "admin_group_settings": safe_send(chat_id, f"{emo('link')} <b>GROUP SETTINGS</b>\n━━━━━━━━━━━━━━━━━━\nManage forward groups and OTP link:", get_group_settings_menu(), msg_id)
    elif c.data == "admin_force_join": safe_send(chat_id, f"{emo('mega')} <b>FORCE JOIN SETTINGS</b>\n━━━━━━━━━━━━━━━━━━", get_force_join_menu(), msg_id)
    elif c.data == "toggle_force_join":
        data["force_join_enabled"] = not data.get("force_join_enabled", False)
        save_data(data)
        safe_send(chat_id, f"{emo('mega')} <b>FORCE JOIN SETTINGS</b>\n━━━━━━━━━━━━━━━━━━", get_force_join_menu(), msg_id)

    elif c.data == "add_fjc":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data="admin_force_join"))
        safe_send(chat_id, f"{emo('link')} Send Channel Link (t.me/...):", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, process_set_force_join_link, msg_id)

    elif c.data.startswith("delfjc_"):
        idx      = int(c.data.split("_")[1])
        channels = data.get("force_join_channels", [])
        if 0 <= idx < len(channels):
            channels.pop(idx)
            save_data(data)
        safe_send(chat_id, f"{emo('mega')} <b>FORCE JOIN SETTINGS</b>\n━━━━━━━━━━━━━━━━━━", get_force_join_menu(), msg_id)

    elif c.data == "add_srv":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data="admin_manage_service"))
        safe_send(chat_id, f"{emo('message')} <b>Send Service Name:</b>", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, process_add_srv, msg_id)

    elif c.data.startswith("adm_s|"): show_admin_countries(chat_id, c.data.split("|")[1], msg_id)
    elif c.data.startswith("add_cnt|"):
        srv_id = c.data.split("|")[1]
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data=f"adm_s|{srv_id}"))
        safe_send(chat_id, f"{emo('globe')} <b>Send Country Name:</b>", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, process_add_cnt, srv_id, msg_id)

    elif c.data.startswith("adm_c|"):
        _, srv_id, cnt_id = c.data.split("|")
        show_admin_ranges(chat_id, srv_id, cnt_id, msg_id)

    elif c.data.startswith("add_rng|"):
        _, srv_id, cnt_id = c.data.split("|")
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data=f"adm_c|{srv_id}|{cnt_id}"))
        safe_send(chat_id, f"{emo('number')} <b>Send Range:</b>\n<i>Example: 8801, 99298XXX</i>", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, process_add_rng, srv_id, cnt_id, msg_id)

    elif c.data.startswith("bulk_rng|"):
        _, srv_id, cnt_id = c.data.split("|")
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data=f"adm_c|{srv_id}|{cnt_id}"))
        safe_send(chat_id, f"{emo('package')} <b>Bulk Import Ranges</b>\nSend multiple ranges, one per line:\n\n<code>8801\n8802\n99298XXX</code>", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, process_bulk_rng, srv_id, cnt_id, msg_id)

    elif c.data.startswith("del_srv|"):
        srv_id = c.data.split("|")[1]
        if srv_id in data.get("services_data", {}):
            del data["services_data"][srv_id]
            save_data(data)
        show_admin_services(chat_id, msg_id)

    elif c.data.startswith("del_cnt|"):
        _, srv_id, cnt_id = c.data.split("|")
        try:
            del data["services_data"][srv_id]["countries"][cnt_id]
            save_data(data)
        except: pass
        show_admin_countries(chat_id, srv_id, msg_id)

    elif c.data.startswith("del_rng|"):
        _, srv_id, cnt_id, rng_id = c.data.split("|")
        try:
            del data["services_data"][srv_id]["countries"][cnt_id]["ranges"][rng_id]
            save_data(data)
        except: pass
        show_admin_ranges(chat_id, srv_id, cnt_id, msg_id)

    elif c.data == "set_main_otp_link":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data="admin_group_settings"))
        safe_send(chat_id, f"{emo('link')} Send OTP Group URL:", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, process_main_otp_link, msg_id)

    elif c.data == "del_main_otp_link":
        data["main_otp_link"] = "https://t.me/"
        save_data(data)
        time.sleep(0.5)
        safe_send(chat_id, f"{emo('link')} <b>Group Settings</b>", get_group_settings_menu(), msg_id)

    elif c.data == "add_fwd_group":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data="admin_group_settings"))
        safe_send(chat_id, f"{emo('plus')} Send Group/Channel Chat ID:", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, step1_add_fwd_group, msg_id)

    elif c.data.startswith("editgrp_"):
        grp_id = c.data[len("editgrp_"):]
        show_edit_group_menu(chat_id, grp_id, msg_id)

    elif c.data.startswith("addgrpbtn_"):
        grp_id = c.data[len("addgrpbtn_"):]
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data=f"editgrp_{grp_id}"))
        safe_send(chat_id, f"{emo('note')} Send Button Name:", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, step_addgrpbtn_name, grp_id, msg_id)

    elif c.data.startswith("delgrpbtn_"):
        parts   = c.data[len("delgrpbtn_"):].rsplit("_", 1)
        grp_id  = parts[0]
        btn_idx = int(parts[1])
        for g in data.get("forward_groups", []):
            if str(g["chat_id"]) == str(grp_id):
                if 0 <= btn_idx < len(g.get("buttons", [])): g["buttons"].pop(btn_idx)
                break
        save_data(data)
        show_edit_group_menu(chat_id, grp_id, msg_id)

    elif c.data.startswith("delfwd_"):
        grp_id = c.data[len("delfwd_"):]
        data["forward_groups"] = [g for g in data.get("forward_groups", []) if str(g["chat_id"]) != str(grp_id)]
        save_data(data)
        time.sleep(0.5)
        safe_send(chat_id, f"{emo('link')} <b>Group Settings</b>", get_group_settings_menu(), msg_id)

    elif c.data == "admin_broadcast":
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data="back_to_admin"))
        safe_send(chat_id, f"{emo('message')} Send message to broadcast to all users:", markup, msg_id)
        bot.register_next_step_handler_by_chat_id(chat_id, process_broadcast, msg_id)

# ============================================================
#  User Step Processing
# ============================================================
def process_custom_range(message, msg_id):
    if message.text == "/cancel":
        try: bot.edit_message_text(f"{emo('cross')} <b>Cancelled.</b>", message.chat.id, msg_id, parse_mode="HTML")
        except: pass
        return
    custom_input = message.text.strip()
    service_info = {"id": f"custom_{custom_input}", "service_name": "Custom Search", "country_name": "Universal", "range": custom_input, "srv_id": None, "cnt_id": None}
    cancel_poll_state(message.chat.id)

    now  = time.time()
    last = number_cooldowns.get(message.from_user.id, 0)
    if now - last < NUMBER_FETCH_COOLDOWN:
        wait = int(NUMBER_FETCH_COOLDOWN - (now - last))
        safe_send(message.chat.id, f"{emo('time')} <b>Wait {wait}s before getting another number.</b>", None, msg_id)
        return
    number_cooldowns[message.from_user.id] = now
    safe_send(message.chat.id, f"{emo('waiting')} <b>Allocating number...</b>", None, msg_id)
    threading.Thread(target=fetch_number, args=(message.chat.id, service_info, msg_id, True), daemon=True).start()

def process_api_traffic_search(message, msg_id):
    if message.text == "/cancel":
        try: bot.edit_message_text(f"{emo('cross')} <b>Cancelled.</b>", message.chat.id, msg_id, parse_mode="HTML")
        except: pass
        return
    uid = message.from_user.id
    now = time.time()
    if uid in traffic_cooldowns and now - traffic_cooldowns[uid] < TRAFFIC_COOLDOWN:
        wait = int(TRAFFIC_COOLDOWN - (now - traffic_cooldowns[uid]))
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Close", callback_data="close_menu"))
        safe_send(message.chat.id, f"{emo('time')} <b>Wait {wait}s before checking again.</b>", markup, msg_id)
        return
    traffic_cooldowns[uid] = now
    service_query = message.text.strip().lower()
    safe_send(message.chat.id, f"{emo('waiting')} <b>Checking live traffic...</b>", None, msg_id)

    def check_traffic():
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("❌ Close", callback_data="close_menu"))
        ranges = {}
        data   = load_data()
        for srv in data.get("services_data", {}).values():
            if service_query in str(srv.get("name", "")).lower():
                for cnt in srv.get("countries", {}).values():
                    for rng in cnt.get("ranges", {}).values():
                        if rng not in ranges: ranges[rng] = {"count": 1, "country": cnt.get("name", "Unknown")}

        target_panel = next((p for p in PANELS if p["url"].startswith("http")), None)
        if target_panel:
            try:
                headers  = {"X-API-Key": target_panel["key"], "Cache-Control": "no-cache"}
                response = requests.get(f"{target_panel['url']}/api/v1/console/logs?limit=200", headers=headers, timeout=10).json()
                if response.get("success") and response.get("data"):
                    for item in response["data"]:
                        sms_text = str(item.get("sms", ""))
                        app_name = str(item.get("app_name", ""))
                        country  = str(item.get("country", "Unknown"))
                        num      = str(item.get("number", ""))
                        detected = detect_service_from_sms(sms_text, app_name)
                        if service_query in detected and len(num) > 7:
                            rng_pattern = num[:7] + "XXX"
                            if rng_pattern not in ranges: ranges[rng_pattern] = {"count": 1, "country": country}
                            else: ranges[rng_pattern]["count"] += 1
            except: pass

        if ranges:
            sorted_ranges = sorted(ranges.items(), key=lambda x: x[1]["count"], reverse=True)
            res_text = f"{emo('traffic')} <b>Top Ranges for {html.escape(service_query.title())}:</b>\n━━━━━━━━━━━━━━━━━━\n"
            for rng, details in sorted_ranges[:15]:
                flag    = get_flag(details["country"])
                bar_len = min(details["count"], 10)
                bar     = "█" * bar_len + "░" * (10 - bar_len)
                res_text += f"{flag} <code>{rng}</code> {bar} {details['count']} OTPs\n"
            res_text += f"\n{emo('note')} Copy a range → use in Custom Search!"
        else:
            res_text = f"{emo('cross')} <b>No active traffic found for '{html.escape(service_query)}'.</b>"
        safe_send(message.chat.id, res_text, markup, msg_id)

    threading.Thread(target=check_traffic, daemon=True).start()

# ============================================================
#  Admin Step Processing
# ============================================================
def process_set_force_join_link(message, msg_id):
    if message.text == "/cancel":
        safe_send(message.chat.id, f"{emo('mega')} <b>FORCE JOIN SETTINGS</b>", get_force_join_menu(), msg_id)
        return
    data = load_data()
    data.setdefault("force_join_channels", []).append(format_url(message.text.strip()))
    save_data(data)
    time.sleep(0.5)
    safe_send(message.chat.id, f"{emo('mega')} <b>FORCE JOIN SETTINGS</b>", get_force_join_menu(), msg_id)

def process_add_srv(message, msg_id):
    if message.text == "/cancel": return show_admin_services(message.chat.id, msg_id)
    data   = load_data()
    srv_id = "s_" + str(uuid.uuid4())[:8]
    data.setdefault("services_data", {})[srv_id] = {"name": message.text.strip(), "countries": {}}
    save_data(data)
    show_admin_services(message.chat.id, msg_id)

def process_add_cnt(message, srv_id, msg_id):
    if message.text == "/cancel": return show_admin_countries(message.chat.id, srv_id, msg_id)
    data   = load_data()
    cnt_id = "c_" + str(uuid.uuid4())[:8]
    if srv_id in data.get("services_data", {}):
        data["services_data"][srv_id]["countries"][cnt_id] = {"name": message.text.strip(), "ranges": {}}
        save_data(data)
    show_admin_countries(message.chat.id, srv_id, msg_id)

def process_add_rng(message, srv_id, cnt_id, msg_id):
    if message.text == "/cancel": return show_admin_ranges(message.chat.id, srv_id, cnt_id, msg_id)
    data   = load_data()
    rng_id = "r_" + str(uuid.uuid4())[:8]
    try:
        data["services_data"][srv_id]["countries"][cnt_id]["ranges"][rng_id] = message.text.strip()
        save_data(data)
    except: pass
    show_admin_ranges(message.chat.id, srv_id, cnt_id, msg_id)

def process_bulk_rng(message, srv_id, cnt_id, msg_id):
    if message.text == "/cancel": return show_admin_ranges(message.chat.id, srv_id, cnt_id, msg_id)
    data  = load_data()
    lines = [l.strip() for l in message.text.strip().splitlines() if l.strip()]
    added = 0
    try:
        for line in lines:
            rng_id = "r_" + str(uuid.uuid4())[:8]
            data["services_data"][srv_id]["countries"][cnt_id]["ranges"][rng_id] = line
            added += 1
        save_data(data)
    except: pass
    safe_send(message.chat.id, f"{emo('done')} <b>Added {added} ranges!</b>", None, msg_id)
    time.sleep(0.5)
    show_admin_ranges(message.chat.id, srv_id, cnt_id, msg_id)

def step1_add_fwd_group(message, msg_id):
    if message.text == "/cancel":
        safe_send(message.chat.id, f"{emo('link')} <b>Group Settings</b>", get_group_settings_menu(), msg_id)
        return
    data   = load_data()
    new_id = message.text.strip()
    data.setdefault("forward_groups", []).append({"chat_id": new_id, "buttons": []})
    save_data(data)
    time.sleep(0.5)
    safe_send(message.chat.id, f"{emo('link')} <b>Group Settings</b>", get_group_settings_menu(), msg_id)

def step_addgrpbtn_name(message, grp_id, msg_id):
    if message.text == "/cancel":
        show_edit_group_menu(message.chat.id, grp_id, msg_id)
        return
    user_states[message.chat.id] = {"grp_id": grp_id, "btn_name": message.text.strip()}
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Cancel", callback_data=f"editgrp_{grp_id}"))
    safe_send(message.chat.id, f"{emo('link')} Send Button URL:", markup, msg_id)
    bot.register_next_step_handler_by_chat_id(message.chat.id, step_addgrpbtn_url, msg_id)

def step_addgrpbtn_url(message, msg_id):
    if message.text == "/cancel":
        grp_id = user_states.get(message.chat.id, {}).get("grp_id")
        if grp_id: show_edit_group_menu(message.chat.id, grp_id, msg_id)
        return
    state    = user_states.get(message.chat.id, {})
    grp_id   = state.get("grp_id")
    btn_name = state.get("btn_name")
    btn_url  = format_url(message.text.strip())
    data     = load_data()
    for grp in data.get("forward_groups", []):
        if str(grp["chat_id"]) == str(grp_id):
            grp.setdefault("buttons", []).append({"name": btn_name, "url": btn_url})
            break
    save_data(data)
    time.sleep(0.5)
    show_edit_group_menu(message.chat.id, grp_id, msg_id)

def process_main_otp_link(message, msg_id):
    if message.text == "/cancel":
        safe_send(message.chat.id, f"{emo('link')} <b>Group Settings</b>", get_group_settings_menu(), msg_id)
        return
    data = load_data()
    data["main_otp_link"] = format_url(message.text.strip())
    save_data(data)
    time.sleep(0.5)
    safe_send(message.chat.id, f"{emo('link')} <b>Group Settings</b>", get_group_settings_menu(), msg_id)

def run_broadcast(chat_id, original_message, msg_id):
    data    = load_data()
    users   = list(data.get("users", {}).keys())
    success = 0
    failed  = 0
    for u in users:
        try:
            bot.copy_message(chat_id=int(u), from_chat_id=chat_id, message_id=original_message.message_id)
            success += 1
            time.sleep(0.05)
        except:
            failed += 1
    markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 Back to Admin", callback_data="back_to_admin"))
    report = (
        f"{emo('mega')} <b>Broadcast Complete!</b>\n━━━━━━━━━━━━━━━━━━\n"
        f"{emo('done')} Sent:   <code>{success}</code>\n"
        f"{emo('cross')} Failed: <code>{failed}</code>\n"
        f"Total:  <code>{len(users)}</code>"
    )
    safe_send(chat_id, report, markup, msg_id)

def process_broadcast(message, msg_id):
    if message.text == "/cancel": return show_admin_panel(message.chat.id, msg_id)
    safe_send(message.chat.id, f"{emo('waiting')} <b>Broadcasting to all users...</b>", None, msg_id)
    threading.Thread(target=run_broadcast, args=(message.chat.id, message, msg_id), daemon=True).start()

# ============================================================
#  Auto Live Range Updater — individual group forward per range
# ============================================================
def auto_update_ranges_worker():
    global last_forwarded_ranges

    while True:
        try:
            active_panel = next((p for p in PANELS if p["url"].startswith("http")), None)
            if not active_panel:
                time.sleep(RANGE_UPDATE_INTERVAL)
                continue

            headers  = {"X-API-Key": active_panel["key"], "Cache-Control": "no-cache"}
            response = requests.get(
                f"{active_panel['url']}/api/v1/console/logs?limit=200",
                headers=headers,
                timeout=15
            ).json()

            if response.get("success") and response.get("data"):
                live_ranges          = defaultdict(lambda: defaultdict(set))
                new_range_entries    = []
                ranges_added_this_cycle = set()

                for item in response["data"]:
                    sms_text = str(item.get("sms", ""))
                    app_name = str(item.get("app_name", ""))
                    country  = str(item.get("country", "Unknown")).title()
                    num      = str(item.get("number", ""))

                    detected = detect_service_from_sms(sms_text, app_name)

                    if detected in TARGET_SERVICES and len(num) > 7:
                        rng_pattern = num[:7] + "XXX"
                        live_ranges[detected][country].add(rng_pattern)

                        flat_key = f"{detected}|{country}|{rng_pattern}"
                        current_time = time.time()
                        
                        # 🌟 সমাধানের অংশ: ৫ মিনিটের স্মার্ট কুলডাউন ট্র্যাকিং (ফ্রিজিং বাগ ফিক্সড)
                        if flat_key not in ranges_added_this_cycle:
                            if flat_key not in last_forwarded_ranges or (current_time - last_forwarded_ranges[flat_key] > RANGE_FORWARD_COOLDOWN):
                                new_range_entries.append((detected, country, rng_pattern))
                                last_forwarded_ranges[flat_key] = current_time
                                ranges_added_this_cycle.add(flat_key)

                # ── Forward each NEW range individually to all groups ──
                if new_range_entries:
                    data       = load_data()
                    fwd_groups = data.get("forward_groups", [])
                    watermark  = data.get("watermark", "THE white x")
                    bot_link   = format_url(data.get("main_otp_link", "https://t.me/"))

                    for (srv_name, country_name, rng_pattern) in new_range_entries:
                        forward_range_to_groups(fwd_groups, watermark, srv_name, country_name, rng_pattern, bot_link)
                        time.sleep(0.4)

                data          = load_data()
                services_data = data.setdefault("services_data", {})
                srv_map = {srv["name"].lower(): srv_id for srv_id, srv in services_data.items()}

                for target in TARGET_SERVICES:
                    if target not in srv_map:
                        new_srv_id = "s_" + str(uuid.uuid4())[:8]
                        services_data[new_srv_id] = {"name": target.capitalize(), "countries": {}}
                        srv_map[target] = new_srv_id
                        print(f"🆕 Auto-created service: {target.capitalize()}")

                added_count  = 0
                removed_count = 0

                for target in TARGET_SERVICES:
                    srv_id = srv_map.get(target)
                    if not srv_id: continue
                    srv_obj = services_data[srv_id]

                    live_for_service = {cnt_name.lower(): rng_set for cnt_name, rng_set in live_ranges.get(target, {}).items()}
                    cnt_map = {cnt["name"].lower(): cnt_id for cnt_id, cnt in srv_obj.get("countries", {}).items()}

                    for cnt_name, ranges_set in live_ranges.get(target, {}).items():
                        cnt_key = cnt_name.lower()
                        if cnt_key not in cnt_map:
                            new_cnt_id = "c_" + str(uuid.uuid4())[:8]
                            srv_obj["countries"][new_cnt_id] = {"name": cnt_name, "ranges": {}}
                            cnt_map[cnt_key] = new_cnt_id

                        cnt_id       = cnt_map[cnt_key]
                        existing_map = srv_obj["countries"][cnt_id]["ranges"]
                        existing_vals = set(existing_map.values())

                        for r_val in ranges_set:
                            if r_val not in existing_vals:
                                r_id = "r_" + str(uuid.uuid4())[:8]
                                existing_map[r_id] = r_val
                                existing_vals.add(r_val)
                                added_count += 1

                    for cnt_key, cnt_id in list(cnt_map.items()):
                        live_set = live_for_service.get(cnt_key, set())
                        rng_map  = srv_obj["countries"][cnt_id]["ranges"]
                        dead_ids = [rid for rid, rval in rng_map.items() if rval not in live_set]
                        for rid in dead_ids:
                            del rng_map[rid]
                            removed_count += 1
                        if not rng_map and cnt_key not in live_for_service: del srv_obj["countries"][cnt_id]
                save_data(data)
                print(f"✅ Cycle done — +{added_count} added, -{removed_count} removed")
        except Exception as e: print(f"❌ Auto Update Error: {e}")
        time.sleep(RANGE_UPDATE_INTERVAL)

# ============================================================
#  Start
# ============================================================
if __name__ == "__main__":
    bot.remove_webhook()
    time.sleep(1)
    print("👑 ADVANCED BOT MULTI-PANEL v8.3 — LIVE (Individual Range Forward)")

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    auto_update_thread = threading.Thread(target=auto_update_ranges_worker)
    auto_update_thread.daemon = True
    auto_update_thread.start()

    bot.infinity_polling(timeout=30, long_polling_timeout=15)
