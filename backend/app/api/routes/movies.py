"""电影素材 API"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter()


@router.get('/')
async def list_movies(genre: str | None = None, min_rating: float | None = None):
    """获取电影列表"""
    library = _load_library()
    movies = library.get('movies', [])

    if genre:
        movies = [m for m in movies if genre in m.get('genre', [])]
    if min_rating:
        movies = [m for m in movies if m.get('rating', 0) >= min_rating]

    return {
        'total': len(movies),
        'movies': [
            {
                'movie_id': m['movie_id'],
                'title': m['title'],
                'year': m['year'],
                'genre': m['genre'],
                'rating': m['rating'],
                'duration_min': m['duration_min'],
                'poster_url': m.get('poster_url', ''),
                'narration_hotspots': m.get('narration_hotspots', []),
            }
            for m in movies
        ],
    }


@router.get('/{movie_id}')
async def get_movie(movie_id: str):
    """获取电影详情"""
    library = _load_library()
    for m in library.get('movies', []):
        if m['movie_id'] == movie_id:
            return m
    raise HTTPException(status_code=404, detail=f'Movie {movie_id} not found')


@router.get('/{movie_id}/scenes')
async def get_movie_scenes(movie_id: str):
    """获取电影关键场景"""
    library = _load_library()
    for m in library.get('movies', []):
        if m['movie_id'] == movie_id:
            return {
                'movie_id': movie_id,
                'title': m['title'],
                'scenes': m.get('key_scenes', []),
            }
    raise HTTPException(status_code=404, detail=f'Movie {movie_id} not found')


def _load_library() -> dict:
    path = Path(settings.movie_library_path)
    if not path.exists():
        return {'movies': []}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
