import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pyrogram import Client
from pyrogram.enums import MessagesFilter
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from db import init_db, add_anime, search_anime, get_meta

load_dotenv()

# --- CONFIG ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) 
ADMIN_KEY = os.getenv("ADMIN_KEY")

# --- LIFESPAN MANAGER (Fixes warnings) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🔄 Initializing Database...")
    init_db()
    print("🤖 Starting Telegram Client...")
    await client.start()
    print("✅ System Ready!")
    yield
    # Shutdown
    print("🛑 Stopping Telegram Client...")
    await client.stop()

# Initialize App
app = FastAPI(lifespan=lifespan)

# Allow CORS (Website Access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pyrogram Client
client = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# --- ROUTES ---

@app.get("/")
def home():
    return {"status": "Online", "mode": "Tunnel + Bot Mode"}

@app.get("/scan")
async def scan_channel(key: str):
    """
    Scans the channel for VIDEO files using Search Method.
    Best for Bots.
    """
    if key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    count = 0
    print(f"🔍 Scanning Channel: {CHANNEL_ID}...")
    
    try:
        # FIX: Using search_messages with VIDEO filter (Works for Bots)
        async for msg in client.search_messages(CHANNEL_ID, filter=MessagesFilter.VIDEO):
            if msg.video:
                # Use Caption as Title, fallback to filename
                title = msg.caption or msg.video.file_name or f"Unknown Video {msg.id}"
                
                # Add to DB
                add_anime(msg.id, title, msg.video.file_size, msg.video.duration or 0)
                count += 1
                
        print(f"✅ Scan Complete. Added {count} videos.")
        return {"status": "scanned", "added": count}
        
    except Exception as e:
        print(f"❌ Error Scanning: {e}")
        return {"status": "error", "message": str(e)}

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
    start = 0
    end = file_size - 1
    
    if range_header:
        bytes_prefix = "bytes="
        if range_header.startswith(bytes_prefix):
            bytes_range = range_header[len(bytes_prefix):]
            parts = bytes_range.split("-")
            if parts[0]: start = int(parts[0])
            if len(parts) > 1 and parts[1]: end = int(parts[1])

    chunk_size = 1024 * 1024 # 1MB chunks
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

if __name__ == "__main__":
    import uvicorn
    # Tunnel 8080 par mapped hai, isliye yaha 8080 hi rakhenge
    uvicorn.run(app, host="0.0.0.0", port=80)
