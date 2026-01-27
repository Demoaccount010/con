import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
from db import init_db, add_anime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) 
OWNER_ID = int(os.getenv("OWNER_ID"))

# DB Initialize
init_db()

# Client
client = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, ipv6=False)

@client.on_message(filters.command(["start", "help"]) & filters.private)
async def start(c, m: Message):
    if m.from_user.id != OWNER_ID: return
    await m.reply_text("✅ **Bot Online!** Forward videos now.")

@client.on_message(filters.private & (filters.video | filters.document | filters.forwarded))
async def add_video(c, m: Message):
    if m.from_user.id != OWNER_ID: return
    
    msg_id = None
    title = None
    real_filename = "video.mp4" # Default fallback
    file_size = 0
    duration = 0
    
    if m.forward_from_chat and m.forward_from_chat.id == CHANNEL_ID:
        msg_id = m.forward_from_message_id
        
        # 1. Get Details
        title = m.caption or m.video.file_name or f"Video {msg_id}"
        
        if m.video:
            real_filename = m.video.file_name or "video.mp4"
            file_size = m.video.file_size
            duration = m.video.duration or 0
        elif m.document:
            real_filename = m.document.file_name or "video.mp4"
            file_size = m.document.file_size
            
        # 2. Save to DB (Passing ALL 5 arguments correctly now)
        add_anime(msg_id, title, real_filename, file_size, duration)
        
        await m.reply_text(f"✅ **Indexed:**\nTitle: {title}\nFile: `{real_filename}`")
        logger.info(f"Added: {title} | {real_filename}")
    else:
        await m.reply_text("❌ Channel se forward karo.")

if __name__ == "__main__":
    print("🤖 Bot Started...")
    client.run()
