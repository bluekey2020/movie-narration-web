"""风格指纹模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StyleFingerprint:
    """风格指纹 —— 完整定义一个解说风格的参数集"""
    style_id: str
    name: str
    display_name: str
    description: str = ''

    # 叙事节奏
    avg_sentence_length: int = 18          # 平均句长 (字数)
    sentence_length_variance: float = 0.3  # 句长变化幅度
    pause_pattern: list[float] = field(default_factory=lambda: [0.3, 0.5, 0.8])  # 段落间停顿偏好

    # 钩子策略
    hook_types: list[str] = field(default_factory=lambda: ['information_gap'])
    hook_density: int = 200               # 每 N 字一个钩子点

    # 情绪曲线
    emotion_switch_frequency: float = 0.3  # 情绪切换频率 (0-1)
    emotion_intensity_baseline: float = 0.7
    emotion_progression: list[str] = field(default_factory=list)  # 标准情绪递进序列

    # 词汇风格
    high_freq_words: list[str] = field(default_factory=list)
    banned_words: list[str] = field(default_factory=list)
    sentence_pattern_preferences: list[str] = field(default_factory=list)

    # 口语特征
    interjection_density: float = 0.05     # 语气词密度
    slang_usage: float = 0.3               # 网络用语使用频率
    rhetorical_question_frequency: float = 0.1

    # 配音偏好
    recommended_voice_id: str = ''
    recommended_speech_rate: float = 1.0
    emotion_intensity: float = 0.7

    # BGM 偏好
    bgm_emotions: list[str] = field(default_factory=list)
    bgm_instruments: list[str] = field(default_factory=list)

    # 参考例句（从风格学习中提取）
    reference_sentences: list[str] = field(default_factory=list)

    # 元数据
    author: str = ''
    usage_count: int = 0
    rating: float = 0.0
    version: int = 1
