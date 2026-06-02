"""BGM 引擎测试"""

import asyncio

import pytest

from app.engines.bgm_engine import BGMEngine, BGMSegment, BGMMixPlan, create_bgm_engine
from app.models.movie import BGMTrack


class TestBGMEngine:
    """BGM 自动匹配引擎测试"""

    def test_create_engine(self):
        engine = create_bgm_engine()
        assert engine is not None

    def test_load_library_empty(self):
        """测试空曲库加载"""
        engine = BGMEngine(library=[])
        engine._load_library()
        # 即使文件不存在，也应该有默认 BGM
        assert len(engine.library) > 0

    def test_load_custom_library(self, sample_bgm_tracks):
        """测试加载自定义曲库"""
        engine = BGMEngine(library=sample_bgm_tracks)
        assert len(engine.library) == 4

    def test_search_by_emotion(self, sample_bgm_tracks):
        """测试按情绪搜索"""
        engine = BGMEngine(library=sample_bgm_tracks)

        results = engine._search_by_emotion('suspense', min_duration=30)
        assert len(results) > 0
        assert results[0].track_id == 'bgm_001'  # 悬疑铺垫

    def test_search_by_emotion_no_match(self, sample_bgm_tracks):
        """测试无匹配情绪搜索"""
        engine = BGMEngine(library=sample_bgm_tracks)

        results = engine._search_by_emotion('calm_relaxing', min_duration=0)
        # 不应崩溃
        assert isinstance(results, list)

    def test_fuzzy_search(self, sample_bgm_tracks):
        """测试模糊搜索"""
        engine = BGMEngine(library=sample_bgm_tracks)

        results = engine._fuzzy_search('any_emotion', min_duration=0)
        assert len(results) > 0

    def test_find_cut_point(self, sample_bgm_tracks):
        """测试切点查找"""
        engine = BGMEngine(library=sample_bgm_tracks)
        track = sample_bgm_tracks[0]  # 悬疑铺垫，120 秒
        track.natural_cut_points = [15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 105.0, 120.0]

        # 应找到 >= 目标时长的最近切点
        cut = engine._find_cut_point(track, 50.0)
        assert cut == 60.0  # 最接近 50 的 >= 切点是 60

        cut = engine._find_cut_point(track, 10.0)
        assert cut == 15.0

        cut = engine._find_cut_point(track, 150.0)
        assert cut == 120.0  # 超过所有切点时返回最后一个

    def test_find_start_point(self, sample_bgm_tracks):
        """测试起始点选择"""
        engine = BGMEngine(library=sample_bgm_tracks)
        track = sample_bgm_tracks[0]

        # 钩子应跳到 highlight 段
        start = engine._find_start_point(track, 'hook')
        assert start >= 0

        # 普通段从 intro 开始
        start = engine._find_start_point(track, 'intro')
        assert start == 0.0

        # 高潮段跳到高潮
        start = engine._find_start_point(track, 'climax')
        assert start >= 0

    def test_plan_mix(self, sample_bgm_tracks, sample_segments):
        """测试完整混音计划生成"""
        engine = BGMEngine(library=sample_bgm_tracks)

        tts_durations = [12.0, 8.0, 10.0]
        plan = asyncio.run(engine.plan_mix(
            segments=sample_segments,
            tts_durations=tts_durations,
            ost_mode=0,  # 纯配音模式
        ))

        assert isinstance(plan, BGMMixPlan)
        assert len(plan.segments) == len(sample_segments)
        assert plan.total_bgm_tracks >= 1
        assert plan.estimated_total_duration > 0

        # 每个 BGM 段应有合理的时长
        for seg in plan.segments:
            assert seg.duration_needed > 0
            assert seg.volume > 0

    def test_plan_mix_ost_modes(self, sample_bgm_tracks, sample_segments):
        """测试不同 OST 模式"""
        engine = BGMEngine(library=sample_bgm_tracks)
        tts_durations = [12.0, 8.0, 10.0]

        for mode in [0, 1, 2]:
            plan = asyncio.run(engine.plan_mix(
                segments=sample_segments,
                tts_durations=tts_durations,
                ost_mode=mode,
            ))
            assert isinstance(plan, BGMMixPlan)

    def test_add_track(self):
        """测试添加 BGM 曲目"""
        engine = BGMEngine(library=[])
        before_count = len(engine.library)
        track = BGMTrack(
            track_id='test_001', title='测试曲目', duration_sec=60.0,
            emotions=['epic'], bpm=120, key='C major', energy=0.5,
            instruments=['piano'], sections=[{'start': 0, 'end': 60, 'type': 'main'}],
            natural_cut_points=[30.0, 60.0], usage_tags=['climax'], license_type='cc0',
        )
        engine.add_track(track)
        assert len(engine.library) == before_count + 1

    def test_search_by_tags(self, sample_bgm_tracks):
        """测试多条件搜索"""
        engine = BGMEngine(library=sample_bgm_tracks)

        # 按情绪
        results = engine.search_by_tags(emotions=['epic'])
        assert len(results) == 1

        # 按 BPM（bgm_001:85 + bgm_004:75）
        results = engine.search_by_tags(bpm_range=(70, 90))
        assert len(results) == 2

        # 按用途
        results = engine.search_by_tags(usage='climax')
        assert len(results) >= 1

    def test_default_bgm(self):
        """测试默认 BGM"""
        engine = BGMEngine(library=[])
        default = engine._get_default_bgm()
        assert default.track_id in ('default_001', 'bgm_001')  # 如果从 JSON 加载了库，会用库里的第一条
        assert default.duration_sec > 0
        assert len(default.emotions) > 0
