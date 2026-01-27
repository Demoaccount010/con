import asyncio
import uvicorn
from main import app, client, init_db, OWNER_ID

async def main():
    print("🔄 Initializing Database...")
    init_db()

    # --- PORT 80 CONFIGURATION ---
    # Hum Port 80 use kar rahe hain kyunki tumhara Cloudflare wahi point kar raha hai
    config = uvicorn.Config(app, host="0.0.0.0", port=80, log_level="info")
    server = uvicorn.Server(config)

    print("🤖 Starting Bot...")
    await client.start()
    
    # Startup Msg
    print(f"✅ Bot Started! Waiting for OWNER_ID: {OWNER_ID}")
    try:
        await client.send_message(OWNER_ID, "🟢 **System Online (Port 80)**")
    except Exception as e:
        print(f"⚠ Notification Failed: {e}")

    print("🚀 Starting Web Server on Port 80...")
    # Ye line server start karegi aur bot ko background mein chalne degi
    await server.serve()

    print("🛑 Stopping Bot...")
    await client.stop()

if __name__ == "__main__":
    asyncio.run(main())
