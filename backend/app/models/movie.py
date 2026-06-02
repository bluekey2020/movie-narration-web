"""电影素材元数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MovieScene:
    """电影关键场景"""
    name: str
    timestamp: str          # HH:MM:SS
    duration_sec: float
    tags: list[str]         # 情绪/类型标签
    description: str        # 画面描述
    characters: list[str] = field(default_factory=list)
    dialogue_highlights: list[str] = field(default_factory=list)


@dataclass
class Movie:
    """电影元数据"""
    movie_id: str
    title: str
    year: int
    genre: list[str]
    rating: float
    duration_min: int
    director: str = ''
    cast: list[str] = field(default_factory=list)
    plot_summary: str = ''
    key_scenes: list[MovieScene] = field(default_factory=list)
    narration_hotspots: list[str] = field(default_factory=list)  # 解说热点
    poster_url: str = ''
    tmdb_id: Optional[str] = None
    douban_id: Optional[str] = None


@dataclass
class BGMTrack:
    """BGM 曲目元数据"""
    track_id: str
    title: str
    duration_sec: float
    emotions: list[str]           # 情绪标签: suspense/tense/epic/...
    bpm: int
    key: str                      # "C minor"
    energy: float                 # 0-1
    instruments: list[str]
    sections: list[dict]          # [{start, end, type: intro/main/climax/outro}]
    natural_cut_points: list[float]  # 自然切出点 (秒)
    usage_tags: list[str]         # hook/buildup/climax/ending/transition
    license_type: str             # cc0 / licensed / suno_generated
    file_path: str = ''
