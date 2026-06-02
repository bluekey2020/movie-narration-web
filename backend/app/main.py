"""Movie Narration Web — FastAPI 主应用"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    import structlog
    logger = structlog.get_logger(__name__)
    logger.info('app_starting', name=settings.app_name)

    # 初始化数据库表
    try:
        from app.db.base import engine, Base
        from app.db import models  # noqa: F401 — register all models
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info('database_tables_created')
    except Exception as e:
        logger.warning('database_init_skipped', reason=str(e))

    yield

    # 关闭时
    await engine.dispose()
    logger.info('app_shutting_down')


app = FastAPI(
    title=settings.app_name,
    version='0.1.0',
    description='AI电影解说一键出片Web平台 API',
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
async def health_check():
    """健康检查"""
    return {'status': 'ok', 'version': '0.1.0'}


# 注册路由
from app.api.routes import projects, generation, movies, styles, auth

app.include_router(auth.router, prefix=f'{settings.api_prefix}/auth', tags=['auth'])
app.include_router(movies.router, prefix=f'{settings.api_prefix}/movies', tags=['movies'])
app.include_router(styles.router, prefix=f'{settings.api_prefix}/styles', tags=['styles'])
app.include_router(projects.router, prefix=f'{settings.api_prefix}/projects', tags=['projects'])
app.include_router(generation.router, prefix=f'{settings.api_prefix}/generation', tags=['generation'])
