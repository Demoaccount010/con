import os
from pyrogram import Client, filters
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# Simple Bot Script
app = Client("test_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, ipv6=False)

@app.on_message()
async def echo(client, message):
    print(f"📩 Message aaya: {message.text}")
    await message.reply_text("✅ Bot Zinda Hai!")

print("🤖 Testing Bot Only Mode... (Telegram par message bhejo)")
app.run()
