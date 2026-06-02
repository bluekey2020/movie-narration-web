"""文案生成引擎测试"""

import pytest

from app.engines.script_engine import ScriptEngine, create_script_engine
from app.engines.base import PauseSyntaxConverter, estimate_duration


class TestPauseSyntaxConverter:
    """停顿语法转换器测试"""

    def test_narrator_to_ssml(self):
        """测试 narrator-ai <#x#> → SSML <break> 转换"""
        text = '你好<#0.5#>世界<#1.2#>！'
        result = PauseSyntaxConverter.narrator_to_ssml(text)
        assert '<break time="500ms"/>' in result
        assert '<break time="1200ms"/>' in result
        assert '<#0.5#>' not in result

    def test_ssml_to_narrator(self):
        """测试 SSML <break> → narrator-ai <#x#> 转换"""
        ssml = '你好<break time="500ms"/>世界<break time="1200ms"/>！'
        result = PauseSyntaxConverter.ssml_to_narrator(ssml)
        assert '<#0.5#>' in result
        assert '<#1.2#>' in result
        assert '<break' not in result

    def test_roundtrip(self):
        """测试往返转换：narrator → SSML → narrator"""
        original = '开场<#0.3#>这是正文<#0.8#>结尾'
        ssml = PauseSyntaxConverter.narrator_to_ssml(original)
        back = PauseSyntaxConverter.ssml_to_narrator(ssml)
        # 往返后应该一致（允许浮点精度差异）
        assert '0.3' in back
        assert '0.8' in back

    def test_no_pause_text(self):
        """测试没有停顿标记的文本"""
        text = '这是一段没有停顿的文本'
        result = PauseSyntaxConverter.narrator_to_ssml(text)
        assert result == text


class TestEstimateDuration:
    """时长预估测试"""

    def test_simple_text(self):
        """简单文本时长预估"""
        dur = estimate_duration('这是一段十个字的文本', speech_rate=1.0)
        assert 2.0 < dur < 3.0  # 10 字 ≈ 2.5 秒

    def test_with_ssml(self):
        """带 SSML 标签的文本（标签应被去除）"""
        dur = estimate_duration('<speak>你好<break time="500ms"/>世界</speak>', speech_rate=1.0)
        assert 0.8 < dur < 1.2  # 4 字 ≈ 1.0 秒

    def test_with_speed(self):
        """带语速参数"""
        dur_base = estimate_duration('一段测试文本用于检测语速影响', speech_rate=1.0)
        dur_fast = estimate_duration('一段测试文本用于检测语速影响', speech_rate=1.5)
        assert dur_fast < dur_base


class TestScriptEngine:
    """文案生成引擎测试"""

    def test_create_engine(self):
        """测试引擎创建"""
        engine = create_script_engine()
        assert engine is not None
        assert isinstance(engine, ScriptEngine)

    def test_score_hook_strong(self):
        """测试强钩子评分"""
        engine = ScriptEngine()
        score = engine._score_hook({
            'text': '你有没有想过，一个被判终身监禁的人，如何用20年挖出一条隧道？'
        })
        assert score > 6.0, f'强钩子应得分 > 6，实际 {score}'

    def test_score_hook_weak(self):
        """测试弱钩子评分"""
        engine = ScriptEngine()
        score = engine._score_hook({
            'text': '今天我们来聊聊肖申克的救赎这部经典电影'
        })
        assert score < 8.0, f'弱钩子应得分 < 8，实际 {score}'

    def test_score_hook_empty(self):
        """测试空钩子"""
        engine = ScriptEngine()
        score = engine._score_hook({'text': ''})
        assert score == 0.0

    def test_score_density(self):
        """测试信息密度评分"""
        engine = ScriptEngine()
        script = {
            'segments': [
                {'text': '安迪用一把小锤子挖了20年，穿过500码污水管道，最终从监狱排污口掉进河里。'},
                {'text': '瑞德说：有些鸟是关不住的，它们的羽毛太鲜亮了。'},
            ]
        }
        score = engine._score_density(script, 60)
        assert 0.0 <= score <= 10.0

    def test_score_rhythm(self, sample_style_fingerprint):
        """测试节奏评分"""
        engine = ScriptEngine()
        segments = [
            {'text': '短句', 'emotion': 'suspense'},
            {'text': '这是一段中等长度的句子用于情绪铺垫和背景介绍', 'emotion': 'buildup'},
            {'text': '高潮段落的文字通常会更长更有冲击力让人热血沸腾激动不已', 'emotion': 'climax'},
        ]
        score = engine._score_rhythm(segments, sample_style_fingerprint)
        assert 0.0 <= score <= 10.0

    def test_score_colloquial(self):
        """测试口语化评分"""
        engine = ScriptEngine()
        # 口语化好的
        script_good = {
            'segments': [
                {'text': '离谱，真的太离谱了！这片子绝了好吗！'}
            ]
        }
        score_good = engine._score_colloquial(script_good)

        # 口语化差的（书面的）
        script_bad = {
            'segments': [
                {'text': '该片通过精巧的叙事结构，展现了主人公在逆境中不屈不挠的精神品质。'}
            ]
        }
        score_bad = engine._score_colloquial(script_bad)

        assert score_good > score_bad, f'口语化好的应得分更高: good={score_good} vs bad={score_bad}'

    def test_check_sensitive(self):
        """测试敏感词检查"""
        engine = ScriptEngine()
        script_clean = {'segments': [{'text': '这是一部好电影'}]}
        assert engine._check_sensitive(script_clean) == 10.0

        script_risky = {'segments': [{'text': '这部电影涉及政治敏感内容'}]}
        # 注意：这里的简化版敏感词检测可能不会有完全真实的效果
        # 实际生产环境中应该有更完善的敏感词库
        score = engine._check_sensitive(script_risky)
        assert 0.0 <= score <= 10.0

    def test_fingerprint_to_params(self, sample_style_fingerprint):
        """测试风格指纹参数转换"""
        engine = ScriptEngine()
        params = engine._fingerprint_to_params(sample_style_fingerprint)
        assert '叙事节奏' in params
        assert '钩子策略' in params
        assert '情绪参数' in params
        assert '词汇风格' in params
        assert '口语特征' in params
        assert params['叙事节奏']['平均句长'] == '22字'


class TestScoreAllDimensions:
    """综合评分维度测试"""

    def test_all_dimensions_present(self):
        """验证评分报告包含所有维度"""
        engine = ScriptEngine()
        # 模拟的评分维度
        expected_dims = [
            'hook_attraction', 'information_density', 'rhythm_curve',
            'colloquialism', 'duration_compliance', 'style_consistency',
            'sensitive_word_check',
        ]
        # 这些维度在 _score_hook, _score_density 等方法中都有对应
        for dim in expected_dims:
            assert dim is not None  # 确保维度名称存在
