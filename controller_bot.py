# controller_bot.py

import asyncio
from telethon import TelegramClient, events

from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from storage import load_map, save_map, remove_map
from logger import log, start_log, append_log, send_log

# 🔥 USERBOT FUNCTIONS (MATCHING user_worker.py)
from user_worker import (
    start_worker,
    trigger_bot,
    start_dm_watch_for,
    get_last_channel_message,
    extract_bot_and_payload
)

# ================= BOT CLIENT =================

bot = TelegramClient(
    "controller_bot",
    API_ID,
    API_HASH
).start(bot_token=BOT_TOKEN)

USERBOT_STARTED = False


# ================= USERBOT CONTROL =================

@bot.on(events.NewMessage(pattern=r"^/start_worker$", from_users=OWNER_ID))
async def start_userbot(event):
    global USERBOT_STARTED

    if USERBOT_STARTED:
        await event.reply("⚠️ Userbot already running")
        return

    USERBOT_STARTED = True
    asyncio.create_task(start_worker())

    await event.reply("✅ Userbot STARTED")
    await send_log("👤 Userbot STARTED manually", bot)


# ================= MAPPING =================

@bot.on(events.NewMessage(pattern=r"^/add_map", from_users=OWNER_ID))
async def add_map_cmd(event):
    parts = event.text.split()
    if len(parts) != 3:
        await event.reply("Usage:\n/add_map <source_channel_id> <target_channel_id>")
        return

    _, source, target = parts
    data = load_map()
    data.setdefault(source, [])

    if target not in data[source]:
        data[source].append(target)
        save_map(data)

    await event.reply("✅ Mapping added")
    await send_log(f"➕ Mapping added: {source} → {target}", bot)


@bot.on(events.NewMessage(pattern=r"^/remove_map", from_users=OWNER_ID))
async def remove_map_cmd(event):
    parts = event.text.split()
    if len(parts) != 2:
        await event.reply("Usage:\n/remove_map <source_channel_id>")
        return

    source = parts[1]
    if remove_map(source):
        await event.reply("🗑 Mapping removed")
        await send_log(f"🗑 Mapping removed: {source}", bot)
    else:
        await event.reply("❌ Source not found")

@bot.on(events.NewMessage(pattern=r"^/check_all$", from_users=OWNER_ID))
async def check_all_channels(event):
    """
    Check ALL configured channels and report userbot access status.
    Output ONLY in DM.
    """

    await event.reply("🔍 Checking all configured channels...\nPlease wait ⏳")

    # Load mappings
    data = load_map()
    if not data:
        await event.reply("❌ No channels configured in mapping.")
        return

    # Import userbot client
    from user_worker import _ACTIVE_CLIENT as userbot

    if not userbot:
        await event.reply("❌ Userbot is NOT running.")
        return

    total = 0
    ok = 0
    failed = 0

    report = []
    report.append("📊 **CHECK ALL REPORT**\n")

    for source_channel in data.keys():
        total += 1
        report.append("━━━━━━━━━━━━━━━━━━")
        report.append(f"📺 **Channel ID:** `{source_channel}`")

        try:
            entity = await userbot.get_entity(int(source_channel))
            report.append(f"• Name: **{entity.title}**")
            report.append("• Access: ✅ READABLE")

            # Read last message
            msgs = await userbot.get_messages(int(source_channel), limit=1)

            if not msgs:
                report.append("• Last Message: ❌ NOT FOUND")
            else:
                msg = msgs[0]
                report.append(f"• Last Msg ID: `{msg.id}`")
                report.append(f"• Has Buttons: {'YES' if msg.buttons else 'NO'}")
                report.append(f"• Has Video: {'YES' if msg.video else 'NO'}")

            # Mode detection
            targets = data.get(source_channel, [])
            report.append(f"• Bot-Forward Mode: {'YES' if targets else 'NO'}")

            ok += 1

        except Exception as e:
            report.append("• Access: ❌ FAILED")
            report.append(f"• Reason: `{e}`")
            failed += 1

    report.append("━━━━━━━━━━━━━━━━━━")
    report.append("")
    report.append("📈 **SUMMARY**")
    report.append(f"• Total Channels : {total}")
    report.append(f"• Working        : {ok}")
    report.append(f"• Failed         : {failed}")

    await event.reply("\n".join(report))


@bot.on(events.NewMessage(pattern=r"^/list_map$", from_users=OWNER_ID))
async def list_map_cmd(event):
    data = load_map()
    if not data:
        await event.reply("❌ No mappings found")
        return

    text = "📌 **Mappings**\n\n"
    for s, t in data.items():
        text += f"`{s}` → {', '.join(t)}\n"

    await event.reply(text)


# ================= TEST COMMAND =================

@bot.on(events.NewMessage(pattern=r"^/test", from_users=OWNER_ID))
async def test_channel(event):
    parts = event.text.split(maxsplit=1)
    if len(parts) != 2:
        await event.reply("Usage:\n/test <source_channel_id>")
        return

    source = parts[1]
    job_id = f"TEST_{source}"

    try:
        msg = await get_last_channel_message(source)
    except Exception as e:
        await event.reply(f"❌ Channel read error:\n{e}")
        return

    buttons = extract_bot_and_payload(msg)
    if not buttons:
        await event.reply("❌ No bot payload buttons found in last post")
        return

    await start_log(
        job_id,
        f"🧪 **TEST MODE**\nChannel: `{source}`\nButtons detected: {len(buttons)}",
        bot
    )

    for bot_username, payload in buttons:
        await append_log(
            job_id,
            f"🤖 Triggering @{bot_username}  | payload={payload}",
            bot
        )
        await trigger_bot(bot_username, payload, source, job_id)
        await start_dm_watch_for(bot_username, source, job_id)

    await event.reply("✅ Test triggered. Check log channel for live updates.")


# ================= DEFAULT HELP =================

@bot.on(events.NewMessage(from_users=OWNER_ID))
async def help_cmd(event):
    await event.reply(
        "📖 **Commands**\n\n"
        "/start_worker – start userbot\n"
        "/add_map <source> <target>\n"
        "/check_all\n"
        "/remove_map <source>\n"
        "/list_map\n"
        "/test <source_channel_id>\n"
    )


# ================= RUN =================

log.info("Controller bot running")
bot.run_until_disconnected()
