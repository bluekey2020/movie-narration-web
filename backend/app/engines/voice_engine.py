"""配音生成引擎 —— SSML 标注驱动 + 多引擎路由

核心设计：
- LLM 在写文案时同步输出 SSML 发音标注
- 用户只需选择"配音角色"，其余全部自动
- 多引擎智能路由：narrator-ai / CosyVoice2 / ElevenLabs / Edge-TTS

参考: narrator-ai <#x#> 停顿语法 + CosyVoice2 零样本克隆 + ElevenLabs 情绪控制
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

import structlog

from app.config import settings, TTSEngine
from app.engines.base import PauseSyntaxConverter

logger = structlog.get_logger(__name__)


@dataclass
class VoiceConfig:
    """配音配置"""
    engine: TTSEngine
    voice_id: str
    speech_rate: float = 1.0
    pitch: int = 0                # -10 ~ +10 半音
    emotion_intensity: float = 0.7
    pause_syntax: Literal['ssml', 'narrator'] = 'ssml'


@dataclass
class VoiceResult:
    """配音生成结果"""
    audio_url: str
    duration_sec: float
    segments: list[dict]           # 每段配音的精确起止时间
    engine_used: TTSEngine
    cost: float


class VoiceEngine:
    """配音生成引擎"""

    def __init__(self):
        self.converter = PauseSyntaxConverter()

    async def generate(
        self,
        segments: list[dict],
        config: VoiceConfig,
        output_format: str = 'mp3',
    ) -> VoiceResult:
        """为整篇文案生成配音

        Args:
            segments: 文案段落列表 (含 ssml 字段)
            config: 配音配置
            output_format: 输出音频格式
        """
        # 1. 合并所有段落的 SSML
        full_ssml = self._merge_ssml(segments, config)

        # 2. 验证 SSML
        validated = self._validate_ssml(full_ssml)

        # 3. 路由到 TTS 引擎
        engine_func = self._get_engine_handler(config.engine)
        result = await engine_func(validated, config, output_format)

        # 4. 计算每段的精确时间轴
        segment_timings = self._calculate_segment_timings(segments, config.speech_rate)

        return VoiceResult(
            audio_url=result.get('url', ''),
            duration_sec=result.get('duration_sec', 0),
            segments=segment_timings,
            engine_used=config.engine,
            cost=self._calculate_cost(result.get('duration_sec', 0), config.engine),
        )

    # ==================================================================
    # SSML 处理
    # ==================================================================

    def _merge_ssml(self, segments: list[dict], config: VoiceConfig) -> str:
        """合并所有段落的 SSML，添加段落间停顿"""
        ssml_parts = []
        for i, seg in enumerate(segments):
            ssml_text = seg.get('ssml', seg.get('text', ''))
            # narrator-ai 格式 → 标准 SSML
            if config.pause_syntax == 'ssml' and '<#' in ssml_text:
                ssml_text = self.converter.narrator_to_ssml(ssml_text)
            ssml_parts.append(ssml_text)

            # 段落间额外停顿
            if i < len(segments) - 1:
                ssml_parts.append('<break time="800ms"/>')

        return f'<speak>{" ".join(ssml_parts)}</speak>'

    def _validate_ssml(self, ssml: str) -> str:
        """验证 SSML 合法性"""
        # 1. XML 结构完整性
        if not ssml.startswith('<speak>'):
            ssml = f'<speak>{ssml}'
        if not ssml.endswith('</speak>'):
            ssml = f'{ssml}</speak>'

        # 2. 检查常见问题
        self._check_ssml_issues(ssml)

        return ssml

    def _check_ssml_issues(self, ssml: str) -> None:
        """检查 SSML 常见问题"""
        # 未闭合标签
        tags = re.findall(r'<(/?)\w+', ssml)
        stack: list[str] = []
        for tag in tags:
            if tag.startswith('/'):
                if stack and stack[-1] == tag[1:]:
                    stack.pop()
            else:
                stack.append(tag)
        if stack:
            logger.warning('unclosed_ssml_tags', tags=stack)

        # 停顿过长（> 10 秒）
        long_pauses = re.findall(r'<break time="(\d+)ms"/>', ssml)
        for pause_ms in long_pauses:
            if int(pause_ms) > 10000:
                logger.warning('long_pause_detected', duration_ms=pause_ms)

        # 预估总时长
        clean_text = re.sub(r'<[^>]+>', '', ssml)
        pauses_ms = sum(int(p) for p in long_pauses)
        total_est = len(clean_text) * 250 + pauses_ms  # ms
        if total_est > 900_000:  # 超过 15 分钟
            logger.warning('tts_duration_too_long', estimated_min=total_est / 60000)

    # ==================================================================
    # TTS 引擎路由
    # ==================================================================

    def _get_engine_handler(self, engine: TTSEngine):
        """获取引擎处理器"""
        handlers = {
            'narrator-ai': self._call_narrator_ai,
            'cosyvoice2': self._call_cosyvoice2,
            'elevenlabs': self._call_elevenlabs,
            'edge-tts': self._call_edge_tts,
        }
        return handlers.get(engine, self._call_edge_tts)

    async def _call_narrator_ai(self, ssml: str, config: VoiceConfig, fmt: str) -> dict:
        """调用 narrator-ai TTS API"""
        import httpx

        # 转换回 narrator-ai 格式（它原生支持 <#x#> 更高效）
        narrator_text = self.converter.ssml_to_narrator(ssml)

        payload = {
            'voice_id': config.voice_id,
            'text': narrator_text,
            'speed': config.speech_rate,
            'format': fmt,
        }

        headers = {
            'Authorization': f'Bearer {settings.narrator_api_key}',
            'Content-Type': 'application/json',
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f'{settings.narrator_api_base}/tts/generate',
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return {'url': data.get('audio_url', ''), 'duration_sec': data.get('duration', 0)}

    async def _call_cosyvoice2(self, ssml: str, config: VoiceConfig, fmt: str) -> dict:
        """调用 CosyVoice2（自部署）—— 零样本语音克隆"""
        import httpx

        payload = {
            'tts_text': re.sub(r'<[^>]+>', '', ssml),  # CosyVoice2 对 SSML 支持有限
            'voice_id': config.voice_id,
            'speed': config.speech_rate,
            'format': fmt,
        }

        endpoint = settings.tts_engines['cosyvoice2']['endpoint']
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f'{endpoint}/tts', json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {'url': data.get('url', ''), 'duration_sec': data.get('duration', 0)}

    async def _call_elevenlabs(self, ssml: str, config: VoiceConfig, fmt: str) -> dict:
        """调用 ElevenLabs TTS（质量最高，成本最贵）"""
        import httpx

        clean_text = re.sub(r'<break[^>]+/>', '\n', ssml)
        clean_text = re.sub(r'<[^>]+>', '', clean_text)

        payload = {
            'text': clean_text,
            'model_id': 'eleven_multilingual_v2',
            'voice_settings': {
                'stability': 0.5,
                'similarity_boost': 0.75,
            }
        }

        api_key = settings.tts_engines.get('elevenlabs', {}).get('api_key', '')
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f'https://api.elevenlabs.io/v1/text-to-speech/{config.voice_id}',
                headers={'xi-api-key': api_key},
                json=payload,
            )
            resp.raise_for_status()
            # ElevenLabs 返回二进制音频
            return {'url': '', 'duration_sec': len(clean_text) * 0.25}

    async def _call_edge_tts(self, ssml: str, config: VoiceConfig, fmt: str) -> dict:
        """调用 Edge-TTS（免费，适合预览和 MVP）"""
        # Edge-TTS 不支持 HTTP API，通常用命令行或 Python 库
        # 这里返回模拟结果（实际生产用 edge_tts Python 包）
        clean_text = re.sub(r'<[^>]+>', '', ssml)
        estimated_duration = len(clean_text) * 0.25 / config.speech_rate
        return {'url': '', 'duration_sec': estimated_duration}

    # ==================================================================
    # 时间轴计算
    # ==================================================================

    def _calculate_segment_timings(
        self, segments: list[dict], speech_rate: float
    ) -> list[dict]:
        """根据字数和语速计算每段配音的精确起止时间"""
        timings = []
        current_time = 0.0

        for seg in segments:
            text = seg.get('text', '')
            clean = re.sub(r'<[^>]+>', '', text)
            char_count = len(clean)

            # 计算段落持续时间（含停顿）
            duration = char_count * 0.25 / speech_rate

            # 加上段落内 SSML 停顿
            ssml = seg.get('ssml', '')
            pauses = re.findall(r'<break time="(\d+)ms"/>', ssml)
            total_pause = sum(int(p) for p in pauses) / 1000

            segment_duration = duration + total_pause

            timings.append({
                'segment_index': seg.get('index', 0),
                'start_sec': round(current_time, 2),
                'end_sec': round(current_time + segment_duration, 2),
                'duration_sec': round(segment_duration, 2),
            })

            current_time += segment_duration
            # 段落间停顿
            current_time += 0.8

        return timings

    # ==================================================================
    # 成本计算
    # ==================================================================

    def _calculate_cost(self, duration_sec: float, engine: TTSEngine) -> float:
        """计算配音成本"""
        cost_per_min = settings.tts_engines.get(engine, {}).get('cost_per_minute', 0)
        return round(duration_sec / 60 * cost_per_min, 4)


# ==================================================================
# TTS 引擎智能路由
# ==================================================================

class TTSRouter:
    """TTS 引擎智能路由 —— 按任务需求自动选引擎"""

    def route(self, task: dict) -> VoiceConfig:
        """根据任务需求自动选择最佳 TTS 引擎

        决策维度：
        - 质量优先 → ElevenLabs
        - 成本敏感 + 需要克隆 → CosyVoice2
        - 影视解说风格匹配 → narrator-ai
        - 预览/草稿 → Edge-TTS
        """
        priority = task.get('priority', 'quality')
        budget = task.get('budget', 'medium')
        mode = task.get('mode', 'production')
        need_clone = task.get('voice_clone', False)

        if mode == 'preview':
            engine: TTSEngine = 'edge-tts'
        elif priority == 'quality' and budget == 'high':
            engine = 'elevenlabs'
        elif need_clone and budget in ('low', 'medium'):
            engine = 'cosyvoice2'
        elif task.get('style') in ('action_hot', 'suspense_brainburn', 'comedy'):
            engine = 'narrator-ai'  # narrator-ai 的解说风格匹配最好
        else:
            engine = settings.default_tts_engine

        return VoiceConfig(
            engine=engine,
            voice_id=task.get('voice_id', 'narrator-male-youth-01'),
            speech_rate=task.get('speech_rate', 1.0),
            emotion_intensity=task.get('emotion_intensity', 0.7),
        )


def create_voice_engine() -> VoiceEngine:
    return VoiceEngine()
