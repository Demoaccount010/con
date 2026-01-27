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
        temp_data[uid] = {
            "msg_id": m.forward_from_message_id,
            "filename": fname,
            "size": m.video.file_size if m.video else m.document.file_size,
            "raw_caption": m.caption or fname,
            "extra_info": m.caption or "No extra info" # Caption ko hi extra info bana diya
        }
        
        buttons = [
            [InlineKeyboardButton("🎬 Movie", callback_data="cat_Movies"),
             InlineKeyboardButton("📺 Series", callback_data="cat_Series")],
            [InlineKeyboardButton("🔞 NSFW", callback_data="cat_NSFW"),
             InlineKeyboardButton("📂 Other", callback_data="cat_Others")]
        ]
        await m.reply_text(f"📂 **Category Select Karo:**", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await m.reply_text("❌ Channel se forward karo!")

@client.on_callback_query(filters.regex(r"^cat_"))
async def category_handler(c, q: CallbackQuery):
    uid = q.from_user.id
    if uid not in temp_data: return await q.answer("Expired", show_alert=True)
    
    temp_data[uid]['category'] = q.data.split("_")[1]
    await q.message.edit_text("⏳ **Searching Info...**")
    
    results = search_jikan(temp_data[uid]['raw_caption'])
    
    if not results:
        save_final(uid, {"title": temp_data[uid]['raw_caption'], "poster": "", "synopsis": "", "rating": "N/A", "genres": ""})
        await q.message.edit_text("✅ Saved directly.")
        return

    temp_data[uid]['search_results'] = results
    buttons = []
    for idx, res in enumerate(results):
        buttons.append([InlineKeyboardButton(f"{res['title']} ({res['rating']})", callback_data=f"sel_{idx}")])
    buttons.append([InlineKeyboardButton("❌ None", callback_data="sel_none")])
    
    await q.message.edit_text("🔍 **Select Anime:**", reply_markup=InlineKeyboardMarkup(buttons))

@client.on_callback_query(filters.regex(r"^sel_"))
async def select_handler(c, q: CallbackQuery):
    uid = q.from_user.id
    if uid not in temp_data: return
    
    sel = q.data.split("_")[1]
    if sel == "none":
        meta = {"title": temp_data[uid]['raw_caption'], "poster": "", "synopsis": "", "rating": "N/A", "genres": ""}
    else:
        meta = temp_data[uid]['search_results'][int(sel)]
    
    save_final(uid, meta)
    await q.message.edit_text(f"✅ **Saved:** {meta['title']}")

def save_final(uid, meta):
    if uid in temp_data:
        data = {**temp_data[uid], **meta}
        add_anime(data)
        del temp_data[uid]

if __name__ == "__main__":
    client.run()
