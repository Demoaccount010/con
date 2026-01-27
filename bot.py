import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv
from db import init_db, add_anime
from fetcher import search_jikan

logging.basicConfig(level=logging.ERROR)
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) 
OWNER_ID = int(os.getenv("OWNER_ID"))

init_db()
client = Client("bot_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, ipv6=False)

# Temporary Storage
temp_data = {}

@client.on_message(filters.command("start"))
async def start(c, m: Message):
    if m.from_user.id == OWNER_ID:
        await m.reply_text("👋 **Boss!** Video forward karo.")

@client.on_message(filters.private & (filters.video | filters.document | filters.forwarded))
async def receive_video(c, m: Message):
    if m.from_user.id != OWNER_ID: return
    
    if m.forward_from_chat and m.forward_from_chat.id == CHANNEL_ID:
        file_id = m.video.file_id if m.video else m.document.file_id
        fname = m.video.file_name if m.video else m.document.file_name
        if not fname: fname = "video.mp4"
        
        uid = m.from_user.id
        # Save state
        temp_data[uid] = {
            "msg_id": m.forward_from_message_id,
            "filename": fname,
            "size": m.video.file_size if m.video else m.document.file_size,
            "raw_caption": m.caption or fname
        }
        
        buttons = [
            [InlineKeyboardButton("🎬 Movie", callback_data="cat_Movies"),
             InlineKeyboardButton("📺 Series", callback_data="cat_Series")],
            [InlineKeyboardButton("🔞 NSFW", callback_data="cat_NSFW"),
             InlineKeyboardButton("📂 Other", callback_data="cat_Others")]
        ]
        await m.reply_text(f"📂 **Category Select Karo:**\nFile: `{fname}`", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await m.reply_text("❌ Channel se forward karo!")

# Step 2: Category Selected
@client.on_callback_query(filters.regex(r"^cat_"))
async def category_handler(c, q: CallbackQuery):
    uid = q.from_user.id
    
    # --- FIX: Check if data exists ---
    if uid not in temp_data:
        await q.answer("❌ Session Expired. Video dobara bhejo.", show_alert=True)
        return
    
    category = q.data.split("_")[1]
    temp_data[uid]['category'] = category
    
    await q.message.edit_text("⏳ **Searching Info...**")
    
    # Search Jikan
    query_text = temp_data[uid]['raw_caption']
    results = search_jikan(query_text)
    
    if not results:
        save_final(uid, {"title": query_text, "poster": "", "synopsis": "", "rating": "N/A", "genres": ""})
        await q.message.edit_text(f"✅ **Saved directly (No info found)**\nCategory: {category}")
        return

    # Save results to temp
    temp_data[uid]['search_results'] = results
    
    buttons = []
    for idx, res in enumerate(results):
        buttons.append([InlineKeyboardButton(f"{res['title']} ({res['rating']})", callback_data=f"sel_{idx}")])
    
    buttons.append([InlineKeyboardButton("❌ None (Use Filename)", callback_data="sel_none")])
    
    await q.message.edit_text("🔍 **Select Correct Anime:**", reply_markup=InlineKeyboardMarkup(buttons))

# Step 3: Result Selected
@client.on_callback_query(filters.regex(r"^sel_"))
async def select_handler(c, q: CallbackQuery):
    uid = q.from_user.id
    
    # --- FIX: Check if data exists ---
    if uid not in temp_data:
        await q.answer("❌ Session Expired. Video dobara bhejo.", show_alert=True)
        return
    
    selection = q.data.split("_")[1]
    final_meta = {}
    
    if selection == "none":
        final_meta = {
            "title": temp_data[uid]['raw_caption'],
            "poster": "https://via.placeholder.com/300x450?text=No+Info",
            "synopsis": "No description.",
            "rating": "N/A",
            "genres": "Unknown"
        }
    else:
        idx = int(selection)
        final_meta = temp_data[uid]['search_results'][idx]
    
    # Save karo
    cat = temp_data[uid]['category'] # Pehle save kar lo variable mein
    save_final(uid, final_meta)
    
    await q.message.edit_text(f"✅ **Done!**\nTitle: **{final_meta['title']}**\nCategory: **{cat}**")

def save_final(uid, meta):
    if uid in temp_data:
        data = temp_data[uid]
        full_data = {**data, **meta}
        add_anime(full_data)
        del temp_data[uid] # Ab delete karo

if __name__ == "__main__":
    print("🤖 Bot Started...")
    client.run()
