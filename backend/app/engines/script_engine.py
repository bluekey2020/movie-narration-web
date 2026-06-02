"""文案生成引擎 —— 4 层 Agent 协作 Pipeline

Layer 1: 电影理解 → 解说角度 × 3
Layer 2: 结构规划 → 7 段式骨架
Layer 3: 文案撰写 → 3 版并行 (含 SSML 标注)
Layer 4: 质量评分 → 选最佳 + 段落移植

参考: NarratoAI prompt chain + narrator-ai 风格学习
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.config import Platform, NarrationStyle, settings
from app.engines.base import LLMClient, estimate_duration
from app.models.project import ScriptSegment, ScriptVersion
from app.models.style import StyleFingerprint

logger = structlog.get_logger(__name__)


class ScriptEngine:
    """文案生成引擎 —— 四层 Agent 协作"""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    # ==================================================================
    # Layer 1: 电影理解
    # ==================================================================

    async def analyze_movie(
        self, movie_metadata: dict, style_fingerprint: StyleFingerprint
    ) -> dict[str, Any]:
        """Layer 1: 理解电影，输出 3 个候选解说角度"""
        system = """你是一位资深电影解说编剧，擅长发现电影中最具传播力的叙事角度。
请基于电影元数据，输出 3 个不同的解说角度。每个角度需要找到最具情感冲击力的情节点。"""

        prompt = f"""电影信息：
- 片名：{movie_metadata.get('title', '')}
- 年份：{movie_metadata.get('year', '')}
- 类型：{', '.join(movie_metadata.get('genre', []))}
- 评分：{movie_metadata.get('rating', '')}
- 剧情摘要：{movie_metadata.get('plot_summary', '')}
- 关键场景：{json.dumps(movie_metadata.get('key_scenes', []), ensure_ascii=False)}
- 解说热点：{json.dumps(movie_metadata.get('narration_hotspots', []), ensure_ascii=False)}

目标风格：{style_fingerprint.display_name}（{style_fingerprint.description}）

请输出 3 个候选解说角度的 JSON：
{{
  "angles": [
    {{
      "name": "角度名称",
      "perspective": "从谁的视角？什么情绪基调？",
      "emotional_arc": "情绪弧线描述",
      "core_conflict": "核心矛盾一句话",
      "three_key_beats": ["情节点1", "情节点2", "情节点3"],
      "one_liner": "一句话钩子（3秒内能讲完）",
      "best_for_style": true/false
    }}
  ]
}}"""
        return await self.llm.generate_json(system, prompt, temperature=0.7)

    # ==================================================================
    # Layer 2: 结构规划
    # ==================================================================

    async def plan_structure(
        self,
        selected_angle: dict,
        style_fingerprint: StyleFingerprint,
        platform: Platform,
    ) -> dict[str, Any]:
        """Layer 2: 规划 7 段式结构骨架"""
        platform_cfg = settings.platforms[platform]

        system = f"""你是{platform_cfg.display_name}平台的影视解说结构规划师。
请将解说内容规划为标准的 7 段式结构。"""

        prompt = f"""解说角度：{json.dumps(selected_angle, ensure_ascii=False)}
风格参数：{json.dumps(self._fingerprint_to_params(style_fingerprint), ensure_ascii=False)}
平台约束：时长 {platform_cfg.duration_range[0]}-{platform_cfg.duration_range[1]}秒，
         钩子必须在 {platform_cfg.hook_window} 秒内建立，
         字数上限 {platform_cfg.max_words}

标准 7 段式结构（每段需要指定以下字段）：
1. hook (开场钩子) — 3秒冲击
2. intro (剧情引入) — 建立背景认知
3. plot_1 (关键情节1) — 第一个爆点
4. twist (转折点) — 打破预期
5. plot_2 (关键情节2) — 第二个爆点
6. climax (高潮) — 情绪峰值
7. ending (结尾点评) — 回味/升华

每段输出 JSON 对象，包含：
- index: 段落序号
- segment_type: 类型 (hook/intro/plot_1/twist/plot_2/climax/ending)
- target_emotion: 目标情绪 (suspense/buildup/tense/revelation/climax/reflection)
- word_count_target: 目标字数
- visual_need: 画面需求描述
- bgm_mood: BGM 情绪

