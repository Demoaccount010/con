import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
from db import init_db, add_anime, search_anime, get_meta

load_dotenv()

# --- CONFIG ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) 
OWNER_ID = int(os.getenv("OWNER_ID"))

# Pyrogram Client
client = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, ipv6=False)

# FastAPI App
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- JASOOS (DEBUGGER) ---
# Ye terminal mein print karega agar koi bhi msg aaya to.
# Agar ye print nahi hota, to samajh lena Webhook atka hai.
@client.on_message(group=-1)
async def debug_logger(c, m: Message):
    print(f"\n👀 JASOOS: Message Received! | From ID: {m.from_user.id} | Name: {m.from_user.first_name}")

# --- BOT COMMANDS ---

@client.on_message(filters.command(["start", "help"]) & filters.private)
async def start_cmd(c, m: Message):
    # Owner Check with Logs
    if m.from_user.id != OWNER_ID:
        print(f"❌ Access Denied for User: {m.from_user.id}")
        await m.reply_text(f"❌ **Access Denied!**\nYour ID: `{m.from_user.id}`\nOwner ID in Config: `{OWNER_ID}`")
        return
    
    print("✅ Owner Verified. Sending Reply...")
    await m.reply_text(
        "👋 **Bot is Online & Ready!**\n\n"
        "1️⃣ **Add Video:** Forward video here.\n"
        "2️⃣ **Check Status:** `/check`"
    )

@client.on_message(filters.command("check"))
async def check_cmd(c, m: Message):
    await m.reply_text("🚀 **Server is Online!** Loop is fixed.")

# Media Handler (Forwards)
@client.on_message(filters.private & (filters.video | filters.document | filters.forwarded))
async def media_handler(c, m: Message):
    if m.from_user.id != OWNER_ID:
        return

    msg_id = None
    title = None
    
    # Check if forwarded from the correct Channel
    if m.forward_from_chat and m.forward_from_chat.id == CHANNEL_ID:
        msg_id = m.forward_from_message_id
        title = m.caption or m.video.file_name or f"Video {msg_id}"
    elif m.video or m.document:
        await m.reply_text("⚠ **Warning:** Please forward from the Channel so I get the correct Message ID.")
        return

    if msg_id:
        file_size = m.video.file_size or m.document.file_size
        duration = m.video.duration or 0
        add_anime(msg_id, title, file_size, duration)
        print(f"💾 Database Updated: {title}")
        await m.reply_text(f"✅ **Saved to DB:**\nTitle: {title}\nID: `{msg_id}`")
    else:
        await m.reply_text("❌ Channel ID match nahi hua.")

# --- WEBSITE ROUTES ---

@app.get("/")
def home():
    return {"status": "Online", "System": "Port 80 Mode"}

@app.get("/search")
def search(q: str):
    return {"results": search_anime(q)}

@app.get("/stream/{message_id}")
async def stream(message_id: int, request: Request):
    meta = get_meta(message_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Video not found in DB")
    
    file_name, file_size = meta
    range_header = request.headers.get("Range")
    start, end = 0, file_size - 1
    
    if range_header:
        bytes_prefix = "bytes="
        if range_header.startswith(bytes_prefix):
            bytes_range = range_header[len(bytes_prefix):]
            parts = bytes_range.split("-")
            if parts[0]: start = int(parts[0])
            if len(parts) > 1 and parts[1]: end = int(parts[1])
    
    chunk_size = 1024 * 1024 
    content_length = end - start + 1
    
    async def iterfile():
        current = start
        while current <= end:
            limit = min(chunk_size, end - current + 1)
            async for chunk in client.stream_media(
                message_id=message_id,
                chat_id=CHANNEL_ID,
                offset=current,
                limit=limit
            ):
                yield chunk
                current += len(chunk)
                if current > end: break
    
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": "video/mp4",
        "Content-Disposition": f'inline; filename="{file_name}"',
    }
    return StreamingResponse(iterfile(), status_code=206, headers=headers)
