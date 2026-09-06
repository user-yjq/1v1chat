"""Pydantic 响应/请求模型（方案 C）"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class _Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# === 用户 ===
class UserCreate(BaseModel):
    username: str = ""
    password: str = ""
    nickname: str = ""


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(_Orm):
    id: int
    username: str
    nickname: str
    avatar_url: str
    is_admin: bool
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str = ""
    user: UserOut


# === 人设 / 剧本 ===
class PersonaOut(_Orm):
    id: int
    name: str
    gender: str
    age: int
    city: str
    occupation: str
    avatar_url: str
    bio: str
    personality: str
    speaking_style: str
    redlines: list[str]
    opening_message: str
    photo_policy: dict[str, Any]
    photo_assets: list[str]
    scenario_id: int | None
    is_active: bool


class ScenarioOut(_Orm):
    id: int
    slug: str
    name: str
    description: str
    goal: str
    stages: list[dict[str, Any]]
    is_active: bool
    created_at: datetime


class PersonaSummary(_Orm):
    """人设选择卡片（新对话用）"""
    id: int
    name: str
    age: int
    gender: str
    city: str
    occupation: str
    avatar_url: str
    bio: str
    opening_message: str
    photo_policy: dict[str, Any]
    scenario_id: int | None
    scenario_name: str | None = None
    stage_count: int = 0


# === 会话 ===
class ConversationCreate(BaseModel):
    title: str = ""
    persona_id: int | None = None


class ConversationOut(_Orm):
    id: int
    user_id: int
    title: str
    persona_id: int | None
    scenario_id: int | None
    state: dict[str, Any]
    status: str
    started_at: datetime
    last_message_at: datetime
    persona: PersonaSummary | None = None


# === 消息 ===
class MessageOut(_Orm):
    id: int
    conversation_id: int
    sender_type: str
    content: str
    content_type: str
    media_url: str
    agent_trace: dict[str, Any] = {}
    sent_at: datetime


class ChatRequest(BaseModel):
    content: str
    content_type: str = "text"


class ChatResponse(BaseModel):
    user_message: MessageOut
    ai_messages: list[MessageOut]
