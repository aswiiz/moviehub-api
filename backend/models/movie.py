from pydantic import BaseModel
from typing import List, Optional

class MovieFile(BaseModel):
    quality: str
    size: str
    movie_id: str # internal ID or file_id
    telegram_link: Optional[str] = None
    caption: Optional[str] = None
    file_name: Optional[str] = None
    year: Optional[int] = None
    language: Optional[str] = None
    season: Optional[int] = None
    episode: Optional[int] = None

class Movie(BaseModel):
    title: str
    imdbID: str
    year: Optional[int] = None
    files: List[MovieFile]

class LinkResponse(BaseModel):
    url: str
