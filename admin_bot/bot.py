import os
import re
import uuid
import base64
import asyncio
import logging
import aiohttp
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, InlineQuery, InlineQueryResultCachedDocument, InlineQueryResultCachedVideo, InlineQueryResultCachedAudio
from pyrogram.errors import FloodWait
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from bson import ObjectId, errors
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
OMDB_API_KEY = os.getenv("OMDB_API_KEY", "9547e152")

if not API_ID or not API_HASH or not BOT_TOKEN:
    logger.error("Missing critical environment variables (API_ID, API_HASH, BOT_TOKEN).")

# Database setup
client = AsyncIOMotorClient(MONGO_URI)
db = client['moviehub']
movies_collection = db.movies

async def init_db():
    await movies_collection.create_index("file_id", unique=True)
    await movies_collection.create_index("search_text")
    await movies_collection.create_index([("file_name", "text"), ("caption", "text"), ("clean_name", "text")])
    # For logging and tracking
    await db.downloads.create_index([("timestamp", -1)])
    logger.info("Database indexes ensured.")

app = Client("admin_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

async def get_imdb_data(title, year=None):
    """Fetch real IMDb ID and Title from OMDb API."""
    url = f"https://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
    if year:
        url += f"&y={year}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("Response") == "True":
                        return {
                            "imdbID": data.get("imdbID"),
                            "title": data.get("Title"),
                            "year": data.get("Year")
                        }
    except Exception as e:
        logger.error(f"OMDb Error: {e}")
    return None

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[_\-.]", " ", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def extract_metadata(filename):
    clean_name = normalize(filename)
    
    quality = "HD"
    for q in ["480p", "720p", "1080p", "2160p", "4k", "cam", "hdtv", "web-dl", "bluray"]:
        if re.search(rf'\b{q}\b', clean_name, re.IGNORECASE):
            quality = q.upper()
            break
            
    year_match = re.search(r'\b(19|20)\d{2}\b', clean_name)
    year = int(year_match.group()) if year_match else None
    
    languages = ["hindi", "english", "tamil", "telugu", "malayalam", "kannada", "bengali", "marathi", "gujarati", "punjabi", "urdu", "korean", "japanese", "spanish", "french"]
    language = "Unknown"
    for lang in languages:
        if re.search(rf'\b{lang}\b', clean_name, re.IGNORECASE):
            language = lang.capitalize()
            break
            
    se_match = re.search(r'\bS(\d{1,2})E(\d{1,2})\b', clean_name, re.IGNORECASE)
    season = int(se_match.group(1)) if se_match else None
    episode = int(se_match.group(2)) if se_match else None
    
    return {
        "clean_name": clean_name,
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

@app.on_message(filters.command("start"))
async def start(client, message):
    if len(message.command) > 1:
        payload = message.command[1]
        
        # Base64 decoding with padding fix
        try:
            # Add padding back if missing
            padding = '=' * (4 - len(payload) % 4)
            file_id = base64.urlsafe_b64decode(payload + padding).decode()
        except Exception:
            # Fallback to raw payload if decoding fails (for backward compatibility)
            file_id = payload
        
        # Try to find file info in DB (by file_id or ObjectId)
        file_info = await movies_collection.find_one({"file_id": file_id})
        
        if not file_info:
            try:
                # Try lookup by ObjectId if it's a valid 24-char hex
                if len(file_id) == 24:
                    file_info = await movies_collection.find_one({"_id": ObjectId(file_id)})
            except (errors.InvalidId, TypeError):
                pass

        if file_info:
            # Use the actual file_id from the database for sending
            real_file_id = file_info.get("file_id")
        else:
            real_file_id = file_id # Fallback
            
        caption = file_info.get("caption") if file_info else ""
        title = file_info.get("title", "Your Movie") if file_info else "Your Movie"
        
        try:
            # Send the file instantly
            await message.reply_chat_action(enums.ChatAction.UPLOAD_DOCUMENT)
            await client.send_cached_media(
                chat_id=message.chat.id,
                file_id=real_file_id,
                caption=caption or f"🎬 **{title}**\n\n@MovieHub",
                parse_mode=enums.ParseMode.HTML
            )
            
            # Log the download
            await db.downloads.insert_one({
                "file_id": file_id,
                "user_id": message.from_user.id,
                "username": message.from_user.username,
                "title": title,
                "timestamp": datetime.utcnow()
            })
            logger.info(f"File {file_id} delivered to user {message.from_user.id}")
            
        except Exception as e:
            logger.error(f"Error sending file {file_id}: {e}")
            await message.reply_text("❌ **Error: Could not send file.**\nThe file might have been deleted or the ID is invalid.")
        return

    # No parameter - check if Admin
    if message.from_user.id == ADMIN_ID:
        await message.reply_text(
            f"👋 **Welcome Admin!**\n\n"
            "I can index movies and series for your MovieHub app.\n\n"
            "**Available Commands:**\n"
            "🚀 `/index [channel]` - Index all files from a public/admin channel\n"
            "📥 **Forwarding** - Forward files from a private channel to index them silently!\n"
            "📂 `/list` - List recent indexed movies\n"
            "🗑 `/delete [file_id]` - Delete a movie file\n"
            "⚙️ `/stats` - Show database statistics",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Channel Indexing", callback_data="help_index")]
            ])
        )
    else:
        # Regular user welcome
        await message.reply_text(
            f"👋 **Welcome to MovieHub!**\n\n"
            "I can help you get the movies you search for in the app.\n\n"
            "👉 **Open the app and search for any movie to get started!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Open MovieHub Website", url="https://moviehub-api-five.vercel.app/")]
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
                
                # Try to enrich with real IMDb metadata
                imdb_data = await get_imdb_data(meta['title'], meta['year'])
                final_imdb_id = imdb_data['imdbID'] if imdb_data else f"hub_{abs(hash(meta['title'])) % 10000000}"
                final_title = imdb_data['title'] if imdb_data else meta['title']
                
                # Generate search_text for efficient querying
                clean_name = meta['clean_name']
                search_text = clean_name + " " + normalize(caption or "")

                try:
                    await movies_collection.insert_one({
                        "file_id": file_id,
                        "file_name": filename,
                        "clean_name": clean_name,
                        "search_text": search_text,
                        "file_size": size,
                        "mime_type": getattr(file, 'mime_type', 'application/octet-stream'),
                        "caption": caption,
                        "title": final_title, # Keep for display
                        "imdbID": final_imdb_id,
                        "quality": meta['quality'],
                        "year": meta['year'] or (imdb_data['year'] if imdb_data else None),
                        "language": meta['language'],
                        "season": meta['season'],
                        "episode": meta['episode'],
                        "indexed_at": datetime.utcnow()
                    })
                    count += 1
                    logger.info(f"Indexed: {filename} (search_text: {search_text})")
                except DuplicateKeyError:
                    skipped += 1
                    logger.debug(f"Skipped (Duplicate): {filename}")
                except Exception as insert_e:
                    logger.error(f"Error inserting {filename}: {insert_e}")
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

    # Try to enrich with real IMDb metadata
    imdb_data = await get_imdb_data(meta['title'], meta['year'])
    final_imdb_id = imdb_data['imdbID'] if imdb_data else f"hub_{abs(hash(meta['title'])) % 10000000}"
    final_title = imdb_data['title'] if imdb_data else meta['title']

    # Generate search_text for efficient querying
    clean_name = meta['clean_name']
    search_text = clean_name + " " + normalize(caption or "")

    try:
        await movies_collection.insert_one({
            "file_id": file_id,
            "file_name": filename,
            "clean_name": clean_name,
            "search_text": search_text,
            "file_size": size,
            "mime_type": getattr(file, 'mime_type', 'application/octet-stream'),
            "caption": caption,
            "title": final_title,
            "imdbID": final_imdb_id,
            "quality": meta['quality'],
            "year": meta['year'] or (imdb_data['year'] if imdb_data else None),
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
                f"🎬 **Title:** {final_title}\n"
                f"💎 **IMDb:** {final_imdb_id}\n"
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
