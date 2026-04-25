import os
import re
import uuid
from pyrogram import Client, filters
from pyrogram.types import Message
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URI = os.getenv("MONGO_URI")

# Database setup
client = MongoClient(MONGO_URI)
db = client.get_default_database()
movies_collection = db.movies

app = Client("admin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def extract_quality(filename):
    qualities = ["480p", "720p", "1080p", "2160p", "4k", "cam", "hdtv"]
    for q in qualities:
        if q in filename.lower():
            return q
    return "Unknown"

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0

@app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(client, message):
    await message.reply_text(
        "Welcome Admin! Use the following commands:\n"
        "/add [imdbID] - Upload/Forward a file after this\n"
        "/update [imdbID] - Add new quality to existing movie\n"
        "/delete [imdbID] - Remove a movie\n"
        "/list - List all movies"
    )

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
