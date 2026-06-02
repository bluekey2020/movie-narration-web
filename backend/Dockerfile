# Movie Narration Web — 后端 Dockerfile
# Python 3.12 + FastAPI + Uvicorn (开发模式)

FROM python:3.12-slim

# 替换为国内 Debian 镜像源
RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 系统依赖: libpq-dev 是 asyncpg 编译所需, ffmpeg 用于视频处理
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# pip 使用国内镜像
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

WORKDIR /app

# 先复制依赖文件 (利用 Docker 层缓存)
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码 (docker-compose 会通过 volume 覆盖, 这里只是基础镜像)
COPY . .

# FastAPI 开发服务器 (带热重载)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app"]
