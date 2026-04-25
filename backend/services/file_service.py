import os
import httpx
from database.connection import db
from bson import ObjectId

class FileService:
    def __init__(self):
        self.api_base = os.getenv("FILE_TO_LINK_API", "https://api.filetolink.com")

    async def get_download_link(self, movie_id: str) -> str:
        # 1. Fetch file_id from DB using movie_id (internal MongoDB ID)
        doc = await db.db.files.find_one({"_id": ObjectId(movie_id)})
        if not doc:
            raise Exception("File not found in database")
        
        file_id = doc.get("file_id")
        if not file_id:
            raise Exception("Telegram file_id not found for this entry")

        # 2. Call external FileToLink API
        # Format: GET {FILE_TO_LINK_API}/get-link?movie_id=<file_id>
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/get-link",
                params={"movie_id": file_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("url")
            else:
                raise Exception(f"FileToLink API error: {response.text}")

file_service = FileService()
