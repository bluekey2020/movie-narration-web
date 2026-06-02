"""画面匹配引擎测试"""

import pytest

from app.engines.scene_matcher import SceneMatcher, MatchResult, SceneMatchReport, create_scene_matcher
from app.models.movie import MovieScene


class TestSceneMatcher:
    """画面匹配引擎测试"""

    def test_create_matcher(self):
        """测试创建匹配器"""
        matcher = create_scene_matcher()
        assert matcher is not None

    def test_match_score_exact_hint(self):
        """测试场景提示精确匹配"""
        matcher = SceneMatcher()
        scene = {
            'name': 'shawshank_prison_exterior',
            'description': '监狱外景',
            'tags': ['压抑', '绝望'],
            'characters': ['安迪'],
        }
        score = matcher._calculate_match_score('安迪走进监狱', 'shawshank_prison_exterior', scene)
        assert score > 0.4, f'精确 hint 匹配应得分 > 0.4，实际 {score}'

    def test_match_score_no_match(self):
        """测试不匹配的场景"""
        matcher = SceneMatcher()
        scene = {
            'name': 'happy_beach_scene',
            'description': '阳光沙滩',
            'tags': ['快乐', '阳光'],
            'characters': ['某人'],
        }
        score = matcher._calculate_match_score('压抑绝望的高墙', '', scene)
        assert score < 0.5, f'不匹配应得分 < 0.5，实际 {score}'

    def test_match_score_emotion_overlap(self):
        """测试情绪标签重叠"""
        matcher = SceneMatcher()
        scene = {
            'name': 'dark_prison',
            'description': '黑暗压抑的监狱内部',
            'tags': ['压抑', '绝望', '黑暗', '恐惧'],
            'characters': [],
        }
        score = matcher._calculate_match_score('压抑绝望的牢房', '', scene)
        assert score > 0.2, f'情绪重叠应得分 > 0.2，实际 {score}'

    def test_empty_query(self):
        """测试空查询"""
        matcher = SceneMatcher()
        scene = {'name': 'test', 'description': 'test', 'tags': [], 'characters': []}
        score = matcher._calculate_match_score('', '', scene)
        # 空查询应有低分但不应崩溃
        assert 0.0 <= score <= 1.0

    def test_match_script_with_scenes(self, sample_movie):
        """测试完整脚本匹配（有预置场景）"""
        import asyncio
        matcher = SceneMatcher()

        segments = [
            {
                'index': 1, 'type': 'hook',
                'visual_requirement': {
                    'description': '监狱高墙黑暗压抑',
                    'scene_hint': '入狱',
                    'preferred_source': 'original_clip',
                },
                'estimated_duration_sec': 12.0,
            },
            {
                'index': 2, 'type': 'intro',
                'visual_requirement': {
                    'description': '阳光下的自由',
                    'scene_hint': '屋顶喝啤酒',
                },
                'estimated_duration_sec': 8.0,
            },
        ]

        report = asyncio.run(matcher.match_script(
            segments=segments,
            movie_id='shawshank_redemption',
            movie_scenes=sample_movie.key_scenes,
        ))

        assert isinstance(report, SceneMatchReport)
        assert len(report.segments) == 2
        assert all(s.segment_index > 0 for s in report.segments)
        assert report.overall_match_rate >= 0.0
        assert report.composition_mode in ('clip_priority', 'hybrid', 'template_only')

    def test_match_script_all_templates(self):
        """测试全部降级为模板的情况"""
        import asyncio
        matcher = SceneMatcher()

        segments = [
            {
                'index': 1, 'type': 'hook',
                'visual_requirement': {
                    'description': '不存在于任何电影中的场景',
                    'scene_hint': 'nonexistent_scene',
                },
                'estimated_duration_sec': 10.0,
            },
        ]

        report = asyncio.run(matcher.match_script(
            segments=segments,
            movie_id='unknown_movie',
            movie_scenes=[],  # 空场景
        ))

        assert report.composition_mode == 'template_only'
        assert report.overall_match_rate == 0.0
        assert report.segments[0].source == 'visual_template'

    def test_emotion_colors(self):
        """测试情绪→颜色映射"""
        matcher = SceneMatcher()
        assert len(matcher._emotion_colors('suspense')) == 2
        assert len(matcher._emotion_colors('unknown')) == 2  # 默认值
        assert matcher._emotion_colors('climax')[0].startswith('#')

    def test_emotion_emoji(self):
        """测试情绪→emoji映射"""
        matcher = SceneMatcher()
        assert matcher._emotion_emoji('suspense') == '😱'
        assert matcher._emotion_emoji('climax') == '🔥'
        assert matcher._emotion_emoji('reflection') == '💭'
        assert matcher._emotion_emoji('unknown') == '🎬'  # 默认值

    def test_timestamp_to_seconds(self):
        """测试时间戳转换"""
        matcher = SceneMatcher()
        assert matcher._timestamp_to_seconds('00:05:30') == 330.0
        assert matcher._timestamp_to_seconds('02:10:00') == 7800.0
        assert matcher._timestamp_to_seconds('01:30') == 90.0
        assert matcher._timestamp_to_seconds('45') == 45.0

    def test_template_plan_for_hook(self):
        """测试钩子段的模板分配"""
        matcher = SceneMatcher()
        seg = {'type': 'hook', 'emotion': 'suspense', 'text': '测试钩子',
               'visual_requirement': {'mood': 'dark'}}
        plan = matcher._get_visual_template_plan(seg)
        assert plan['template_id'] == 'emotion_card'
        assert 'config' in plan

    def test_template_plan_for_intro(self):
        """测试引入段的模板分配"""
        matcher = SceneMatcher()
        seg = {'type': 'intro', 'emotion': 'buildup', 'text': '测试引入',
               'visual_requirement': {}}
        plan = matcher._get_visual_template_plan(seg)
        assert plan['template_id'] == 'photo_card'
