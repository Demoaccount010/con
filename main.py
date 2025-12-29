import json, re, asyncio, os, sys, time
from pyrogram import Client, filters
from config import *

START_TIME = time.time()
EP_LOCK = asyncio.Lock()
MAX_EP_CACHE = 500

# ---------- LOAD ----------
def load_json(f, default):
    try:
        return json.load(open(f))
    except:
        return default

def save_json(f, d):
    json.dump(d, open(f, "w"), indent=2)

DATA = load_json("storage.json", {"enabled": True, "maps": {}})
LOGS = load_json("logs.json", {})

# ---------- CLIENTS ----------
bot = Client("bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)
user = Client(
    "user",
    session_string=open("user.session").read(),
    api_id=API_ID,
    api_hash=API_HASH
)

async def force_activate_channel(chat_id: int):
    try:
        # 1️⃣ Dialogs scan (THIS IS THE KEY)
        async for d in user.get_dialogs():
            if d.chat and d.chat.id == chat_id:
                return True

        # 2️⃣ Force dialog creation
        await user.send_chat_action(chat_id, "typing")
        await asyncio.sleep(1)

        # 3️⃣ Re-scan dialogs
        async for d in user.get_dialogs():
            if d.chat and d.chat.id == chat_id:
                return True

    except Exception as e:
        print("ACTIVATION FAIL:", e)

    return False


# ---------- FORCE ACCESS ----------
async def force_access(chat_id: int) -> bool:
    """
    Ensure userbot has dialog-level access to channel
    """
    try:
        # 1️⃣ Check existing dialogs (REAL truth)
        async for d in user.get_dialogs():
            if d.chat and d.chat.id == chat_id:
                return True

        # 2️⃣ Force dialog creation
        await user.send_chat_action(chat_id, "typing")
        await asyncio.sleep(1)

        # 3️⃣ Re-check dialogs
        async for d in user.get_dialogs():
            if d.chat and d.chat.id == chat_id:
                return True

    except Exception as e:
        print("FORCE_ACCESS ERROR:", e)

    return False


# ---------- UTIL ----------
def extract_episode(text: str):
    if not text:
        return "NA"

    t = re.sub(r'[\[\]\(\)\._\-]', ' ', text.lower())

    m = re.search(r'\[(\d{1,4})\]', t)
    if m:
        return m.group(1)

    patterns = [
        r's\d{1,2}\s*e(\d{1,4})',
        r'episode\s*[:\-]?\s*(\d{1,4})',
        r'\bep\s*(\d{1,4})',
        r'\be(\d{1,4})\b',
        r'\b(\d{1,3})\b',
    ]

    for p in patterns:
        m = re.search(p, t)
        if m:
            ep = int(m.group(1))
            if ep <= 2000:
                return str(ep)

    return "NA"

def extract_quality(text: str):
    for q in ["2160p", "1080p", "720p", "480p"]:
        if q in text.lower():
            return q.upper()
    return "Unknown"

def build_caption(text):
    text = re.sub(r'@\w+', REPLACE_AT, text or "")
    ep = extract_episode(text)
    q = extract_quality(text)

    return (
        f"**📟 Episode = {ep}**\n"
        f"**🎧 Language = {DEFAULT_LANGUAGE}**\n"
        f"**💿 Quality = {q}**\n"
        f"**━━━━━━━━━━━━━━━━━━**\n"
        f"**🔥 {REPLACE_AT} 🔥**"
    )

# ---------- LOG SYSTEM ----------
async def log_update(src_id: str, chat_title: str, event: str):
    src_id = str(src_id)
    data = LOGS.setdefault(src_id, {})
    data.setdefault("msg_id", None)
    data.setdefault("videos", 0)
    data.setdefault("ignored", 0)
    data.setdefault("duplicates", 0)
    data.setdefault("episodes", [])

    if event == "video":
        data["videos"] += 1
    elif event == "ignored":
        data["ignored"] += 1
    elif event == "duplicate":
        data["duplicates"] += 1

    text = (
        f"📡 **Channel Detected**\n\n"
        f"🏷 **Name:** {chat_title}\n"
        f"🆔 **ID:** `{src_id}`\n\n"
        f"🎬 **Videos:** {data['videos']}\n"
        f"🚫 **Ignored:** {data['ignored']}\n"
        f"♻️ **Duplicates:** {data['duplicates']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔥 **24×7 Active**"
    )

    try:
        if not data["msg_id"]:
            m = await bot.send_message(LOG_CHANNEL, text)
            data["msg_id"] = m.id
        else:
            await bot.edit_message_text(LOG_CHANNEL, data["msg_id"], text)
    except Exception as e:
        print("LOG ERROR:", e)

    save_json("logs.json", LOGS)

# ---------- BOT COMMANDS ----------
@bot.on_message(filters.private & filters.user(OWNER_ID))
async def commands(_, m):
    cmd = m.text.split()

    if cmd[0] == "/start":
        await m.reply(
            "🔥 **Hybrid Auto Forward System**\n\n"
            "/add source target1 target2\n"
            "/remove source\n"
            "/list\n"
            "/on /off\n"
            "/status\n"
            "/stats\n"
            "/restart"
        )

    elif cmd[0] == "/add":
        src = int(cmd[1])
        tgts = [int(x) for x in cmd[2:]]

        ok = await force_activate_channel(src)

        if not ok:
            return await m.reply("❌ Userbot cannot activate source channel")

        for t in tgts:
            await force_activate_channel(t)

        DATA["maps"][str(src)] = [str(x) for x in tgts]
        save_json("storage.json", DATA)

        await m.reply("✅ Source & Targets activated + added")


    elif cmd[0] == "/remove":
        DATA["maps"].pop(cmd[1], None)
        save_json("storage.json", DATA)
        await m.reply("❌ Source removed")

    elif cmd[0] == "/list":
        if not DATA["maps"]:
            return await m.reply("❌ No mappings found")

        text = "📋 **Channel Mapping & Access**\n\n"

        for src, tgts in DATA["maps"].items():
            src_id = int(src)

            # 🔥 FORCE ACCESS CHECK (REAL)
            has_access = await force_access(src_id)

            name = "Unknown"
            if has_access:
                try:
                    async for d in user.get_dialogs():
                        if d.chat and d.chat.id == src_id:
                            name = d.chat.title
                            break
                except:
                    pass

            text += (
                f"📡 **Source:** `{src}`\n"
                f"🏷 **Name:** {name}\n"
                f"👤 **Userbot:** {'✅ ACCESS' if has_access else '❌ NO ACCESS'}\n"
            )

            for t in tgts:
                text += f" └➤ 🎯 `{t}`\n"

            text += "━━━━━━━━━━━━━━━━━━\n"

        await m.reply(text)


    elif cmd[0] == "/on":
        DATA["enabled"] = True
        save_json("storage.json", DATA)
        await m.reply("🟢 Userbot ON")

    elif cmd[0] == "/off":
        DATA["enabled"] = False
        save_json("storage.json", DATA)
        await m.reply("🔴 Userbot OFF")

    elif cmd[0] == "/status":
        up = int(time.time() - START_TIME)
        await m.reply(
            f"📊 **Status**\n\n"
            f"Userbot: {'ON' if DATA['enabled'] else 'OFF'}\n"
            f"Sources: {len(DATA['maps'])}\n"
            f"Uptime: {up//3600}h {(up%3600)//60}m"
        )

    elif cmd[0] == "/stats":
        msg = "📈 **Stats**\n\n"
        for k, v in LOGS.items():
            msg += f"`{k}` → {v.get('videos',0)} vids | {v.get('duplicates',0)} dup\n"
        await m.reply(msg)

    elif cmd[0] == "/restart":
        await m.reply("♻️ Restarting...")
        save_json("storage.json", DATA)
        save_json("logs.json", LOGS)
        os._exit(1)

# ---------- DAILY SUMMARY ----------
async def daily_summary():
    while True:
        now = time.localtime()
        if now.tm_hour == 0 and now.tm_min == 0:
            v=i=d=0
            for x in LOGS.values():
                v+=x.get("videos",0)
                i+=x.get("ignored",0)
                d+=x.get("duplicates",0)

            await bot.send_message(
                OWNER_ID,
                f"📅 **Daily Summary**\n\n"
                f"🎬 Videos: `{v}`\n"
                f"🚫 Ignored: `{i}`\n"
                f"♻️ Duplicates: `{d}`"
            )
            await asyncio.sleep(60)
        await asyncio.sleep(30)

# ---------- USERBOT WATCHER ----------
@user.on_message(filters.channel)
async def watcher(_, m):
    if not DATA["enabled"]:
        return

    # ignore self posts
    if m.from_user and m.from_user.is_self:
        return

    src = str(m.chat.id)

    # build target set
    all_targets = set()
    for tgts in DATA["maps"].values():
        all_targets.update(tgts)

    # ignore target channels
    if src in all_targets:
        return

    # process only source
    if src not in DATA["maps"]:
        return

    if not m.video:
        await log_update(m.chat.id, m.chat.title, "ignored")
        return

    async with EP_LOCK:
        base = m.text or m.caption or ""
        ep = extract_episode(base)
        q = extract_quality(base)
        key = f"{ep}|{q}"

        data = LOGS.setdefault(src, {})
        data.setdefault("episodes", [])

        if ep != "NA" and key in data["episodes"]:
            await log_update(m.chat.id, m.chat.title, "duplicate")
            return

        caption = build_caption(base)

        for tgt in DATA["maps"][src]:
            await m.copy(int(tgt), caption=caption)

        data["episodes"].append(key)
        if len(data["episodes"]) > MAX_EP_CACHE:
            data["episodes"] = data["episodes"][-MAX_EP_CACHE:]

        save_json("logs.json", LOGS)
        await log_update(m.chat.id, m.chat.title, "video")

# ---------- AUTO RESTART ----------
async def start_all():
    await bot.start()
    await user.start()
    asyncio.create_task(daily_summary())
    print("🔥 SYSTEM RUNNING")

while True:
    try:
        asyncio.get_event_loop().run_until_complete(start_all())
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        time.sleep(5)
