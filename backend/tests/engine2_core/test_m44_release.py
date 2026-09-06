"""M4.4（R-E5/R-E6）：readiness 探测 + Docker/Makefile/依赖单一入口一致性。"""
import re
import tomllib
from pathlib import Path

from db.database import db_is_ready, make_engine

_REPO_ROOT = Path(__file__).resolve().parents[3]


class BrokenEngine:
    def connect(self):
        raise RuntimeError("db down")


def _pkg_name(spec: str) -> str:
    # 去版本与 extras：uvicorn[standard]==0.30.0 -> uvicorn
    name = spec.split("==", 1)[0].split("[", 1)[0].strip()
    return re.sub(r"[\s<>=!~;]+.*$", "", name)


# --- readiness（R-E5） ----------------------------------------------------- #
def test_db_is_ready_true_for_working_engine():
    eng = make_engine("sqlite://")
    try:
        assert db_is_ready(eng) is True
    finally:
        eng.dispose()


def test_db_is_ready_false_when_connect_fails():
    assert db_is_ready(BrokenEngine()) is False


def test_health_ready_route_registered():
    from main import app

    ready = [r for r in app.routes if getattr(r, "path", None) == "/api/health/ready"]
    live = [r for r in app.routes if getattr(r, "path", None) == "/api/health"]
    assert live, "liveness /api/health 应存在"
    assert ready and "GET" in getattr(ready[0], "methods", set()), "readiness GET /api/health/ready 应存在"


# --- 镜像 / 配置一致性（R-E5） --------------------------------------------- #
def test_docker_and_nginx_hardening_markers():
    dockerfile = (_REPO_ROOT / "backend/Dockerfile").read_text(encoding="utf-8")
    compose = (_REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    nginx = (_REPO_ROOT / "frontend/nginx.conf").read_text(encoding="utf-8")
    assert "USER 10001" in dockerfile, "backend 应非 root 运行"
    assert "/api/health/ready" in compose, "compose 健康检查应对齐 readiness"
    assert "/ws/" not in nginx, "nginx 死代理 /ws/ 应已清理"


# --- 依赖单一入口 / Makefile 一致性（R-E6） --------------------------------- #
def test_no_stale_makefile_references():
    makefile = (_REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for stale in ("requirements-py310", "langgraph", "chromadb", "chroma_data", "docker-compose"):
        assert stale not in makefile, f"Makefile 不应残留 {stale}"
    assert "backend/requirements.txt" in makefile


def test_single_dependency_entry():
    """R-E6：根 requirements.txt 已废弃；pyproject 依赖 == backend/requirements.txt。"""
    assert not (_REPO_ROOT / "requirements.txt").exists(), "根 requirements.txt 已废弃（单一入口 backend/requirements.txt）"
    req_path = _REPO_ROOT / "backend/requirements.txt"
    req_names = {_pkg_name(line) for line in req_path.read_text(encoding="utf-8").splitlines()
                 if line.strip() and not line.lstrip().startswith("#")}
    with open(_REPO_ROOT / "pyproject.toml", "rb") as f:
        meta = tomllib.load(f)
    proj_names = {_pkg_name(dep) for dep in meta["project"]["dependencies"]}
    assert req_names == proj_names, (
        f"缺失={sorted(proj_names - req_names)} 多余={sorted(req_names - proj_names)}"
    )
