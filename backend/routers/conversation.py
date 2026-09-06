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
    before_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = (db.query(Conversation)
            .filter(Conversation.id == conv_id, Conversation.user_id == user.id)
            .first())
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return [MessageOut.model_validate(m) for m in page_messages(db, conv.id, limit, before_id)]


def page_messages(
    db: Session,
    conversation_id: int,
    limit: int = 50,
    before_id: int | None = None,
) -> list[Message]:
    """R-B5 游标分页：按消息 id 倒序取游标之前的 limit 条，再转升序返回。

    - 默认返回最新 limit 条（升序），供前端一次加载会话尾部；
    - 游标=该会话内某条消息 id，返回比它更早的消息；游标非法返回 404；
    - limit 收敛到 [1, 500]，避免全表量拉取。
    """
    if limit is None or limit < 1:
        limit = 50
    limit = min(int(limit), 500)
    q = db.query(Message).filter(Message.conversation_id == conversation_id)
    if before_id is not None:
        anchor = q.filter(Message.id == before_id).first()
        if anchor is None:
            raise HTTPException(status_code=404, detail="分页游标不存在")
        q = q.filter(Message.id < before_id)
    rows = q.order_by(Message.id.desc()).limit(limit).all()
    rows.reverse()
    return rows


def _owned_conversation(db: Session, user_id: int, conv_id: int) -> Conversation:
    conv = (db.query(Conversation)
            .filter(Conversation.id == conv_id, Conversation.user_id == user_id)
            .first())
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conv


def conversation_export_body(db: Session, conv: Conversation) -> dict:
    """R-B7 导出载荷构建（对话级与账号级共用）：不含内部 state/agent_trace。"""
    msgs = (db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.sent_at.asc(), Message.id.asc())
            .all())
    p = conv.persona
    return {
        "conversation": {
            "id": conv.id,
            "title": conv.title,
            "persona_id": conv.persona_id,
            "scenario_id": conv.scenario_id,
            "status": conv.status,
            "started_at": conv.started_at.isoformat() if conv.started_at else None,
            "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            "persona": {
                "name": p.name, "age": p.age, "gender": p.gender,
                "city": p.city, "occupation": p.occupation,
                "avatar_url": p.avatar_url,
            } if p else None,
        },
        "messages": [
            {
                "id": m.id,
                "sender_type": m.sender_type,
                "content": m.content,
                "content_type": m.content_type,
                "media_url": m.media_url,
                "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            }
            for m in msgs
        ],
    }


@router.get("/{conv_id}/export")
def export_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """R-B7 数据导出：返回会话元数据 + 完整消息（不含内部 agent_trace/state）。"""
    conv = _owned_conversation(db, user.id, conv_id)
    body = conversation_export_body(db, conv)
    body["exported_at"] = datetime.utcnow().isoformat()
    return body


@router.delete("/{conv_id}/purge")
def purge_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """R-B7 彻底删除：清空消息并删除会话（含 state），删除后不可恢复。"""
    conv = _owned_conversation(db, user.id, conv_id)
    deleted = (db.query(Message)
               .filter(Message.conversation_id == conv_id)
               .delete(synchronize_session=False))
    db.delete(conv)
    db.commit()
    return {"ok": True, "deleted_messages": deleted}


@router.delete("/{conv_id}")
def delete_conversation(
    conv_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    conv = _owned_conversation(db, user.id, conv_id)
    conv.status = "archived"
    db.commit()
    return {"ok": True}
