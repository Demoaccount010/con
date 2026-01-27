import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from db import init_db, add_anime, search_anime, get_meta

load_dotenv()

# --- CONFIG ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) 
OWNER_ID = int(os.getenv("OWNER_ID"))

# Pyrogram Client
client = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- HELPER FUNCTION ---
async def is_owner(user_id):
    if user_id == OWNER_ID:
        return True
    return False

# --- BOT COMMANDS ---

@client.on_message(filters.command(["start", "help"]) & filters.private)
async def start_handler(c, m: Message):
    # Debug Print
    print(f"📩 Message from: {m.from_user.id} | Owner ID expected: {OWNER_ID}")
    
    if m.from_user.id != OWNER_ID:
        await m.reply_text(f"❌ **Access Denied!**\nYour ID: `{m.from_user.id}`\nOwner ID in Config: `{OWNER_ID}`")
        return

    await m.reply_text(
        "👋 **Welcome Boss! Anime Stream Bot Ready.**\n\n"
        "**Available Commands:**\n"
        "1️⃣ **Forward Video:** Add directly to DB.\n"
        "2️⃣ `/batch <start> <end>` : Add multiple videos by ID.\n"
        "3️⃣ `/index <id>` : Add single video by ID.\n"
        "4️⃣ `/check` : Check Server Status."
    )

@client.on_message(filters.command("check"))
async def check_handler(c, m: Message):
    await m.reply_text("✅ **Server is Online!**\nBot is listening.")

# Handle Forwards & Videos
@client.on_message(filters.private & (filters.video | filters.document | filters.forwarded))
async def media_handler(c, m: Message):
    if m.from_user.id != OWNER_ID:
        return # Ignore strangers silently for media

    # Logic to handle forwards
    msg_id = None
    title = None
    
    # Case 1: Forwarded from Channel
    if m.forward_from_chat and m.forward_from_chat.id == CHANNEL_ID:
        msg_id = m.forward_from_message_id
        title = m.caption or m.video.file_name or f"Video {msg_id}"
    
    # Case 2: Just a random video sent to bot (No Link)
    elif m.video or m.document:
        await m.reply_text("⚠ **Warning:** Please forward from the **Channel** so I get the correct Message ID.")
        return

    if msg_id:
        file_size = m.video.file_size or m.document.file_size
        duration = m.video.duration or 0
        
        add_anime(msg_id, title, file_size, duration)
        await m.reply_text(f"✅ **Added to DB!**\n🆔 ID: `{msg_id}`\n📺 Title: {title}")
    else:
        await m.reply_text("❌ Could not get Message ID. Make sure you forwarded from the configured Channel.")

# Batch Command
@client.on_message(filters.command("batch") & filters.private)
async def batch_handler(c, m: Message):
    if m.from_user.id != OWNER_ID:
        return

    try:
        if len(m.command) < 3:
            await m.reply_text("ℹ **Usage:** `/batch <start_id> <end_id>`\nExample: `/batch 100 200`")
            return
            
        start_id = int(m.command[1])
        end_id = int(m.command[2])
        
        status_msg = await m.reply_text(f"⏳ **Starting Batch Scan:** {start_id} to {end_id}...")
        
        count = 0
        batch_size = 200
        
        for i in range(start_id, end_id + 1, batch_size):
            current_end = min(i + batch_size, end_id + 1)
            batch_ids = list(range(i, current_end))
            
            messages = await c.get_messages(CHANNEL_ID, batch_ids)
            
            for msg in messages:
                if msg and not msg.empty and (msg.video or msg.document):
                    media = msg.video or msg.document
                    if msg.document and "video" not in (msg.document.mime_type or ""):
                        continue
                        
                    title = msg.caption or media.file_name or f"Video {msg.id}"
                    add_anime(msg.id, title, media.file_size, media.duration or 0)
                    count += 1
            
            await status_msg.edit_text(f"🔄 **Scanning...**\nChecked till: {current_end-1}\nFound: {count}")
            
        await status_msg.edit_text(f"✅ **Batch Complete!**\n🎯 Range: {start_id}-{end_id}\n📂 Added: {count} Videos")
        
    except Exception as e:
        await m.reply_text(f"❌ Error: {e}")

# Manual Index
@client.on_message(filters.command("index") & filters.private)
async def index_handler(c, m: Message):
    if m.from_user.id != OWNER_ID:
        return

    try:
        if len(m.command) < 2:
            await m.reply_text("ℹ **Usage:** `/index <id>`")
            return
        
        msg_id = int(m.command[1])
        msg = await c.get_messages(CHANNEL_ID, msg_id)
        
        if msg and (msg.video or msg.document):
            media = msg.video or msg.document
            title = msg.caption or media.file_name or f"Video {msg.id}"
            add_anime(msg.id, title, media.file_size, media.duration or 0)
            await m.reply_text(f"✅ **Indexed:** {title}")
        else:
            await m.reply_text("❌ Video not found at this ID.")
    except Exception as e:
        await m.reply_text(f"❌ Error: {e}")

# --- SERVER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Server Starting...")
    init_db()
    await client.start()
    print("🤖 Bot Connected! Waiting for commands...")
    
    # Koshish karo owner ko msg bhejne ki
    try:
        await client.send_message(OWNER_ID, "🟢 **Bot & Server Online!**")
    except Exception as e:
        print(f"⚠ Could not send startup msg: {e}")

    yield
    print("🛑 Server Stopping...")
    await client.stop()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def home(): return {"status": "Online"}

@app.get("/search")
def search(q: str): return {"results": search_anime(q)}

@app.get("/stream/{message_id}")
async def stream(message_id: int, request: Request):
    meta = get_meta(message_id)
    if not meta: raise HTTPException(status_code=404, detail="Not Found")
    
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
            async for chunk in client.stream_media(message_id=message_id, chat_id=CHANNEL_ID, offset=current, limit=limit):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
