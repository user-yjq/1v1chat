# 1v1Chat backend —— 生产候选镜像（M4.4 R-E5：非 root + readiness 探测）
# 依赖安装：uv + backend/requirements.txt（单一依赖源，uv export 产物）
# 国内镜像为默认值；海外/CI 可用 --build-arg 覆盖回官方源：
#   docker build --build-arg APT_MIRROR=deb.debian.org \
#                --build-arg PIP_INDEX_URL=https://pypi.org/simple \
#                -f backend/Dockerfile .
FROM python:3.11-slim

ARG APT_MIRROR=mirrors.aliyun.com
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ARG UV_VERSION=0.12.9

# apt 源切国内镜像（Debian 12 deb822；兼容 legacy sources.list）
RUN sed -i "s|deb\.debian\.org|${APT_MIRROR}|g; s|security\.debian\.org|${APT_MIRROR}|g" \
        /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list 2>/dev/null || true

# 仅保留健康检查所需最小工具（无编译链，镜像更小更安全）
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Python 包源：pip(仅装 uv)与 uv 均走同一镜像；uv 版本钉死保证可复现
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    UV_INDEX_URL=${PIP_INDEX_URL}
RUN pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN uv pip install --system --no-cache -r /app/backend/requirements.txt

COPY backend /app/backend
# 运行期可读/可写：代码统一放开读位（防宿主 600/700 源被 COPY 后 10001 读不了）；
# 可写目录：SQLite 数据与媒体资产（compose 用 named volume 挂载）
RUN chmod -R a+rX /app/backend \
    && mkdir -p /app/backend/data /app/backend/media \
    && chown -R 10001:10001 /app/backend/data /app/backend/media

# 非 root 运行（uid 10001；若用宿主机 bind mount 需把目录 chown 到该 uid）
USER 10001
WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
