"""API 路由集成测试"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthCheck:
    """健康检查测试"""

    def test_health(self):
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'


class TestMoviesAPI:
    """电影 API 测试"""

    def test_list_movies(self):
        response = client.get('/api/v1/movies/')
        assert response.status_code == 200
        data = response.json()
        assert 'movies' in data
        assert data['total'] > 0

    def test_get_movie(self):
        response = client.get('/api/v1/movies/shawshank_redemption')
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == '肖申克的救赎'
        assert data['year'] == 1994

    def test_get_movie_not_found(self):
        response = client.get('/api/v1/movies/nonexistent')
        assert response.status_code == 404

    def test_get_movie_scenes(self):
        response = client.get('/api/v1/movies/shawshank_redemption/scenes')
        assert response.status_code == 200
        data = response.json()
        assert 'scenes' in data
        assert len(data['scenes']) > 0


class TestStylesAPI:
    """风格 API 测试"""

    def test_list_styles(self):
        response = client.get('/api/v1/styles/')
        assert response.status_code == 200
        data = response.json()
        assert 'styles' in data
        assert data['total'] > 0

    def test_get_style(self):
        response = client.get('/api/v1/styles/suspense_brainburn')
        assert response.status_code == 200
        data = response.json()
        assert data['display_name'] == '烧脑悬疑'

    def test_get_style_not_found(self):
        response = client.get('/api/v1/styles/nonexistent')
        assert response.status_code == 200
        assert response.json() is None


class TestProjectsAPI:
    """项目 API 测试"""

    def test_create_project(self):
        response = client.post('/api/v1/projects/', json={
            'title': '测试项目',
            'movie_id': 'shawshank_redemption',
            'style': 'suspense_brainburn',
            'platform': 'douyin',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == '测试项目'
        assert 'project_id' in data

    def test_list_projects(self):
        response = client.get('/api/v1/projects/')
        assert response.status_code == 200
        data = response.json()
        assert 'projects' in data

    def test_get_project_not_found(self):
        response = client.get('/api/v1/projects/nonexistent')
        assert response.status_code == 200
        assert response.json() is None


class TestGenerationAPI:
    """生成 API 测试"""

    def test_start_generation_missing_params(self):
        response = client.post('/api/v1/generation/start', json={})
        assert response.status_code == 400

    def test_start_generation_invalid_movie(self):
        response = client.post('/api/v1/generation/start', json={
            'movie_id': 'nonexistent',
            'style': 'suspense_brainburn',
        })
        assert response.status_code == 404

    def test_start_generation_invalid_style(self):
        response = client.post('/api/v1/generation/start', json={
            'movie_id': 'shawshank_redemption',
            'style': 'nonexistent',
        })
        assert response.status_code == 404

    def test_task_status(self):
        response = client.get('/api/v1/generation/task/test-123/status')
        assert response.status_code == 200
        assert response.json()['status'] == 'completed'
