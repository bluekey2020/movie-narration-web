"""编排决策引擎

将"工作流引擎"与"决策引擎"分离：
- Temporal 负责执行步骤（Activity 按序调用）
- Orchestrator 负责决策（每步完成后：auto_continue / suggest_review / auto_retry）

核心设计：
- 质量评分驱动的自动决策
- 用户行为学习（连续修改模式检测）
- 可热更新的决策阈值

参考: NarratoAI 任务编排 + narrator-ai Agent Skill
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import structlog

from app.config import Platform

logger = structlog.get_logger(__name__)


class DecisionAction(str, Enum):
    AUTO_CONTINUE = 'auto_continue'
    WAIT_FOR_REVIEW = 'wait_for_review'
    AUTO_RETRY = 'auto_retry'
    DOWNGRADE = 'downgrade'


@dataclass
class OrchestrationDecision:
    """编排决策"""
    action: DecisionAction
    next_stage: Optional[str] = None
    message: str = ''
    composition_mode: str = 'clip_priority'
    retry_params: Optional[dict] = None
    review_highlights: Optional[list[str]] = None
    template_replacements: Optional[list] = None
    downgrade_reason: str = ''


@dataclass
class QualityThresholds:
    """质量阈值配置 —— 可热更新，可 A/B 测试"""
    script_auto_continue: float = 85.0      # >= 此分 → 自动进入配音
    script_suggest_review: float = 65.0     # 此分以上 → 建议审阅但不强制
    script_auto_retry: float = 0.0           # < 此分 → 自动重写

    scene_match_auto: float = 0.70           # >= 70% 匹配率 → 素材优先
    scene_match_hybrid: float = 0.40         # 40-70% → 混合模式
    scene_match_downgrade: float = 0.0       # < 40% → 纯模板

    voice_quality_auto: float = 80.0
    voice_quality_retry: float = 60.0


@dataclass
class UserPreferences:
    """用户偏好（从历史行为学习中积累）"""
    prefers_auto_mode: bool = False           # 偏好全自动
    review_frequency: float = 0.5             # 主动审阅频率 (0-1)
    common_edit_patterns: list[dict] = field(default_factory=list)
    favorite_styles: list[str] = field(default_factory=list)
    favorite_voices: list[str] = field(default_factory=list)


class Orchestrator:
    """编排决策引擎"""

    def __init__(
        self,
        thresholds: QualityThresholds | None = None,
        preferences: UserPreferences | None = None,
    ):
        self.thresholds = thresholds or QualityThresholds()
        self.preferences = preferences or UserPreferences()

    # ==================================================================
    # 文案阶段决策
    # ==================================================================

    def decide_after_script(
        self, quality_report: dict
    ) -> OrchestrationDecision:
        """文案生成后的决策"""
        overall = quality_report.get('overall_score', 0)
        scores = quality_report.get('quality_scores', {})
        transplant_count = len(quality_report.get('transplant_suggestions', []))

        if overall >= self.thresholds.script_auto_continue:
            # 高质量：自动继续
            return OrchestrationDecision(
                action=DecisionAction.AUTO_CONTINUE,
                next_stage='voice_generation',
                message=f'文案质量 {overall} 分，自动进入配音阶段',
            )

        elif overall >= self.thresholds.script_suggest_review:
            # 中等质量
            if self.preferences.prefers_auto_mode:
                return OrchestrationDecision(
                    action=DecisionAction.AUTO_CONTINUE,
                    next_stage='voice_generation',
                    message=f'文案质量 {overall} 分，按用户偏好自动继续',
                )
            else:
                # 生成审阅重点
                highlights = self._extract_review_highlights(scores)
                return OrchestrationDecision(
                    action=DecisionAction.WAIT_FOR_REVIEW,
                    next_stage=None,
                    message=f'文案已生成（{overall} 分），建议审阅以下方面',
                    review_highlights=highlights,
                )

        else:
            # 低质量：自动重试
            retry_params = {
                'change_angle': True,
                'previous_angles': quality_report.get('angles_tried', []),
                'focus_areas': self._identify_weak_areas(scores),
            }
            return OrchestrationDecision(
                action=DecisionAction.AUTO_RETRY,
                next_stage='script_generation',
                message=f'文案质量不足（{overall} 分），自动换个角度重写',
                retry_params=retry_params,
            )

    # ==================================================================
    # 画面匹配阶段决策
    # ==================================================================

    def decide_after_scene_matching(
        self, match_report: dict
    ) -> OrchestrationDecision:
        """画面匹配后的决策"""
        match_rate = match_report.get('overall_match_rate', 0)
        mode = match_report.get('composition_mode', 'clip_priority')

        if match_rate >= self.thresholds.scene_match_auto:
            return OrchestrationDecision(
                action=DecisionAction.AUTO_CONTINUE,
                next_stage='video_composition',
                composition_mode='clip_priority',
                message=f'画面匹配率 {match_rate:.0%}，素材优先合成',
            )

        elif match_rate >= self.thresholds.scene_match_hybrid:
            # 混合模式：素材不够的段落用模板代替
            replacements = self._get_template_assignments(match_report)
            return OrchestrationDecision(
                action=DecisionAction.AUTO_CONTINUE,
                next_stage='video_composition',
                composition_mode='hybrid',
                template_replacements=replacements,
                message=f'画面匹配率 {match_rate:.0%}，启用混合模式（素材 + 视觉模板）',
            )

        else:
            return OrchestrationDecision(
                action=DecisionAction.DOWNGRADE,
                next_stage='video_composition',
                composition_mode='template_only',
                downgrade_reason=f'画面匹配率仅 {match_rate:.0%}，低于阈值',
                message=f'画面匹配率 {match_rate:.0%}，降级为纯视觉模板模式',
            )

    # ==================================================================
    # 配音阶段决策
    # ==================================================================

    def decide_after_voice(
        self, quality_score: float, voice_metadata: dict
    ) -> OrchestrationDecision:
        """配音生成后的决策"""
        if quality_score >= self.thresholds.voice_quality_auto:
            return OrchestrationDecision(
                action=DecisionAction.AUTO_CONTINUE,
                next_stage='scene_matching',
                message=f'配音质量 {quality_score} 分，自动进入画面匹配',
            )
        elif quality_score >= self.thresholds.voice_quality_retry:
            return OrchestrationDecision(
                action=DecisionAction.WAIT_FOR_REVIEW,
                next_stage=None,
                message=f'配音已生成（{quality_score} 分），建议试听确认',
            )
        else:
            return OrchestrationDecision(
                action=DecisionAction.AUTO_RETRY,
                next_stage='voice_generation',
                retry_params={'change_voice': True, 'previous_voice': voice_metadata.get('voice_id')},
                message=f'配音质量不足（{quality_score} 分），自动切换配音角色重试',
            )

    # ==================================================================
    # 用户行为学习
    # ==================================================================

    def learn_from_user_edits(
        self, original: dict, edited: dict, edit_history: list[dict]
    ) -> dict:
        """从用户的修改行为中学习偏好

        当用户连续 3 次做出同一类修改时，自动学习并应用到后续段落。
        """
        if len(edit_history) < 3:
            return {'learned': False}

        patterns = self._detect_edit_patterns(edit_history)

        if patterns:
            self.preferences.common_edit_patterns.extend(patterns)
            return {
                'learned': True,
                'patterns': patterns,
                'confidence': min(0.3 + len(edit_history) * 0.1, 0.9),
                'apply_to_remaining': True,
            }

        return {'learned': False}

    def update_preferences_from_task(self, task_result: dict) -> None:
        """从已完成任务的用户操作中更新偏好"""
        # 如果用户全程没停（auto_continue 率高），标记偏好全自动
        decisions = task_result.get('decisions', [])
        if decisions:
            auto_rate = sum(1 for d in decisions if d.get('action') == 'auto_continue') / len(decisions)
            if auto_rate > 0.8:
                self.preferences.prefers_auto_mode = True

        # 记录常用风格和声音
        style = task_result.get('style')
        if style and style not in self.preferences.favorite_styles:
            self.preferences.favorite_styles.append(style)

        voice = task_result.get('voice_id')
        if voice and voice not in self.preferences.favorite_voices:
            self.preferences.favorite_voices.append(voice)

    # ==================================================================
    # 辅助方法
    # ==================================================================

    def _extract_review_highlights(self, scores: dict) -> list[str]:
        """从评分中提取审阅重点（得分最低的维度）"""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1])
        highlights = []
        for dim, score in sorted_scores[:3]:
            if score < 7.0:
                highlights.append(self._dimension_advice(dim, score))
        return highlights

    @staticmethod
    def _dimension_advice(dimension: str, score: float) -> str:
        """给出具体审阅建议"""
        advices = {
            'hook_attraction': f'开场钩子吸引力不足（{score}分），建议制造更强的信息差或情感冲击',
            'information_density': f'信息密度偏低（{score}分），考虑减少废话、增加情节细节',
            'rhythm_curve': f'叙事节奏平淡（{score}分），建议增加句子长度变化和情绪切换',
            'colloquialism': f'口语化不足（{score}分），太像书面文章，需要更自然的口播语感',
            'duration_compliance': f'时长不符合平台要求（{score}分），需要调整内容量',
            'style_consistency': f'与目标风格有偏差（{score}分），检查高频词和句式是否符合风格指纹',
            'sensitive_word_check': f'存在敏感词风险，请审阅',
        }
        return advices.get(dimension, f'{dimension} 得分偏低（{score}分）')

    @staticmethod
    def _identify_weak_areas(scores: dict) -> list[str]:
        """找出薄弱维度"""
        return [dim for dim, score in scores.items() if score < 6.0]

    @staticmethod
    def _get_template_assignments(match_report: dict) -> list[dict]:
        """为匹配失败的段落分配视觉模板"""
        segments = match_report.get('segments', [])
        return [
            {
                'segment_index': s.get('segment_index', 0),
                'original_source': s.get('source', ''),
                'assigned_template': s.get('fallback', {}).get('template_id', 'photo_card'),
                'confidence': s.get('confidence', 0),
            }
            for s in segments
            if s.get('confidence', 0) < 0.5
        ]

    def _detect_edit_patterns(self, edit_history: list[dict]) -> list[dict]:
        """检测用户编辑模式"""
        patterns = []
        # 简化版：检测重复修改类型
        edit_types = [e.get('edit_type', '') for e in edit_history]
        from collections import Counter
        type_counts = Counter(edit_types)

        for edit_type, count in type_counts.items():
            if count >= 2:
                patterns.append({
                    'edit_type': edit_type,
                    'frequency': count / len(edit_history),
                    'suggestion': self._suggest_automation(edit_type),
                })

        return patterns

    @staticmethod
    def _suggest_automation(edit_type: str) -> str:
        """根据编辑类型建议自动化"""
        suggestions = {
            'shorten_sentence': '自动缩短所有后续段落句长',
            'add_emphasis': '自动为后续段落的关键词添加 emphasis 标注',
            'change_emotion': '自动调整后续段落情绪标签',
            'add_pause': '自动增加段落间停顿',
            'rewrite_hook': '自动重写开场钩子',
        }
        return suggestions.get(edit_type, '自动应用修改模式')


# ==================================================================
# 完整编排流程
# ==================================================================

class NarrationPipeline:
    """一键出片完整编排流程 —— 串联所有引擎"""

    def __init__(self):
        from app.engines.script_engine import ScriptEngine
        from app.engines.scene_matcher import SceneMatcher
        from app.engines.voice_engine import VoiceEngine, TTSRouter
        from app.engines.bgm_engine import BGMEngine
        from app.engines.vdl_compiler import VDLCompiler, VDLBuilder
        from app.engines.platform_adapter import PlatformAdapter

        self.script_engine = ScriptEngine()
        self.scene_matcher = SceneMatcher()
        self.voice_engine = VoiceEngine()
        self.tts_router = TTSRouter()
        self.bgm_engine = BGMEngine()
        self.vdl_compiler = VDLCompiler()
        self.vdl_builder = VDLBuilder()
        self.platform_adapter = PlatformAdapter()
        self.orchestrator = Orchestrator()

    async def run(
        self,
        movie_metadata: dict,
        style_fingerprint,
        platform: Platform,
        voice_id: str,
        user_preferences: dict | None = None,
    ) -> dict[str, Any]:
        """执行完整的一键出片流程

        Returns:
            {
                'success': bool,
                'script': ...,
                'match_report': ...,
                'voice_result': ...,
                'bgm_plan': ...,
                'vdl': ...,
                'decisions': [...],
                'total_duration': float
            }
        """
        decisions_log: list[dict] = []
        start_time = __import__('time').time()

        # 设置用户偏好
        if user_preferences:
            self.orchestrator.preferences = UserPreferences(**user_preferences)

        # Stage 1: 文案生成
        logger.info('pipeline_stage_start', stage='script_generation')
        angles = await self.script_engine.analyze_movie(movie_metadata, style_fingerprint)
        best_angle = angles.get('angles', [{}])[0]

        structure = await self.script_engine.plan_structure(
            best_angle, style_fingerprint, platform
        )
        scripts = await self.script_engine.generate_scripts_parallel(
            structure.get('structure', []), style_fingerprint, platform,
            movie_metadata.get('title', '')
        )
        quality_report = await self.script_engine.score_scripts(
            scripts, style_fingerprint, platform
        )

        decision = self.orchestrator.decide_after_script(quality_report)
        decisions_log.append({
            'stage': 'script',
            'action': decision.action.value,
            'score': quality_report['best_version']['overall_score'],
        })

        # Stage 2: 配音生成
        logger.info('pipeline_stage_start', stage='voice_generation')
        tts_config = self.tts_router.route({
            'voice_id': voice_id,
            'priority': 'quality',
            'mode': 'production',
        })
        voice_result = await self.voice_engine.generate(
            segments=quality_report['best_version']['segments'],
            config=tts_config,
        )

        decision = self.orchestrator.decide_after_voice(
            voice_result.duration_sec / 180 * 10,  # 简化的质量评分
            {'voice_id': voice_id}
        )
        decisions_log.append({'stage': 'voice', 'action': decision.action.value})

        # Stage 3: 画面匹配
        logger.info('pipeline_stage_start', stage='scene_matching')
        match_report = await self.scene_matcher.match_script(
            segments=quality_report['best_version']['segments'],
            movie_id=movie_metadata.get('movie_id', ''),
        )

        decision = self.orchestrator.decide_after_scene_matching({
            'overall_match_rate': match_report.overall_match_rate,
            'composition_mode': match_report.composition_mode,
            'segments': [{'segment_index': s.segment_index, 'confidence': s.confidence,
                          'source': s.source, 'fallback': s.fallback}
                         for s in match_report.segments],
        })
        decisions_log.append({
            'stage': 'scene_matching',
            'action': decision.action.value,
            'match_rate': match_report.overall_match_rate,
            'mode': decision.composition_mode,
        })

        # Stage 4: BGM 规划
        logger.info('pipeline_stage_start', stage='bgm_planning')
        tts_durations = [s.get('estimated_duration_sec', 10) for s in quality_report['best_version']['segments']]
        bgm_plan = await self.bgm_engine.plan_mix(
            segments=quality_report['best_version']['segments'],
            tts_durations=tts_durations,
        )

        # Stage 5: 构建 VDL 文档
        logger.info('pipeline_stage_start', stage='vdl_building')
        builder = VDLBuilder()
        builder.set_metadata(
            title=f'{movie_metadata.get("title", "")} 解说',
            movie=movie_metadata.get('title', ''),
            style=style_fingerprint.name,
            platform=platform,
        )
        builder.set_canvas(platform)

        for i, seg in enumerate(quality_report['best_version']['segments']):
            match = next(
                (m for m in match_report.segments if m.segment_index == seg.get('index', i + 1)),
                None
            )
            bgm_seg = bgm_plan.segments[i] if i < len(bgm_plan.segments) else None

            video_source = {}
            if match and match.source == 'original_clip':
                video_source = {
                    'source': 'movie_clip',
                    'clipRef': {
                        'movieId': movie_metadata.get('movie_id', ''),
                        'timeRange': match.time_range or [0, 10],
                    }
                }
            else:
                video_source = {
                    'source': 'visual_template',
                    'templateId': match.template_id if match else 'photo_card',
                }

            builder.add_segment(
                index=i + 1,
                start_time=sum(
                    quality_report['best_version']['segments'][j].get('estimated_duration_sec', 10)
                    for j in range(i)
                ),
                duration=seg.get('estimated_duration_sec', 10),
                video_source=video_source,
                tts_ssml=seg.get('ssml', ''),
                tts_voice=voice_id,
                bgm_track_id=bgm_seg.track_id if bgm_seg else '',
            )

        vdl_doc = builder.build()

        total_duration = __import__('time').time() - start_time

        return {
            'success': True,
            'script': quality_report['best_version'],
            'all_scripts': quality_report['all_versions'],
            'match_report': {
                'overall_match_rate': match_report.overall_match_rate,
                'composition_mode': match_report.composition_mode,
            },
            'voice_result': {
                'duration_sec': voice_result.duration_sec,
                'engine_used': voice_result.engine_used,
            },
            'bgm_plan': {'total_tracks': bgm_plan.total_bgm_tracks},
            'vdl': vdl_doc,
            'decisions': decisions_log,
            'total_pipeline_duration_sec': round(total_duration, 1),
        }


def create_orchestrator() -> Orchestrator:
    return Orchestrator()
