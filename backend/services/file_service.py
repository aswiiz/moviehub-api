import os
from database.connection import db
from bson import ObjectId

class FileService:
    def __init__(self):
        # Prefer RENDER_EXTERNAL_URL if set, otherwise use BACKEND_URL, fallback to localhost
        self.backend_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("BACKEND_URL", "http://localhost:8000")
        # Ensure no trailing slash
        self.backend_url = self.backend_url.rstrip('/')

    async def get_download_link(self, movie_id: str) -> str:
        # 1. Find the file in the database
        doc = await db.db.movies.find_one({"files.movie_id": movie_id})
        if not doc:
            raise Exception("File not found in database")
        
        file_id = None
        for file in doc.get("files", []):
            if file.get("movie_id") == movie_id:
                file_id = file.get("file_id")
                break
        
        if not file_id:
            raise Exception("Telegram file_id not found")

        # 2. Return the link to our built-in stream route
        # This follows the VJBots/FileToLink pattern of providing a direct web link
        return f"{self.backend_url}/dl/{file_id}"

file_service = FileService()
