"""ComfyUI 客户端 —— 连接本地 ComfyUI 实例

基于 Pixelle-Video 的 ComfyKit 设计理念：
- 每个视觉生成能力对应一个 ComfyUI workflow JSON
- 管线与具体模型完全解耦
- 支持队列提交 + WebSocket 进度监听

ComfyUI 路径: e:/comfyui/resources/ComfyUI/
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# ComfyUI 路径
COMFYUI_ROOT = Path(r'e:\comfyui\resources\ComfyUI')
WORKFLOWS_DIR = Path(__file__).parent.parent.parent / 'data' / 'workflows'


@dataclass
class ComfyUIWorkflow:
    """ComfyUI 工作流封装"""
    name: str
    description: str
    workflow_json: dict
    output_node_id: int  # 输出图片的节点 ID


@dataclass
class ComfyUIGenerationResult:
    """ComfyUI 生成结果"""
    images: list[bytes]     # 生成的图片二进制数据
    metadata: dict          # 生成参数元数据
    workflow_name: str


class ComfyUIClient:
    """ComfyUI API 客户端

    用法:
        client = ComfyUIClient()
        result = await client.generate(
            workflow=photo_card_workflow,
            prompt_text="肖申克的救赎 - 希望与自由",
            positive_prompt="cinematic poster, dramatic lighting",
            negative_prompt="text, watermark, low quality",
            width=1080, height=1920,
        )
    """

    def __init__(self, server_url: str = 'http://127.0.0.1:8188'):
        self.server_url = server_url.rstrip('/')
        self.client_id = str(uuid.uuid4())[:8]
        self._workflows: dict[str, ComfyUIWorkflow] = {}

    # ==================================================================
    # 工作流管理
    # ==================================================================

    def load_workflow(self, name: str) -> ComfyUIWorkflow:
        """加载 workflow JSON 文件"""
        if name in self._workflows:
            return self._workflows[name]

        workflow_path = WORKFLOWS_DIR / f'{name}.json'
        if not workflow_path.exists():
            raise FileNotFoundError(f'Workflow not found: {workflow_path}')

        with open(workflow_path, 'r', encoding='utf-8') as f:
            wf_json = json.load(f)

        workflow = ComfyUIWorkflow(
            name=name,
            description=wf_json.get('_description', ''),
            workflow_json=wf_json,
            output_node_id=wf_json.get('_output_node_id', 0),
        )
        self._workflows[name] = workflow
        return workflow

    def list_workflows(self) -> list[str]:
        """列出所有可用的 workflow"""
        if not WORKFLOWS_DIR.exists():
            return []
        return [p.stem for p in WORKFLOWS_DIR.glob('*.json') if not p.name.startswith('_')]

    # ==================================================================
    # 生成方法
    # ==================================================================

    async def generate(
        self,
        workflow: ComfyUIWorkflow,
        prompt_text: str = '',
        positive_prompt: str = '',
        negative_prompt: str = '',
        width: int = 1080,
        height: int = 1920,
        batch_size: int = 1,
        seed: int | None = None,
        steps: int = 20,
        cfg: float = 7.0,
        timeout_sec: float = 300.0,
    ) -> ComfyUIGenerationResult:
        """提交工作流到 ComfyUI 并等待生成完成

        Args:
            workflow: 工作流对象
            prompt_text: 中文提示词（用于 CLIP Text Encode）
            positive_prompt: 正向提示词
            negative_prompt: 负向提示词
            width/height: 输出分辨率
            batch_size: 批量数量
            seed: 随机种子（None = 随机）
            steps: 采样步数
            cfg: CFG scale
            timeout_sec: 超时时间
        """
        import random
        if seed is None:
            seed = random.randint(0, 2**31 - 1)

        # 1. 深拷贝 workflow 并注入参数
        wf = json.loads(json.dumps(workflow.workflow_json))

        # 注入参数到各节点
        for node_id, node in wf.items():
            if node_id.startswith('_'):
                continue

            node_class = node.get('class_type', '')
            inputs = node.get('inputs', {})

            # CLIPTextEncode 节点 → 注入 prompt
            if node_class == 'CLIPTextEncode':
                if 'positive' in node.get('_meta', {}).get('role', ''):
                    inputs['text'] = f'{positive_prompt}\n{prompt_text}'
                elif 'negative' in node.get('_meta', {}).get('role', ''):
                    inputs['text'] = negative_prompt

            # EmptyLatentImage 节点 → 注入分辨率
            elif node_class == 'EmptyLatentImage':
                inputs['width'] = width
                inputs['height'] = height
                inputs['batch_size'] = batch_size

            # KSampler 节点 → 注入参数
            elif node_class == 'KSampler':
                inputs['seed'] = seed
                inputs['steps'] = steps
                inputs['cfg'] = cfg

        # 2. 提交 prompt
        prompt_id = await self._queue_prompt(wf)

        # 3. 等待完成（轮询 + WebSocket）
        images = await self._wait_for_result(prompt_id, timeout_sec)

        return ComfyUIGenerationResult(
            images=images,
            metadata={
                'workflow': workflow.name,
                'prompt': prompt_text,
                'seed': seed,
                'steps': steps,
                'cfg': cfg,
                'width': width,
                'height': height,
            },
            workflow_name=workflow.name,
        )

    async def generate_batch(
        self,
        workflow: ComfyUIWorkflow,
        prompts: list[dict],
        width: int = 1080,
        height: int = 1920,
    ) -> list[ComfyUIGenerationResult]:
        """批量生成 —— 同一 workflow 对多个 prompt 依次执行"""
        results = []
        for prompt_data in prompts:
            result = await self.generate(
                workflow=workflow,
                prompt_text=prompt_data.get('text', ''),
                positive_prompt=prompt_data.get('positive', ''),
                negative_prompt=prompt_data.get('negative', 'text, watermark, low quality'),
                width=width,
                height=height,
            )
            results.append(result)
        return results

    # ==================================================================
    # 底层 API 通信
    # ==================================================================

    async def _queue_prompt(self, workflow: dict) -> str:
        """POST /prompt 提交工作流"""
        payload = {
            'client_id': self.client_id,
            'prompt': workflow,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f'{self.server_url}/prompt',
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            prompt_id = data.get('prompt_id', '')
            logger.info('comfyui_prompt_queued', prompt_id=prompt_id)
            return prompt_id

    async def _wait_for_result(
        self, prompt_id: str, timeout_sec: float = 300.0
    ) -> list[bytes]:
        """轮询直到生成完成 → 获取图片"""
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_sec:
                raise TimeoutError(f'ComfyUI generation timed out after {timeout_sec}s')

            # GET /history/{prompt_id}
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(f'{self.server_url}/history/{prompt_id}')
                    if resp.status_code == 200:
                        history = resp.json()
                        if prompt_id in history:
                            return await self._fetch_images(history[prompt_id])
            except httpx.ConnectError:
                logger.warning('comfyui_not_running')
                raise RuntimeError(
                    'ComfyUI is not running. Please start it first:\n'
                    f'  cd {COMFYUI_ROOT}\n'
                    '  python main.py'
                )

            await asyncio.sleep(1.0)

    async def _fetch_images(self, history_entry: dict) -> list[bytes]:
        """从历史记录中获取生成图片"""
        images = []
        outputs = history_entry.get('outputs', {})

        async with httpx.AsyncClient(timeout=30.0) as client:
            for node_id, node_outputs in outputs.items():
                for output in node_outputs:
                    filename = output.get('filename', '')
                    subfolder = output.get('subfolder', '')
                    img_type = output.get('type', 'output')

                    params = {'filename': filename, 'subfolder': subfolder, 'type': img_type}
                    resp = await client.get(f'{self.server_url}/view', params=params)
                    resp.raise_for_status()
                    images.append(resp.content)
                    logger.info('comfyui_image_fetched', filename=filename)

        return images

    # ==================================================================
    # 健康检查
    # ==================================================================

    async def check_health(self) -> dict:
        """检查 ComfyUI 是否在线以及模型状态"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 检查系统状态
                resp = await client.get(f'{self.server_url}/system_stats')
                resp.raise_for_status()
                stats = resp.json()

                # 检查可用模型
                resp2 = await client.get(f'{self.server_url}/object_info')
                resp2.raise_for_status()
                object_info = resp2.json()

                checkpoints = object_info.get('CheckpointLoaderSimple', {}).get('input', {}).get('required', {}).get('ckpt_name', [])
                if isinstance(checkpoints, list):
                    checkpoints = checkpoints[0] if checkpoints else []

                return {
                    'status': 'online',
                    'device': stats.get('system', {}).get('device', 'unknown'),
                    'python_version': stats.get('system', {}).get('python_version', ''),
                    'available_checkpoints': checkpoints if isinstance(checkpoints, list) else [str(checkpoints)],
                    'workflows_available': self.list_workflows(),
                }
        except httpx.ConnectError:
            return {
                'status': 'offline',
                'message': f'Cannot connect to {self.server_url}. Start ComfyUI first.',
                'start_command': f'cd {COMFYUI_ROOT} && python main.py',
            }


# ==================================================================
# 预定义工作流快捷方式
# ==================================================================

# 工作流名称常量
WF_PHOTO_CARD = 'photo_card'
WF_EMOTION_CARD = 'emotion_card'
WF_SPLIT_COMPARISON = 'split_comparison'
WF_TIMELINE = 'timeline'


def create_comfyui_client() -> ComfyUIClient:
    """创建 ComfyUI 客户端"""
    return ComfyUIClient()
