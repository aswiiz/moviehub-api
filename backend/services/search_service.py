import re
from datetime import datetime
from typing import List
from database.connection import db
from models.movie import Movie, MovieFile
from services.file_service import file_service

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
        # Split query into keywords for better matching (multi-keyword support)
        keywords = query.split()
        if not keywords:
            return []
            
        # Match each keyword against title, file_name, or caption
        match_conditions = []
        for kw in keywords:
            escaped_kw = re.escape(kw)
            match_conditions.append({
                "$or": [
                    {"title": {"$regex": escaped_kw, "$options": "i"}},
                    {"file_name": {"$regex": escaped_kw, "$options": "i"}},
                    {"caption": {"$regex": escaped_kw, "$options": "i"}}
                ]
            })

        pipeline = [
            {
                "$match": {"$and": match_conditions}
            },
            {
                # Normalize documents: if "files" array exists (old schema), use it.
                # Otherwise, wrap the flat fields (new schema) into an array.
                "$project": {
                    "title": 1,
                    "imdbID": 1,
                    "file_data": {
                        "$cond": {
                            "if": {"$isArray": "$files"},
                            "then": "$files",
                            "else": [{
                                "quality": "$quality",
                                "file_size": "$file_size",
                                "size": "$size",
                                "file_id": "$file_id",
                                "movie_id": "$movie_id",
                                "caption": "$caption",
                                "file_name": "$file_name",
                                "year": "$year",
                                "language": "$language",
                                "season": "$season",
                                "episode": "$episode",
                                "imdbID": "$imdbID"
                            }]
                        }
                    }
                }
            },
            {"$unwind": "$file_data"},
            {
                "$group": {
                    "_id": "$title",
                    "imdbID": { "$first": "$file_data.imdbID" },
                    "year": { "$first": "$file_data.year" },
                    "files": {
                        "$push": {
                            "quality": "$file_data.quality",
                            "size": { "$ifNull": ["$file_data.file_size", "$file_data.size"] },
                            "movie_id": { "$ifNull": ["$file_data.file_id", "$file_data.movie_id"] },
                            "caption": "$file_data.caption",
                            "file_name": "$file_data.file_name",
                            "year": "$file_data.year",
                            "language": "$file_data.language",
                            "season": "$file_data.season",
                            "episode": "$file_data.episode"
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
                    movie_id=f.get("movie_id", "Unknown"),
                    caption=f.get("caption"),
                    file_name=f.get("file_name"),
                    year=f.get("year"),
                    language=f.get("language"),
                    season=f.get("season"),
                    episode=f.get("episode"),
                    telegram_link=file_service.get_telegram_link(f.get("movie_id") or f.get("file_id"))
                )
                for f in doc.get("files", []) if f.get("movie_id") or f.get("file_id") # Filter out empty/invalid pushes
            ]

            if not files:
                continue

            # Sort files by quality (Highest first)
            def quality_rank(q):
                ranks = {"4K": 5, "2160P": 5, "1080P": 4, "720P": 3, "480P": 2, "HD": 1, "CAM": 0}
                return ranks.get(q.upper(), -1)

            files.sort(key=lambda x: quality_rank(x.quality), reverse=True)

            results.append(Movie(
                title=doc.get("_id", "Unknown"),
                imdbID=doc.get("imdbID") or f"hub_{abs(hash(doc.get('_id', 'Unknown'))) % 10000000}",
                year=doc.get("year"),
                files=files
            ))

        return results

search_service = SearchService()
