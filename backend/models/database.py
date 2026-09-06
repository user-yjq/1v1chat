"""
数据库模型（方案 C）
- User：登录用户
- Persona：人设卡（含照片策略/素材）
- Scenario：剧本（阶段列表 + 目标）
- Conversation：会话（绑定人设/剧本 + 运行状态 JSON）
- Message：聊天消息（text / image 等）
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(64), default="")
    avatar_url = Column(String(512), default="")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user",
                                 cascade="all, delete-orphan")


class Scenario(Base):
    """剧本：一组有序阶段，每个阶段描述推进目标与转折条件"""

    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(64), nullable=False)
    description = Column(Text, default="")
    goal = Column(Text, default="")       # 剧本总目标，例如“自然地让对方对你产生好感和信任”
    stages = Column(JSON, default=list)   # [{"key","label","min_turns","objective","advance_on":[]}]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    personas = relationship("Persona", back_populates="scenario")


class Persona(Base):
    """人设卡：AI 扮演的固定角色（姓名/照片策略/开场白等）"""

    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    gender = Column(String(8), default="女")
    age = Column(Integer, default=25)
    city = Column(String(64), default="杭州")
    occupation = Column(String(64), default="")
    avatar_url = Column(String(512), default="")
    bio = Column(Text, default="")            # 背景故事
    personality = Column(Text, default="")    # 性格关键词/描述
    speaking_style = Column(Text, default="") # 说话风格、口头禅
    redlines = Column(JSON, default=list)     # 绝不能做的事（如“不暴露AI”）
    opening_message = Column(Text, default="")
    photo_policy = Column(JSON, default=dict) # 照片策略 {mode, need_stage, max_photos,...}
    photo_assets = Column(JSON, default=list) # 可发送的照片 URL/路径列表
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scenario = relationship("Scenario", back_populates="personas")
    conversations = relationship("Conversation", back_populates="persona")

    @property
    def scenario_name(self) -> str:
        return self.scenario.name if self.scenario else ""

    @property
    def stage_count(self) -> int:
        if not self.scenario or not self.scenario.stages:
            return 0
        return len(self.scenario.stages)


class Conversation(Base):
    """会话：一次与某个 AI 人设的微信式对话"""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(128), default="新对话")
    persona_id = Column(Integer, ForeignKey("personas.id"), nullable=True)
    scenario_id = Column(Integer, ForeignKey("scenarios.id"), nullable=True)
    state = Column(JSON, default=dict)  # 运行状态：阶段/事实/红包/照片计数等
    status = Column(String(32), default="active")  # active / archived
    started_at = Column(DateTime, default=datetime.utcnow)
    last_message_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    persona = relationship("Persona", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            cascade="all, delete-orphan")


class Message(Base):
    """聊天消息（sender_type: user/ai；content_type: text/image）"""

    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_conversation_sent_at", "conversation_id", "sent_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_type = Column(String(16), nullable=False)  # user / ai
    content = Column(Text, nullable=False)
    content_type = Column(String(32), default="text")  # text / image
    media_url = Column(String(512), default="")
    agent_trace = Column(JSON, default=dict)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)

    conversation = relationship("Conversation", back_populates="messages")


class AuthToken(Base):
    """可撤销 refresh token（M4.6 R-C3）：只存 sha256，不落明文。"""

    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    """管理动作审计（M4.6 R-C5）：写操作留痕（操作者/动作/对象/前后摘要）。"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(64), nullable=False)
    object_type = Column(String(32), nullable=False)
    object_id = Column(Integer, nullable=True)
    detail = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def as_dict(obj):
    """通用 ORM → dict（用于 trace/响应拼接）"""
    data = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    for k, v in data.items():
        if isinstance(v, datetime):
            data[k] = v.isoformat()
    return data
