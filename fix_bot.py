import logging
import os
from pyrogram import Client
from dotenv import load_dotenv

# 1. Full Debug Logging On
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

print("🚀 Starting Diagnostic Mode...")

# 2. Force IPv4 (Ye sabse main fix hai restricted VPS ke liye)
# Pyrogram IPv6 try karta hai aur fail ho jata hai
app = Client(
    "debug_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    ipv6=False 
)

@app.on_message()
async def hello(client, message):
    print(f"\n🎉 MESSAGE RECEIVED! {message.text}\n")
    await message.reply_text("Zinda hu bhai!")

print("🤖 Connecting to Telegram Servers...")
app.run()
