# =====================================================
# 1v1Chat - Makefile
# 优先级：
#   1) uv（最快，自动管理 Python 版本）
#   2) venv + pip（备选）
# 兼容策略：
#   - Python >= 3.11：完整功能（langgraph, chromadb 等）
#   - Python 3.10  ：使用 requirements-py310.txt（去掉部分高版本依赖）
#   - Python < 3.10 ：强烈建议先装 uv（uv 可一键安装 3.11）
# =====================================================

.PHONY: help install dev backend frontend test lint docker-up docker-down clean \
        uv-install py-install py-sync lock check-env check-uv py-version

UV        ?= uv
PYTHON    ?= python3.11
VENV      ?= .venv
PY_REQ    ?= 3.11

# ---------- 帮助 ----------
help:
	@echo "1v1Chat 常用命令："
	@echo "  make install      - 安装后端 + 前端依赖（自动装 uv / 探测 Python）"
	@echo "  make dev          - 同时启动后端和前端（需另开两个终端）"
	@echo "  make backend      - 启动 FastAPI 后端"
	@echo "  make frontend     - 启动 Vue3 前端"
	@echo "  make test         - 运行后端测试"
	@echo "  make lint         - 代码风格检查"
	@echo "  make lock         - 重新生成 uv.lock / requirements*.txt"
	@echo "  make docker-up    - Docker Compose 一键启动（自带 Python 3.11）"
	@echo "  make clean        - 清理缓存与数据"
	@echo ""
	@echo "  推荐先执行：make uv-install  （一键装 uv + Python 3.11）"

# ---------- 环境探测 ----------
check-env: check-uv py-version
	@echo ""
	@PYVER=$$( $(PYTHON) -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo 0.0 ); \
	if [ "$$(echo \"$$PYVER < 3.10\" | bc -l 2>/dev/null || python3 -c \"print(int(float('$$PYVER')*10<31))\")" = "1" ]; then \
		echo "⚠️  系统 Python $$PYVER 过旧，建议装 uv 后用 uv 自动管理 3.11："; \
		echo "    make uv-install"; \
	fi

check-uv:
	@if command -v $(UV) >/dev/null 2>&1; then \
		echo "✓ uv: $$($(UV) --version)"; \
	else \
		echo "✗ uv: 未安装（建议先 make uv-install）"; \
	fi

py-version:
	@$(PYTHON) -c 'import sys;v=sys.version_info;print(f"Python {v.major}.{v.minor}.{v.micro} ({sys.executable})")' 2>/dev/null \
		|| echo "✗ Python: 未找到"

# ---------- 安装 uv（含 Python 3.11） ----------
uv-install:
	@echo "→ 安装 uv（官方一键脚本，0 依赖）..."
	@curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo ""
	@echo "→ 让 uv 安装 Python $(PY_REQ)（无 root 权限可用，无需 apt）..."
	@if [ -d "$$HOME/.cargo/bin" ]; then export PATH="$$HOME/.cargo/bin:$$PATH"; fi; \
	export PATH="$$HOME/.local/bin:$$PATH"; \
	if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) python install $(PY_REQ); \
		echo "✓ Python $(PY_REQ) 已就绪"; \
	else \
		echo "✗ uv 安装失败，请检查网络或改用 pip"; \
	fi
	@echo ""
	@echo "✓ 下一步：make install"

# ---------- 安装依赖 ----------
install: check-env py-install frontend-install
	@echo ""
	@echo "✓ 全部依赖安装完成"
	@echo "  启动后端：make backend"
	@echo "  启动前端：make frontend"

