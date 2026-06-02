"""VDL 编译器与平台适配器测试"""

import pytest

from app.engines.vdl_compiler import (
    VDLCompiler, VDLBuilder, FFmpegCommand, TransitionType, create_vdl_compiler
)
from app.engines.platform_adapter import PlatformAdapter, AdaptedScript, create_platform_adapter


class TestVDLBuilder:
    """VDL 构建器测试"""

    def test_build_minimal(self):
        builder = VDLBuilder()
        builder.set_metadata('测试视频', '测试电影', 'comedy', 'douyin')
        builder.set_canvas('douyin')

        doc = builder.build()
        assert doc['version'] == '1.0'
        assert doc['metadata']['title'] == '测试视频'
        assert doc['metadata']['platform'] == 'douyin'
        assert doc['segments'] == []

    def test_build_with_segments(self):
        builder = VDLBuilder()
        builder.set_metadata('测试', '测试电影', 'action_hot', 'bilibili')
        builder.set_canvas('bilibili')

        builder.add_segment(
            index=1,
            start_time=0,
            duration=12.5,
            video_source={'source': 'movie_clip', 'clipRef': {'movieId': 'test', 'timeRange': [0, 12.5]}},
            tts_ssml='<speak>测试钩子</speak>',
            tts_voice='test-voice',
            bgm_track_id='bgm_001',
            subtitle_text='测试字幕',
            transition='fade',
        )

        doc = builder.build()
        assert len(doc['segments']) == 1
        seg = doc['segments'][0]
        assert seg['index'] == 1
        assert seg['duration'] == 12.5
        assert seg['video']['primary']['source'] == 'movie_clip'
        assert seg['audio']['tts']['ssml'] == '<speak>测试钩子</speak>'
        assert seg['transition']['type'] == 'fade'

    def test_build_canvas_size(self):
        builder = VDLBuilder()
        builder.set_canvas('douyin')
        doc = builder.build()
        assert doc['canvas']['width'] == 1080
        assert doc['canvas']['height'] == 1920

        builder2 = VDLBuilder()
        builder2.set_canvas('bilibili')
        doc2 = builder2.build()
        assert doc2['canvas']['width'] == 1920
        assert doc2['canvas']['height'] == 1080


class TestVDLCompiler:
    """VDL 编译器测试"""

    def test_create_compiler(self):
        compiler = create_vdl_compiler()
        assert compiler is not None

    def test_compile_empty_segments_raises(self):
        compiler = VDLCompiler()
        doc = {'segments': [], 'canvas': {'width': 1080, 'height': 1920, 'fps': 30}}
        with pytest.raises(ValueError, match='at least one segment'):
            compiler.compile(doc)

    def test_compile_minimal(self):
        compiler = VDLCompiler()
        doc = {
            'version': '1.0',
            'metadata': {'output_path': '/tmp/test.mp4'},
            'canvas': {'width': 1080, 'height': 1920, 'fps': 30},
            'segments': [{
                'index': 1,
                'startTime': 0,
                'duration': 10.0,
                'video': {'primary': {'source': 'visual_template', 'templateId': 'photo_card'}},
                'audio': {'tts': {'engine': 'narrator-ai', 'voiceId': 'test', 'ssml': '<speak>测试</speak>'}},
                'transition': {'type': 'cut', 'duration': 0},
            }],
        }

        result = compiler.compile(doc)
        assert isinstance(result, FFmpegCommand)
        assert len(result.inputs) > 0
        assert 'concat' in result.filter_complex
        assert result.estimated_duration == 10.0

    def test_compile_movie_clip(self):
        compiler = VDLCompiler()
        doc = {
            'canvas': {'width': 1920, 'height': 1080, 'fps': 30},
            'segments': [{
                'index': 1, 'startTime': 0, 'duration': 30.0,
                'video': {
                    'primary': {
                        'source': 'movie_clip',
                        'clipRef': {
                            'movieId': 'shawshank',
                            'timeRange': [100.0, 130.0],
                            'effects': [],
                        }
                    }
                },
                'audio': {'tts': {}},
                'transition': {'type': 'dissolve', 'duration': 500},
            }],
        }

        result = compiler.compile(doc)
        assert 'scale=1920:1080' in result.filter_complex
        assert 'fade=t=in' in result.filter_complex

    def test_resolve_video_source_movie_clip(self):
        compiler = VDLCompiler()
        src = compiler._resolve_video_source({
            'source': 'movie_clip',
            'clipRef': {'movieId': 'test_movie'},
        })
        assert src['type'] == 'file'
        assert 'test_movie' in src['path']

    def test_resolve_video_source_template(self):
        compiler = VDLCompiler()
        src = compiler._resolve_video_source({
            'source': 'visual_template',
            'templateId': 'photo_card',
        })
        assert src['type'] == 'template'

    def test_validate_invalid_canvas(self):
        compiler = VDLCompiler()
        doc = {
            'canvas': {'width': 0, 'height': 0},
            'segments': [{'index': 1, 'duration': 10}],
        }
        with pytest.raises(ValueError, match='Invalid canvas'):
            compiler._validate(doc)


class TestPlatformAdapter:
    """平台适配器测试"""

    def test_create_adapter(self):
        adapter = create_platform_adapter()
        assert adapter is not None

    def test_get_export_params(self):
        adapter = PlatformAdapter()
        params = adapter.get_export_params('douyin')
        assert params['resolution'] == '1080x1920'
        assert params['aspect_ratio'] == '9:16'
        assert params['format'] == 'mp4'

        params = adapter.get_export_params('bilibili')
        assert params['resolution'] == '1920x1080'
        assert params['aspect_ratio'] == '16:9'

    def test_bitrate_recommendation(self):
        adapter = PlatformAdapter()
        assert adapter._recommend_bitrate((3840, 2160)) == '45M'   # 4K
        assert adapter._recommend_bitrate((1920, 1080)) == '15M'   # 横屏1080p
        assert adapter._recommend_bitrate((1080, 1920)) == '15M'   # 竖屏1080p (同像素数)
        assert adapter._recommend_bitrate((1280, 720)) == '10M'    # 720p

    def test_extract_full_text(self):
        adapter = PlatformAdapter()
        script = {
            'segments': [
                {'text': '第一段文案'},
                {'text': '第二段文案'},
                {'text': '第三段文案'},
            ]
        }
        text = adapter._extract_full_text(script)
        assert '第一段文案' in text
        assert '第二段文案' in text
        assert '\n\n' in text
