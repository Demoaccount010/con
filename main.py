import os
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
client = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, ipv6=False)

# --- DEBUG LOGGER (Terminal mein msg print karega) ---
@client.on_message(group=-1)
async def log_everything(c, m: Message):
    print(f"👀 New Message! From User ID: {m.from_user.id} | Name: {m.from_user.first_name}")

# --- COMMANDS ---

@client.on_message(filters.command(["start", "help"]) & filters.private)
async def start_handler(c, m: Message):
    print(f"👉 Start Command Received from: {m.from_user.id}")
    
    if m.from_user.id != OWNER_ID:
        await m.reply_text(f"❌ **Access Denied!**\nYour ID: `{m.from_user.id}`\nOwner ID: `{OWNER_ID}`")
        return

    await m.reply_text(
        "👋 **Bot is Online!**\n\n"
        "1. Forward video here to add.\n"
        "2. `/batch 100 200`\n"
        "3. `/check`"
    )

@client.on_message(filters.command("check"))
async def check_handler(c, m: Message):
    await m.reply_text("✅ I am Alive and Listening!")

# Media Handler
@client.on_message(filters.private & (filters.video | filters.document | filters.forwarded))
async def media_handler(c, m: Message):
    if m.from_user.id != OWNER_ID:
        return

    msg_id = None
    title = None
    
    if m.forward_from_chat and m.forward_from_chat.id == CHANNEL_ID:
        msg_id = m.forward_from_message_id
        title = m.caption or m.video.file_name or f"Video {msg_id}"
    elif m.video or m.document:
        await m.reply_text("⚠ Please forward from the Channel to get the correct Message ID.")
        return

    if msg_id:
        file_size = m.video.file_size or m.document.file_size
        duration = m.video.duration or 0
        add_anime(msg_id, title, file_size, duration)
        await m.reply_text(f"✅ **Saved:** {title}")
    else:
        await m.reply_text("❌ Channel ID match nahi hua.")

# Batch Handler
@client.on_message(filters.command("batch") & filters.private)
async def batch_handler(c, m: Message):
    if m.from_user.id != OWNER_ID: return

    try:
        if len(m.command) < 3:
            await m.reply_text("Usage: `/batch start end`")
            return
        
        start = int(m.command[1])
        end = int(m.command[2])
        status = await m.reply_text("⏳ Scanning...")
        
        count = 0
        batch_ids = list(range(start, end + 1))
        
        for i in range(0, len(batch_ids), 200):
            chunk = batch_ids[i:i+200]
            msgs = await c.get_messages(CHANNEL_ID, chunk)
            for msg in msgs:
                if msg and (msg.video or msg.document):
                    add_anime(msg.id, msg.caption or "Video", 0, 0)
                    count += 1
            await status.edit_text(f"Processed: {chunk[-1]}...")
            
        await status.edit_text(f"✅ Done. Added: {count}")
    except Exception as e:
        await m.reply_text(f"Error: {e}")

# --- SERVER LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Server Starting...")
    init_db()
    print("🤖 Connecting to Telegram...")
    await client.start()
    
    # Send startup msg
    try:
        await client.send_message(OWNER_ID, "🟢 **Bot Connected!**")
    except:
        print("⚠ Could not send startup msg (Check Owner ID)")

    yield
    print("🛑 Stopping...")
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
