"""Async generation tasks for the movie narration pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from celery import chain, group
from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.config import settings

logger = get_task_logger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / 'data'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)


@celery_app.task(bind=True, name='generate_script')
def generate_script(self, params: dict) -> dict:
    """Stage 1: Generate narration script using 4-stage prompt chain.

    Args:
        params: {movie_id, style, platform, voice_id, mode}

    Returns:
        {script_segments: [...], quality_report: {...}}
    """
    self.update_state(state='PROGRESS', meta={'stage': 'script_generation', 'progress': 10, 'message': 'Loading movie data...'})

    movie_id = params['movie_id']
    style = params['style']
    platform = params.get('platform', 'douyin')

    # Load movie data
    library_path = DATA_DIR / 'movie_library.json'
    if not library_path.exists():
        raise FileNotFoundError(f'Movie library not found: {library_path}')

    with open(library_path, 'r', encoding='utf-8') as f:
        library = json.load(f)

    movie = next((m for m in library.get('movies', []) if m['movie_id'] == movie_id), None)
    if not movie:
        raise ValueError(f'Movie {movie_id} not found')

    # Load style fingerprint
    style_path = DATA_DIR / 'style_fingerprints.json'
    with open(style_path, 'r', encoding='utf-8') as f:
        style_data = json.load(f)

    style_info = next((s for s in style_data.get('styles', []) if s['style_id'] == style), None)
    if not style_info:
        raise ValueError(f'Style {style} not found')

    self.update_state(state='PROGRESS', meta={'stage': 'script_generation', 'progress': 30, 'message': 'Generating script with DeepSeek...'})

    # Run the 4-stage prompt chain
    from app.engines.script_engine import ScriptEngine
    from app.models.style import StyleFingerprint

    # Build StyleFingerprint from style_info
    style_fields = {k: v for k, v in style_info.items() if k != 'style_id'}
    fingerprint = StyleFingerprint(**style_fields)
    fingerprint.style_id = style_info['style_id']

    engine = ScriptEngine()

    import asyncio
    result = asyncio.get_event_loop().run_until_complete(
        engine.generate(
            movie_data=movie,
            style=fingerprint,
            platform=platform,
            num_variants=3,
        )
    )

    self.update_state(state='PROGRESS', meta={'stage': 'script_generation', 'progress': 90, 'message': 'Script generated, evaluating quality...'})

    # Extract script segments from the best variant
    best_variant = result.get('best_variant', result.get('variants', [{}])[0])
    segments = best_variant.get('segments', [])

    # Save output
    output_path = OUTPUT_DIR / f'{movie_id}_{style}_{platform}.json'
    output_path.write_text(json.dumps({
        'movie': movie,
        'style': style_info,
        'platform': platform,
        'script': result,
    }, ensure_ascii=False, indent=2), encoding='utf-8')

    return {
        'script_segments': segments,
        'quality_report': result.get('quality_report', {}),
        'output_path': str(output_path),
    }


@celery_app.task(bind=True, name='match_scenes')
def match_scenes(self, params: dict) -> dict:
    """Stage 2: Match script segments to movie scenes.

    Args:
        params: {movie_id, script_segments: [...]}

    Returns:
        {match_plan: [{segment_index, time_range, source, confidence}]}
    """
    self.update_state(state='PROGRESS', meta={'stage': 'scene_matching', 'progress': 20, 'message': 'Matching scenes...'})

    from app.engines.scene_matcher import SceneMatcher

    matcher = SceneMatcher()
    movie_id = params['movie_id']
    segments = params['script_segments']

    match_plan = []
    for i, seg in enumerate(segments):
        progress = 20 + int((i / max(len(segments), 1)) * 70)
        self.update_state(state='PROGRESS', meta={
            'stage': 'scene_matching',
            'progress': progress,
            'message': f'Matching segment {i + 1}/{len(segments)}...',
        })

        result = matcher.match(
            movie_id=movie_id,
            visual_requirement=seg.get('visual_requirement', {}),
            emotion=seg.get('emotion', 'neutral'),
        )
        match_plan.append(result)

    return {'match_plan': match_plan}


@celery_app.task(bind=True, name='generate_voice')
def generate_voice(self, params: dict) -> dict:
    """Stage 3: Generate TTS voice audio.

    Args:
        params: {script_segments: [...], voice_id: str}

    Returns:
        {audio_path: str, segments: [{index, duration_sec, audio_url}]}
    """
    self.update_state(state='PROGRESS', meta={'stage': 'voice_generation', 'progress': 10, 'message': 'Generating voice...'})

    from app.engines.voice_engine import VoiceEngine

    engine = VoiceEngine()
    segments = params['script_segments']
    voice_id = params.get('voice_id', 'narrator-male-youth-01')

    voice_results = []
    for i, seg in enumerate(segments):
        progress = 10 + int((i / max(len(segments), 1)) * 80)
        self.update_state(state='PROGRESS', meta={
            'stage': 'voice_generation',
            'progress': progress,
            'message': f'Generating voice segment {i + 1}/{len(segments)}...',
        })

        result = engine.synthesize(
            text=seg.get('text', ''),
            voice_id=voice_id,
            emotion=seg.get('emotion', 'neutral'),
        )
        voice_results.append(result)

    return {
        'segments': voice_results,
    }


@celery_app.task(bind=True, name='plan_bgm')
def plan_bgm(self, params: dict) -> dict:
    """Stage 4: Plan BGM mix for the narration.

    Args:
        params: {script_segments: [...]}

    Returns:
        {mix_plan: [{segment_index, track_id, play_start, play_end, volume}]}
    """
    self.update_state(state='PROGRESS', meta={'stage': 'bgm_planning', 'progress': 20, 'message': 'Planning BGM...'})

    from app.engines.bgm_engine import BGMEngine

    engine = BGMEngine()
    segments = params['script_segments']

    mix_plan = engine.plan_mix(segments)

    return {'mix_plan': mix_plan}


@celery_app.task(bind=True, name='compose_video')
def compose_video(self, params: dict) -> dict:
    """Stage 5: Compose final video using FFmpeg.

    Args:
        params: {script_segments, match_plan, voice_results, mix_plan, platform}

    Returns:
        {video_path: str, video_url: str, duration: float}
    """
    self.update_state(state='PROGRESS', meta={'stage': 'video_composition', 'progress': 10, 'message': 'Composing video...'})

    from app.engines.vdl_compiler import VDLCompiler, VDLDocument, VDLSegment

    platform = params.get('platform', 'douyin')
    segments = params['script_segments']
    match_plan = params.get('match_plan', [])
    voice_results = params.get('voice_results', {}).get('segments', [])

    # Build VDL document
    vdl_segments = []
    for i, seg in enumerate(segments):
        match = match_plan[i] if i < len(match_plan) else {}
        voice = voice_results[i] if i < len(voice_results) else {}
        duration = voice.get('duration_sec', seg.get('estimated_duration_sec', 15.0))

        vdl_seg = VDLSegment(
            index=i,
            start_time=sum(
                (voice_results[j].get('duration_sec', segments[j].get('estimated_duration_sec', 15.0))
                 for j in range(i))
            ) if i > 0 else 0,
            duration=duration,
            audio={
                'tts': {
                    'engine': 'narrator-ai',
                    'voice_id': params.get('voice_id', 'narrator-male-youth-01'),
                    'ssml': seg.get('text', ''),
                    'volume': 1.0,
                }
            },
            video={
                'primary': {
                    'source': match.get('source', 'visual_template'),
                    'template_id': match.get('template', 'photo_card'),
                }
            },
            transition={'type': 'cut', 'duration': 500},
        )
        vdl_segments.append(vdl_seg)

    vdl = VDLDocument(
        version='1.0',
        metadata={
            'title': params.get('movie_title', 'Untitled'),
            'movie_name': params.get('movie_id', ''),
            'style': params.get('style', ''),
            'platform': platform,
            'total_duration': sum(s.duration for s in vdl_segments),
        },
        canvas={'width': 1080, 'height': 1920, 'fps': 30},
        defaults={
            'subtitle_style': {},
            'transition': {'type': 'cut', 'duration': 500},
            'bgm_volume': 0.3,
            'tts_volume': 1.0,
        },
        segments=vdl_segments,
    )

    self.update_state(state='PROGRESS', meta={'stage': 'video_composition', 'progress': 50, 'message': 'Rendering video with FFmpeg...'})

    compiler = VDLCompiler()
    output_path = OUTPUT_DIR / f'{params.get("movie_id", "output")}_{platform}.mp4'

    command = compiler.compile(vdl)
    # In production, execute the FFmpeg command here
    # For now, return the compilation result
    import subprocess
    try:
        result = subprocess.run(
            command.to_args(),
            capture_output=True,
            text=True,
            timeout=300,
        )
        success = result.returncode == 0
    except Exception as e:
        logger.error(f'FFmpeg failed: {e}')
        success = False

    self.update_state(state='PROGRESS', meta={'stage': 'video_composition', 'progress': 95, 'message': 'Finalizing...'})

    return {
        'video_path': str(output_path) if success else None,
        'video_url': f'/output/{output_path.name}' if success else None,
        'duration': sum(s.duration for s in vdl_segments),
        'success': success,
    }


@celery_app.task(bind=True, name='run_full_pipeline')
def run_full_pipeline(self, params: dict) -> dict:
    """Run the full narration video generation pipeline.

    This is the main entry point called by the API. It chains all stages:
    script → scene matching → voice + BGM (parallel) → video composition

    Supports a `platforms` list parameter for multi-platform export.
    When provided, the base script is generated once, then adapted and
    rendered for each platform via PlatformAdapter.
    """
    platforms: list[str] = params.get('platforms', [])
    single_platform = params.get('platform', 'douyin')

    # Normalize: if platforms is not provided, use the legacy single platform
    if not platforms:
        platforms = [single_platform]
        params['platform'] = single_platform

    self.update_state(state='PROGRESS', meta={
        'stage': 'script_generation', 'progress': 0,
        'message': f'Starting pipeline for {len(platforms)} platform(s)...'
    })

    # Stage 1: Generate script once (use the first platform for prompt styling)
    first_platform = platforms[0]
    script_params = {**params, 'platform': first_platform}
    script_result = generate_script(script_params)
    base_segments = script_result['script_segments']

    total_platforms = len(platforms)
    platform_results: dict[str, dict] = {}

    for idx, platform_name in enumerate(platforms):
        platform_progress_base = int((idx / total_platforms) * 100)
        self.update_state(state='PROGRESS', meta={
            'stage': 'script_generation',
            'progress': platform_progress_base,
            'message': f'Adapting script for {platform_name} ({idx + 1}/{total_platforms})...'
        })

        # Adapt script for this platform (skip if it matches the base)
        if platform_name != first_platform:
            adapted_segments = _adapt_script_for_platform(
                base_segments, platform_name, params
            )
        else:
            adapted_segments = base_segments

        # Stage 2: Match scenes
        match_result = match_scenes({
            'movie_id': params['movie_id'],
            'script_segments': adapted_segments,
        })

        # Stage 3+4: Voice and BGM
        voice_result = generate_voice({
            'script_segments': adapted_segments,
            'voice_id': params.get('voice_id', 'narrator-male-youth-01'),
        })

        bgm_result = plan_bgm({
            'script_segments': adapted_segments,
        })

        # Stage 5: Compose video for this platform
        compose_result = compose_video({
            'movie_id': params['movie_id'],
            'movie_title': params.get('movie_title', ''),
            'style': params['style'],
            'platform': platform_name,
            'voice_id': params.get('voice_id', 'narrator-male-youth-01'),
            'script_segments': adapted_segments,
            'match_plan': match_result['match_plan'],
            'voice_results': voice_result,
            'mix_plan': bgm_result.get('mix_plan', []),
        })

        platform_results[platform_name] = {
            'script': adapted_segments,
            'match_plan': match_result['match_plan'],
            'voice': voice_result,
            'bgm': bgm_result,
            'video': compose_result,
        }

    self.update_state(state='PROGRESS', meta={
        'stage': 'done', 'progress': 100,
        'message': f'Pipeline complete for {total_platforms} platform(s)'
    })

    return {
        'quality_report': script_result.get('quality_report', {}),
        'platforms': platform_results,
    }


def _adapt_script_for_platform(
    base_segments: list[dict],
    target_platform: str,
    params: dict,
) -> list[dict]:
    """Adapt base script segments for a target platform using PlatformAdapter.

    Uses async LLM calls to rewrite the script in the platform's native
    discourse style, then adjusts duration estimates and other metadata.
    Falls back to the original segments if adaptation fails.
    """
    import asyncio

    from app.engines.platform_adapter import PlatformAdapter
    from app.config import Platform

    adapter = PlatformAdapter()

    base_script = {
        'text': '\n\n'.join(s.get('text', '') for s in base_segments),
        'segments': base_segments,
    }

    try:
        adapted = asyncio.get_event_loop().run_until_complete(
            adapter.adapt(base_script, Platform(target_platform))
        )
        adapted_segments = adapted.segments
    except Exception as exc:
        logger.warning(
            'Platform adaptation failed for %s: %s; falling back to base segments',
            target_platform, exc,
        )
        adapted_segments = base_segments

    if not adapted_segments:
        return base_segments

    # Merge adapted text back into the original segment structure,
    # preserving metadata like visual_requirement and emotion
    result = []
    for i, base_seg in enumerate(base_segments):
        seg = dict(base_seg)
        if i < len(adapted_segments):
            adapted_seg = adapted_segments[i]
            if isinstance(adapted_seg, dict):
                seg['text'] = adapted_seg.get('text', base_seg.get('text', ''))
                if 'estimated_duration_sec' in adapted_seg:
                    seg['estimated_duration_sec'] = adapted_seg['estimated_duration_sec']
        result.append(seg)

    return result
