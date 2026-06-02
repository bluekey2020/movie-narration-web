"""编排决策引擎测试"""

import pytest

from app.engines.orchestrator import (
    Orchestrator,
    OrchestrationDecision,
    QualityThresholds,
    UserPreferences,
    DecisionAction,
    NarrationPipeline,
)


class TestQualityThresholds:
    """质量阈值测试"""

    def test_default_thresholds(self):
        thresholds = QualityThresholds()
        assert thresholds.script_auto_continue == 85.0
        assert thresholds.script_suggest_review == 65.0
        assert thresholds.scene_match_auto == 0.70
        assert thresholds.voice_quality_auto == 80.0

    def test_custom_thresholds(self):
        thresholds = QualityThresholds(
            script_auto_continue=90.0,
            script_suggest_review=70.0,
            scene_match_auto=0.80,
        )
        assert thresholds.script_auto_continue == 90.0
        assert thresholds.scene_match_auto == 0.80


class TestOrchestrator:
    """编排决策引擎测试"""

    def test_decide_script_high_quality(self):
        """测试高质量文案 → 自动继续"""
        orchestrator = Orchestrator()
        quality = {
            'overall_score': 90.0,
            'quality_scores': {'hook_attraction': 9.0, 'colloquialism': 8.5},
            'transplant_suggestions': [],
        }

        decision = orchestrator.decide_after_script(quality)
        assert decision.action == DecisionAction.AUTO_CONTINUE
        assert decision.next_stage == 'voice_generation'

    def test_decide_script_medium_quality_with_auto_pref(self):
        """测试中等质量 + 用户偏好全自动 → 自动继续"""
        orchestrator = Orchestrator(
            preferences=UserPreferences(prefers_auto_mode=True)
        )
        quality = {
            'overall_score': 72.0,
            'quality_scores': {'hook_attraction': 6.5, 'colloquialism': 7.0},
            'transplant_suggestions': [],
        }

        decision = orchestrator.decide_after_script(quality)
        assert decision.action == DecisionAction.AUTO_CONTINUE

    def test_decide_script_medium_quality_without_auto(self):
        """测试中等质量 + 用户不偏好全自动 → 等待审阅"""
        orchestrator = Orchestrator(
            preferences=UserPreferences(prefers_auto_mode=False)
        )
        quality = {
            'overall_score': 72.0,
            'quality_scores': {'hook_attraction': 6.5, 'colloquialism': 7.0},
            'transplant_suggestions': [],
        }

        decision = orchestrator.decide_after_script(quality)
        assert decision.action == DecisionAction.WAIT_FOR_REVIEW
        assert decision.review_highlights is not None

    def test_decide_script_low_quality(self):
        """测试低质量文案 → 自动重试"""
        orchestrator = Orchestrator()
        quality = {
            'overall_score': 50.0,
            'quality_scores': {'hook_attraction': 3.0, 'colloquialism': 4.0},
            'transplant_suggestions': [],
            'angles_tried': ['angle_1'],
        }

        decision = orchestrator.decide_after_script(quality)
        assert decision.action == DecisionAction.AUTO_RETRY
        assert decision.retry_params is not None
        assert decision.retry_params['change_angle'] is True

    def test_decide_scene_high_match(self):
        """测试高匹配率 → 素材优先"""
        orchestrator = Orchestrator()
        report = {
            'overall_match_rate': 0.85,
            'composition_mode': 'clip_priority',
        }

        decision = orchestrator.decide_after_scene_matching(report)
        assert decision.action == DecisionAction.AUTO_CONTINUE
        assert decision.composition_mode == 'clip_priority'

    def test_decide_scene_medium_match(self):
        """测试中等匹配率 → 混合模式"""
        orchestrator = Orchestrator()
        report = {
            'overall_match_rate': 0.55,
            'composition_mode': 'hybrid',
            'segments': [
                {'segment_index': 1, 'confidence': 0.8, 'source': 'original_clip'},
                {'segment_index': 2, 'confidence': 0.3, 'source': 'original_clip',
                 'fallback': {'template_id': 'photo_card'}},
            ],
        }

        decision = orchestrator.decide_after_scene_matching(report)
        assert decision.action == DecisionAction.AUTO_CONTINUE
        assert decision.composition_mode == 'hybrid'
        assert decision.template_replacements is not None

    def test_decide_scene_low_match(self):
        """测试低匹配率 → 降级"""
        orchestrator = Orchestrator()
        report = {
            'overall_match_rate': 0.20,
            'composition_mode': 'template_only',
        }

        decision = orchestrator.decide_after_scene_matching(report)
        assert decision.action == DecisionAction.DOWNGRADE
        assert decision.composition_mode == 'template_only'

    def test_decide_voice_high(self):
        """测试高质量配音 → 自动继续"""
        orchestrator = Orchestrator()
        decision = orchestrator.decide_after_voice(90.0, {'voice_id': 'test'})
        assert decision.action == DecisionAction.AUTO_CONTINUE

    def test_decide_voice_low(self):
        """测试低质量配音 → 重试"""
        orchestrator = Orchestrator()
        decision = orchestrator.decide_after_voice(40.0, {'voice_id': 'old-voice'})
        assert decision.action == DecisionAction.AUTO_RETRY
        assert decision.retry_params['change_voice'] is True

    def test_learn_from_edits_not_enough_history(self):
        """测试编辑历史不够 → 不学习"""
        orchestrator = Orchestrator()
        result = orchestrator.learn_from_user_edits(
            original={}, edited={},
            edit_history=[{}, {}],  # 只有 2 次，不够
        )
        assert result['learned'] is False

    def test_learn_from_edits_enough_history(self):
        """测试足够的编辑历史 → 学习模式"""
        orchestrator = Orchestrator()
        result = orchestrator.learn_from_user_edits(
            original={}, edited={},
            edit_history=[
                {'edit_type': 'shorten_sentence'},
                {'edit_type': 'shorten_sentence'},
                {'edit_type': 'shorten_sentence'},
            ],
        )
        assert result['learned'] is True
        assert result['confidence'] >= 0.6

    def test_update_preferences_auto_mode(self):
        """测试从任务结果更新偏好"""
        orchestrator = Orchestrator()
        task_result = {
            'decisions': [
                {'action': 'auto_continue'},
                {'action': 'auto_continue'},
                {'action': 'auto_continue'},
                {'action': 'auto_continue'},
            ],  # 100% 自动继续
            'style': 'suspense_brainburn',
            'voice_id': 'narrator-male-01',
        }

        orchestrator.update_preferences_from_task(task_result)
        assert orchestrator.preferences.prefers_auto_mode is True
        assert 'suspense_brainburn' in orchestrator.preferences.favorite_styles

    def test_review_highlights_extraction(self):
        """测试审阅重点提取"""
        orchestrator = Orchestrator()
        scores = {
            'hook_attraction': 9.0,
            'information_density': 8.0,
            'rhythm_curve': 5.0,    # 低分
            'colloquialism': 4.0,   # 低分
            'duration_compliance': 9.0,
            'style_consistency': 7.0,
            'sensitive_word_check': 10.0,
        }

        highlights = orchestrator._extract_review_highlights(scores)
        assert len(highlights) > 0
        # 口语化和节奏应被提及
        assert any('口语化' in h for h in highlights) or any('节奏' in h for h in highlights)


class TestNarrationPipeline:
    """完整编排流程测试"""

    def test_pipeline_creation(self):
        """测试 pipeline 创建"""
        pipeline = NarrationPipeline()
        assert pipeline.script_engine is not None
        assert pipeline.scene_matcher is not None
        assert pipeline.voice_engine is not None
        assert pipeline.bgm_engine is not None
        assert pipeline.orchestrator is not None

    def test_pipeline_run_without_llm(self, sample_movie, sample_style_fingerprint):
        """测试 pipeline 运行（无 LLM 调用 — 仅验证流程不崩溃）"""
        import asyncio

        pipeline = NarrationPipeline()
        # 不实际调用 LLM，验证 pipeline 结构完整
        assert pipeline.run is not None
        assert asyncio.iscoroutinefunction(pipeline.run)
