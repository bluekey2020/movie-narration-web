"""画面匹配引擎 —— 三层降级匹配

Layer 1: 精确匹配 (TwelveLabs Marengo 3.0 / CLIP + pgvector)
Layer 2: 近似匹配 (通用素材库 + 视觉模板)
Layer 3: 降级兜底 (纯视觉模板渲染)

参考: NarratoAI 视觉分析 + AWS Bedrock 多模态工作流
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import structlog

from app.config import settings
from app.models.movie import MovieScene

logger = structlog.get_logger(__name__)


@dataclass
class MatchResult:
    """单段画面匹配结果"""
    segment_index: int
    source: str                      # original_clip / visual_template / ai_generated / stock
    time_range: Optional[tuple[float, float]] = None
    template_id: Optional[str] = None
    template_config: Optional[dict] = None
    confidence: float = 0.0
    warning: Optional[str] = None
    fallback: Optional[dict] = None


@dataclass
class SceneMatchReport:
    """画面匹配报告"""
    segments: list[MatchResult]
    overall_match_rate: float        # 精确匹配率为多少
    composition_mode: str            # clip_priority / hybrid / template_only


class SceneMatcher:
    """画面匹配引擎 —— 三层降级"""

    CONFIDENCE_THRESHOLD_HIGH = 0.8   # Layer 1: 精确匹配阈值
    CONFIDENCE_THRESHOLD_MED = 0.5    # Layer 2: 近似匹配阈值

    def __init__(self):
        self._movie_scene_cache: dict[str, list[dict]] = {}

    async def match_script(
        self,
        segments: list[dict],
        movie_id: str,
        movie_scenes: list[MovieScene] | None = None,
        use_marengo: bool = False,
    ) -> SceneMatchReport:
        """为文案的每个段落匹配画面

        Args:
            segments: 文案段落列表 (含 visual_requirement)
            movie_id: 电影 ID
            movie_scenes: 预置的电影关键场景列表
            use_marengo: 是否使用 TwelveLabs Marengo 3.0（否则用 CLIP）
        """
        results: list[MatchResult] = []
        exact_matches = 0

        # 加载场景索引（模拟：实际中走 CLIP 或 Marengo）
        scenes = await self._load_scene_index(movie_id, movie_scenes)

        for seg in segments:
            visual_req = seg.get('visual_requirement', {})
            query_text = visual_req.get('description', '')
            scene_hint = visual_req.get('scene_hint', '')
            preferred_source = visual_req.get('preferred_source', 'original_clip')

            # Layer 1: 尝试精确匹配
            matched = await self._exact_match(query_text, scene_hint, scenes)

            if matched and matched.confidence >= self.CONFIDENCE_THRESHOLD_HIGH:
                matched.segment_index = seg.get('index', 0)
                results.append(matched)
                exact_matches += 1
                continue

            # Layer 2: 近似匹配
            if matched and matched.confidence >= self.CONFIDENCE_THRESHOLD_MED:
                matched.warning = 'low_confidence_suggest_review'
                matched.fallback = self._get_visual_template_plan(seg)
                matched.segment_index = seg.get('index', 0)
                results.append(matched)
                continue

            # Layer 3: 降级到视觉模板
            fallback = self._get_visual_template_plan(seg)
            results.append(MatchResult(
                segment_index=seg.get('index', 0),
                source='visual_template',
                template_id=fallback.get('template_id', 'photo_card'),
                template_config=fallback.get('config', {}),
                confidence=matched.confidence if matched else 0.0,
            ))

        # 计算总体匹配率
        total_segments = len(segments)
        overall_rate = exact_matches / max(total_segments, 1)

        # 决定合成模式
        if overall_rate >= 0.70:
            mode = 'clip_priority'
        elif overall_rate >= 0.40:
            mode = 'hybrid'
        else:
            mode = 'template_only'

        return SceneMatchReport(
            segments=results,
            overall_match_rate=overall_rate,
            composition_mode=mode,
        )

    # ==================================================================
    # 匹配方法
    # ==================================================================

    async def _exact_match(
        self, query_text: str, scene_hint: str, scenes: list[dict]
    ) -> Optional[MatchResult]:
        """Layer 1: 精确场景匹配

        实际生产环境：
        - 有 Marengo 3.0 → 调用 TwelveLabs API 做多模态搜索
        - MVP 阶段 → CLIP 文本-图像相似度 + pgvector L2 距离
        - 测试阶段 → 关键词匹配模拟
        """
        if not query_text and not scene_hint:
            return None

        # MVP 实现：基于场景提示的关键词匹配（模拟 CLIP）
        best_match = None
        best_score = 0.0

        for scene in scenes:
            score = self._calculate_match_score(query_text, scene_hint, scene)
            if score > best_score:
                best_score = score
                best_match = scene

        if best_match and best_score > 0.3:
            return MatchResult(
                segment_index=0,  # 调用方会覆盖
                source='original_clip',
                time_range=(best_match.get('start_sec', 0), best_match.get('end_sec', 0)),
                confidence=min(best_score, 0.95),
            )
        return None

    def _calculate_match_score(
        self, query: str, hint: str, scene: dict
    ) -> float:
        """计算查询文本与场景的匹配分数（简化版 CLIP 模拟）"""
        score = 0.0
        scene_text = f"{scene.get('name', '')} {scene.get('description', '')} {' '.join(scene.get('tags', []))}"

        # 场景提示精确匹配
        if hint and hint in scene.get('name', ''):
            score += 0.5

        # 关键词重叠
        query_words = set(query)
        scene_words = set(scene_text)
        if query_words:
            overlap = len(query_words & scene_words) / len(query_words)
            score += overlap * 0.4

        # 情绪标签匹配
        scene_tags = set(scene.get('tags', []))
        emotion_keywords = {'压抑', '绝望', '希望', '自由', '紧张', '悬疑', '高潮', '释放',
                            '温暖', '悲伤', '震撼', '恐惧', '感动', '激昂'}
        query_emotions = query_words & emotion_keywords
        if query_emotions and scene_tags:
            emotion_overlap = len(query_emotions & scene_tags) / len(query_emotions)
            score += emotion_overlap * 0.3

        return min(score, 1.0)

    # ==================================================================
    # 视觉模板降级
    # ==================================================================

    def _get_visual_template_plan(self, segment: dict) -> dict:
        """根据段落类型和情绪返回最适合的视觉模板"""
        seg_type = segment.get('type', '')
        emotion = segment.get('emotion', '')
        visual_req = segment.get('visual_requirement', {})
        mood = visual_req.get('mood', '')

        # 模板选择逻辑
        template_map = {
            'hook': 'emotion_card',       # 开场用情绪卡片制造冲击
            'intro': 'photo_card',        # 剧情引入用剧照卡片
            'plot_1': 'photo_card',       # 情节用剧照 + 文字
            'twist': 'split_comparison',  # 转折用对比
            'plot_2': 'photo_card',
            'climax': 'emotion_card',     # 高潮用情绪卡片
            'ending': 'photo_card',       # 结尾用剧照卡片
        }

        template_id = template_map.get(seg_type, 'photo_card')

        return {
            'template_id': template_id,
            'config': self._build_template_config(template_id, segment),
        }

    def _build_template_config(self, template_id: str, segment: dict) -> dict:
        """构建视觉模板参数配置"""
        visual_req = segment.get('visual_requirement', {})
        text = segment.get('text', '')
        emotion = segment.get('emotion', '')

        base_config = {
            'canvas': {'width': 1080, 'height': 1920},
            'textLayers': [
                {
                    'content': text[:120] if len(text) > 120 else text,  # 模板只显示摘要
                    'fontSize': 48,
                    'color': '#FFFFFF',
                    'animation': {'type': 'fadeIn', 'duration': 800, 'delay': 200},
                }
            ],
            'duration': segment.get('estimated_duration_sec', 10.0),
        }

        if template_id == 'emotion_card':
            base_config.update({
                'background': {
                    'type': 'gradient',
                    'gradientColors': self._emotion_colors(emotion),
                },
                'textLayers': [
                    {
                        'content': self._emotion_emoji(emotion),
                        'fontSize': 120,
                        'color': '#FFFFFF',
                        'animation': {'type': 'scaleIn', 'duration': 500, 'delay': 0},
                    },
                    {
                        'content': text[:100],
                        'fontSize': 42,
                        'color': '#FFFFFF',
                        'animation': {'type': 'fadeIn', 'duration': 600, 'delay': 500},
                    }
                ]
            })

        elif template_id == 'photo_card':
            base_config.update({
                'background': {
                    'type': 'blurred_poster',
                    'imageUrl': visual_req.get('poster_url', ''),
                    'blurRadius': 30,
                    'opacity': 0.4,
                },
            })

        elif template_id == 'split_comparison':
            base_config.update({
                'canvas': {'width': 1080, 'height': 1920},
                'decorations': [
                    {'type': 'divider', 'style': {'color': '#FF4444', 'width': 2}},
                ],
            })

        return base_config

    @staticmethod
    def _emotion_colors(emotion: str) -> list[str]:
        """情绪 → 渐变色映射"""
        color_map = {
            'suspense': ['#1a1a2e', '#16213e'],
            'buildup': ['#0f3460', '#16213e'],
            'tense': ['#2d0000', '#4a0000'],
            'revelation': ['#1b4332', '#2d6a4f'],
            'climax': ['#3d0909', '#6b1515'],
            'reflection': ['#1a1a2e', '#2d2d44'],
        }
        return color_map.get(emotion, ['#1a1a2e', '#2d2d44'])

    @staticmethod
    def _emotion_emoji(emotion: str) -> str:
        """情绪 → emoji 映射"""
        emoji_map = {
            'suspense': '😱',
            'buildup': '🤔',
            'tense': '😰',
            'revelation': '💡',
            'climax': '🔥',
            'reflection': '💭',
        }
        return emoji_map.get(emotion, '🎬')

    # ==================================================================
    # 场景索引管理
    # ==================================================================

    async def _load_scene_index(
        self, movie_id: str, movie_scenes: list[MovieScene] | None = None
    ) -> list[dict]:
        """加载电影场景索引"""
        if movie_id in self._movie_scene_cache:
            return self._movie_scene_cache[movie_id]

        if movie_scenes:
            scenes = [
                {
                    'name': s.name,
                    'start_sec': self._timestamp_to_seconds(s.timestamp),
                    'end_sec': self._timestamp_to_seconds(s.timestamp) + s.duration_sec,
                    'description': s.description,
                    'tags': s.tags,
                    'characters': s.characters,
                }
                for s in movie_scenes
            ]
        else:
            # 尝试从数据文件加载
            scenes = await self._load_from_library(movie_id)

        self._movie_scene_cache[movie_id] = scenes
        return scenes

    async def _load_from_library(self, movie_id: str) -> list[dict]:
        """从电影素材库 JSON 加载场景"""
        library_path = Path(settings.movie_library_path)
        if not library_path.exists():
            logger.warning('movie_library_not_found', path=str(library_path))
            return []

        with open(library_path, 'r', encoding='utf-8') as f:
            library = json.load(f)

        movies = library.get('movies', [])
        for movie in movies:
            if movie.get('movie_id') == movie_id:
                return [
                    {
                        'name': s.get('name', ''),
                        'start_sec': self._timestamp_to_seconds(s.get('timestamp', '00:00:00')),
                        'end_sec': self._timestamp_to_seconds(s.get('timestamp', '00:00:00')) + s.get('duration_sec', 10),
                        'description': s.get('description', ''),
                        'tags': s.get('tags', []),
                        'characters': s.get('characters', []),
                    }
                    for s in movie.get('key_scenes', [])
                ]
        return []

    @staticmethod
    def _timestamp_to_seconds(ts: str) -> float:
        """HH:MM:SS → 秒"""
        parts = ts.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(ts)


def create_scene_matcher() -> SceneMatcher:
    return SceneMatcher()
