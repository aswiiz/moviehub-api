from fastapi import APIRouter, Query
from typing import List
from models.movie import Movie
from services.search_service import search_service

router = APIRouter()

@router.get("/search", response_model=List[Movie])
async def search(query: str = Query(..., min_length=1)):
    return await search_service.search_movies(query)
