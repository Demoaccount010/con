import asyncio
from config import MAIN_CHANNEL_ID, POST_DELAY
from utils.logger import info, error
from utils.jsondb import mark_episode_posted, is_episode_posted


async def post_episode(
    client,
    source_id: str,
    series_name: str,
    episode: str,
    invite_link: str,
    reply_msg_id: int
):
    """
    Send final message in main channel as reply to image (if possible)
    """

    # 🔥 STEP 0: DUPLICATE EPISODE CHECK (MOST IMPORTANT)
    try:
        if is_episode_posted(source_id, episode):
            info(f"Episode {episode} already posted for {series_name}, skipping.")
            return
    except Exception:
        # agar function missing ho to bhi crash na ho
        pass

    text = (
        f"🔰 **Anime :- {series_name}** 🔰\n"
        f"🔰 **Episode {episode} Added** 🔰\n"
        f"**{invite_link}**"
    )

    try:
        await asyncio.sleep(POST_DELAY)

        # 🔥 STEP 1: verify image message exists in MAIN CHANNEL
        try:
            if reply_msg_id:
                await client.get_messages(MAIN_CHANNEL_ID, reply_msg_id)
        except Exception:
            error(
                f"Image message {reply_msg_id} not found in main channel. "
                f"Posting without reply."
            )
            reply_msg_id = None

        # 🔥 STEP 2: send message (reply if possible)
        await client.send_message(
            chat_id=MAIN_CHANNEL_ID,
            text=text,
            reply_to_message_id=reply_msg_id
        )

        # 🔥 STEP 3: mark episode posted (ONLY ONCE)
        mark_episode_posted(source_id, episode)
        info(f"Posted Episode {episode} for {series_name}")

    except Exception as e:
        error(f"Failed to post episode {episode}: {e}")
