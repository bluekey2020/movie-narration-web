"""应用配置 —— 所有环境变量和模型路由参数"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Platform = Literal['douyin', 'bilibili', 'kuaishou', 'xiaohongshu']
NarrationStyle = Literal[
    'action_hot', 'suspense_brainburn', 'inspirational', 'comedy',
    'disaster_survival', 'thriller_suspense', 'horror', 'oriental_fantasy',
    'family_drama', 'emotional_life', 'scifi_fantasy', 'legend_biography'
]
TTSEngine = Literal['narrator-ai', 'cosyvoice2', 'elevenlabs', 'edge-tts']


@dataclass
class PlatformConfig:
    """单平台参数配置"""
    display_name: str
    duration_range: tuple[int, int]
    hook_window: float  # 前 N 秒必须有强钩子
    aspect_ratio: tuple[int, int]
    resolution: tuple[int, int]
    speech_rate: float
    subtitle_style: str
    max_words: int
    style_params: dict


@dataclass
class Settings:
    """全局配置"""
    # 应用
    app_name: str = 'Movie Narration Web'
    debug: bool = field(default_factory=lambda: os.getenv('DEBUG', 'false').lower() == 'true')
    secret_key: str = field(default_factory=lambda: os.getenv('SECRET_KEY', 'dev-secret-change-me'))
    api_prefix: str = '/api/v1'

    # 数据库
    database_url: str = field(default_factory=lambda: os.getenv(
        'DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/movie_narration'
    ))
    redis_url: str = field(default_factory=lambda: os.getenv('REDIS_URL', 'redis://localhost:6379/0'))

    # 文件存储
    s3_endpoint: str = field(default_factory=lambda: os.getenv('S3_ENDPOINT', 'localhost:9000'))
    s3_bucket: str = field(default_factory=lambda: os.getenv('S3_BUCKET', 'movie-narration'))
    cdn_base_url: str = field(default_factory=lambda: os.getenv('CDN_BASE_URL', ''))

    # LLM
    llm_provider: Literal['openai', 'anthropic', 'deepseek'] = 'deepseek'
    llm_api_key: str = field(default_factory=lambda: os.getenv('LLM_API_KEY', ''))
    llm_base_url: str = field(default_factory=lambda: os.getenv('LLM_BASE_URL', 'https://api.deepseek.com/v1'))
    llm_model_creative: str = 'deepseek-v4-pro'       # 创意写作
    llm_model_reasoning: str = 'deepseek-v4-pro'      # 深度推理
    llm_model_fast: str = 'deepseek-v4-flash'         # 快速评分

    # narrator-ai API
    narrator_api_key: str = field(default_factory=lambda: os.getenv('NARRATOR_API_KEY', ''))
    narrator_api_base: str = 'https://api.jieshuo.cn/v2'

    # TwelveLabs
    twelvelabs_api_key: str = field(default_factory=lambda: os.getenv('TWELVELABS_API_KEY', ''))

    # TTS
    default_tts_engine: TTSEngine = 'narrator-ai'
    tts_engines: dict[TTSEngine, dict] = field(default_factory=lambda: {
        'narrator-ai': {'cost_per_minute': 0.15, 'quality': 8.0},
        'cosyvoice2': {'cost_per_minute': 0.0, 'quality': 7.5, 'endpoint': 'http://localhost:9880'},
        'elevenlabs': {'cost_per_minute': 0.50, 'quality': 9.0},
        'edge-tts': {'cost_per_minute': 0.0, 'quality': 6.0},
    })

    # BGM 曲库路径
    bgm_library_path: str = field(default_factory=lambda: os.getenv(
        'BGM_LIBRARY_PATH', str(Path(__file__).parent.parent / 'data' / 'bgm_library.json')
    ))

    # 电影素材库路径
    movie_library_path: str = field(default_factory=lambda: os.getenv(
        'MOVIE_LIBRARY_PATH', str(Path(__file__).parent.parent / 'data' / 'movie_library.json')
    ))

    # FFmpeg
    ffmpeg_path: str = 'ffmpeg'
    ffmpeg_threads: int = 4

    # 平台配置
    platforms: dict[Platform, PlatformConfig] = field(default_factory=lambda: {
        'douyin': PlatformConfig(
            display_name='抖音', duration_range=(60, 180), hook_window=3.0,
            aspect_ratio=(9, 16), resolution=(1080, 1920), speech_rate=1.15,
            subtitle_style='large_keyword_highlight', max_words=600,
            style_params={
                'opening_tone': 'aggressive_hook', 'address_term': '家人们',
                'closing': '关注我，下期更精彩', 'slang_density': 0.8, 'sentence_length': 'short'
            }
        ),
        'bilibili': PlatformConfig(
            display_name='B站', duration_range=(180, 900), hook_window=15.0,
            aspect_ratio=(16, 9), resolution=(1920, 1080), speech_rate=1.0,
            subtitle_style='standard_with_notes', max_words=3000,
            style_params={
                'opening_tone': 'informative_hook', 'address_term': '各位观众',
                'closing': '如果喜欢这个视频，记得一键三连', 'slang_density': 0.4, 'sentence_length': 'mixed'
            }
        ),
        'kuaishou': PlatformConfig(
            display_name='快手', duration_range=(60, 180), hook_window=3.0,
            aspect_ratio=(9, 16), resolution=(1080, 1920), speech_rate=1.1,
            subtitle_style='colloquial_large', max_words=600,
            style_params={
                'opening_tone': 'down_to_earth', 'address_term': '老铁们',
                'closing': '觉得好的给老弟来个双击', 'slang_density': 0.7, 'sentence_length': 'short'
            }
        ),
        'xiaohongshu': PlatformConfig(
            display_name='小红书', duration_range=(60, 300), hook_window=5.0,
            aspect_ratio=(3, 4), resolution=(1080, 1440), speech_rate=0.9,
            subtitle_style='literary_elegant', max_words=1000,
            style_params={
                'opening_tone': 'emotional_resonance', 'address_term': '姐妹们',
                'closing': '你觉得呢？评论区聊聊吧', 'slang_density': 0.5, 'sentence_length': 'medium'
            }
        ),
    })

    # 风格指纹模板路径
    style_fingerprints_path: str = field(default_factory=lambda: os.getenv(
        'STYLE_FINGERPRINTS_PATH', str(Path(__file__).parent.parent / 'data' / 'style_fingerprints.json')
    ))


# 全局单例
settings = Settings()
