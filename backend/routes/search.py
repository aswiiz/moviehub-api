from fastapi import APIRouter, Query
from typing import List
from models.movie import Movie
from services.search_service import search_service

router = APIRouter()

@router.get("/search", response_model=List[Movie])
async def search(
    query: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    return await search_service.search_movies(query, limit, offset)