py-install:
	@if command -v $(UV) >/dev/null 2>&1; then \
		echo "→ uv 探测 Python $(PY_REQ)..."; \
		export PATH="$$HOME/.local/bin:$$PATH"; \
		$(UV) python install $(PY_REQ) 2>/dev/null || true; \
		echo "→ uv sync --extra dev ..."; \
		$(UV) sync --extra dev --python $(PY_REQ); \
	else \
		echo "→ venv + pip 路径..."; \
		$(PYTHON) -m venv $(VENV) || { echo "✗ venv 创建失败"; exit 1; }; \
		. $(VENV)/bin/activate; \
		python -m pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple/ || \
		python -m pip install --upgrade pip; \
		PY_MAJOR=$$(python -c 'import sys;print(sys.version_info.major)'); \
		PY_MINOR=$$(python -c 'import sys;print(sys.version_info.minor)'); \
		if [ $$PY_MAJOR -lt 3 ] || { [ $$PY_MAJOR -eq 3 ] && [ $$PY_MINOR -lt 10 ]; }; then \
			echo "⚠️  Python $$PY_MAJOR.$$PY_MINOR 过老，部分包不兼容，使用 requirements-py310.txt"; \
			pip install -r backend/requirements-py310.txt -i https://mirrors.aliyun.com/pypi/simple/ || \
			pip install -r backend/requirements-py310.txt; \
		else \
			pip install -r backend/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ || \
			pip install -r backend/requirements.txt; \
		fi; \
		pip install -q pytest pytest-asyncio pytest-cov ruff; \
	fi

frontend-install:
	@echo "→ npm install（前端依赖）..."
	@cd frontend && npm install --registry=https://registry.npmmirror.com || npm install

seed:
	@if command -v $(UV) >/dev/null 2>&1; then \
		export PATH="$$HOME/.local/bin:$$PATH"; \
		cd backend && $(UV) run --python $(PY_REQ) python seed.py; \
	else \
		. $(VENV)/bin/activate && cd backend && python seed.py; \
	fi

py-sync:
	@if command -v $(UV) >/dev/null 2>&1; then \
		export PATH="$$HOME/.local/bin:$$PATH"; \
		$(UV) sync --extra dev --python $(PY_REQ); \
	else \
		$(MAKE) py-install; \
	fi

# ---------- 启动 ----------
dev:
	@echo "→ 后端 8000 / 前端 3000"
	@echo "  请在两个终端分别执行：make backend / make frontend"

backend:
	@if command -v $(UV) >/dev/null 2>&1; then \
		export PATH="$$HOME/.local/bin:$$PATH"; \
		echo "→ uv run uvicorn ..."; \
		cd backend && $(UV) run --python $(PY_REQ) uvicorn main:app --host 0.0.0.0 --port 8000 --reload; \
	else \
		. $(VENV)/bin/activate; \
		cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload; \
	fi

frontend:
	cd frontend && npm run dev

# ---------- 锁文件 ----------
lock:
	@if command -v $(UV) >/dev/null 2>&1; then \
		export PATH="$$HOME/.local/bin:$$PATH"; \
		$(UV) lock --python $(PY_REQ); \
		$(UV) export --no-hashes -o requirements.txt; \
		$(UV) export --no-hashes --extra dev -o requirements-dev.txt; \
		echo "✓ uv.lock / requirements.txt / requirements-dev.txt 已生成"; \
	else \
		echo "✗ 需要先 make uv-install"; \
	fi

# ---------- 测试 / 静态检查 ----------
test:
	@if command -v $(UV) >/dev/null 2>&1; then \
		export PATH="$$HOME/.local/bin:$$PATH"; \
		$(UV) run --python $(PY_REQ) pytest -v; \
	else \
		. $(VENV)/bin/activate && cd backend && pytest -v; \
	fi

lint:
	@if command -v $(UV) >/dev/null 2>&1; then \
		export PATH="$$HOME/.local/bin:$$PATH"; \
		$(UV) run --python $(PY_REQ) ruff check backend; \
	else \
		. $(VENV)/bin/activate && cd backend && ruff check .; \
	fi
	cd frontend && npx eslint src --ext .vue,.ts

# ---------- Docker ----------
docker-up:
	mkdir -p data
	docker-compose up -d --build

docker-down:
	docker-compose down

# ---------- 清理 ----------
clean:
	rm -rf data/*.db chroma_data/ .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(VENV)
	docker-compose down -v --rmi local