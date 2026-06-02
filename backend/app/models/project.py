"""项目 & 解说任务数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

from app.config import Platform, NarrationStyle


@dataclass
class Project:
    """创作项目"""
    project_id: str
    title: str = 'Untitled'
    movie_id: str = ''
    style: str = ''
    platform: Platform = 'douyin'
    status: str = 'draft'
    created_at: float = 0.0
    updated_at: float = 0.0
    tasks: list = field(default_factory=list)


class TaskStatus(str, Enum):
    DRAFT = 'draft'
    SELECTING_MOVIE = 'selecting_movie'
    CONFIGURING_STYLE = 'configuring_style'
    GENERATING_SCRIPT = 'generating_script'
    AWAITING_REVIEW = 'awaiting_review'
    GENERATING_VOICE = 'generating_voice'
    MATCHING_SCENES = 'matching_scenes'
    COMPOSING_VIDEO = 'composing_video'
    QUALITY_CHECK = 'quality_check'
    COMPLETED = 'completed'
    FAILED = 'failed'


@dataclass
class ScriptSegment:
    """文案段落"""
    index: int
    segment_type: Literal['hook', 'intro', 'plot_1', 'twist', 'plot_2', 'climax', 'ending']
    text: str
    ssml: str
    emotion: str                          # suspense/buildup/tense/revelation/climax/reflection
    emphasis_words: list[str]
    visual_requirement: dict              # {description, preferred_source, scene_hint, mood}
    estimated_duration_sec: float
    hook_score: Optional[float] = None    # 仅 hook 段


@dataclass
class ScriptVersion:
    """文案版本"""
    script_id: str
    style: NarrationStyle
    segments: list[ScriptSegment]
    total_words: int
    estimated_duration_sec: float
    quality_scores: dict = field(default_factory=dict)
    overall_score: float = 0.0


@dataclass
class ClipPlan:
    """画面匹配计划"""
    segment_index: int
    source: Literal['original_clip', 'visual_template', 'ai_generated', 'stock']
    time_range: Optional[tuple[float, float]] = None  # 原片时间范围
    template_id: Optional[str] = None
    template_config: Optional[dict] = None
    confidence: float = 0.0
    warning: Optional[str] = None
    fallback: Optional[dict] = None


@dataclass
class NarrationTask:
    """解说任务 —— 一次完整的出片任务"""
    task_id: str
    project_id: str
    movie_id: str
    style: NarrationStyle
    platform: Platform
    voice_id: str
    ost_mode: int = 0                     # 0=纯配音 1=纯原声 2=混合
    status: TaskStatus = TaskStatus.DRAFT
    script_versions: list[ScriptVersion] = field(default_factory=list)
    selected_script_id: Optional[str] = None
    clip_plan: list[ClipPlan] = field(default_factory=list)
    composition_mode: str = 'clip_priority'
    output_path: Optional[str] = None
    quality_report: Optional[dict] = None
    created_at: float = 0.0
    completed_at: Optional[float] = None
