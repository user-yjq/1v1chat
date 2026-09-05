"""聊天路由（v1/v2 双引擎：ENGINE_VERSION 切换，T-12）

安全/业务边界都在这里做：会话归属校验、消息长度、限流；
engine 层只做领域处理，不直接面对 HTTP。
"""
from datetime import datetime

from config import settings
from core.ratelimit import check_chat_rate
from core.security import get_current_user
from db.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models.database import Conversation, Message, User
from models.schemas import ChatResponse, MessageOut
from pydantic import BaseModel
from services import chat_engine, chat_engine2
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/chat", tags=["聊天"])


class _ChatPayload(BaseModel):
    conversation_id: int
    content: str
    content_type: str = "text"


def find_owned_conversation(
    db: Session, user_id: int, conversation_id: int,
) -> Conversation:
    """归属校验（NFR-SEC-1）：只能操作自己的会话，否则 404。"""
    conv = (db.query(Conversation)
            .filter(Conversation.id == conversation_id,
                    Conversation.user_id == user_id)
            .first())
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conv


def ensure_message_length(content: str) -> None:
    """输入约束（NFR-SEC-3）：超限 400，不进入引擎。"""
    if len(content) > settings.MSG_MAX_LEN:
        raise HTTPException(status_code=400,
                            detail=f"消息过长（上限 {settings.MSG_MAX_LEN} 字）")


@router.post("/send", response_model=ChatResponse)
async def send_message(
    payload: _ChatPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = find_owned_conversation(db, user.id, payload.conversation_id)
    ensure_message_length(payload.content)
    check_chat_rate(user.id)

    user_msg = Message(
        conversation_id=conv.id,
        sender_type="user",
        content=payload.content,
        content_type="text",
    )
    db.add(user_msg)
    db.flush()
    db.refresh(user_msg)

    try:
        if settings.ENGINE_VERSION == "v2":
            ai_plans, trace, state = await chat_engine2.process_message2(
                conv.id, payload.content, user.id, db)
            conv.state = state
        else:
            ai_plans, trace = await chat_engine.process_message(
                conv.id, payload.content, user.id, db)
    except (chat_engine.EngineError, chat_engine2.Engine2Error) as exc:
        db.rollback()
        detail = str(exc)
        raise HTTPException(status_code=400 if "过长" in detail else 404,
                            detail=detail) from None

    ai_msgs: list[Message] = []
    for idx, plan in enumerate(ai_plans):
        m = Message(
            conversation_id=conv.id,
            sender_type="ai",
            content=plan.get("content", ""),
            content_type=plan.get("content_type", "text"),
            media_url=plan.get("media_url", ""),
            agent_trace=trace if idx == len(ai_plans) - 1 else {},
        )
        db.add(m)
        ai_msgs.append(m)

    conv.last_message_at = datetime.utcnow()
    db.commit()
    for m in ai_msgs:
        db.refresh(m)

    return ChatResponse(
        user_message=MessageOut.model_validate(user_msg),
        ai_messages=[MessageOut.model_validate(m) for m in ai_msgs],
    )
