"""配音引擎测试"""

import pytest

from app.engines.voice_engine import VoiceEngine, VoiceConfig, TTSRouter, create_voice_engine


class TestVoiceConfig:
    """配音配置测试"""

    def test_default_config(self):
        config = VoiceConfig(engine='narrator-ai', voice_id='narrator-male-youth-01')
        assert config.speech_rate == 1.0
        assert config.pitch == 0
        assert config.emotion_intensity == 0.7
        assert config.pause_syntax == 'ssml'

    def test_custom_config(self):
        config = VoiceConfig(
            engine='elevenlabs',
            voice_id='custom-voice-01',
            speech_rate=1.2,
            pitch=2,
            emotion_intensity=0.9,
            pause_syntax='narrator',
        )
        assert config.speech_rate == 1.2
        assert config.pitch == 2
        assert config.pause_syntax == 'narrator'


class TestVoiceEngine:
    """配音引擎测试"""

    def test_create_engine(self):
        engine = create_voice_engine()
        assert engine is not None

    def test_merge_ssml(self, sample_segments):
        """测试 SSML 合并"""
        engine = VoiceEngine()
        config = VoiceConfig(engine='narrator-ai', voice_id='test-voice')

        merged = engine._merge_ssml(sample_segments, config)
        assert merged.startswith('<speak>')
        assert merged.endswith('</speak>')
        # 段落间应有额外停顿（各段 SSML 内可能也含有 800ms 停顿）
        assert merged.count('<break time="800ms"/>') >= len(sample_segments) - 1

    def test_merge_ssml_narrator_format(self, sample_segments):
        """测试 narrator-ai 格式的停顿转换"""
        engine = VoiceEngine()
        # 造一段带 <#x#> 的文本
        segments = [{'ssml': '你好<#0.5#>世界<#0.3#>！', 'text': '你好<#0.5#>世界<#0.3#>！'}]
        config = VoiceConfig(engine='narrator-ai', voice_id='test', pause_syntax='ssml')

        merged = engine._merge_ssml(segments, config)
        # <#x#> 应该被转换为 <break>
        assert '<break time="500ms"/>' in merged
        assert '<break time="300ms"/>' in merged

    def test_validate_ssml_adds_speak_tag(self):
        """测试 SSML 验证 - 自动添加 speak 标签"""
        engine = VoiceEngine()
        raw = '你好世界'
        validated = engine._validate_ssml(raw)
        assert validated.startswith('<speak>')
        assert validated.endswith('</speak>')

    def test_validate_ssml_preserve_existing(self):
        """测试 SSML 验证 - 保留已有的 speak 标签"""
        engine = VoiceEngine()
        raw = '<speak>你好世界</speak>'
        validated = engine._validate_ssml(raw)
        assert validated == raw

    def test_calculate_segment_timings(self, sample_segments):
        """测试段落时间轴计算"""
        engine = VoiceEngine()
        timings = engine._calculate_segment_timings(sample_segments, speech_rate=1.0)

        assert len(timings) == len(sample_segments)
        # 第一个段落应该从 0 开始
        assert timings[0]['start_sec'] == 0.0
        # 每段应有正时长
        for t in timings:
            assert t['duration_sec'] > 0
            assert t['end_sec'] > t['start_sec']

    def test_calculate_segment_timings_fast_rate(self, sample_segments):
        """测试快速语速下的时间轴"""
        engine = VoiceEngine()
        timings_slow = engine._calculate_segment_timings(sample_segments, speech_rate=1.0)
        timings_fast = engine._calculate_segment_timings(sample_segments, speech_rate=1.5)

        # 快速语速总时长应该更短
        total_slow = sum(t['duration_sec'] for t in timings_slow)
        total_fast = sum(t['duration_sec'] for t in timings_fast)
        assert total_fast < total_slow

    def test_cost_calculation(self):
        """测试成本计算"""
        engine = VoiceEngine()
        cost = engine._calculate_cost(60.0, 'edge-tts')
        assert cost == 0.0  # Edge-TTS 免费

        cost_eleven = engine._calculate_cost(60.0, 'elevenlabs')
        assert cost_eleven == 0.50  # ¥0.50/分钟

        cost_narrator = engine._calculate_cost(60.0, 'narrator-ai')
        assert cost_narrator == 0.15  # ¥0.15/分钟


class TestTTSRouter:
    """TTS 路由测试"""

    def test_preview_mode(self):
        router = TTSRouter()
        config = router.route({'mode': 'preview'})
        assert config.engine == 'edge-tts'

    def test_quality_high_budget(self):
        router = TTSRouter()
        config = router.route({'priority': 'quality', 'budget': 'high', 'mode': 'production'})
        assert config.engine == 'elevenlabs'

    def test_voice_clone_low_budget(self):
        router = TTSRouter()
        config = router.route({
            'voice_clone': True, 'budget': 'low',
            'mode': 'production', 'priority': 'standard',
        })
        assert config.engine == 'cosyvoice2'

    def test_narration_style_match(self):
        """测试影视解说风格优先匹配 narrator-ai"""
        router = TTSRouter()
        config = router.route({
            'style': 'suspense_brainburn',
            'mode': 'production', 'priority': 'standard',
        })
        assert config.engine == 'narrator-ai'

    def test_default_route(self):
        router = TTSRouter()
        config = router.route({'mode': 'production'})
        assert config.engine in ('narrator-ai', 'cosyvoice2', 'elevenlabs', 'edge-tts')
