import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_db(cls):
        cls.client = AsyncIOMotorClient(MONGO_URI)
        cls.db = cls.client['moviehub'] # Explicitly setting the DB name

    @classmethod
    async def close_db(cls):
        cls.client.close()

db = Database()
