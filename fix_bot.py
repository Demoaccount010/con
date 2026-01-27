import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ Error: .env file nahi mili ya BOT_TOKEN missing hai!")
    exit()

print(f"🔧 Repairing Bot: {BOT_TOKEN[:10]}...")

# 1. Force Delete Webhook
url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True"
try:
    response = requests.get(url)
    data = response.json()
    if data.get("ok"):
        print("✅ Webhook Successfully DELETED! (Ab Bot sunega)")
    else:
        print(f"❌ Webhook Error: {data}")
except Exception as e:
    print(f"❌ Connection Error: {e}")

# 2. Delete Corrupt Session
if os.path.exists("bot_session.session"):
    os.remove("bot_session.session")
    print("✅ Purani Session File Delete kar di.")
else:
    print("ℹ️ Koi purani session file nahi thi.")

print("\n🎉 REPAIR COMPLETE! Ab 'python run.py' chalao.")
