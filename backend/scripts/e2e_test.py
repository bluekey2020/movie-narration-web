"""End-to-end test — uses FastAPI TestClient (no server needed).

Usage:
    python scripts/e2e_test.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
PASS = 0
FAIL = 0


def check(name: str, ok: bool, detail: str = ''):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f'  PASS  {name}')
    else:
        FAIL += 1
        print(f'  FAIL  {name}: {detail}')


print(f'\n{"="*60}')
print('E2E Full Flow Test')
print(f'{"="*60}')

# ===== Health =====
print('\n--- Health ---')
r = client.get('/health')
check('GET /health returns 200', r.status_code == 200, f'status={r.status_code}')
check('GET /health status=ok', r.json().get('status') == 'ok')

# ===== Auth: Register =====
print('\n--- Auth: Register ---')
r = client.post('/api/v1/auth/register', json={
    'email': 'e2e@test.com',
    'password': 'testpass123',
    'display_name': 'E2E User',
})
check('POST /auth/register returns 200', r.status_code == 200,
      f'status={r.status_code} body={r.text[:150]}')
register_data = r.json() if r.status_code == 200 else {}
token = register_data.get('token', '')
check('POST /auth/register returns token', bool(token))

# ===== Auth: Login =====
print('\n--- Auth: Login ---')
r = client.post('/api/v1/auth/login', json={
    'email': 'e2e@test.com',
    'password': 'testpass123',
})
check('POST /auth/login returns 200', r.status_code == 200,
      f'status={r.status_code} body={r.text[:150]}')
login_data = r.json() if r.status_code == 200 else {}
token = login_data.get('token', token)
check('POST /auth/login returns token', bool(token))

# ===== Auth: Login with wrong password =====
r = client.post('/api/v1/auth/login', json={
    'email': 'e2e@test.com',
    'password': 'wrongpassword',
})
check('POST /auth/login wrong pw returns 401', r.status_code == 401,
      f'status={r.status_code}')

# ===== Auth: Me =====
print('\n--- Auth: Me ---')
r = client.get('/api/v1/auth/me', headers={
    'Authorization': f'Bearer {token}',
})
check('GET /auth/me returns 200', r.status_code == 200,
      f'status={r.status_code}')
if r.status_code == 200:
    me = r.json()
    check('GET /auth/me has email', me.get('email') == 'e2e@test.com')

# ===== Auth: Me without token =====
r = client.get('/api/v1/auth/me')
check('GET /auth/me no token returns 401', r.status_code == 401,
      f'status={r.status_code}')

# ===== Movies =====
print('\n--- Movies ---')
r = client.get('/api/v1/movies/')
check('GET /movies/ returns 200', r.status_code == 200,
      f'status={r.status_code}')
movies_data = r.json() if r.status_code == 200 else {}
movie_list = movies_data.get('movies', movies_data) if isinstance(movies_data, dict) else movies_data
movie_count = len(movie_list) if isinstance(movie_list, list) else 0
check(f'GET /movies/ has movies ({movie_count})', movie_count >= 2,
      f'count={movie_count}')

r = client.get('/api/v1/movies/shawshank_redemption')
check('GET /movies/:id returns 200', r.status_code == 200)
if r.status_code == 200:
    check('GET /movies/:id is Shawshank', r.json().get('title') == '肖申克的救赎')

r = client.get('/api/v1/movies/shawshank_redemption/scenes')
check('GET /movies/:id/scenes returns 200', r.status_code == 200)
if r.status_code == 200:
    check('GET /movies/:id/scenes has scenes', len(r.json()) >= 2)

# ===== Styles =====
print('\n--- Styles ---')
r = client.get('/api/v1/styles/')
check('GET /styles/ returns 200', r.status_code == 200,
      f'status={r.status_code}')
styles = r.json() if r.status_code == 200 else {}
style_list = styles.get('styles', styles) if isinstance(styles, dict) else styles
style_count = len(style_list) if isinstance(style_list, list) else 0
check(f'GET /styles/ has styles ({style_count})', style_count >= 3,
      f'count={style_count}')

r = client.get('/api/v1/styles/action_hot')
check('GET /styles/:id returns 200', r.status_code == 200)
if r.status_code == 200:
    check('GET /styles/:id is hot action',
          '热血' in r.json().get('display_name', ''))

# ===== Projects CRUD =====
print('\n--- Projects ---')
r = client.post('/api/v1/projects/', json={
    'movie_id': 'shawshank_redemption',
    'movie_title': '肖申克的救赎',
    'style_id': 'suspense_brainburn',
    'style_name': '烧脑悬疑',
    'platform': 'douyin',
    'status': 'draft',
    'script_segments': [],
    'voice_id': 'narrator-male-youth-01',
})
check('POST /projects/ returns 200', r.status_code == 200,
      f'status={r.status_code} body={r.text[:200]}')
project = r.json() if r.status_code == 200 else {}
project_id = project.get('project_id', '')
check('POST /projects/ returns project_id', bool(project_id))

r = client.get('/api/v1/projects/')
check('GET /projects/ returns 200', r.status_code == 200)
if r.status_code == 200:
    check('GET /projects/ has projects', len(r.json()) >= 1)

r = client.get(f'/api/v1/projects/{project_id}')
if project_id:
    check('GET /projects/:id returns 200', r.status_code == 200)
    if r.status_code == 200:
        check('GET /projects/:id matches', r.json().get('movie_id') == 'shawshank_redemption')

# ===== Generation =====
print('\n--- Generation ---')
r = client.post('/api/v1/generation/start', json={
    'movie_id': 'shawshank_redemption',
    'style': 'suspense_brainburn',
    'platform': 'douyin',
    'voice_id': 'narrator-male-youth-01',
    'mode': 'auto',
})
check('POST /generation/start returns 200', r.status_code == 200,
      f'status={r.status_code} body={r.text[:200]}')
gen_data = r.json() if r.status_code == 200 else {}
task_id = gen_data.get('task_id', '')
check('POST /generation/start returns task_id', bool(task_id))
if task_id:
    print(f'      (task_id={task_id})')

# Test missing params
r = client.post('/api/v1/generation/start', json={})
check('POST /generation/start no params returns 400', r.status_code == 400,
      f'status={r.status_code}')

if task_id:
    r = client.get(f'/api/v1/generation/task/{task_id}/status')
    check('GET /generation/task/:id/status returns 200', r.status_code == 200,
          f'status={r.status_code}')
    if r.status_code == 200:
        data = r.json()
        check('GET /generation/task/:id has status', 'status' in data)
        print(f'      (status={data.get("status")}, stage={data.get("stage", "?")})')

r = client.get('/api/v1/generation/task/nonexistent/status')
check('GET /generation/task/nonexistent returns 404', r.status_code == 404,
      f'status={r.status_code}')

# ===== Summary =====
print(f'\n{"="*60}')
print(f'RESULTS: {PASS} passed, {FAIL} failed, {PASS+FAIL} total')
print(f'{"="*60}')

if FAIL > 0:
    sys.exit(1)