输出格式：
{{ "structure": [...七段...], "estimated_total_duration_sec": 180, "estimated_total_words": 850 }}"""
        return await self.llm.generate_json(system, prompt, temperature=0.6)

    # ==================================================================
    # Layer 3: 文案撰写 (3 版并行)
    # ==================================================================

    async def generate_scripts_parallel(
        self,
        structure: list[dict],
        style_fingerprint: StyleFingerprint,
        platform: Platform,
        movie_title: str,
    ) -> list[dict]:
        """Layer 3: 并行生成 3 版文案"""
        platform_cfg = settings.platforms[platform]

        variants = [
            {'id': 'v1_aggressive', 'persona': '激进型', 'desc': '钩子更夸张、节奏更快、多用反转'},
            {'id': 'v2_balanced', 'persona': '稳健型', 'desc': '叙事饱满、情绪递进、经典结构'},
            {'id': 'v3_creative', 'persona': '创意型', 'desc': '非常规切入、独特比喻、记忆点强化'},
        ]

        # 实际生产中用 asyncio.gather 并行调用
        # 这里展示完整的 prompt 结构
        results = []
        for variant in variants:
            result = await self._generate_single_script(
                structure=structure,
                style_fingerprint=style_fingerprint,
                platform_cfg=platform_cfg,
                movie_title=movie_title,
                variant=variant,
            )
            result['script_id'] = variant['id']
            result['variant_persona'] = variant['persona']
            results.append(result)
        return results

    async def _generate_single_script(
        self,
        structure: list[dict],
        style_fingerprint: StyleFingerprint,
        platform_cfg,
        movie_title: str,
        variant: dict,
    ) -> dict:
        """生成单个版本的完整文案（含 SSML 标注）"""
        system = f"""你是{variant['persona']}风格的影视解说文案写手。
写作风格：{variant['desc']}

关键要求：
1. 每句话都标注 SSML 发音指令（<prosody> <break> <emphasis>）
2. 用 narrator-ai 的 <#x.x#> 语法标注段落间停顿
3. 标注每段的 emotion 标签和 emphasis_words
4. 为每段写出 visual_requirement（画面需求描述）
5. 开场钩子必须在 {platform_cfg.hook_window} 秒内建立信息差或情感冲击
6. 称呼用户为"{platform_cfg.style_params['address_term']}"
7. 结尾风格参考："{platform_cfg.style_params['closing']}"
8. 语速 {platform_cfg.speech_rate}x
"""

        prompt = f"""电影：《{movie_title}》

结构规划：
{json.dumps(structure, ensure_ascii=False, indent=2)}

风格指纹：
{json.dumps(self._fingerprint_to_params(style_fingerprint), ensure_ascii=False, indent=2)}

