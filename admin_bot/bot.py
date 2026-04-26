import os
import re
import uuid
import asyncio
import logging
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultCachedDocument, InlineQueryResultCachedVideo, InlineQueryResultCachedAudio
from pyrogram.errors import FloodWait
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_ID_ENV = os.getenv("API_ID", "").strip()
API_ID = int(API_ID_ENV) if API_ID_ENV else 0
API_HASH = os.getenv("API_HASH", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_ENV = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID_ENV) if ADMIN_ID_ENV else 0
MONGO_URI = os.getenv("MONGO_URI")
INDEX_CHANNELS_STR = os.getenv("INDEX_CHANNELS", "")
INDEX_CHANNELS = [int(x.strip()) for x in INDEX_CHANNELS_STR.split(",") if x.strip()]

if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.error("Missing critical environment variables (API_ID, API_HASH, BOT_TOKEN).")

# Database setup
client = AsyncIOMotorClient(MONGO_URI)
db = client.get_default_database()
movies_collection = db.movies

async def init_db():
    await movies_collection.create_index("file_id", unique=True)
    await movies_collection.create_index([("file_name", "text"), ("caption", "text"), ("title", "text")])
    logger.info("Database indexes ensured.")

app = Client("admin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def extract_metadata(filename):
    normalized = re.sub(r'[\._\-]', ' ', str(filename))
    normalized = re.sub(r'@\w+|www\.\S+|http\S+|t\.me/\S+', '', normalized, flags=re.IGNORECASE)
    
    quality = "HD"
    for q in ["480p", "720p", "1080p", "2160p", "4k", "cam", "hdtv", "web-dl", "bluray"]:
        if re.search(rf'\b{q}\b', normalized, re.IGNORECASE):
            quality = q.upper()
            break
            
    year_match = re.search(r'\b(19|20)\d{2}\b', normalized)
    year = int(year_match.group()) if year_match else None
    
    languages = ["hindi", "english", "tamil", "telugu", "malayalam", "kannada", "bengali", "marathi", "gujarati", "punjabi", "urdu", "korean", "japanese", "spanish", "french"]
    language = "Unknown"
    for lang in languages:
        if re.search(rf'\b{lang}\b', normalized, re.IGNORECASE):
            language = lang.capitalize()
            break
            
    se_match = re.search(r'\bS(\d{1,2})E(\d{1,2})\b', normalized, re.IGNORECASE)
    season = int(se_match.group(1)) if se_match else None
    episode = int(se_match.group(2)) if se_match else None
    
    title = normalized
    title = re.sub(rf'\b{quality}\b', '', title, flags=re.IGNORECASE)
    if year:
        title = re.sub(rf'\b{year}\b', '', title)
    if language != "Unknown":
        title = re.sub(rf'\b{language}\b', '', title, flags=re.IGNORECASE)
    if se_match:
        title = re.sub(r'\bS\d{1,2}E\d{1,2}\b', '', title, flags=re.IGNORECASE)
        
    title = re.sub(r'\b(mkv|mp4|avi|webm|mp3|flac|wav|m4a)\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[\[\]\(\)\{\}]', '', title)
    title = ' '.join(title.split()).title()
    
    return {
        "title": title,
        "quality": quality,
        "year": year,
        "language": language,
        "season": season,
        "episode": episode
    }

def format_size(size):
    if not isinstance(size, (int, float)):
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f}{unit}"
        size /= 1024.0
    return "Unknown"

@app.on_message(filters.command("start") & filters.user(ADMIN_ID))
async def start(client, message):
    await message.reply_text(
        f"👋 **Welcome Admin!**\n\n"
        "I can index movies and series for your MovieHub app.\n\n"
        "**Available Commands:**\n"
        "🚀 `/index [channel]` - Index all files from a public/admin channel\n"
        "📥 **Forwarding** - Forward files from a private channel to index them silently!\n"
        "📂 `/list` - List recent indexed movies\n"
        "🗑 `/delete [imdbID]` - Delete a movie\n"
        "⚙️ `/stats` - Show database statistics",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Channel Indexing", callback_data="help_index")]
        ])
    )

@app.on_message(filters.command("stats") & filters.user(ADMIN_ID))
async def stats(client, message):
    total_files = await movies_collection.count_documents({})
    
    await message.reply_text(
        "📊 **Database Statistics**\n\n"
        f"📁 Total Files Indexed: {total_files}"
    )

