import os
import re
import uuid
import asyncio
import httpx
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URI = os.getenv("MONGO_URI")
OMDB_API_KEY = os.getenv("OMDB_API_KEY")

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
    
    chat_id = message.command[1]
    status_msg = await message.reply_text(f"🔍 **Starting indexing for `{chat_id}`...**")
    
    count = 0
    skipped = 0
    
    try:
        async for m in app.get_chat_history(chat_id):
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
                # Basic search by title if no IMDb found
                imdb_data = await get_imdb_data(raw_title)
                imdb_id = imdb_data.get("imdbID") if imdb_data else "tt0000000"
                title = imdb_data.get("Title") if imdb_data else raw_title
            else:
                title = raw_title # We'll refine this if needed
            
            movie_id = str(uuid.uuid4())[:8]
            
            # Index to DB
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
        
        await status_msg.edit_text(
            f"✅ **Indexing Complete!**\n"
            f"📍 Channel: `{chat_id}`\n"
            f"📂 Total Added: {count}\n"
            f"⏩ Total Skipped: {skipped}"
        )
        
    except Exception as e:
        await status_msg.edit_text(f"❌ **Error during indexing:**\n`{str(e)}`")

@app.on_message(filters.command("add") & filters.user(ADMIN_ID))
async def add_movie_prompt(client, message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: /add [imdbID]")
    
    imdb_id = message.command[1]
    await message.reply_text(f"Now send/forward the movie file for {imdb_id}")

@app.on_message(filters.document & filters.user(ADMIN_ID))
async def handle_document(client, message: Message):
    # This logic assumes the admin just sent a file
    # In a more robust version, we'd use a state machine (ConversationHandler)
    # But for now, we'll try to find if there's a pending add or just extract info
    
    filename = message.document.file_name
    file_id = message.document.file_id
    size = format_size(message.document.file_size)
    quality = extract_quality(filename)
    
    # We'll use the filename as title if no imdbID is provided in the session
    # For a simple implementation, let's just ask for imdbID or use a dummy
    # Realistically, the admin would use /add [imdbID] first.
    
    # Simple logic: check if the caption has the imdbID
    imdb_id = message.caption if message.caption and message.caption.startswith("tt") else "tt0000000"
    title = filename.split(".")[0].replace("_", " ").replace("-", " ")

    movie_id = str(uuid.uuid4())[:8]

    # Update or Insert
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
        f"✅ File Indexed!\n"
        f"Title: {title}\n"
        f"IMDb: {imdb_id}\n"
        f"Quality: {quality}\n"
        f"Size: {size}\n"
        f"Internal ID: {movie_id}"
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
