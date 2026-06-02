"""Seed database with data from JSON files.

Usage:
    python -m app.db.seed          # Seed all
    python -m app.db.seed --movies # Seed movies only
    python -m app.db.seed --styles # Seed styles only
    python -m app.db.seed --bgm    # Seed BGM only
"""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.db.base import async_session_factory
from app.db.models import MovieModel, StyleModel, BGMTrackModel

DATA_DIR = Path(__file__).parent.parent.parent / 'data'


async def seed_movies():
    path = DATA_DIR / 'movie_library.json'
    if not path.exists():
        print(f'  [SKIP] Movie library not found at {path}')
        return

    data = json.loads(path.read_text(encoding='utf-8'))
    async with async_session_factory() as session:
        for m in data.get('movies', []):
            existing = await session.get(MovieModel, m['movie_id'])
            if existing:
                print(f'  [SKIP] Movie already exists: {m["title"]}')
                continue

            movie = MovieModel(
                movie_id=m['movie_id'],
                title=m['title'],
                year=m.get('year'),
                genre=m.get('genre', []),
                rating=m.get('rating', 0.0),
                duration=m.get('duration'),
                poster_url=m.get('poster_url'),
                plot_summary=m.get('plot_summary'),
                key_scenes=m.get('key_scenes', []),
                character_list=m.get('character_list', []),
                hot_topics=m.get('hot_topics', []),
            )
            session.add(movie)
            print(f'  [OK] Seeded movie: {m["title"]}')
        await session.commit()


async def seed_styles():
    path = DATA_DIR / 'style_fingerprints.json'
    if not path.exists():
        print(f'  [SKIP] Style fingerprints not found at {path}')
        return

    data = json.loads(path.read_text(encoding='utf-8'))
    async with async_session_factory() as session:
        for s in data.get('styles', []):
            existing = await session.get(StyleModel, s['style_id'])
            if existing:
                print(f'  [SKIP] Style already exists: {s["name"]}')
                continue

            style = StyleModel(
                style_id=s['style_id'],
                name=s['name'],
                description=s.get('description', ''),
                narrative_rhythm=s.get('narrative_rhythm'),
                hook_strategy=s.get('hook_strategy'),
                emotion_curve=s.get('emotion_curve'),
                vocabulary_style=s.get('vocabulary_style'),
                voice_config=s.get('voice_config'),
                bgm_strategy=s.get('bgm_strategy'),
                visual_style=s.get('visual_style'),
                platform_adaptations=s.get('platform_adaptations', {}),
            )
            session.add(style)
            print(f'  [OK] Seeded style: {s["name"]}')
        await session.commit()


async def seed_bgm():
    path = DATA_DIR / 'bgm_library.json'
    if not path.exists():
        print(f'  [SKIP] BGM library not found at {path}')
        return

    data = json.loads(path.read_text(encoding='utf-8'))
    async with async_session_factory() as session:
        for b in data.get('tracks', []):
            existing = await session.get(BGMTrackModel, b['track_id'])
            if existing:
                print(f'  [SKIP] BGM already exists: {b["title"]}')
                continue

            bgm = BGMTrackModel(
                track_id=b['track_id'],
                title=b['title'],
                duration=b.get('duration', 0),
                emotions=b.get('emotions', []),
                bpm=b.get('bpm'),
                key_signature=b.get('key'),
                energy=b.get('energy', 0.5),
                instruments=b.get('instruments', []),
                sections=b.get('sections', []),
                natural_cut_points=b.get('natural_cut_points', []),
                usage=b.get('usage', []),
                license_type=b.get('license', 'cc0'),
                file_url=b.get('file_url'),
            )
            session.add(bgm)
            print(f'  [OK] Seeded BGM: {b["title"]}')
        await session.commit()


async def seed_all():
    print('Seeding database...')
    await seed_movies()
    await seed_styles()
    await seed_bgm()
    print('Done.')


if __name__ == '__main__':
    asyncio.run(seed_all())