@app.on_message(filters.command("index") & filters.user(ADMIN_ID))
async def index_channel(client, message):
    if len(message.command) < 2:
        return await message.reply_text(
            "Usage: `/index [channel_username/id]`\n\n"
            "⚠️ **Note on Private Channels:**\n"
            "I cannot index private channels via invite links. To index a private channel, simply **select all files and forward them to me**. I will silently index them in the background!"
        )
    
    chat_id = message.command[1]
    status_msg = await message.reply_text(f"🔍 **Starting indexing for `{chat_id}`...**")
    await perform_index(chat_id, status_msg)

async def perform_index(chat_id, status_msg):
    count = 0
    skipped = 0
    try:
        chat = await app.get_chat(chat_id)
        
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
                file = m.document or m.video or m.audio
                if not file:
                    continue
                    
                filename = getattr(file, 'file_name', "Unknown")
                if not filename.lower().endswith(('.mkv', '.mp4', '.avi', '.mp3', '.flac', '.webm')):
                    skipped += 1
                    continue
                    
                file_id = file.file_id
                size = file.file_size
                meta = extract_metadata(filename)
                caption = m.caption.html if m.caption else ""
                
                try:
                    await movies_collection.insert_one({
                        "file_id": file_id,
                        "file_name": filename,
                        "file_size": size,
                        "mime_type": getattr(file, 'mime_type', 'application/octet-stream'),
                        "caption": caption,
                        "title": meta['title'],
                        "quality": meta['quality'],
                        "year": meta['year'],
                        "language": meta['language'],
                        "season": meta['season'],
                        "episode": meta['episode'],
                        "indexed_at": datetime.utcnow()
                    })
                    count += 1
                except DuplicateKeyError:
                    skipped += 1
                    
                if count % 20 == 0:
                    await status_msg.edit_text(
                        f"🔄 **Indexing `{chat_id}`...**\n"
                        f"✅ Added: {count}\n"
                        f"⏩ Skipped: {skipped}"
                    )
            except FloodWait as e:
                logger.warning(f"FloodWait: Sleeping for {e.value} seconds.")
                await asyncio.sleep(e.value)
            except Exception as inner_e:
                logger.error(f"Error indexing message {m.id}: {inner_e}")
                skipped += 1
                continue
        
        await status_msg.edit_text(
            f"✅ **Indexing Complete!**\n"
            f"📍 Chat: `{chat_id}`\n"
            f"📂 Total Added: {count}\n"
            f"⏩ Total Skipped: {skipped}"
        )
    except Exception as e:
        logger.error(f"Error during perform_index: {e}")
        await status_msg.edit_text(f"❌ **Error during indexing:**\n`{str(e)}`")

@app.on_message(filters.forwarded & filters.user(ADMIN_ID))
async def handle_forwarded_message(client, message: Message):
    if message.forward_from_chat and message.forward_from_chat.type == enums.ChatType.CHANNEL:
        source_chat = message.forward_from_chat
        try:
            member = await app.get_chat_member(source_chat.id, "me")
            if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                status_msg = await message.reply_text(f"💎 **Bot is Admin in `{source_chat.title or 'Private Channel'}`!**\nIndexing the entire channel...")
                await perform_index(source_chat.id, status_msg)
                return
        except Exception:
            pass 
            
        if not (message.document or message.video or message.audio):
            await message.reply_text(
                "❌ **Cannot Index Channel**\n\n"
                "You forwarded a message from a channel, but I am **not an admin** there.\n"
                "Telegram's API physically prevents bots from reading the history of private channels they are not admins in.\n\n"
                "**Solutions:**\n"
                "1. Add this bot as an Admin to that private channel, then forward a message again.\n"
                "2. If you can't add the bot as an admin, you must manually select and forward the files (up to 100 at a time) to me."
            )
            return
            
    if message.document or message.video or message.audio:
        await process_single_file(message)

@app.on_message((filters.document | filters.video | filters.audio) & ~filters.forwarded & filters.user(ADMIN_ID))
async def handle_direct_file(client, message: Message):
    await process_single_file(message)

