"""风格 API"""

import json
from pathlib import Path

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get('/')
async def list_styles():
    """获取所有风格"""
    path = Path(settings.style_fingerprints_path)
    if not path.exists():
        return {'styles': []}

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return {
        'total': len(data.get('styles', [])),
        'styles': [
            {
                'style_id': s['style_id'],
                'display_name': s['display_name'],
                'description': s['description'],
                'usage_count': s.get('usage_count', 0),
                'rating': s.get('rating', 0),
            }
            for s in data.get('styles', [])
        ],
    }


@router.get('/{style_id}')
async def get_style(style_id: str):
    """获取风格详情（含完整指纹参数）"""
    path = Path(settings.style_fingerprints_path)
    if not path.exists():
        return None

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for s in data.get('styles', []):
        if s['style_id'] == style_id:
            return s
    return None
