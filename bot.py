import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
from db import init_db, add_anime

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# CONFIG
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) 
OWNER_ID = int(os.getenv("OWNER_ID"))

# Initialize DB
init_db()

# Client (IPv6 False zindabad)
app = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, ipv6=False)

@app.on_message(filters.command(["start", "help"]) & filters.private)
async def start(c, m: Message):
    if m.from_user.id != OWNER_ID:
        await m.reply_text("❌ Access Denied.")
        return
    await m.reply_text("✅ **Bot Online!** Forward videos to add.")

@app.on_message(filters.private & (filters.video | filters.document | filters.forwarded))
async def add_video(c, m: Message):
    if m.from_user.id != OWNER_ID: return
    
    msg_id = None
    title = None
    
    if m.forward_from_chat and m.forward_from_chat.id == CHANNEL_ID:
        msg_id = m.forward_from_message_id
        title = m.caption or m.video.file_name or f"Video {msg_id}"
        
        # Save to DB
        add_anime(msg_id, title, 0, 0)
        await m.reply_text(f"✅ **Saved:** {title}")
        logger.info(f"Saved Video: {title}")
    else:
        await m.reply_text("❌ Forward from Channel only.")

if __name__ == "__main__":
    print("🤖 Bot Started Independently...")
    app.run()
