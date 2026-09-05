"""
FastAPI 应用入口（方案 C）
"""
from contextlib import asynccontextmanager
from pathlib import Path

from config import settings
from db.database import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import admin_router, auth_router, chat_router, conversation_router, personas_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="1v1Chat API",
    description="人设剧本驱动的 1v1 角色聊天平台后端",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
    return {"status": "ok", "service": "1v1chat", "version": "0.2.0"}
