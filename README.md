# 🎬 Movie Narration Web

> AI 电影解说一键出片 Web 平台 — 选片 → AI 生成 → 人工微调 → 多平台导出

专为影视解说创作者打造的 AI 创作工作台。选择一个电影、挑选解说风格，AI 自动完成文案、配音、画面匹配和视频合成，一键导出适配抖音/B站/快手/小红书的解说视频。

## ✨ 核心功能

- **🎯 智能选片** — 50 部热门电影库，搜索/类型/评分筛选
- **🎨 12 种解说风格** — 热血动作、烧脑悬疑、爆笑喜剧、励志成长等
- **🤖 AI 4 层文案生成** — DeepSeek 驱动的电影理解→结构规划→并行写作→质量评分
- **✏️ 可视化文案编辑器** — 7 段式结构、情绪标签、停顿标记、AI 辅助润色
- **⏱️ 时间线编辑器** — 4 轨同步（文案/画面/BGM/特效）、拖拽调整
- **🎵 146 首 BGM 库** — 按情绪/类型智能匹配
- **📱 多平台一键导出** — 抖音/B站/快手/小红书，自动适配语体和格式
- **📊 版本对比** — 3 版文案并排比较 + 6 维质量雷达图

## 🚀 快速开始

### 前提条件

- Docker & Docker Compose
- DeepSeek API Key（[获取](https://platform.deepseek.com/)）

### 一键启动（开发环境）

```bash
# 1. 克隆项目
git clone <repo-url> movie-narration-web
cd movie-narration-web

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写 DEEPSEEK_API_KEY

# 3. 启动所有服务
docker compose up -d

# 4. 访问
# 前端: http://localhost:3000
# API 文档: http://localhost:8000/docs
# 健康检查: http://localhost:8000/health
```

### 生产部署

```bash
# 1. 配置生产环境变量
cp .env.example .env
# 编辑 .env，填写 SECRET_KEY（强随机字符串）和 DEEPSEEK_API_KEY

# 2. 启动生产环境
docker compose -f docker-compose.prod.yml up -d

# 3. 访问 http://localhost
```

## 🏗️ 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui, Zustand |
| **后端** | Python 3.12, FastAPI, Celery, SQLAlchemy |
| **AI** | DeepSeek V4 Pro, narrator-ai API, SSML 标注 |
| **数据库** | PostgreSQL 16 + pgvector |
| **缓存/队列** | Redis 7, Celery |
| **视频处理** | FFmpeg, Pillow (模板渲染) |
| **部署** | Docker, Docker Compose, Nginx |

## 📁 项目结构

```
movie-narration-web/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # API 路由 (auth/movies/styles/projects/generation)
│   │   ├── engines/            # AI 引擎 (script/scene/voice/BGM/VDL/orchestrator/platform)
│   │   ├── db/                 # 数据库 ORM 模型
│   │   ├── tasks/              # Celery 异步任务
│   │   └── models/             # Pydantic/Dataclass 模型
│   ├── data/                   # JSON 数据 (50 电影/12 风格/146 BGM)
│   ├── scripts/                # CLI 工具 (render_video.py, run_pipeline.py)
│   └── tests/                  # Pytest 测试
├── frontend/
│   └── src/
│       ├── app/                # Next.js 页面路由
│       ├── components/         # UI 组件 (timeline/script/export/generation/layout)
│       ├── stores/             # Zustand 状态管理
│       └── lib/                # API 客户端 + 工具函数
├── docs/                       # 设计文档 + 计划
├── docker-compose.yml          # 开发环境
├── docker-compose.prod.yml     # 生产环境
└── nginx.conf                  # Nginx 反向代理配置
```

## 🔧 本地开发（不使用 Docker）

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### 启动 Celery Worker（另开终端）

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

## 📡 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/v1/auth/register` | 用户注册 |
| POST | `/api/v1/auth/login` | 用户登录 |
| GET | `/api/v1/auth/me` | 当前用户信息 |
| GET | `/api/v1/movies/` | 电影列表 |
| GET | `/api/v1/movies/{id}` | 电影详情 |
| GET | `/api/v1/styles/` | 风格列表 |
| GET | `/api/v1/styles/{id}` | 风格详情 |
| POST | `/api/v1/projects/` | 创建项目 |
| GET | `/api/v1/projects/` | 项目列表 |
| GET | `/api/v1/projects/{id}` | 项目详情 |
| POST | `/api/v1/generation/start` | 一键生成 |
| GET | `/api/v1/generation/task/{id}/status` | 任务状态 |
| POST | `/api/v1/generation/export-all` | 多平台导出 |

完整 API 文档启动后端后访问 `http://localhost:8000/docs`

## 🎬 命令行渲染

```bash
cd backend
python scripts/render_video.py output/shawshank_redemption_suspense_brainburn_douyin.json
python scripts/render_video.py output/xxx.json --platform bilibili --output my_video.mp4
```

## 📄 许可证

MIT
