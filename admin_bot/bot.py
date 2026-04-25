import os
import re
import uuid
import asyncio
import httpx
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_ID_ENV = os.getenv("API_ID", "").strip()
API_ID = int(API_ID_ENV) if API_ID_ENV else 0
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_ENV = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID_ENV) if ADMIN_ID_ENV else 0
MONGO_URI = os.getenv("MONGO_URI")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")

if not API_ID or not API_HASH or not BOT_TOKEN:
    print("❌ ERROR: Missing critical environment variables (API_ID, API_HASH, BOT_TOKEN). Check your Render settings!")

# Database setup
client = MongoClient(MONGO_URI)
db = client.get_default_database()
movies_collection = db.movies

app = Client("admin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def extract_quality(filename):
    qualities = ["480p", "720p", "1080p", "2160p", "4k", "cam", "hdtv", "web-dl", "bluray"]
    for q in qualities:
        if q in filename.lower():
            return q.upper()
    return "HD"

def clean_title(filename):
    # Remove quality, year, and extensions
    title = filename.lower()
    title = re.sub(r'\.(mp4|mkv|avi|mov)$', '', title)
    title = re.sub(r'\d{3,4}p.*', '', title)
    title = re.sub(r'\[.*\]', '', title)
    title = re.sub(r'\(.*\)', '', title)
    title = title.replace('.', ' ').replace('_', ' ').strip()
    return title.title()

async def get_imdb_data(query):
    async with httpx.AsyncClient() as client:
        url = f"https://www.omdbapi.com/?t={query}&apikey={OMDB_API_KEY}"
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("Response") == "True":
                return data
    return None

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0

@app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(client, message):
    await message.reply_text(
        f"👋 **Welcome Admin!**\n\n"
        "I can index movies and series for your MovieHub app.\n\n"
        "**Available Commands:**\n"
        "🚀 `/index [channel]` - Index all files from a channel\n"
        "➕ `/add [imdbID]` - Add a file manually\n"
        "📂 `/list` - List all indexed movies\n"
        "🗑 `/delete [imdbID]` - Delete a movie\n"
        "⚙️ `/stats` - Show database statistics",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Channel Indexing", callback_data="help_index")],
            [InlineKeyboardButton("Manual Add", callback_data="help_add")]
        ])
    )

@app.on_message(filters.command("stats") & filters.user(ADMIN_ID))
async def stats(client, message):
    total_movies = movies_collection.count_documents({})
    pipeline = [{"$unwind": "$files"}, {"$count": "total_files"}]
    total_files_res = list(movies_collection.aggregate(pipeline))
    total_files = total_files_res[0]['total_files'] if total_files_res else 0
    
    await message.reply_text(
        "📊 **Database Statistics**\n\n"
        f"🎬 Total Movies: {total_movies}\n"
        f"📁 Total Files: {total_files}"
    )

