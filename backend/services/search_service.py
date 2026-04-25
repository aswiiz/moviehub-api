import re
from typing import List
from database.connection import db
from models.movie import Movie, MovieFile

class SearchService:
    async def search_movies(self, query: str) -> List[Movie]:
        # Perform regex search on the 'movie_name' or 'file_name' field
        # Assuming the collection name is 'files' based on previous context
        # Adjust 'movie_name' to the actual field name in the provided DB
        cursor = db.db.files.find({
            "file_name": {"$regex": query, "$options": "i"}
        })

        movie_map = {}

        async for doc in cursor:
            title = doc.get("movie_name", doc.get("file_name", "Unknown"))
            imdb_id = doc.get("imdbID", doc.get("imdb_id", "tt0000000"))
            
            # Clean title: usually remove quality tags etc for grouping
            # For now, we trust the DB has a clean 'movie_name'
            
            if imdb_id not in movie_map:
                movie_map[imdb_id] = Movie(
                    title=title,
                    imdbID=imdb_id,
                    files=[]
                )
            
            # Avoid duplicate qualities for the same movie if necessary
            # For now, we just add all files
            movie_map[imdb_id].files.append(MovieFile(
                quality=doc.get("quality", "Unknown"),
                size=doc.get("size", "Unknown"),
                movie_id=str(doc.get("_id")) # This is the internal ID used for get-link
            ))

        return list(movie_map.values())

search_service = SearchService()
