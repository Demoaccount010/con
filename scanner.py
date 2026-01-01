import asyncio
from core.forwarder import forward_video
from utils.logger import log_scan
from utils.episode import extract_episode, is_episode_done, mark_episode_done
from utils.quality import extract_quality

SCAN_LIMIT = 6
SCAN_INTERVAL = 300  # ✅ 5 MINUTES

async def background_scanner(user, bot, DATA):
    await asyncio.sleep(15)  # let clients fully start

    while True:
        if not DATA.get("enabled"):
            await asyncio.sleep(SCAN_INTERVAL)
            continue

        for src, targets in DATA["maps"].items():
            src_id = int(src)

            scanned = 0
            forwarded = 0
            ignored = 0

            forwarded_keys = []
            ignored_keys = []

            # 🔒 ACCESS CHECK
            try:
                await user.get_chat(src_id)
            except:
                # ❌ no access → no log spam
                continue

            try:
                async for m in user.get_chat_history(src_id, limit=SCAN_LIMIT):
                    scanned += 1

                    # ❌ ONLY VIDEO
                    if not m.video:
                        ignored += 1
                        continue

                    text = m.caption or m.text or ""

                    ep = extract_episode(text)
                    q = extract_quality(text)

                    if ep == "NA":
                        ignored += 1
                        continue

                    # 🔑 UNIQUE PER QUALITY
                    key = f"{ep}|{q}"

                    # ❌ DUPLICATE
                    if is_episode_done(src, key):
                        ignored += 1
                        ignored_keys.append(key)
                        continue

                    # ✅ FORWARD
                    await forward_video(m, targets)

                    # ✅ MARK DONE
                    mark_episode_done(src, key)

                    forwarded += 1
                    forwarded_keys.append(key)

            except Exception:
                # silent fail
                continue

            # 🔥 LOG ONLY IF SOMETHING FORWARDED
            if forwarded > 0:
                await log_scan(
                    bot=bot,
                    src_id=src_id,
                    mode="AUTO SCAN",
                    scanned=scanned,
                    forwarded=forwarded,
                    ignored=ignored,
                    forwarded_eps=forwarded_keys,
                    ignored_eps=ignored_keys
                )

        await asyncio.sleep(SCAN_INTERVAL)
