import os
import logging
import mimetypes
from urllib.parse import quote
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pyrogram import Client
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from db import search_anime, get_meta, get_latest_anime

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) 

client = Client("stream_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, ipv6=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Web Server Starting...")
    await client.start()
    try:
        await client.get_chat(CHANNEL_ID)
        print("✅ Handshake Success")
    except:
        pass
    yield
    await client.stop()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.get("/")
def home(): return {"status": "Online"}

@app.get("/latest")
def latest():
    return {"results": get_latest_anime()}

@app.get("/search")
def search(q: str): 
    return {"results": search_anime(q)}

@app.get("/stream/{message_id}")
async def stream(message_id: int, request: Request):
    meta = get_meta(message_id)
    if not meta: raise HTTPException(status_code=404, detail="Not Found")
    
    file_name, file_size = meta
    
    try:
        safe_filename = quote(file_name)
    except:
        safe_filename = "video.mp4"

    mime_type, _ = mimetypes.guess_type(file_name)
    if not mime_type: mime_type = "video/mp4"

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
        try:
            # 1. Pehle Message Fetch karo (Zaruri hai)
            msg = await client.get_messages(CHANNEL_ID, message_id)
            if not msg or (not msg.video and not msg.document):
                logger.error("Message/Video not found on Telegram")
                return

            # 2. File ID nikalo
            file_id = msg.video.file_id if msg.video else msg.document.file_id

            current = start
            while current <= end:
                limit = min(chunk_size, end - current + 1)
                
                # 3. FIX: Arguments ab sahi hain
                # Hum File ID pass kar rahe hain, aur offset/limit keyword args se
                async for chunk in client.stream_media(
                    file_id, 
                    offset=current, 
                    limit=limit
                ):
                    yield chunk
                    current += len(chunk)
                    if current > end: break
        except Exception as e:
            logger.error(f"Stream Error: {e}")

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": mime_type,
        "Content-Disposition": f'inline; filename="{safe_filename}"',
    }
    return StreamingResponse(iterfile(), status_code=206, headers=headers)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
