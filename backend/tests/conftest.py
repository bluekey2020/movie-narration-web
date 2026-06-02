"""测试配置 & 共享 Fixtures"""

import json
from pathlib import Path

import pytest

from app.config import Settings, PlatformConfig, settings
from app.models.movie import BGMTrack, Movie, MovieScene
from app.models.style import StyleFingerprint


# ==================================================================
# 测试数据 fixtures
# ==================================================================

@pytest.fixture
def sample_movie() -> Movie:
    """测试用电影数据"""
    return Movie(
        movie_id='shawshank_redemption',
        title='肖申克的救赎',
        year=1994,
        genre=['剧情', '犯罪'],
        rating=9.7,
        duration_min=142,
        director='弗兰克·德拉邦特',
        cast=['蒂姆·罗宾斯', '摩根·弗里曼'],
        plot_summary='银行家安迪被冤枉谋杀，被判终身监禁。他用20年完成惊天越狱。',
        narration_hotspots=['越狱片段', '希望主题', '屋顶喝啤酒'],
        key_scenes=[
            MovieScene(
                name='入狱', timestamp='00:05:30', duration_sec=45.0,
                tags=['压抑', '绝望'], description='安迪走进肖申克监狱',
                characters=['安迪']
            ),
            MovieScene(
                name='屋顶喝啤酒', timestamp='00:41:30', duration_sec=120.0,
                tags=['自由', '希望', '温暖'], description='安迪为狱友争取到喝啤酒的机会',
                characters=['安迪', '瑞德']
            ),
            MovieScene(
                name='越狱', timestamp='02:10:00', duration_sec=180.0,
                tags=['高潮', '释放', '自由'], description='安迪爬过污水管在雨中拥抱自由',
                characters=['安迪']
            ),
        ],
    )


@pytest.fixture
def sample_style_fingerprint() -> StyleFingerprint:
    """测试用风格指纹"""
    return StyleFingerprint(
        style_id='suspense_brainburn',
        name='suspense_brainburn',
        display_name='烧脑悬疑',
        description='设问句式+层层递进+信息密度高',
        avg_sentence_length=22,
        sentence_length_variance=0.35,
        pause_pattern=[0.5, 0.8, 1.2],
        hook_types=['information_gap', 'mystery_setup'],
        hook_density=250,
        emotion_switch_frequency=0.4,
        emotion_intensity_baseline=0.65,
        high_freq_words=['细节', '真相', '反转', '伏笔', '细思极恐'],
        banned_words=['该片', '影片', '总而言之'],
        sentence_pattern_preferences=['设问句', '层层递进', '留白结尾'],
        interjection_density=0.03,
        slang_usage=0.2,
        rhetorical_question_frequency=0.3,
        recommended_voice_id='narrator-male-middle-01',
        recommended_speech_rate=0.95,
        emotion_intensity=0.6,
        bgm_emotions=['suspense', 'mysterious', 'dark'],
        bgm_instruments=['piano', 'strings', 'electronic'],
        reference_sentences=[
            '你有没有想过，导演在开场第3分钟就已经告诉了你凶手是谁？',
        ],
    )


@pytest.fixture
def sample_segments() -> list[dict]:
    """测试用文案段落"""
    return [
        {
            'index': 1, 'type': 'hook',
            'text': '你有没有想过，一个被判终身监禁的银行家，如何用20年挖出一条隧道？',
            'ssml': '<speak><prosody rate="0.95">你有没有<emphasis>想过</emphasis></prosody><break time="500ms"/>一个被判<emphasis>终身监禁</emphasis>的银行家<break time="300ms"/>如何用20年挖出一条<emphasis>隧道</emphasis>？<break time="800ms"/></speak>',
            'emotion': 'suspense',
            'emphasis_words': ['想过', '终身监禁', '隧道'],
            'visual_requirement': {
                'description': '监狱高墙的压迫感',
                'preferred_source': 'original_clip',
                'scene_hint': 'shawshank_prison_exterior',
                'mood': 'oppressive_but_hopeful',
            },
            'estimated_duration_sec': 12.0,
        },
        {
            'index': 2, 'type': 'intro',
            'text': '1994年，弗兰克·德拉邦特拍出了一部传世经典。',
            'ssml': '<speak>1994年，弗兰克·德拉邦特拍出了一部<emphasis>传世经典</emphasis>。<break time="600ms"/></speak>',
            'emotion': 'buildup',
            'emphasis_words': ['传世经典'],
            'visual_requirement': {
                'description': '电影海报 + 年代感',
                'preferred_source': 'visual_template',
                'scene_hint': '',
                'mood': 'nostalgic',
            },
            'estimated_duration_sec': 8.0,
        },
        {
            'index': 7, 'type': 'ending',
            'text': '希望是好事，也许是人间至善。关注我，下期更精彩。',
            'ssml': '<speak>希望是好事，也许是人间至善。<break time="500ms"/>关注我，下期更精彩。<break time="800ms"/></speak>',
            'emotion': 'reflection',
            'emphasis_words': ['希望', '至善'],
            'visual_requirement': {
                'description': '电影结尾画面 + 升华文字',
                'preferred_source': 'visual_template',
            },
            'estimated_duration_sec': 10.0,
        },
    ]


@pytest.fixture
def sample_bgm_tracks() -> list[BGMTrack]:
    """测试用 BGM 曲库"""
    return [
        BGMTrack(
            track_id='bgm_001', title='悬疑铺垫', duration_sec=120.0,
            emotions=['suspense', 'dark', 'mysterious'], bpm=85,
            key='C minor', energy=0.3, instruments=['piano', 'strings'],
            sections=[
                {'start': 0, 'end': 15, 'type': 'intro'},
                {'start': 15, 'end': 90, 'type': 'main'},
                {'start': 90, 'end': 120, 'type': 'outro'},
            ],
            natural_cut_points=[15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 105.0, 120.0],
            usage_tags=['buildup', 'hook'], license_type='cc0',
        ),
        BGMTrack(
            track_id='bgm_002', title='紧张追逐', duration_sec=90.0,
            emotions=['tense', 'intense', 'urgent'], bpm=140,
            key='D minor', energy=0.8, instruments=['electronic', 'drums'],
            sections=[
                {'start': 0, 'end': 10, 'type': 'intro'},
                {'start': 10, 'end': 70, 'type': 'main'},
            ],
            natural_cut_points=[10.0, 25.0, 40.0, 55.0, 70.0, 90.0],
            usage_tags=['climax'], license_type='cc0',
        ),
        BGMTrack(
            track_id='bgm_003', title='史诗高潮', duration_sec=180.0,
            emotions=['epic', 'triumphant', 'heroic'], bpm=100,
            key='C major', energy=0.9, instruments=['orchestra', 'choir'],
            sections=[
                {'start': 0, 'end': 20, 'type': 'intro'},
                {'start': 20, 'end': 120, 'type': 'main'},
            ],
            natural_cut_points=[20.0, 40.0, 60.0, 80.0, 100.0, 120.0],
            usage_tags=['climax', 'ending'], license_type='licensed',
        ),
        BGMTrack(
            track_id='bgm_004', title='温暖回忆', duration_sec=150.0,
            emotions=['warm', 'nostalgic', 'hopeful'], bpm=75,
            key='G major', energy=0.4, instruments=['piano', 'guitar'],
            sections=[
                {'start': 0, 'end': 20, 'type': 'intro'},
                {'start': 20, 'end': 130, 'type': 'main'},
            ],
            natural_cut_points=[20.0, 50.0, 80.0, 110.0, 130.0],
            usage_tags=['reflection', 'ending'], license_type='cc0',
        ),
    ]
