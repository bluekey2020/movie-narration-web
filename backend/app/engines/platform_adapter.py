"""多平台自适应引擎

核心突破：不只是格式转换（分辨率/时长/字幕），
而是"语体翻译" —— 同一段文案在不同平台用不同的话语体系表达。

参考: B站花生/UpDream 平台适配 + narrator-ai 多平台参数
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from app.config import Platform, settings
from app.engines.base import LLMClient

logger = structlog.get_logger(__name__)


@dataclass
class AdaptedScript:
    """适配后的文案"""
    platform: Platform
    text: str
    ssml: str
    segments: list[dict]
    canvas: dict         # width, height
    subtitle_style: str
    speech_rate: float
    total_words: int
    estimated_duration_sec: float


class PlatformAdapter:
    """多平台自适应引擎"""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    async def adapt(
        self, base_script: dict, target_platform: Platform
    ) -> AdaptedScript:
        """将基础文案适配到目标平台

        核心步骤：
        1. 语体翻译（LLM 改写话语体系）
        2. 格式适配（分辨率/字幕/语速）
        3. 时长压缩/扩展
        """
        platform_cfg = settings.platforms[target_platform]

        # 1. 语体翻译
        adapted_text = await self._translate_style(
            base_script=base_script,
            platform_config=platform_cfg,
        )

        # 2. 格式适配
        adapted = AdaptedScript(
            platform=target_platform,
            text=adapted_text.get('text', ''),
            ssml=adapted_text.get('ssml', ''),
            segments=adapted_text.get('segments', []),
            canvas={
                'width': platform_cfg.resolution[0],
                'height': platform_cfg.resolution[1],
            },
            subtitle_style=platform_cfg.subtitle_style,
            speech_rate=platform_cfg.speech_rate,
            total_words=adapted_text.get('total_words', 0),
            estimated_duration_sec=adapted_text.get('estimated_duration_sec', 0),
        )

        return adapted

    async def batch_adapt(
        self, base_script: dict, platforms: list[Platform]
    ) -> dict[Platform, AdaptedScript]:
        """一键适配多平台 —— 实际生产中并发调用"""
        import asyncio

        tasks = {p: self.adapt(base_script, p) for p in platforms}
        results = {}
        for platform, task in tasks.items():
            results[platform] = await task
        return results

    # ==================================================================
    # 语体翻译
    # ==================================================================

    async def _translate_style(self, base_script: dict, platform_cfg) -> dict:
        """LLM 语体翻译 —— 改变话语体系而不仅是缩写"""
        base_text = self._extract_full_text(base_script)

        style_params = platform_cfg.style_params

        system = f"""你是一位{platform_cfg.display_name}平台的资深影视解说博主。
请将以下基础解说文案改写为适合{platform_cfg.display_name}平台的版本。

改写要求（不是简单的缩写/扩写，而是要改变话语体系）：
1. 称呼用户为"{style_params['address_term']}"
2. 开场风格：{style_params['opening_tone']}
3. 结尾参考："{style_params['closing']}"
4. 网络用语密度：{style_params['slang_density']} （0=完全不用, 1=密集使用）
5. 句长风格：{style_params['sentence_length']}
6. 总字数控制在 {platform_cfg.max_words} 字以内
7. 时长控制在 {platform_cfg.duration_range[0]}-{platform_cfg.duration_range[1]} 秒
8. 开场必须在 {platform_cfg.hook_window} 秒内建立钩子

原始文案：
{base_text}

请输出改写后的 JSON（包含完整的 7 段结构和 SSML 标注）：
{{
  "text": "完整文案（纯文本）",
  "ssml": "完整 SSML 标注版本",
  "segments": [ ...七段... ],
  "total_words": 600,
  "estimated_duration_sec": 180
}}"""

        return await self.llm.generate_json(system, '', temperature=0.75)

    # ==================================================================
    # 钩子策略转换
    # ==================================================================

    async def adapt_hook(self, hook_text: str, platform: Platform) -> str:
        """单独改写开场钩子（高优先级操作）"""
        platform_cfg = settings.platforms[platform]

        prompt = f"""请将以下解说视频的开场钩子改写为{platform_cfg.display_name}风格。

原始钩子：{hook_text}

要求：
- {platform_cfg.display_name}风格，称呼用户为"{platform_cfg.style_params['address_term']}"
- 必须在 {platform_cfg.hook_window} 秒内讲完
- 制造信息差或情感冲击
- 保持原意但改变表达方式"""
        result = await self.llm.generate_json(prompt, '', temperature=0.85)
        return result.get('hook', hook_text)

    # ==================================================================
    # 结尾话术转换
    # ==================================================================

    async def adapt_ending(
        self, ending_text: str, platform: Platform, style_name: str = ''
    ) -> str:
        """改写结尾（引导关注/三连/评论）"""
        platform_cfg = settings.platforms[platform]

        prompt = f"""请改写解说视频的结尾，适配{platform_cfg.display_name}平台。

原始结尾：{ending_text}
解说风格：{style_name}

{platform_cfg.display_name}的结尾风格参考："{platform_cfg.style_params['closing']}"

请输出改写的结尾（2-3句话），保留原意的情感余韵。"""
        result = await self.llm.generate_json(prompt, '', temperature=0.7)
        return result.get('ending', ending_text)

    # ==================================================================
    # 格式参数
    # ==================================================================

    def get_export_params(self, platform: Platform) -> dict:
        """获取平台导出参数"""
        cfg = settings.platforms[platform]
        return {
            'resolution': f'{cfg.resolution[0]}x{cfg.resolution[1]}',
            'aspect_ratio': f'{cfg.aspect_ratio[0]}:{cfg.aspect_ratio[1]}',
            'fps': 30,
            'video_bitrate': self._recommend_bitrate(cfg.resolution),
            'audio_bitrate': '192k',
            'format': 'mp4',
            'codec': 'h264',
        }

    @staticmethod
    def _recommend_bitrate(resolution: tuple[int, int]) -> str:
        """根据分辨率推荐码率"""
        pixels = resolution[0] * resolution[1]
        if pixels >= 3840 * 2160:
            return '45M'
        elif pixels >= 1920 * 1080:
            return '15M'
        elif pixels >= 1280 * 720:
            return '10M'
        else:
            return '5M'

    @staticmethod
    def _extract_full_text(script: dict) -> str:
        """从脚本中提取完整文本"""
        segments = script.get('segments', [])
        return '\n\n'.join(s.get('text', '') for s in segments)


def create_platform_adapter() -> PlatformAdapter:
    return PlatformAdapter()
