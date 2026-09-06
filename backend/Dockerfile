# 1v1Chat backend —— 生产候选镜像（M4.4 R-E5：非 root + readiness 探测）
FROM python:3.11-slim

# 仅保留健康检查所需最小工具（无编译链，镜像更小更安全）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
# 运行期可写目录：SQLite 数据与媒体资产（compose 用 named volume 挂载）
RUN mkdir -p /app/backend/data /app/backend/media \
    && chown -R 10001:10001 /app/backend/data /app/backend/media

# 非 root 运行（uid 10001；若用宿主机 bind mount 需把目录 chown 到该 uid）
USER 10001
WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
