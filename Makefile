# =====================================================
# 1v1Chat - Makefile（M4.4 R-E6 修正版）
#
# 依赖入口唯一：
#   - 源码依赖源：root pyproject.toml（requires-python >= 3.11）
#   - pip / Docker / CI 锁定文件：backend/requirements.txt（uv export 产物）
# 日常命令优先使用仓库 .venv；不存在时由 make install 创建。
# =====================================================

.PHONY: help install py-install frontend-install backend frontend dev seed test lint \
        docker-up docker-down clean lock

UV      ?= uv
PYTHON  ?= python3
VENV    ?= .venv
VENV_PY := $(VENV)/bin/python
PY_REQ  ?= 3.11

# ---------- 帮助 ----------
help:
	@echo "1v1Chat 常用命令："
	@echo "  make install   - 安装后端依赖（uv sync；无 uv 则 venv+pip）"
	@echo "  make backend   - 启动 FastAPI 后端 (8000)"
	@echo "  make frontend  - 启动 Vue3 前端 dev (5173)"
	@echo "  make test      - 运行后端测试（pytest）"
	@echo "  make lint      - ruff 静态检查 backend"
	@echo "  make lock      - uv 生成 uv.lock 并同步 backend/requirements.txt"
	@echo "  make docker-up - docker compose 构建启动 backend+frontend"

# ---------- 安装 ----------
install: py-install frontend-install
	@echo "✓ 依赖安装完成：make backend / make frontend"

py-install:
	@if [ -x $(VENV_PY) ]; then \
		echo "✓ $(VENV) 已存在（如需重建请先 make clean）"; \
	elif command -v $(UV) >/dev/null 2>&1; then \
		echo "→ uv sync --extra dev ..."; \
		$(UV) sync --extra dev --python $(PY_REQ); \
	else \
		echo "→ venv + pip 路径（推荐安装 uv 以获得锁文件支持）..."; \
		$(PYTHON) -m venv $(VENV); \
		$(VENV_PY) -m pip install --upgrade pip; \
		$(VENV_PY) -m pip install -r backend/requirements.txt; \
		$(VENV_PY) -m pip install pytest pytest-asyncio pytest-cov ruff; \
	fi

frontend-install:
	@cd frontend && npm install --registry=https://registry.npmmirror.com || npm install

# ---------- 锁文件（uv 单一依赖源） ----------
lock:
	@command -v $(UV) >/dev/null 2>&1 || { echo "✗ 需要 uv"; exit 1; }
	$(UV) lock --python $(PY_REQ)
	$(UV) export --no-hashes -o backend/requirements.txt
	@echo "✓ uv.lock 与 backend/requirements.txt 已同步"

# ---------- 启动 ----------
backend:
	@if [ ! -x $(VENV_PY) ]; then echo "✗ 先 make install"; exit 1; fi
	cd backend && ../$(VENV_PY) -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

dev:
	@echo "→ 分别执行：make backend（8000）/ make frontend（5173）"

seed:
	@if [ ! -x $(VENV_PY) ]; then echo "✗ 先 make install"; exit 1; fi
	cd backend && ../$(VENV_PY) seed.py

# ---------- 质量门 ----------
test:
	@if [ ! -x $(VENV_PY) ]; then echo "✗ 先 make install"; exit 1; fi
	cd backend && ../$(VENV_PY) -m pytest -q

lint:
	@if [ ! -x $(VENV_PY) ]; then echo "✗ 先 make install"; exit 1; fi
	$(VENV_PY) -m ruff check backend

# ---------- Docker ----------
docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

# ---------- 清理（危险：删除数据/卷/.venv） ----------
clean:
	@echo "⚠️  将删除 data/*.db、backend/data/*.db、__pycache__、$(VENV) 与 compose 卷"
	rm -f data/*.db backend/data/*.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(VENV)
	docker compose down -v --rmi local
