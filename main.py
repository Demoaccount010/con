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
OWNER_ID = int(os.getenv("OWNER_ID")) # Teri User ID

# Pyrogram Client Setup
client = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- BOT COMMANDS (Pyrogram Handlers) ---

# 1. Start Command
@client.on_message(filters.command("start") & filters.private)
async def start_handler(c, m: Message):
    if m.from_user.id != OWNER_ID:
        return
    await m.reply_text(
        "👋 **Welcome Boss!**\n\n"
        "**Commands:**\n"
        "1. Forward any video here to add instantly.\n"
        "2. `/batch <start_id> <end_id>` (Bulk Add)\n"
        "3. `/index <message_id>` (Add Single ID)"
    )

# 2. Add Single Video via Forward or ID
@client.on_message(filters.private & filters.user(OWNER_ID) & (filters.video | filters.document | filters.forwarded))
async def forward_handler(c, m: Message):
    # Agar forward kiya hai channel se
    if m.forward_from_chat and m.forward_from_chat.id == CHANNEL_ID:
        msg_id = m.forward_from_message_id
        title = m.caption or m.video.file_name or f"Video {msg_id}"
        file_size = m.video.file_size or m.document.file_size
        duration = m.video.duration or 0
        
        add_anime(msg_id, title, file_size, duration)
        await m.reply_text(f"✅ **Added to DB:**\nID: `{msg_id}`\nTitle: {title}")
    else:
        await m.reply_text("❌ Sirf apne Channel se forward karo, ya `/index <id>` use karo.")

# 3. Manual Index Command (/index 123)
@client.on_message(filters.command("index") & filters.user(OWNER_ID))
async def index_handler(c, m: Message):
    try:
        if len(m.command) < 2:
            await m.reply_text("⚠ Usage: `/index <message_id>`")
            return
            
        msg_id = int(m.command[1])
        msg = await c.get_messages(CHANNEL_ID, msg_id)
        
        if msg and (msg.video or msg.document):
            media = msg.video or msg.document
            title = msg.caption or media.file_name or f"Video {msg.id}"
            add_anime(msg.id, title, media.file_size, media.duration or 0)
            await m.reply_text(f"✅ **Indexed:** {title}")
        else:
            await m.reply_text("❌ Is ID par koi Video nahi mili.")
            
    except Exception as e:
        await m.reply_text(f"❌ Error: {e}")

# 4. Batch Scan Command (/batch 100 200)
@client.on_message(filters.command("batch") & filters.user(OWNER_ID))
async def batch_handler(c, m: Message):
    try:
        if len(m.command) < 3:
            await m.reply_text("⚠ Usage: `/batch <start_id> <end_id>`")
            return
            
        start_id = int(m.command[1])
        end_id = int(m.command[2])
        
        status_msg = await m.reply_text(f"⏳ **Scanning** {start_id} to {end_id}...")
        
        count = 0
        batch_size = 200
        
        for i in range(start_id, end_id + 1, batch_size):
            # Calculate batch range
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
            
            # Progress update har batch ke baad
            await status_msg.edit_text(f"⏳ Scanning... Processed till ID {current_end-1}\n✅ Found: {count}")
            
        await status_msg.edit_text(f"🎉 **Batch Complete!**\nScanned: {start_id}-{end_id}\n✅ Added: {count} Videos")
        
    except Exception as e:
        await m.reply_text(f"❌ Error: {e}")

# --- FASTAPI SERVER SETUP ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Init DB...")
    init_db()
    print("🤖 Starting Bot...")
    await client.start()
    
    # Send startup message to owner
    try:
        await client.send_message(OWNER_ID, "🟢 **Server Started!**\nWebsite is Live.")
    except:
        pass
        
    yield
    print("🛑 Stopping Bot...")
    await client.stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ROUTES (Website ke liye) ---

@app.get("/")
def home():
    return {"status": "Online", "bot": "Active"}

@app.get("/search")
def search(q: str):
    return {"results": search_anime(q)}

@app.get("/stream/{message_id}")
async def stream(message_id: int, request: Request):
    meta = get_meta(message_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Video not found")
    
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
    uvicorn.run(app, host="0.0.0.0", port=8080)
