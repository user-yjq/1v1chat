"""
FastAPI 应用入口（方案 C）
"""
from contextlib import asynccontextmanager
from pathlib import Path

from config import settings, validate_prod_settings
from core.admin_bootstrap import bootstrap_admin_if_configured
from core.logging import configure_logging
from core.metrics import render as render_metrics
from core.middleware import ObservabilityMiddleware
from db.database import db_is_ready, init_db, run_migrations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from llm.provider import llm_config_report
from routers import (
    account_router,
    admin_router,
    auth_router,
    chat_router,
    conversation_router,
    personas_router,
)
from version import APP_VERSION

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    problems = validate_prod_settings()
    if problems:
        raise RuntimeError("生产配置校验失败： " + "; ".join(problems))
    # 生产：schema 走 Alembic 版本迁移；开发：create_all 快速可用（M4.1）
    if (settings.APP_ENV or "").strip().lower() == "prod":
        run_migrations()
    else:
        init_db()
    # M4.6 R-C6：配置了 ADMIN_BOOTSTRAP_* 且 users 空表时创建管理员
    bootstrap_admin_if_configured()
    yield


app = FastAPI(
    title="1v1Chat API",
    description="人设剧本驱动的 1v1 角色聊天平台后端",
    version=APP_VERSION,
    lifespan=lifespan,
)

_origins = list(settings.CORS_ORIGINS) if settings.CORS_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ObservabilityMiddleware)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(personas_router)
app.include_router(admin_router)
app.include_router(account_router)

# 媒体（头像 / AI 发送的照片）
Path(settings.MEDIA_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "1v1chat", "version": APP_VERSION}


@app.get("/api/health/ready")
def health_ready():
    """readiness（R-D4）：DB 连通为硬条件；LLM 为配置探测（不发起真实网络调用）。"""
    report = readiness_report()
    status_code = 503 if report["status"] == "unavailable" else 200
    return JSONResponse(content=report, status_code=status_code)


@app.get("/api/meta")
def app_meta():
    """公开元信息（M4.7 R-F1/R-F3）：产品层透明披露文案与开关，供前端渲染。"""
    return {
        "disclosure": {
            "enabled": bool(settings.DISCLOSURE_ENABLED),
            "text": settings.DISCLOSURE_TEXT,
        }
    }


def readiness_report(db_target=None) -> dict:
    db_ok = db_is_ready(db_target)
    llm = llm_config_report()
    if not db_ok:
        status = "unavailable"
    elif llm["ready"]:
        status = "ok"
    else:
        status = "degraded"
    return {
        "status": status,
        "service": "1v1chat",
        "version": APP_VERSION,
        "checks": {"db": db_ok, "llm": llm},
    }


@app.get("/api/metrics", include_in_schema=False)
def metrics_endpoint():
    """Prometheus 文本指标（M4.5 R-D2）；按进程独立计数。"""
    return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")
