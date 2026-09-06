"""账号级数据权端点（M5.1/R-B7 收尾）：GET/DELETE /api/me/data。

- GET：导出当前账号全部会话与消息（最小化字段，不含内部 state/agent_trace）；
- DELETE：彻底删除账号全部数据与会话（消息/会话/refresh tokens/账号本身，
  删除后不可恢复）；共享目录 personas/scenarios 与审计行保留。
"""
from datetime import datetime

from core.security import get_current_user
from db.database import get_db
from fastapi import APIRouter, Depends
from models.database import AuditLog, AuthToken, Conversation, Message, User
from routers.conversation import conversation_export_body
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/me/data", tags=["数据权"])


def export_account_data(db: Session, user: User) -> dict:
    """R-B7 账号级导出：user 概览 + 全部会话（含归档）与消息。"""
    convs = (db.query(Conversation)
             .filter(Conversation.user_id == user.id)
             .order_by(Conversation.started_at.asc(), Conversation.id.asc())
             .all())
    return {
        "account": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar_url": user.avatar_url,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "conversations": [conversation_export_body(db, c) for c in convs],
        "exported_at": datetime.utcnow().isoformat(),
    }


def purge_account_data(db: Session, user: User) -> dict:
    """R-B7 账号级彻底删除：先删数据（ORM 级联），再删账号；审计留痕不解引用。"""
    convs = (db.query(Conversation)
             .filter(Conversation.user_id == user.id)
             .order_by(Conversation.id.asc())
             .all())
    n_msg = 0
    for conv in convs:
        n_msg += (db.query(Message)
                  .filter(Message.conversation_id == conv.id).count())
        db.delete(conv)  # Message 级联删除（User→Conversation→Message 均 delete-orphan）
    # refresh tokens 随账号清除；审计中该用户作为操作者的引用置空（动作行保留）
    (db.query(AuthToken)
     .filter(AuthToken.user_id == user.id)
     .delete(synchronize_session=False))
    (db.query(AuditLog)
     .filter(AuditLog.admin_user_id == user.id)
     .update({AuditLog.admin_user_id: None}, synchronize_session=False))
    # 留痕最小化：不落用户名等 PII，仅记 id 与计数
    db.add(AuditLog(
        action="account.purge", object_type="user", object_id=user.id,
        detail={"conversations": len(convs), "messages": n_msg},
    ))
    db.delete(user)  # 会话已删，级联不再重放
    db.commit()
    return {
        "ok": True,
        "deleted_conversations": len(convs),
        "deleted_messages": n_msg,
    }


@router.get("")
def get_account_export(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return export_account_data(db, user)


@router.delete("")
def delete_account_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return purge_account_data(db, user)
