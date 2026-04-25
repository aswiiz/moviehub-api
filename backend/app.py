import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes import search, link, stream
from services.stream_service import stream_service
from database.connection import db
import os
import sys

# Add root directory to path to import admin_bot
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from admin_bot.bot import app as admin_bot_app
except ImportError:
    admin_bot_app = None
    print("⚠️ Could not import admin_bot. Ensure it exists in the root directory.")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MovieHub API")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Lifecycle
@app.on_event("startup")
async def startup_db_client():
    await db.connect_db()
    await stream_service.start()
    if admin_bot_app:
        await admin_bot_app.start()
    logger.info("Connected to MongoDB, Telegram Streamer, and Admin Bot")

@app.on_event("shutdown")
async def shutdown_db_client():
    await db.close_db()
    await stream_service.stop()
    if admin_bot_app:
        await admin_bot_app.stop()
    logger.info("Closed MongoDB and Telegram Clients")

# Error Handling
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred", "detail": str(exc)},
    )

# Routes
app.include_router(search.router)
app.include_router(link.router)
app.include_router(stream.router)

@app.get("/")
async def root():
    return {"status": "online", "message": "MovieHub Backend is active"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
