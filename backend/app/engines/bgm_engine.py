"""BGM 自动匹配引擎

核心设计：
- 文案情绪标签序列 → BGM 曲库匹配 → 切点规划 → 混音计划
- 146 首 BGM 预标注（情绪/BPM/调性/结构分段/自然切点）
- OST 三模式：0=纯配音 / 1=纯原声 / 2=混合

参考: NarratoAI OST 三模式 + pydub 精确叠加
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import structlog

from app.config import settings
from app.models.movie import BGMTrack

logger = structlog.get_logger(__name__)


@dataclass
class BGMSegment:
    """单段 BGM 配置"""
    segment_index: int
    track_id: str
    track_title: str
    play_start_sec: float          # 从 BGM 的哪个位置开始播放
    play_end_sec: float            # 播到哪个位置
    duration_needed: float         # 需要覆盖的时长
    volume: float = 0.3
    fade_in_sec: float = 1.0
    fade_out_sec: float = 2.0
    tts_ducking: bool = True       # TTS 时自动降低 BGM 音量
    natural_cut: bool = False      # 是否在自然小节结尾切出


@dataclass
class BGMMixPlan:
    """BGM 混音计划"""
    segments: list[BGMSegment]
    total_bgm_tracks: int           # 使用了多少首不同的 BGM
    switch_points: list[dict]       # BGM 切换点详情
    estimated_total_duration: float


class BGMEngine:
    """BGM 自动匹配引擎"""

    # 情绪→BGM 情绪标签映射
    EMOTION_MAP = {
        'suspense': ['suspense', 'dark', 'tense', 'mysterious'],
        'buildup': ['buildup', 'anticipation', 'rising', 'tension'],
        'tense': ['tense', 'intense', 'urgent', 'danger'],
        'revelation': ['epic', 'triumphant', 'revelation', 'dramatic'],
        'climax': ['epic', 'climax', 'powerful', 'heroic'],
        'reflection': ['calm', 'melancholic', 'warm', 'nostalgic', 'hopeful'],
    }

    # 段落类型→BGM 使用策略
    SEGMENT_STRATEGY = {
        'hook': {'duration_padding': 1.2, 'volume': 0.35, 'fade_in': 0.5},
        'intro': {'duration_padding': 1.1, 'volume': 0.25, 'fade_in': 1.0},
        'plot_1': {'duration_padding': 1.1, 'volume': 0.30, 'fade_in': 0.5},
        'twist': {'duration_padding': 1.3, 'volume': 0.35, 'fade_in': 0.3},
        'plot_2': {'duration_padding': 1.1, 'volume': 0.30, 'fade_in': 0.5},
        'climax': {'duration_padding': 1.3, 'volume': 0.35, 'fade_in': 0.5},
        'ending': {'duration_padding': 1.5, 'volume': 0.20, 'fade_in': 2.0},
    }

    def __init__(self, library: list[BGMTrack] | None = None):
        self.library: list[BGMTrack] = library or []
        self._load_library()

    # ==================================================================
    # 混音计划生成
    # ==================================================================

    async def plan_mix(
        self,
        segments: list[dict],
        tts_durations: list[float],
        ost_mode: int = 0,
    ) -> BGMMixPlan:
        """根据文案情绪序列生成完整混音计划

        Args:
            segments: 文案段落（含 emotion 字段）
            tts_durations: 每段配音实际时长
            ost_mode: 0=纯配音 1=纯原声 2=混合
        """
        mix_segments: list[BGMSegment] = []
        switch_points: list[dict] = []
        current_track_id: Optional[str] = None
        tracks_used: set[str] = set()

        total_time = 0.0

        for i, seg in enumerate(segments):
            emotion = seg.get('emotion', 'reflection')
            seg_type = seg.get('type', 'intro')
            duration = tts_durations[i] if i < len(tts_durations) else 10.0

            # 1. 匹配 BGM
            strategy = self.SEGMENT_STRATEGY.get(seg_type, self.SEGMENT_STRATEGY['intro'])
            padded_duration = duration * strategy['duration_padding']

            candidates = self._search_by_emotion(emotion, min_duration=padded_duration)

            if not candidates:
                # 降级：按情绪模糊匹配
                candidates = self._fuzzy_search(emotion, min_duration=padded_duration)

            best = candidates[0] if candidates else self._get_default_bgm()

            # 2. 决定是否需要切换
            if current_track_id and current_track_id != best.track_id:
                switch_points.append({
                    'time_sec': round(total_time, 2),
                    'from_track': current_track_id,
                    'to_track': best.track_id,
                    'crossfade_duration': 2.0,
                })

            # 3. 找到自然切出点
            cut_sec = self._find_cut_point(best, padded_duration)
            natural_cut = cut_sec in best.natural_cut_points

            # 4. 生成 BGM 段配置
            bgm_seg = BGMSegment(
                segment_index=i + 1,
                track_id=best.track_id,
                track_title=best.title,
                play_start_sec=self._find_start_point(best, seg_type),
                play_end_sec=cut_sec,
                duration_needed=padded_duration,
                volume=strategy['volume'],
                fade_in_sec=strategy['fade_in'],
                natural_cut=natural_cut,
            )
            mix_segments.append(bgm_seg)
            tracks_used.add(best.track_id)
            current_track_id = best.track_id
            total_time += padded_duration

        return BGMMixPlan(
            segments=mix_segments,
            total_bgm_tracks=len(tracks_used),
            switch_points=switch_points,
            estimated_total_duration=round(total_time, 2),
        )

    # ==================================================================
    # BGM 搜索
    # ==================================================================

    def _search_by_emotion(self, emotion: str, min_duration: float = 0) -> list[BGMTrack]:
        """按情绪精确搜索"""
        target_emotions = self.EMOTION_MAP.get(emotion, [emotion])

        scored: list[tuple[BGMTrack, float]] = []
        for track in self.library:
            overlap = set(track.emotions) & set(target_emotions)
            if overlap and track.duration_sec >= min_duration:
                score = len(overlap) / len(target_emotions)
                scored.append((track, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [t for t, _ in scored[:5]]

    def _fuzzy_search(self, emotion: str, min_duration: float = 0) -> list[BGMTrack]:
        """模糊搜索 —— 情绪不完全匹配时的降级"""
        results = []
        for track in self.library:
            if track.duration_sec >= min_duration:
                results.append(track)
        # 按能量匹配度排序
        results.sort(key=lambda t: abs(t.energy - 0.5))
        return results[:3]

    def _get_default_bgm(self) -> BGMTrack:
        """获取默认 BGM（当曲库为空时）"""
        if self.library:
            return self.library[0]
        # 返回一个默认的空白 BGM
        return BGMTrack(
            track_id='default_001',
            title='Default Ambient',
            duration_sec=300.0,
            emotions=['neutral'],
            bpm=90,
            key='C major',
            energy=0.5,
            instruments=['piano'],
            sections=[{'start': 0, 'end': 300, 'type': 'main'}],
            natural_cut_points=[60, 120, 180, 240, 300],
            usage_tags=['transition'],
            license_type='cc0',
        )

    # ==================================================================
    # 切点计算
    # ==================================================================

    def _find_cut_point(self, track: BGMTrack, target_duration: float) -> float:
        """找到最接近目标时长的自然切出点"""
        cut_points = sorted(track.natural_cut_points)

        # 找 >= target_duration 的最近切点
        for cp in cut_points:
            if cp >= target_duration:
                return cp

        # 如果所有切点都 < target_duration
        if cut_points:
            return cut_points[-1]

        # 没有预标注切点 → 返回目标时长
        return min(target_duration, track.duration_sec)

    def _find_start_point(self, track: BGMTrack, seg_type: str) -> float:
        """根据段落类型决定从 BGM 的哪个位置开始播放"""
        sections = track.sections
        if not sections:
            return 0.0

        if seg_type == 'hook':
            # 钩子：从高潮段开始（如果有的话）
            for s in sections:
                if s.get('type') == 'climax':
                    return s.get('start', 0)
            return 0.0

        elif seg_type in ('climax', 'twist'):
            # 高潮/转折：跳到 BGM 的高潮段
            for s in sections:
                if s.get('type') in ('climax', 'main'):
                    return s.get('start', 0)
            return 0.0

        else:
            # 其他段落：从 intro 或 main 段开始
            for s in sections:
                if s.get('type') == 'intro':
                    return s.get('start', 0)
            return 0.0

    # ==================================================================
    # 曲库管理
    # ==================================================================

    def _load_library(self) -> None:
        """从 JSON 文件加载 BGM 曲库"""
        if self.library:
            return

        library_path = Path(settings.bgm_library_path)
        if not library_path.exists():
            logger.info('bgm_library_not_found_using_defaults', path=str(library_path))
            self.library = [self._get_default_bgm()]
            return

        with open(library_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.library = [
            BGMTrack(
                track_id=t.get('track_id', ''),
                title=t.get('title', ''),
                duration_sec=t.get('duration_sec', 0),
                emotions=t.get('emotions', []),
                bpm=t.get('bpm', 120),
                key=t.get('key', 'C major'),
                energy=t.get('energy', 0.5),
                instruments=t.get('instruments', []),
                sections=t.get('sections', []),
                natural_cut_points=t.get('natural_cut_points', []),
                usage_tags=t.get('usage_tags', []),
                license_type=t.get('license_type', 'cc0'),
                file_path=t.get('file_path', ''),
            )
            for t in data.get('tracks', [])
        ]
        logger.info('bgm_library_loaded', track_count=len(self.library))

    def add_track(self, track: BGMTrack) -> None:
        """添加 BGM 曲目"""
        self.library.append(track)

    def search_by_tags(
        self, emotions: list[str] | None = None, bpm_range: tuple[int, int] | None = None,
        instruments: list[str] | None = None, usage: str | None = None,
    ) -> list[BGMTrack]:
        """多条件搜索 BGM"""
        results = self.library

        if emotions:
            results = [t for t in results if set(t.emotions) & set(emotions)]

        if bpm_range:
            lo, hi = bpm_range
            results = [t for t in results if lo <= t.bpm <= hi]

        if instruments:
            results = [t for t in results if set(t.instruments) & set(instruments)]

        if usage:
            results = [t for t in results if usage in t.usage_tags]

        return results


def create_bgm_engine() -> BGMEngine:
    return BGMEngine()
