"""API 路由包（方案 C）"""
from routers.admin import router as admin_router
from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.conversation import router as conversation_router
from routers.personas import router as personas_router

__all__ = ["auth_router", "chat_router", "conversation_router", "personas_router", "admin_router"]
