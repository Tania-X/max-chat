# ---------- 阶段 1：构建前端 ----------
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry=https://registry.npmmirror.com
COPY frontend/ ./
RUN npm run build

# ---------- 阶段 2：后端运行时 ----------
FROM python:3.11-slim
WORKDIR /app

ENV PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

COPY backend/requirements.txt backend/requirements.lock.txt ./
# 按锁文件安装，保证构建可复现（requirements.txt 仅声明直接依赖）
RUN pip install -r requirements.lock.txt

COPY backend/ ./
COPY --from=frontend /build/dist ./static

RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
