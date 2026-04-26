import os
import base64
from database.connection import db
from bson import ObjectId

class FileService:
    def __init__(self):
        # Prefer RENDER_EXTERNAL_URL if set, otherwise use BACKEND_URL, fallback to localhost
        self.backend_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("BACKEND_URL", "http://localhost:8000")
        # Ensure no trailing slash
        self.backend_url = self.backend_url.rstrip('/')
        self.bot_username = os.getenv("BOT_USERNAME", "greenmoviebot")

    def encode_file_id(self, file_id: str) -> str:
        """Encode file_id to be URL-safe for Telegram's start parameter."""
        return base64.urlsafe_b64encode(file_id.encode()).decode().rstrip("=")

    def decode_file_id(self, encoded_id: str) -> str:
        """Decode the encoded file_id from Telegram's start parameter."""
        try:
            # Add padding back if missing
            padding = '=' * (4 - len(encoded_id) % 4)
            return base64.urlsafe_b64decode(encoded_id + padding).decode()
        except:
            return encoded_id  # Fallback to raw if decoding fails

    def get_telegram_link(self, file_id: str) -> str:
        """Generate a Telegram deep link for the given file_id."""
        encoded = self.encode_file_id(file_id)
        return f"https://t.me/{self.bot_username}?start={encoded}"


    async def get_download_link(self, movie_id: str) -> str:
        # 1. Find the file in the database (supporting both flat and nested schemas)
        doc = await db.db.movies.find_one({
            "$or": [
                {"file_id": movie_id},
                {"movie_id": movie_id},
                {"files.file_id": movie_id},
                {"files.movie_id": movie_id}
            ]
        })

        if not doc:
            raise Exception("File not found in database")
        
        file_id = None
        
        # Check if it's a flat document (new schema)
        if doc.get("file_id") == movie_id or doc.get("movie_id") == movie_id:
            file_id = doc.get("file_id")
        else:
            # Check if it's a nested document (old schema)
            for file in doc.get("files", []):
                if file.get("file_id") == movie_id or file.get("movie_id") == movie_id:
                    file_id = file.get("file_id")
                    break
        
        if not file_id:
            raise Exception("Telegram file_id not found")

        # 2. Return the Telegram deep link
        return self.get_telegram_link(file_id)

file_service = FileService()
