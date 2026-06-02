"""SQLAlchemy ORM models for movie-narration-web."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base
from app.config import Platform, NarrationStyle


def gen_uuid() -> str:
    return str(uuid.uuid4())


# ===== User =====

class UserModel(Base):
    __tablename__ = 'users'

    user_id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    plan = Column(String(20), default='free')  # free | personal | professional | team
    credits_remaining = Column(Integer, default=100)
    monthly_videos_used = Column(Integer, default=0)
    monthly_videos_limit = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship('ProjectModel', back_populates='owner')


# ===== Movie =====

class MovieModel(Base):
    __tablename__ = 'movies'

    movie_id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    year = Column(Integer)
    genre = Column(JSON, default=list)  # ["剧情", "犯罪"]
    rating = Column(Float, default=0.0)
    duration = Column(Integer)  # minutes
    poster_url = Column(Text, nullable=True)
    plot_summary = Column(Text)
    key_scenes = Column(JSON, default=list)
    character_list = Column(JSON, default=list)
    hot_topics = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


# ===== Style Fingerprint =====

class StyleModel(Base):
    __tablename__ = 'styles'

    style_id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    narrative_rhythm = Column(JSON)
    hook_strategy = Column(JSON)
    emotion_curve = Column(JSON)
    vocabulary_style = Column(JSON)
    voice_config = Column(JSON)
    bgm_strategy = Column(JSON)
    visual_style = Column(JSON)
    platform_adaptations = Column(JSON, default=dict)
    is_builtin = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ===== BGM Track =====

class BGMTrackModel(Base):
    __tablename__ = 'bgm_tracks'

    track_id = Column(String, primary_key=True)
    title = Column(String(255), nullable=False)
    duration = Column(Float, nullable=False)  # seconds
    emotions = Column(JSON, default=list)  # ["suspense", "tense"]
    bpm = Column(Integer, nullable=True)
    key_signature = Column(String(20), nullable=True)  # "C minor"
    energy = Column(Float, default=0.5)
    instruments = Column(JSON, default=list)
    sections = Column(JSON, default=list)  # [{start, end, type}]
    natural_cut_points = Column(JSON, default=list)  # [8.5, 16.0, ...]
    usage = Column(JSON, default=list)  # ["hook", "climax"]
    license_type = Column(String(50), default='cc0')
    file_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ===== Project =====

class ProjectModel(Base):
    __tablename__ = 'projects'

    project_id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=True)
    movie_id = Column(String, ForeignKey('movies.movie_id'), nullable=False)
    movie_title = Column(String(255), nullable=False)
    style_id = Column(String, ForeignKey('styles.style_id'), nullable=False)
    style_name = Column(String(100), nullable=False)
    platform = Column(String(20), nullable=False)  # douyin, bilibili, etc.
    status = Column(String(20), default='draft')  # draft|selecting|scripting|voicing|composing|reviewing|completed|failed
    voice_id = Column(String(100), default='narrator-male-youth-01')
    script_segments = Column(JSON, default=list)  # [{index, type, text, emotion, ...}]
    output_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship('UserModel', back_populates='projects')


# ===== Narration Task (Celery) =====

class TaskModel(Base):
    __tablename__ = 'tasks'

    task_id = Column(String, primary_key=True, default=gen_uuid)
    project_id = Column(String, ForeignKey('projects.project_id'), nullable=False)
    celery_task_id = Column(String(255), nullable=True)
    stage = Column(String(50), default='script_generation')
    status = Column(String(20), default='pending')  # pending|running|completed|failed
    progress = Column(Integer, default=0)  # 0-100
    message = Column(Text, default='')
    error = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
