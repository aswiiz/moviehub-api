import os
from database.connection import db
from bson import ObjectId

class FileService:
    def __init__(self):
        # We use our own backend as the streaming server
        # This matches the FileToLink logic but is built-in
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

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
