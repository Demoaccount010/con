import asyncio
import uvicorn
from main import app, client, init_db, OWNER_ID

async def main():
    # 1. Database Initialize
    print("🔄 Initializing Database...")
    init_db()

    # 2. Uvicorn Server Config (Manual Setup)
    # Port 8080 wahi rakhna jo Cloudflare Tunnel mein hai
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)

    # 3. Start Pyrogram Client
    print("🤖 Starting Bot...")
    await client.start()
    
    # Try cleaning webhook
    try:
        await client.delete_webhook()
    except:
        pass
        
    print("✅ Bot Started! Sending notification...")
    try:
        await client.send_message(OWNER_ID, "🟢 **System Online (Custom Loop Mode)**")
    except Exception as e:
        print(f"⚠ Notification Failed: {e}")

    # 4. Start Web Server (Ye block karega jab tak server chal raha hai)
    print("🚀 Starting Web Server...")
    await server.serve()

    # 5. Stop Pyrogram jab server band ho
    print("🛑 Stopping Bot...")
    await client.stop()

if __name__ == "__main__":
    # Ye Magic Line hai jo sabko ek hi Loop par chalati hai
    asyncio.run(main())
