"""
FastAPI 应用入口（方案 C）
"""
from contextlib import asynccontextmanager
from pathlib import Path

from config import settings, validate_prod_settings
from db.database import init_db, run_migrations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import admin_router, auth_router, chat_router, conversation_router, personas_router
from version import APP_VERSION


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

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversation_router)
app.include_router(personas_router)
app.include_router(admin_router)

# 媒体（头像 / AI 发送的照片）
Path(settings.MEDIA_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "1v1chat", "version": APP_VERSION}
