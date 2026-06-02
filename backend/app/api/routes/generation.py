"""一键生成 API —— 核心接口（Celery 异步版）"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.config import settings as app_settings
from app.tasks.generation_tasks import run_full_pipeline

router = APIRouter()

# In-memory task store (MVP — will move to Redis/DB later)
_task_store: dict[str, dict] = {}


@router.post('/start')
async def start_generation(data: dict):
    """启动一键出片任务（异步 Celery）

    请求体:
    {
        "movie_id": "shawshank_redemption",
        "style": "suspense_brainburn",
        "platform": "douyin",
        "voice_id": "narrator-male-youth-01",
        "mode": "auto"
    }
    """
    movie_id = data.get('movie_id')
    style = data.get('style')
    platform = data.get('platform', 'douyin')
    voice_id = data.get('voice_id', 'narrator-male-youth-01')
    mode = data.get('mode', 'auto')

    if not movie_id or not style:
        raise HTTPException(status_code=400, detail='movie_id and style are required')

    # Load movie data (still from JSON for now — will read from DB in phase 2)
    library_path = Path(app_settings.movie_library_path)
    if not library_path.exists():
        raise HTTPException(status_code=500, detail='Movie library not found')

    with open(library_path, 'r', encoding='utf-8') as f:
        library = json.load(f)

    movie = next(
        (m for m in library.get('movies', []) if m['movie_id'] == movie_id), None
    )
    if not movie:
        raise HTTPException(status_code=404, detail=f'Movie {movie_id} not found')

    # Load style fingerprint
    style_path = Path(app_settings.style_fingerprints_path)
    with open(style_path, 'r', encoding='utf-8') as f:
        style_data = json.load(f)

    style_info = next(
        (s for s in style_data.get('styles', []) if s['style_id'] == style), None
    )
    if not style_info:
        raise HTTPException(status_code=404, detail=f'Style {style} not found')

    # Dispatch Celery task
    task_params = {
        'movie_id': movie_id,
        'movie_title': movie.get('title', ''),
        'style': style,
        'platform': platform,
        'voice_id': voice_id,
        'mode': mode,
    }

    celery_task = run_full_pipeline.delay(task_params)

    # Store task info for status polling
    task_id = str(uuid.uuid4())
    _task_store[task_id] = {
        'task_id': task_id,
        'celery_task_id': celery_task.id,
        'project_id': task_params.get('project_id', ''),
        'stage': 'script_generation',
        'status': 'pending',
        'progress': 0,
        'message': 'Task queued',
        'movie_title': movie.get('title', ''),
        'style_name': style_info.get('display_name', style_info.get('name', '')),
        'platform': platform,
    }

    return {
        'success': True,
        'task_id': task_id,
        'celery_task_id': celery_task.id,
        'message': f'Generation started for {movie["title"]} ({style_info.get("display_name", style)})',
    }


@router.get('/task/{task_id}/status')
async def get_task_status(task_id: str):
    """获取 Celery 任务状态"""
    task_info = _task_store.get(task_id)

    if not task_info:
        # Fallback: try to find by celery_task_id
        for tid, info in _task_store.items():
            if info.get('celery_task_id') == task_id:
                task_info = info
                task_id = tid
                break

    if not task_info:
        raise HTTPException(status_code=404, detail=f'Task {task_id} not found')

    # Try to get real Celery task status
    celery_task_id = task_info.get('celery_task_id')
    if celery_task_id:
        from celery.result import AsyncResult
        result = AsyncResult(celery_task_id, app=run_full_pipeline.app)

        if result.ready():
            if result.successful():
                task_info['status'] = 'completed'
                task_info['progress'] = 100
                task_info['stage'] = 'done'
                task_info['message'] = 'Video generation complete'
                task_info['result'] = result.result
            else:
                task_info['status'] = 'failed'
                task_info['error'] = str(result.info) if result.info else 'Unknown error'
                task_info['message'] = 'Generation failed'
        elif result.state == 'PROGRESS':
            meta = result.info or {}
            task_info['status'] = 'running'
            task_info['stage'] = meta.get('stage', task_info['stage'])
            task_info['progress'] = meta.get('progress', 0)
            task_info['message'] = meta.get('message', '')
        elif result.state == 'STARTED':
            task_info['status'] = 'running'

    return task_info


@router.post('/export-all')
async def export_all_platforms(data: dict):
    """一键多平台导出 —— 并发调度每个平台的生成任务

    POST /api/v1/generation/export-all
    Body: {
        "project_id": "...",
        "platforms": ["douyin", "bilibili", "kuaishou", "xiaohongshu"],
        "movie_id": "...",
        "style": "suspense_brainburn",
        "voice_id": "narrator-male-youth-01",
        "mode": "auto"
    }
    Response: {
        "success": true,
        "tasks": { "douyin": { "task_id": "..." }, "bilibili": { ... } }
    }
    """
    project_id = data.get('project_id')
    platforms: list[str] = data.get('platforms', [])
    movie_id = data.get('movie_id')
    style = data.get('style')
    voice_id = data.get('voice_id', 'narrator-male-youth-01')
    mode = data.get('mode', 'auto')

    if not project_id:
        raise HTTPException(status_code=400, detail='project_id is required')

    if not platforms or len(platforms) == 0:
        raise HTTPException(status_code=400, detail='at least one platform is required')

    valid_platforms = {'douyin', 'bilibili', 'kuaishou', 'xiaohongshu'}
    for p in platforms:
        if p not in valid_platforms:
            raise HTTPException(status_code=400, detail=f'Invalid platform: {p}')

    # If movie_id and style are not provided, try to load from project store / DB
    if not movie_id or not style:
        # Look up from any existing task store entry for this project
        project_task = next(
            (info for info in _task_store.values() if info.get('project_id') == project_id),
            None
        )
        if not project_task:
            raise HTTPException(
                status_code=400,
                detail='movie_id and style are required when project has no prior tasks'
            )

        movie_id = movie_id or project_task.get('movie_id', '')
        style = style or project_task.get('style', 'suspense_brainburn')
        voice_id = voice_id or project_task.get('voice_id', 'narrator-male-youth-01')
        mode = mode or project_task.get('mode', 'auto')

    # Load movie title
    movie_title = ''
    library_path = Path(app_settings.movie_library_path)
    if library_path.exists():
        with open(library_path, 'r', encoding='utf-8') as f:
            library = json.load(f)
        movie = next(
            (m for m in library.get('movies', []) if m['movie_id'] == movie_id), None
        )
        if movie:
            movie_title = movie.get('title', '')

    # Dispatch one Celery task per platform
    tasks: dict[str, dict[str, str]] = {}

    for platform_name in platforms:
        task_params = {
            'project_id': project_id,
            'movie_id': movie_id,
            'movie_title': movie_title,
            'style': style,
            'platform': platform_name,
            'voice_id': voice_id,
            'mode': mode,
        }

        celery_task = run_full_pipeline.delay(task_params)

        task_id = str(uuid.uuid4())
        _task_store[task_id] = {
            'task_id': task_id,
            'celery_task_id': celery_task.id,
            'project_id': project_id,
            'stage': 'script_generation',
            'status': 'pending',
            'progress': 0,
            'message': f'Export task queued for {platform_name}',
            'movie_title': movie_title,
            'style_name': style,
            'platform': platform_name,
        }

        tasks[platform_name] = {
            'task_id': task_id,
            'celery_task_id': celery_task.id,
        }

    return {
        'success': True,
        'tasks': tasks,
        'message': f'Dispatched {len(platforms)} platform export tasks',
    }


@router.get('/task/{task_id}/result')
async def get_task_result(task_id: str):
    """Get the final result of a completed task."""
    task_info = _task_store.get(task_id)
    if not task_info:
        raise HTTPException(status_code=400, detail=f'Task {task_id} not found')

    if task_info['status'] == 'completed':
        return task_info.get('result', {})

    raise HTTPException(status_code=400, detail=f'Task {task_id} is not yet completed (status: {task_info["status"]})')