async def process_single_file(message: Message, auto_index=False):
    file = message.document or message.video or message.audio
    if not file:
        return
        
    filename = getattr(file, 'file_name', "Unknown")
    file_id = file.file_id
    size = getattr(file, 'file_size', 0)
    meta = extract_metadata(filename)
    caption = message.caption.html if message.caption else ""

    try:
        await movies_collection.insert_one({
            "file_id": file_id,
            "file_name": filename,
            "file_size": size,
            "mime_type": getattr(file, 'mime_type', 'application/octet-stream'),
            "caption": caption,
            "title": meta['title'],
            "quality": meta['quality'],
            "year": meta['year'],
            "language": meta['language'],
            "season": meta['season'],
            "episode": meta['episode'],
            "indexed_at": datetime.utcnow()
        })
        is_new = True
    except DuplicateKeyError:
        is_new = False
    except Exception as e:
        logger.error(f"Error inserting single file: {e}")
        is_new = False

    if not auto_index and not message.forward_from_chat and not message.forward_from:
        if is_new:
            await message.reply_text(
                f"✅ **Single File Indexed!**\n\n"
                f"🎬 **Title:** {meta['title']}\n"
                f"💎 **Quality:** {meta['quality']}\n"
                f"📦 **Size:** {format_size(size)}\n"
            )
        else:
            await message.reply_text("⚠️ File already indexed.")

if INDEX_CHANNELS:
    @app.on_message(filters.chat(INDEX_CHANNELS) & (filters.document | filters.video | filters.audio))
    async def auto_index_channel_handler(client, message):
        await process_single_file(message, auto_index=True)

@app.on_inline_query()
async def inline_search(client, query: InlineQuery):
    q = query.query.strip()
    if not q:
        return
        
    offset = int(query.offset) if query.offset else 0
    limit = 20
    
    try:
        cursor = movies_collection.find(
            {"$text": {"$search": q}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).skip(offset).limit(limit)
        
        results = await cursor.to_list(length=limit)
        
        if not results:
            regex = re.compile(q, re.IGNORECASE)
            cursor = movies_collection.find({"$or": [{"file_name": regex}, {"caption": regex}]}).skip(offset).limit(limit)
            results = await cursor.to_list(length=limit)
            
        inline_results = []
        for res in results:
            file_id = res['file_id']
            file_name = res['file_name']
            caption = res.get('caption', file_name)
            size = format_size(res.get('file_size', 0))
            
            title = res.get('title', file_name)
            year = f" ({res['year']})" if res.get('year') else ""
            quality = f" [{res['quality']}]" if res.get('quality') and res['quality'] != "HD" else ""
            lang = f" [{res['language']}]" if res.get('language') and res['language'] != "Unknown" else ""
            
            display_title = f"{title}{year}{quality}{lang}"
            description = f"Size: {size}"
            
            if file_name.lower().endswith(('.mp3', '.flac', '.wav', '.m4a')):
                inline_results.append(InlineQueryResultCachedAudio(
                    audio_file_id=file_id,
                    caption=caption
                ))
            elif file_name.lower().endswith(('.mp4', '.mkv', '.webm', '.avi')):
                inline_results.append(InlineQueryResultCachedVideo(
                    video_file_id=file_id,
                    title=display_title,
                    description=description,
                    caption=caption
                ))
            else:
                inline_results.append(InlineQueryResultCachedDocument(
                    title=display_title,
                    document_file_id=file_id,
                    description=description,
                    caption=caption
                ))
                
        next_offset = str(offset + limit) if len(results) == limit else ""
        await query.answer(inline_results, cache_time=300, next_offset=next_offset)
    except Exception as e:
        logger.error(f"Inline search error: {e}")

@app.on_message(filters.command("list") & filters.user(ADMIN_ID))
async def list_movies(client, message):
    cursor = movies_collection.find().sort("indexed_at", -1).limit(20)
    movies = await cursor.to_list(length=20)
    text = "📂 Recent Indexed Movies:\n\n"
    for m in movies:
        title = m.get('title', m.get('file_name', 'Unknown'))
        size = format_size(m.get('file_size', 0))
        text += f"🎬 {title} - {m.get('quality', 'HD')} ({size})\n"
    
    if not movies:
        text = "No movies indexed yet."
    
    await message.reply_text(text)

@app.on_message(filters.command("delete") & filters.user(ADMIN_ID))
async def delete_movie(client, message):
    # This might need updating to delete by file_id if we removed imdbID
    if len(message.command) < 2:
        return await message.reply_text("Usage: /delete [file_id]")
    
    file_id = message.command[1]
    result = await movies_collection.delete_one({"file_id": file_id})
    
    if result.deleted_count:
        await message.reply_text(f"🗑 Deleted file {file_id}")
    else:
        await message.reply_text("File not found.")

if __name__ == "__main__":
    logger.info("Initializing database...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    logger.info("Admin Bot Starting...")
    app.run()
