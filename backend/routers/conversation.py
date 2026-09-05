"""对话管理路由（方案 C：绑定人设/剧本创建，带开场白）"""
from datetime import datetime

from core.security import get_current_user
from db.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models.database import Conversation, Message, Persona, Scenario, User
from models.schemas import ConversationCreate, ConversationOut, MessageOut
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/conversations", tags=["对话"])


@router.post("", response_model=ConversationOut, status_code=201)
def create_conversation(
    data: ConversationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    persona = None
    if data.persona_id:
        persona = (db.query(Persona)
                   .filter(Persona.id == data.persona_id, Persona.is_active.is_(True))
                   .first())
        if not persona:
            raise HTTPException(status_code=404, detail="人设不存在")
    scenario: Scenario | None = persona.scenario if persona else None
    title = data.title.strip() or (f"和{persona.name}聊天" if persona else "新对话")

    conv = Conversation(
        user_id=user.id,
        title=title,
        persona_id=persona.id if persona else None,
        scenario_id=scenario.id if scenario else None,
        state={},
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)

    if persona and persona.opening_message:
        opener = Message(
            conversation_id=conv.id,
            sender_type="ai",
            content=persona.opening_message,
            content_type="text",
        )
        db.add(opener)
        db.commit()
        db.refresh(opener)
        conv.last_message_at = datetime.utcnow()
        db.commit()

    db.refresh(conv)
    return ConversationOut.model_validate(conv)


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    convs = (db.query(Conversation)
             .filter(Conversation.user_id == user.id, Conversation.status == "active")
             .order_by(Conversation.last_message_at.desc())
             .all())
    return [ConversationOut.model_validate(c) for c in convs]


@router.get("/{conv_id}", response_model=ConversationOut)
def get_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = (db.query(Conversation)
            .filter(Conversation.id == conv_id, Conversation.user_id == user.id)
            .first())
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return ConversationOut.model_validate(conv)


@router.get("/{conv_id}/messages", response_model=list[MessageOut])
def get_messages(
    conv_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = (db.query(Conversation)
            .filter(Conversation.id == conv_id, Conversation.user_id == user.id)
            .first())
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    msgs = (db.query(Message)
            .filter(Message.conversation_id == conv_id)
            .order_by(Message.sent_at.asc())
            .limit(limit)
            .all())
    return [MessageOut.model_validate(m) for m in msgs]


@router.delete("/{conv_id}")
def delete_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = (db.query(Conversation)
            .filter(Conversation.id == conv_id, Conversation.user_id == user.id)
            .first())
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    conv.status = "archived"
    db.commit()
    return {"ok": True}
