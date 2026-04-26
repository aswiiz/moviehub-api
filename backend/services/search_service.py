import re
from typing import List
from database.connection import db
from models.movie import Movie, MovieFile

class SearchService:
    def format_size(self, size):
        if not isinstance(size, (int, float)):
            return str(size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return str(size)

    async def search_movies(self, query: str) -> List[Movie]:
        # Search the flat 'movies' collection and aggregate by title
        pipeline = [
            {
                "$match": {
                    "$or": [
                        {"title": {"$regex": query, "$options": "i"}},
                        {"file_name": {"$regex": query, "$options": "i"}},
                        {"caption": {"$regex": query, "$options": "i"}}
                    ]
                }
            },
            {
                "$group": {
                    "_id": "$title",
                    "files": {
                        "$push": {
                            "quality": "$quality",
                            "size": "$file_size",
                            "movie_id": "$file_id",
                            "caption": "$caption",
                            "file_name": "$file_name"
                        }
                    }
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        cursor = db.db.movies.aggregate(pipeline)

        results = []

        async for doc in cursor:
            files = [
                MovieFile(
                    quality=f.get("quality", "Unknown"),
                    size=self.format_size(f.get("size", 0)),
                    movie_id=f.get("movie_id"),
                    caption=f.get("caption"),
                    file_name=f.get("file_name")
                )
                for f in doc.get("files", [])
            ]

            # Sort files by quality (Highest first)
            def quality_rank(q):
                ranks = {"4K": 5, "2160P": 5, "1080P": 4, "720P": 3, "480P": 2, "HD": 1, "CAM": 0}
                return ranks.get(q.upper(), -1)

            files.sort(key=lambda x: quality_rank(x.quality), reverse=True)

            results.append(Movie(
                title=doc.get("_id", "Unknown"),
                imdbID=f"hub_{abs(hash(doc.get('_id', 'Unknown'))) % 10000000}", # Generate deterministic ID based on title
                files=files
            ))

        return results

search_service = SearchService()
