import os
import requests
from typing import Optional

class LinkService:
    def __init__(self):
        # Configuration for FileToLink backend
        self.file_to_link_url = os.getenv("FILE_TO_LINK_API", "http://your-filetolink-instance.com/api")
        self.api_token = os.getenv("FILE_TO_LINK_TOKEN", "")

    async def get_direct_link(self, movie_id: str) -> Optional[str]:
        # In a real scenario, this would convert movie_id (DB ID) -> Telegram file_id -> Link
        # Integrating with FileToLink backend logic
        
        # Mocking the interaction with FileToLink API
        # Example: return f"https://server.filetolink.com/dl/{movie_id}"
        
        # Real logic would look like:
        # response = requests.post(f"{self.file_to_link_url}/generate", json={"file_id": movie_id}, headers={"Authorization": f"Bearer {self.api_token}"})
        # return response.json().get("link")
        
        return f"https://demo-link.com/download/{movie_id}.mp4"

link_service = LinkService()
