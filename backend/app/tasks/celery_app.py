"""Celery application configuration."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    'movie_narration',
    broker=settings.redis_url.replace('redis://', 'redis://') or 'redis://localhost:6379/1',
    backend=settings.redis_url.replace('redis://', 'redis://').replace('/0', '/2')
    or 'redis://localhost:6379/2',
    include=['app.tasks.generation_tasks'],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max per task
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
