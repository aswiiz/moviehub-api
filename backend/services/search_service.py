import re
from typing import List
from database.connection import db
from models.movie import Movie, MovieFile

class SearchService:
    async def search_movies(self, query: str) -> List[Movie]:
        # Search the 'movies' collection (updated schema)
        cursor = db.db.movies.find({
            "title": {"$regex": query, "$options": "i"}
        }).sort("title", 1) # Sort alphabetically by title

        results = []

        async for doc in cursor:
            # The files are already grouped in the document array
            files = [
                MovieFile(
                    quality=f.get("quality", "Unknown"),
                    size=f.get("size", "Unknown"),
                    movie_id=f.get("movie_id")
                )
                for f in doc.get("files", [])
            ]

            # Sort files by quality (Highest first)
            def quality_rank(q):
                ranks = {"4K": 5, "2160P": 5, "1080P": 4, "720P": 3, "480P": 2, "HD": 1, "CAM": 0}
                return ranks.get(q.upper(), -1)

            files.sort(key=lambda x: quality_rank(x.quality), reverse=True)

            results.append(Movie(
                title=doc.get("title", "Unknown"),
                imdbID=doc.get("imdbID", "tt0000000"),
                files=files
            ))

        return results

search_service = SearchService()
