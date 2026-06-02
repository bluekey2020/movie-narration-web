"""一键生成 API —— 核心接口"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post('/start')
async def start_generation(data: dict):
    """启动一键出片任务

    请求体:
    {
        "movie_id": "shawshank_redemption",
        "style": "suspense_brainburn",
        "platform": "douyin",
        "voice_id": "narrator-male-youth-01",
        "mode": "auto"  // auto | manual_review
    }
    """
    movie_id = data.get('movie_id')
    style = data.get('style')
    platform = data.get('platform', 'douyin')
    voice_id = data.get('voice_id', 'narrator-male-youth-01')
    mode = data.get('mode', 'auto')

    if not movie_id or not style:
        raise HTTPException(status_code=400, detail='movie_id and style are required')

    # 加载电影数据
    import json
    from pathlib import Path
    from app.config import settings as app_settings

    library_path = Path(app_settings.movie_library_path)
    if not library_path.exists():
        raise HTTPException(status_code=500, detail='Movie library not found')

    with open(library_path, 'r', encoding='utf-8') as f:
        library = json.load(f)

    movie = next((m for m in library.get('movies', []) if m['movie_id'] == movie_id), None)
    if not movie:
        raise HTTPException(status_code=404, detail=f'Movie {movie_id} not found')

    # 加载风格指纹
    style_path = Path(app_settings.style_fingerprints_path)
    with open(style_path, 'r', encoding='utf-8') as f:
        style_data = json.load(f)

    style_info = next((s for s in style_data.get('styles', []) if s['style_id'] == style), None)
    if not style_info:
        raise HTTPException(status_code=404, detail=f'Style {style} not found')

    # 构建 StyleFingerprint 对象
    from app.models.style import StyleFingerprint
    fingerprint = StyleFingerprint(**{k: v for k, v in style_info.items() if k != 'style_id'})
    fingerprint.style_id = style_info['style_id']

    # 执行完整编排流程
    from app.engines.orchestrator import NarrationPipeline
    pipeline = NarrationPipeline()

    result = await pipeline.run(
        movie_metadata=movie,
        style_fingerprint=fingerprint,
        platform=platform,
        voice_id=voice_id,
        user_preferences={'prefers_auto_mode': mode == 'auto'},
    )

    return {
        'success': result['success'],
        'movie': movie['title'],
        'style': style_info['display_name'],
        'platform': platform,
        'script': {
            'text': result['script'].get('text', ''),
            'total_words': result['script'].get('total_words', 0),
            'overall_score': result['script'].get('overall_score', 0),
        },
        'match_report': result['match_report'],
        'voice_engine': result['voice_result']['engine_used'],
        'decisions': result['decisions'],
        'pipeline_duration_sec': result['total_pipeline_duration_sec'],
    }


@router.get('/task/{task_id}/status')
async def get_task_status(task_id: str):
    """获取任务状态（SSE 实时推送）"""
    # MVP：返回模拟状态
    return {
        'task_id': task_id,
        'status': 'completed',
        'progress': 100,
    }
