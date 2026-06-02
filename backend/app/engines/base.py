"""引擎层共享工具 —— LLM 客户端抽象、重试、日志"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = structlog.get_logger(__name__)


class LLMClient:
    """统一的 LLM 客户端抽象层 —— 支持 OpenAI / Anthropic / DeepSeek 协议"""

    def __init__(self, model: str | None = None):
        self.model = model or settings.llm_model_creative
        self.api_key = settings.llm_api_key
        self.base_url = settings.llm_base_url

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.8,
        max_tokens: int = 4096,
        response_format: str = 'json_object',
    ) -> str:
        """调用 LLM 生成文本"""
        import httpx

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        payload = {
            'model': model or self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
        }

        # OpenAI-compatible 协议
        if response_format == 'json_object':
            payload['response_format'] = {'type': 'json_object'}

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data['choices'][0]['message']['content']

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.8,
    ) -> dict[str, Any]:
        """调用 LLM 生成 JSON"""
        text = await self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            response_format='json_object',
        )
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        """容错 JSON 解析 —— 处理 LLM 输出中的 markdown 包装"""
        # 去除可能的 markdown 代码块包装
        text = text.strip()
        if text.startswith('```'):
            text = re.sub(r'^```(?:json)?\s*\n', '', text)
            text = re.sub(r'\n```\s*$', '', text)
        return json.loads(text)


class PauseSyntaxConverter:
    """narrator-ai <#x#> 停顿语法 ←→ 标准 SSML <break> 互转"""

    PAUSE_PATTERN = re.compile(r'<#(\d+\.?\d*)#>')
    BREAK_PATTERN = re.compile(r'<break\s+time="([^"]+)"\s*/>')

    @classmethod
    def narrator_to_ssml(cls, text: str) -> str:
        """<#1.2#> → <break time="1200ms"/>"""
        def replace(m: re.Match) -> str:
            seconds = float(m.group(1))
            ms = int(seconds * 1000)
            return f'<break time="{ms}ms"/>'
        return cls.PAUSE_PATTERN.sub(replace, text)

    @classmethod
    def ssml_to_narrator(cls, ssml: str) -> str:
        """<break time="500ms"/> → <#0.5#>"""
        def replace(m: re.Match) -> str:
            time_str = m.group(1)
            if 'ms' in time_str:
                seconds = float(time_str.replace('ms', '')) / 1000
            else:
                seconds = float(time_str.replace('s', ''))
            return f'<#{seconds:.1f}#>'
        return cls.BREAK_PATTERN.sub(replace, ssml)


def estimate_duration(text: str, speech_rate: float = 1.0) -> float:
    """根据字数和语速估算配音时长（秒）
    - 中文标准语速：约 4 字/秒
    - 含停顿：实际约为字数的 0.3 倍
    """
    # 去除 SSML 标签，只计数字数
    clean = re.sub(r'<[^>]+>', '', text)
    char_count = len(clean)
    base_duration = char_count * 0.25  # 每字 0.25 秒
    return base_duration / speech_rate
