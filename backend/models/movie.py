from pydantic import BaseModel
from typing import List, Optional

class MovieFile(BaseModel):
    quality: str
    size: str
    movie_id: str # internal ID or file_id

class Movie(BaseModel):
    title: str
    imdbID: str
    files: List[MovieFile]

class LinkResponse(BaseModel):
    url: str
