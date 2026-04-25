import os
import asyncio
from pyrogram import Client
from fastapi import Request
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

class StreamService:
    def __init__(self):
        self.api_id = int(os.getenv("API_ID"))
        self.api_hash = os.getenv("API_HASH")
        self.bot_token = os.getenv("BOT_TOKEN")
        self.client = Client(
            "stream_session",
            api_id=self.api_id,
            api_hash=self.api_hash,
            bot_token=self.bot_token,
            in_memory=True
        )

    async def start(self):
        await self.client.start()

    async def stop(self):
        await self.client.stop()

    async def generate_stream(self, file_id: str, offset: int = 0) -> AsyncGenerator[bytes, None]:
        # Using pyrogram's get_file and yield_file logic
        # For simplicity in this implementation, we use the stream_media helper if available
        # or a custom chunk-by-chunk downloader
        
        chunk_size = 1024 * 1024 # 1MB
        async for chunk in self.client.stream_media(file_id, offset=offset):
            yield chunk

stream_service = StreamService()
