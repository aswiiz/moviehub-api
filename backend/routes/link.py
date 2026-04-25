from fastapi import APIRouter, Query, HTTPException
from models.movie import LinkResponse
from services.file_service import file_service

router = APIRouter()

@router.get("/get-link", response_model=LinkResponse)
async def get_link(movie_id: str = Query(..., min_length=1)):
    try:
        url = await file_service.get_download_link(movie_id)
        return LinkResponse(url=url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
