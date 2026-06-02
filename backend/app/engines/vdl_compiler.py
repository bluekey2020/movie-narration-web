"""VDL (Video Description Language) 编译器

声明式视频描述 → FFmpeg filter_complex 图 → 视频文件

设计理念（借鉴 Pixelle-Video 的 JSON pipeline + Remotion 的组件化）:
- 用户/LLM 输出声明式 VDL JSON
- 编译器将其转为 FFmpeg 执行命令
- 引擎无关：同一份 VDL 可以分别编译为 FFmpeg / Remotion 代码

参考: Pixelle-Video JSON pipeline + NarratoAI MoviePy 合成
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

from app.config import Platform, settings

logger = structlog.get_logger(__name__)


class TransitionType(str, Enum):
    CUT = 'cut'
    DISSOLVE = 'dissolve'
    FADE = 'fade'
    SLIDE = 'slide'
    ZOOM = 'zoom'


@dataclass
class FFmpegCommand:
    """FFmpeg 执行命令"""
    inputs: list[str]
    filter_complex: str
    output_path: str
    output_options: dict = field(default_factory=dict)
    estimated_duration: float = 0.0


@dataclass
class VDLDocument:
    """VDL 文档 —— 声明式视频描述"""
    version: str = '1.0'
    metadata: dict = field(default_factory=dict)
    canvas: dict = field(default_factory=lambda: {'width': 1080, 'height': 1920, 'fps': 30})
    defaults: dict = field(default_factory=dict)
    segments: list[dict] = field(default_factory=list)


class VDLCompiler:
    """VDL → FFmpeg 编译器"""

    def __init__(self):
        self.ffmpeg_path = settings.ffmpeg_path
        self.threads = settings.ffmpeg_threads

    def compile(self, vdl: VDLDocument) -> FFmpegCommand:
        """编译 VDL 文档为 FFmpeg 执行命令"""
        vdl_dict = vdl if isinstance(vdl, dict) else vdl.__dict__

        # 验证 VDL
        self._validate(vdl_dict)

        filter_parts: list[str] = []
        input_files: list[str] = []
        input_labels: dict[str, str] = {}
        total_duration = 0.0

        for i, seg in enumerate(vdl_dict.get('segments', [])):
            prefix = f'seg{i}'

            # 1. 视频输入
            video_src = self._resolve_video_source(seg.get('video', {}).get('primary', {}))
            if video_src.get('type') == 'file':
                input_label = f'{i}v'
                input_files.append(video_src['path'])
                input_labels[f'video_{i}'] = input_label

                # 构建视频滤镜链
                video_filter = self._build_video_filter(seg, prefix, input_label, vdl_dict.get('canvas', {}))
                filter_parts.append(video_filter)

            elif video_src.get('type') == 'template':
                # 视觉模板：预渲染为临时 MP4，然后作为输入
                template_path = video_src.get('rendered_path', f'/tmp/template_{i}.mp4')
                input_label = f'{i}v'
                input_files.append(template_path)
                input_labels[f'video_{i}'] = input_label

                video_filter = self._build_template_filter(seg, prefix, input_label, vdl_dict.get('canvas', {}))
                filter_parts.append(video_filter)

            # 2. 音频输入
            audio_filters = self._build_audio_filter(seg, prefix, input_files, input_labels, i)
            if audio_filters:
                filter_parts.append(audio_filters)

            # 3. BGM 输入
            bgm_cfg = seg.get('audio', {}).get('bgm', {})
            if bgm_cfg:
                bgm_label = f'{i}bgm'
                bgm_path = bgm_cfg.get('file_path', '')
                if bgm_path:
                    input_files.append(bgm_path)
                    input_labels[f'bgm_{i}'] = bgm_label

            total_duration += seg.get('duration', 10.0)

        # 4. 拼接所有段
        canvas = vdl_dict.get('canvas', {})
        width = canvas.get('width', 1080)
        height = canvas.get('height', 1920)
        fps = canvas.get('fps', 30)

        concat_filter = self._build_concat(filter_parts, len(vdl_dict.get('segments', [])))

        # 5. 构建完整命令
        return FFmpegCommand(
            inputs=input_files,
            filter_complex=concat_filter,
            output_path=vdl_dict.get('metadata', {}).get('output_path', '/tmp/output.mp4'),
            output_options={
                'c:v': 'libx264',
                'preset': 'medium',
                'crf': '18',
                'c:a': 'aac',
                'b:a': '192k',
                'pix_fmt': 'yuv420p',
                'movflags': '+faststart',
                'threads': self.threads,
            },
            estimated_duration=round(total_duration, 2),
        )

    # ==================================================================
    # 视频滤镜构建
    # ==================================================================

    def _build_video_filter(
        self, seg: dict, prefix: str, input_label: str, canvas: dict
    ) -> str:
        """为单段构建视频滤镜链"""
        video_cfg = seg.get('video', {}).get('primary', {})
        width = canvas.get('width', 1080)
        height = canvas.get('height', 1920)

        filters = []

        # 基础：trim + setpts
        clip_ref = video_cfg.get('clipRef', {})
        if clip_ref:
            start = clip_ref.get('timeRange', [0, 10])[0]
            end = clip_ref.get('timeRange', [0, 10])[1]
            filters.append(
                f"[{input_label}] "
                f"trim=start={start}:end={end}, "
                f"setpts=PTS-STARTPTS, "
                f"scale={width}:{height}:force_original_aspect_ratio=decrease, "
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2 "
                f"[{prefix}_scaled]"
            )
        else:
            filters.append(
                f"[{input_label}] "
                f"scale={width}:{height}:force_original_aspect_ratio=decrease, "
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2 "
                f"[{prefix}_scaled]"
            )

        # 转场
        transition = seg.get('transition', {})
        t_type = transition.get('type', 'cut')
        t_dur = transition.get('duration', 500) / 1000

        if t_type != 'cut':
            filters.append(
                f"[{prefix}_scaled] "
                f"fade=t=in:st=0:d={t_dur} "
                f"[{prefix}_transitioned]"
            )
            last_label = f'{prefix}_transitioned'
        else:
            last_label = f'{prefix}_scaled'

        # 特效
        effects = clip_ref.get('effects', [])
        for effect in effects:
            effect_type = effect.get('type', '')
            if effect_type == 'slow_motion':
                speed = effect.get('speed', 0.5)
                filters.append(
                    f"[{last_label}] "
                    f"setpts={1/speed}*PTS "
                    f"[{prefix}_slowed]"
                )
                last_label = f'{prefix}_slowed'
            elif effect_type == 'grayscale':
                filters.append(
                    f"[{last_label}] "
                    f"hue=s=0 "
                    f"[{prefix}_bw]"
                )
                last_label = f'{prefix}_bw'

        # 重命名最终输出
        filters.append(f"[{last_label}] copy [{prefix}_final]")

        return '; '.join(filters)

    def _build_template_filter(
        self, seg: dict, prefix: str, input_label: str, canvas: dict
    ) -> str:
        """构建视觉模板的滤镜链"""
        width = canvas.get('width', 1080)
        height = canvas.get('height', 1920)

        return (
            f"[{input_label}] "
            f"scale={width}:{height}:force_original_aspect_ratio=decrease, "
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2, "
            f"fade=t=in:st=0:d=0.5 "
            f"[{prefix}_final]"
        )

    # ==================================================================
    # 音频滤镜构建
    # ==================================================================

    def _build_audio_filter(
        self, seg: dict, prefix: str,
        input_files: list[str], input_labels: dict, seg_index: int,
    ) -> Optional[str]:
        """构建音频滤镜链（TTS + 原声混合）"""
        audio_cfg = seg.get('audio', {})
        ost_mode = audio_cfg.get('ost_mode', 0)

        # TTS 音频
        tts_cfg = audio_cfg.get('tts', {})
        tts_path = tts_cfg.get('file_path', '')
        if tts_path and ost_mode != 1:  # OST=1 是纯原声，不加 TTS
            tts_label = f'{seg_index}tts'
            input_files.append(tts_path)
            input_labels[f'tts_{seg_index}'] = tts_label

        # 原声
        original_cfg = audio_cfg.get('originalAudio', {})
        if original_cfg and ost_mode in (1, 2):
            orig_label = f'{seg_index}orig'
            input_files.append(original_cfg.get('file_path', ''))
            input_labels[f'original_{seg_index}'] = orig_label

        # 音量调整 + 混合
        filters = []
        if tts_path:
            tts_vol = audio_cfg.get('tts', {}).get('volume', 1.0)
            filters.append(
                f"[{seg_index}tts] volume={tts_vol} [{prefix}_tts_vol]"
            )

        return '; '.join(filters) if filters else None

    # ==================================================================
    # 拼接
    # ==================================================================

    def _build_concat(self, filter_parts: list[str], segment_count: int) -> str:
        """构建 concat 滤镜，拼接所有段落"""
        # 收集所有段的 final 输出
        seg_labels = ' '.join(f'[seg{i}_final]' for i in range(segment_count))

        # concat 滤镜
        concat = (
            f"{seg_labels} "
            f"concat=n={segment_count}:v=1:a=1 "
            f"[out_v][out_a]"
        )

        # 合并所有 part
        all_parts = '; '.join(p for p in filter_parts if p) + '; ' + concat
        return all_parts

    # ==================================================================
    # 视频源解析
    # ==================================================================

    def _resolve_video_source(self, primary: dict) -> dict:
        """解析视频源"""
        source_type = primary.get('source', 'visual_template')

        if source_type == 'movie_clip':
            clip = primary.get('clipRef', {})
            return {
                'type': 'file',
                'path': f"/data/movies/{clip.get('movieId', 'unknown')}/source.mp4",
            }
        elif source_type == 'ai_generated':
            ai = primary.get('aiGeneration', {})
            return {
                'type': 'file',
                'path': f"/data/ai_generated/{ai.get('prompt', '')[:20]}.mp4",
            }
        elif source_type == 'visual_template':
            template_id = primary.get('templateId', 'photo_card')
            return {
                'type': 'template',
                'rendered_path': f'/tmp/template_{template_id}.mp4',
            }
        else:
            return {'type': 'file', 'path': ''}

    # ==================================================================
    # 验证
    # ==================================================================

    def _validate(self, vdl: dict) -> None:
        """验证 VDL 文档"""
        segments = vdl.get('segments', [])
        if not segments:
            raise ValueError('VDL must contain at least one segment')

        for i, seg in enumerate(segments):
            # 检查必要字段
            if 'duration' not in seg and 'audio' not in seg:
                raise ValueError(f'Segment {i} missing duration or audio')

            # 检查时间连续性
            if i > 0:
                prev_end = segments[i - 1].get('startTime', 0) + segments[i - 1].get('duration', 0)
                current_start = seg.get('startTime', 0)
                if abs(current_start - prev_end) > 0.1:
                    logger.warning('vdl_timing_gap', segment=i, gap=current_start - prev_end)

        # 检查画布
        canvas = vdl.get('canvas', {})
        if canvas.get('width', 0) <= 0 or canvas.get('height', 0) <= 0:
            raise ValueError('Invalid canvas dimensions')


# ==================================================================
# VDL Builder — 辅助构建 VDL 文档
# ==================================================================

class VDLBuilder:
    """VDL 文档构建器 —— 提供流式 API 方便构造"""

    def __init__(self):
        self._doc: dict = {
            'version': '1.0',
            'metadata': {},
            'canvas': {'width': 1080, 'height': 1920, 'fps': 30},
            'defaults': {
                'subtitleStyle': {'fontSize': 42, 'color': '#FFFFFF'},
                'transition': {'type': 'cut', 'duration': 0},
                'bgmVolume': 0.3,
                'ttsVolume': 1.0,
            },
            'segments': [],
        }

    def set_metadata(self, title: str, movie: str, style: str, platform: Platform) -> 'VDLBuilder':
        self._doc['metadata'] = {
            'title': title, 'movieName': movie,
            'style': style, 'platform': platform,
        }
        return self

    def set_canvas(self, platform: Platform) -> 'VDLBuilder':
        cfg = settings.platforms[platform]
        self._doc['canvas'] = {
            'width': cfg.resolution[0],
            'height': cfg.resolution[1],
            'fps': 30,
        }
        return self

    def add_segment(
        self,
        index: int,
        start_time: float,
        duration: float,
        video_source: dict,
        tts_ssml: str = '',
        tts_voice: str = '',
        bgm_track_id: str = '',
        bgm_emotion: str = '',
        subtitle_text: str = '',
        transition: str = 'cut',
    ) -> 'VDLBuilder':
        seg = {
            'index': index,
            'startTime': start_time,
            'duration': duration,
            'audio': {
                'tts': {
                    'engine': 'narrator-ai',
                    'voiceId': tts_voice,
                    'ssml': tts_ssml,
                    'volume': 1.0,
                },
                'bgm': {
                    'trackId': bgm_track_id,
                    'emotion': bgm_emotion,
                    'volume': 0.3,
                    'fadeIn': 1.0,
                    'fadeOut': 2.0,
                },
            },
            'video': {'primary': video_source},
            'transition': {'type': transition, 'duration': 500},
        }

        if subtitle_text:
            seg['subtitle'] = {'text': subtitle_text}

        self._doc['segments'].append(seg)
        return self

    def build(self) -> dict:
        return self._doc


def create_vdl_compiler() -> VDLCompiler:
    return VDLCompiler()
