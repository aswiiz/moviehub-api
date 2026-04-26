import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
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
        logger.info("Starting Admin Bot...")
        await admin_bot_app.start()
        logger.info("Admin Bot started successfully")
    else:
        logger.warning("Admin Bot app is None, skipping startup")
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

@app.get("/api/info")
async def api_info():
    return {
        "status": "online", 
        "message": "MovieHub Backend is active",
        "bot_username": os.getenv("BOT_USERNAME", "MovieHubAdminBot")
    }

# Serve Frontend - Mount at the end to avoid capturing API routes
# Try to find 'frontend' directory in current or parent folder (for Render/Vercel support)
frontend_path = "frontend"
if not os.path.exists(frontend_path):
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    logger.warning(f"Frontend directory not found at {frontend_path}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
