# Movie Narration Web — 前端 Dockerfile
# Node.js 22 + Next.js 15 (开发模式)

FROM node:22-alpine

# 使用国内 npm 镜像
RUN npm config set registry https://registry.npmmirror.com

WORKDIR /app

# 先复制 package 文件 (利用 Docker 层缓存)
COPY package.json package-lock.json ./

# 安装依赖
RUN npm ci

# 复制应用代码 (docker-compose 会通过 volume 覆盖)
COPY . .

# Next.js 开发服务器 (带热重载和 Turbopack)
CMD ["npm", "run", "dev"]
