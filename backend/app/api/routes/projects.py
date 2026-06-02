"""项目 API"""

from fastapi import APIRouter

router = APIRouter()

# 项目存储（MVP 阶段用内存，生产环境用 PostgreSQL）
_projects: dict[str, dict] = {}


@router.post('/')
async def create_project(data: dict):
    """创建新项目"""
    import uuid
    project_id = str(uuid.uuid4())[:8]
    project = {
        'project_id': project_id,
        'title': data.get('title', 'Untitled'),
        'movie_id': data.get('movie_id', ''),
        'style': data.get('style', ''),
        'platform': data.get('platform', 'douyin'),
        'status': 'draft',
        'created_at': __import__('time').time(),
    }
    _projects[project_id] = project
    return project


@router.get('/')
async def list_projects():
    """获取所有项目"""
    return {'projects': list(_projects.values())}


@router.get('/{project_id}')
async def get_project(project_id: str):
    """获取项目详情"""
    if project_id not in _projects:
        return None
    return _projects[project_id]


@router.put('/{project_id}')
async def update_project(project_id: str, data: dict):
    """更新项目"""
    if project_id not in _projects:
        return None
    _projects[project_id].update(data)
    return _projects[project_id]