@app.on_message(filters.command("index") & filters.user(ADMIN_ID))
async def index_channel(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/index [channel_username/id]`")
    
async def perform_index(chat_id, status_msg):
    count = 0
    skipped = 0
    try:
        # Check chat type first
        chat = await app.get_chat(chat_id)
        
        # Check if bot is admin
        try:
            member = await app.get_chat_member(chat_id, "me")
            is_admin = member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
        except:
            is_admin = False

        if not is_admin and chat.type == enums.ChatType.CHANNEL:
             await status_msg.edit_text(
                "❌ **Bot is not an Admin**\n\n"
                "I need to be an **Administrator** in this channel to read its history. "
                "Please add me as an admin and try again."
            )
             return

        if chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            await status_msg.edit_text(
                "⚠️ **Group Indexing Restricted**\n\n"
                "Telegram does not allow bots to read the history of **Groups**. "
                "However, you can still index files by:\n"
                "1. **Forwarding** files to me (individually or in batches).\n"
                "2. Posting **new** files in the group (I'll index them automatically)."
            )
            return

        async for m in app.get_chat_history(chat_id):
            try:
                file = m.document or m.video
                if not file:
                    continue
                    
                filename = file.file_name or "Unknown"
                if not filename.lower().endswith(('.mkv', '.mp4', '.avi')):
                    skipped += 1
                    continue
                    
                file_id = file.file_id
                size = format_size(file.file_size)
                quality = extract_quality(filename)
                raw_title = clean_title(filename)
                
                # Try to get IMDb ID from caption or title
                imdb_id = None
                if m.caption:
                    match = re.search(r'tt\d{7,8}', m.caption)
                    if match:
                        imdb_id = match.group(0)
                
                if not imdb_id:
                    imdb_data = await get_imdb_data(raw_title)
                    imdb_id = imdb_data.get("imdbID") if imdb_data else "tt0000000"
                    title = imdb_data.get("Title") if imdb_data else raw_title
                else:
                    title = raw_title
                
                movie_id = str(uuid.uuid4())[:8]
                
                movies_collection.update_one(
                    {"imdbID": imdb_id},
                    {
                        "$set": {"title": title},
                        "$push": {
                            "files": {
                                "quality": quality,
                                "size": size,
                                "file_id": file_id,
                                "movie_id": movie_id
                            }
                        }
                    },
                    upsert=True
                )
                
                count += 1
                if count % 20 == 0:
                    await status_msg.edit_text(
                        f"🔄 **Indexing `{chat_id}`...**\n"
                        f"✅ Added: {count}\n"
                        f"⏩ Skipped: {skipped}"
                    )
            except Exception as inner_e:
                print(f"Error indexing message {m.id}: {inner_e}")
                skipped += 1
                continue
        
        await status_msg.edit_text(
            f"✅ **Indexing Complete!**\n"
            f"📍 Chat: `{chat_id}`\n"
            f"📂 Total Added: {count}\n"
            f"⏩ Total Skipped: {skipped}"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error during indexing:**\n`{str(e)}`")

@app.on_message(filters.command("index") & filters.user(ADMIN_ID))
async def index_command(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/index [channel_username/id]`")
    
    chat_id = message.command[1]
    status_msg = await message.reply_text(f"🔍 **Starting indexing for `{chat_id}`...**")
    await perform_index(chat_id, status_msg)

@app.on_message((filters.document | filters.video) & filters.user(ADMIN_ID))
async def handle_incoming_file(client, message: Message):
    # Check if this is a forward from a channel
    if message.forward_from_chat:
        source_chat = message.forward_from_chat
        if source_chat.type == enums.ChatType.CHANNEL:
            try:
                # Check if bot is admin in the source chat
                member = await app.get_chat_member(source_chat.id, "me")
                if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                    status_msg = await message.reply_text(f"💎 **Bot is Admin in `{source_chat.title}`!**\nIndexing the entire channel...")
                    await perform_index(source_chat.id, status_msg)
                    return
            except Exception:
                pass # Not an admin or couldn't check

    # Standard indexing for single file (or fallback if not admin)
    file = message.document or message.video
    filename = file.file_name or "Unknown"
    file_id = file.file_id
    size = format_size(file.file_size)
    quality = extract_quality(filename)
    raw_title = clean_title(filename)
    
    imdb_id = None
    if message.caption:
        match = re.search(r'tt\d{7,8}', message.caption)
        if match: imdb_id = match.group(0)
    
    if not imdb_id:
        imdb_data = await get_imdb_data(raw_title)
        imdb_id = imdb_data.get("imdbID") if imdb_data else "tt0000000"
        title = imdb_data.get("Title") if imdb_data else raw_title
    else:
        title = raw_title

    movie_id = str(uuid.uuid4())[:8]

    movies_collection.update_one(
        {"imdbID": imdb_id},
        {
            "$set": {"title": title},
            "$push": {
                "files": {
                    "quality": quality,
                    "size": size,
                    "file_id": file_id,
                    "movie_id": movie_id
                }
            }
        },
        upsert=True
    )

    await message.reply_text(
        f"✅ **Single File Indexed!**\n\n"
        f"🎬 **Title:** {title}\n"
        f"🆔 **IMDb:** `{imdb_id}`\n"
        f"💎 **Quality:** {quality}\n"
        f"📦 **Size:** {size}\n"
        f"🔗 **Internal ID:** `{movie_id}`"
    )

@app.on_message(filters.command("list") & filters.user(ADMIN_ID))
async def list_movies(client, message):
    movies = movies_collection.find()
    text = "📂 Indexed Movies:\n\n"
    for m in movies:
        text += f"🎬 {m['title']} ({m['imdbID']})\n"
        for f in m.get('files', []):
            text += f"  └ {f['quality']} - {f['size']}\n"
        text += "\n"
    
    if len(text) > 4096:
        # Split or send as file
        await message.reply_text("List is too long, showing recent...")
    else:
        await message.reply_text(text)

@app.on_message(filters.command("delete") & filters.user(ADMIN_ID))
async def delete_movie(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /delete [imdbID]")
    
    imdb_id = message.command[1]
    result = movies_collection.delete_one({"imdbID": imdb_id})
    
    if result.deleted_count:
        await message.reply_text(f"🗑 Deleted movie {imdb_id}")
    else:
        await message.reply_text("Movie not found.")

if __name__ == "__main__":
    print("Admin Bot Starting...")
    app.run()
