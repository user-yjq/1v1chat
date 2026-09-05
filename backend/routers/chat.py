"""聊天路由（方案 C：事件/状态/生成在 engine 内完成）"""
from datetime import datetime

from core.security import get_current_user
from db.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models.database import Conversation, Message, User
from models.schemas import ChatResponse, MessageOut
from pydantic import BaseModel
from services.chat_engine import EngineError, process_message
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/chat", tags=["聊天"])


class _ChatPayload(BaseModel):
    conversation_id: int
    content: str
    content_type: str = "text"


@router.post("/send", response_model=ChatResponse)
async def send_message(
    payload: _ChatPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = (db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id,
                    Conversation.user_id == user.id)
            .first())
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    user_msg = Message(
        conversation_id=conv.id,
        sender_type="user",
        content=payload.content,
        content_type="text",
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    try:
        ai_plans, trace = await process_message(conv.id, payload.content, user.id, db)
    except EngineError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None

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