请逐段输出完整文案和所有标注。对于每段，输出：
{{
  "segments": [
    {{
      "index": 1,
      "type": "hook",
      "text": "完整文案文本（无标注）",
      "ssml": "带 <prosody> <break> <emphasis> 标注的版本",
      "emotion": "suspense",
      "emphasis_words": ["词1", "词2"],
      "visual_requirement": {{
        "description": "画面需求中文描述",
        "preferred_source": "original_clip|visual_template",
        "scene_hint": "shawshank_prison_exterior",
        "mood": "oppressive_but_hopeful"
      }}
    }}
  ],
  "total_words": 850,
  "hooks": {{ "opening_hook_type": "information_gap", "surprise_level": 0.85 }}
}}"""
        return await self.llm.generate_json(system, prompt, temperature=0.85)

    # ==================================================================
    # Layer 4: 质量评分
    # ==================================================================

    async def score_scripts(
        self, scripts: list[dict], style_fingerprint: StyleFingerprint, platform: Platform
    ) -> dict[str, Any]:
        """Layer 4: 多维度评分 + 段落移植"""
        platform_cfg = settings.platforms[platform]
        max_words = platform_cfg.max_words

        scored_versions: list[ScriptVersion] = []

        for script in scripts:
            segments = self._parse_segments(script.get('segments', []))
            total_words = sum(len(s.get('text', '')) for s in script.get('segments', []))

            scores = {
                'hook_attraction': self._score_hook(segments[0] if segments else {}),
                'information_density': self._score_density(script, total_words),
                'rhythm_curve': self._score_rhythm(segments, style_fingerprint),
                'colloquialism': self._score_colloquial(script),
                'duration_compliance': self._score_duration(segments, platform_cfg),
                'style_consistency': self._score_style_match(script, style_fingerprint),
                'sensitive_word_check': self._check_sensitive(script),
            }

            weights = {'hook_attraction': 0.25, 'information_density': 0.20,
                       'rhythm_curve': 0.15, 'colloquialism': 0.15,
                       'duration_compliance': 0.10, 'style_consistency': 0.10,
                       'sensitive_word_check': 0.05}

            overall = sum(scores[k] * weights[k] for k in weights)

            scored_versions.append({
                'script_id': script.get('script_id', ''),
                'variant_persona': script.get('variant_persona', ''),
                'segments': segments,
                'total_words': total_words,
                'estimated_duration_sec': sum(
                    estimate_duration(s.get('text', ''), platform_cfg.speech_rate)
                    for s in segments
                ),
                'quality_scores': scores,
                'overall_score': round(overall, 1),
            })

        # 排序 + 选择最佳
        scored_versions.sort(key=lambda v: v['overall_score'], reverse=True)
        best = scored_versions[0]

        # 段落移植：检查其他版本中是否有单项更好的段落
        transplant_suggestions = self._find_transplant_candidates(
            best, scored_versions[1:], style_fingerprint
        )

        return {
            'best_version': best,
            'all_versions': scored_versions,
            'transplant_suggestions': transplant_suggestions,
            'score_breakdown': {v['script_id']: v['overall_score'] for v in scored_versions},
        }

    # ==================================================================
    # 评分辅助方法
    # ==================================================================

    def _score_hook(self, hook_segment: dict) -> float:
        """评估钩子吸引力"""
        text = hook_segment.get('text', '')
        if not text:
            return 0.0

        score = 5.0  # 基准分
        # 信息差检测：设问句/反转词/数据
        if any(kw in text for kw in ['?', '？', '有没有', '想过', '知道吗']):
            score += 1.5
        if any(kw in text for kw in ['但是', '然而', '可是', '居然', '竟然']):
            score += 1.0
        if any(kw in text for kw in ['万', '亿', '年', '吨', '%', '倍']):
            score += 0.5
        # 情感冲击
        if any(kw in text for kw in ['死', '杀', '恐怖', '震惊', '最', '绝不', '永远']):
            score += 0.5
        # 长度惩罚：钩子应控制在 60 字以内
        if len(text) > 80:
            score -= 1.0
        return min(round(score, 1), 10.0)

    def _score_density(self, script: dict, total_words: int) -> float:
        """评估信息密度"""
        if total_words == 0:
            return 5.0
        # 检测废话特征词
        filler_words = ['然后', '就是', '那个', '这个', '的话', '其实', '所以',
                        '总而言之', '众所周知', '不可否认']
        segments_text = ' '.join(s.get('text', '') for s in script.get('segments', []))
        filler_count = sum(segments_text.count(w) for w in filler_words)
        filler_ratio = filler_count / max(total_words, 1)
        # 信息点数：专有名词、数字、专有术语
        info_markers = len([c for c in segments_text if c.isdigit()])
        info_ratio = info_markers / max(total_words, 1)

        score = 5.0 - filler_ratio * 20 + info_ratio * 50
        return min(max(round(score, 1), 0.0), 10.0)

    def _score_rhythm(self, segments: list[dict], style: StyleFingerprint) -> float:
        """评估节奏曲线"""
        if not segments:
            return 5.0
        lengths = [len(s.get('text', '')) for s in segments]
        if len(lengths) < 3:
            return 5.0
        # 句长变化是否接近目标方差
        import statistics
        variance = statistics.pvariance(lengths) if len(lengths) > 1 else 0
        target_variance = style.sentence_length_variance * 100
        variance_diff = abs(variance - target_variance)
        # 情绪是否在变化（不应 7 段都是同一情绪）
        emotions = [s.get('emotion', '') for s in segments]
        unique_emotions = len(set(e for e in emotions if e))
        emotion_variety = min(unique_emotions / 4.0, 1.0)

        score = 7.0 - variance_diff * 0.1 + emotion_variety * 3.0
        return min(max(round(score, 1), 0.0), 10.0)

    def _score_colloquial(self, script: dict) -> float:
        """评估口语化程度"""
        all_text = ' '.join(s.get('text', '') for s in script.get('segments', []))
        if not all_text:
            return 5.0
        # 书面语特征词
        formal_markers = ['该片', '影片', '通过', '展现', '呈现', '诠释', '这一', '其',
                          '综上所述', '总而言之', '不可否认']
        formal_count = sum(all_text.count(w) for w in formal_markers)
        formal_ratio = formal_count / max(len(all_text), 1) * 100
        # 口语特征词
        colloquial_markers = ['离谱', '绝了', '太', '真的', '吗', '吧', '啊', '呢',
                              '卧槽', '牛', '我天', '给我', '简直']
        colloquial_count = sum(all_text.count(w) for w in colloquial_markers)
        colloquial_ratio = colloquial_count / max(len(all_text), 1) * 100

        score = 5.0 - formal_ratio * 2 + colloquial_ratio * 3
        return min(max(round(score, 1), 0.0), 10.0)

    def _score_duration(self, segments: list[dict], platform_cfg) -> float:
        """评估时长合规性"""
        total_duration = sum(
            estimate_duration(s.get('text', ''), platform_cfg.speech_rate)
            for s in segments
        )
        min_dur, max_dur = platform_cfg.duration_range
        if min_dur <= total_duration <= max_dur:
            return 10.0
        elif total_duration < min_dur:
            return max(0.0, 10.0 - (min_dur - total_duration) / 10)
        else:
            return max(0.0, 10.0 - (total_duration - max_dur) / 20)

    def _score_style_match(self, script: dict, style: StyleFingerprint) -> float:
        """评估风格一致性"""
        all_text = ' '.join(s.get('text', '') for s in script.get('segments', []))
        if not all_text or not style.high_freq_words:
            return 7.0
        # 检查高频词命中率
        hit_count = sum(all_text.count(w) for w in style.high_freq_words)
        # 检查禁用词
        ban_count = sum(all_text.count(w) for w in style.banned_words)
        score = 5.0 + hit_count * 0.5 - ban_count * 2
        return min(max(round(score, 1), 0.0), 10.0)

    def _check_sensitive(self, script: dict) -> float:
        """敏感词检查"""
        all_text = ' '.join(s.get('text', '') for s in script.get('segments', []))
        sensitive_keywords = ['政治', '反动', '色情', '暴力', '违法']  # 简化版
        for kw in sensitive_keywords:
            if kw in all_text:
                return 0.0
        return 10.0

    def _find_transplant_candidates(
        self, best: dict, others: list[dict], style: StyleFingerprint
    ) -> list[dict]:
        """寻找可移植的更好段落"""
        suggestions = []
        best_segments = best.get('segments', [])

        for seg_idx, best_seg in enumerate(best_segments):
            best_seg_score = self._score_single_segment(best_seg, style)
            for other in others:
                other_segs = other.get('segments', [])
                if seg_idx < len(other_segs):
                    other_score = self._score_single_segment(other_segs[seg_idx], style)
                    if other_score > best_seg_score + 1.0:  # 显著更好才移植
                        suggestions.append({
                            'segment_index': seg_idx + 1,
                            'from_version': other['script_id'],
                            'current_score': best_seg_score,
                            'candidate_score': other_score,
                            'improvement': round(other_score - best_seg_score, 1),
                        })
        return suggestions

    def _score_single_segment(self, segment: dict, style: StyleFingerprint) -> float:
        """单段评分"""
        text = segment.get('text', '')
        if not text:
            return 0.0
        # 长度合理性（接近平均值）
        len_score = 10.0 - abs(len(text) - style.avg_sentence_length)
        # 有情绪标注
        emotion_score = 5.0 if segment.get('emotion') else 0.0
        # 有 visual requirement
        visual_score = 3.0 if segment.get('visual_requirement') else 0.0
        return max(0.0, len_score + emotion_score + visual_score)

    # ==================================================================
    # 辅助方法
    # ==================================================================

    def _parse_segments(self, raw_segments: list[dict]) -> list[dict]:
        """将 LLM 输出解析为标准 ScriptSegment 字典列表"""
        return raw_segments

    def _fingerprint_to_params(self, fp: StyleFingerprint) -> dict:
        """将风格指纹转为 LLM prompt 可用的参数字典"""
        return {
            '叙事节奏': {
                '平均句长': f'{fp.avg_sentence_length}字',
                '句长变化': fp.sentence_length_variance,
                '停顿偏好': fp.pause_pattern,
            },
            '钩子策略': {
                '钩子类型': fp.hook_types,
                '钩子密度': f'每{fp.hook_density}字一个',
            },
            '情绪参数': {
                '切换频率': fp.emotion_switch_frequency,
                '基线强度': fp.emotion_intensity_baseline,
            },
            '词汇风格': {
                '高频词': fp.high_freq_words[:20],
                '禁用词': fp.banned_words,
            },
            '口语特征': {
                '语气词密度': fp.interjection_density,
                '网络用语频率': fp.slang_usage,
            },
        }


# ==================================================================
# 工厂函数
# ==================================================================

def create_script_engine() -> ScriptEngine:
    """创建文案生成引擎实例"""
    return ScriptEngine()
