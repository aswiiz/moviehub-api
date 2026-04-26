from fastapi import APIRouter, Header, Request, HTTPException
from fastapi.responses import StreamingResponse
from services.stream_service import stream_service
from database.connection import db

router = APIRouter()

@router.get("/dl/{file_id}")
async def download_file(file_id: str, request: Request, range: str = Header(None)):
    # In a real scenario, we'd handle Range requests for seeking in videos
    # For now, we provide a basic stream
    
    try:
        # Check if file exists in our DB (security and metadata)
        doc = await db.db.movies.find_one({
            "$or": [
                {"file_id": file_id},
                {"files.file_id": file_id}
            ]
        })
        
        if not doc:
            raise HTTPException(status_code=404, detail="File not indexed")

        # Get filename
        filename = "movie.mp4"
        if doc.get("file_id") == file_id:
            filename = doc.get("file_name", "movie.mp4")
        else:
            for f in doc.get("files", []):
                if f.get("file_id") == file_id:
                    filename = f.get("file_name", "movie.mp4")
                    break

        return StreamingResponse(
            stream_service.generate_stream(file_id),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Accept-Ranges": "bytes"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
