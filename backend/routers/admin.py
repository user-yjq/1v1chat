"""管理后台 API（is_admin）：人设/剧本维护 + 会话查看"""

from core.security import get_current_user
from db.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models.database import AuditLog, Conversation, Message, Persona, Scenario, User
from models.schemas import MessageOut, PersonaOut, ScenarioOut
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def record_admin_audit(
    db: Session,
    admin: User,
    action: str,
    object_type: str,
    object_id: int | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    """写操作审计（R-C5）：同事务落 audit_logs，不单独 commit。"""
    detail = {}
    if before is not None:
        detail["before"] = before
    if after is not None:
        detail["after"] = after
    db.add(AuditLog(
        admin_user_id=admin.id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        detail=detail,
    ))


class PersonaIn(BaseModel):
    name: str = Field(..., max_length=64)
    gender: str = "女"
    age: int = 25
    city: str = "杭州"
    occupation: str = ""
    avatar_url: str = ""
    bio: str = ""
    personality: str = ""
    speaking_style: str = ""
    opening_message: str = ""
    photo_policy: dict = {}
    photo_assets: list[str] = []
    scenario_id: int | None = None
    is_active: bool = True


class ScenarioIn(BaseModel):
    slug: str = Field(..., max_length=64)
    name: str = Field(..., max_length=64)
    description: str = ""
    goal: str = ""
    stages: list[dict] = []
    is_active: bool = True


@router.get("/personas", response_model=list[PersonaOut])
def admin_list_personas(db: Session = Depends(get_db), _=Depends(_require_admin)):
    return db.query(Persona).order_by(Persona.id.asc()).all()


@router.post("/personas", response_model=PersonaOut, status_code=201)
def admin_create_persona(
    data: PersonaIn,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    p = Persona(**data.model_dump())
    db.add(p)
    db.flush()
    record_admin_audit(db, admin, "persona.create", "persona", p.id,
                       after={"name": p.name, "scenario_id": p.scenario_id})
    db.commit()
    db.refresh(p)
    return p


@router.put("/personas/{pid}", response_model=PersonaOut)
def admin_update_persona(
    pid: int,
    data: PersonaIn,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    p = db.query(Persona).filter(Persona.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="人设不存在")
    before = {"name": p.name, "is_active": p.is_active}
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    record_admin_audit(db, admin, "persona.update", "persona", p.id,
                       before=before,
                       after={"name": p.name, "is_active": p.is_active})
    db.commit()
    db.refresh(p)
    return p


@router.get("/scenarios", response_model=list[ScenarioOut])
def admin_list_scenarios(db: Session = Depends(get_db), _=Depends(_require_admin)):
    return db.query(Scenario).order_by(Scenario.id.asc()).all()


@router.post("/scenarios", response_model=ScenarioOut, status_code=201)
def admin_create_scenario(
    data: ScenarioIn,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    if db.query(Scenario).filter(Scenario.slug == data.slug).first():
        raise HTTPException(status_code=400, detail="slug 已存在")
    sc = Scenario(**data.model_dump())
    db.add(sc)
    db.flush()
    record_admin_audit(db, admin, "scenario.create", "scenario", sc.id,
                       after={"slug": sc.slug, "name": sc.name})
    db.commit()
    db.refresh(sc)
    return sc


@router.put("/scenarios/{sid}", response_model=ScenarioOut)
def admin_update_scenario(
    sid: int,
    data: ScenarioIn,
    db: Session = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    sc = db.query(Scenario).filter(Scenario.id == sid).first()
    if not sc:
        raise HTTPException(status_code=404, detail="剧本不存在")
    before = {"slug": sc.slug, "name": sc.name, "is_active": sc.is_active}
    for k, v in data.model_dump().items():
        setattr(sc, k, v)
    record_admin_audit(db, admin, "scenario.update", "scenario", sc.id,
                       before=before,
                       after={"slug": sc.slug, "name": sc.name, "is_active": sc.is_active})
    db.commit()
    db.refresh(sc)
    return sc


@router.get("/audit")
def admin_list_audit(
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    rows = (db.query(AuditLog)
            .order_by(AuditLog.id.desc())
            .limit(min(limit, 200))
            .all())
    ids = {r.admin_user_id for r in rows if r.admin_user_id}
    admins = {u.id: u.username for u in db.query(User).filter(User.id.in_(ids)).all()} if ids else {}
    return [
        {
            "id": r.id,
            "admin_user_id": r.admin_user_id,
            "admin_username": admins.get(r.admin_user_id),
            "action": r.action,
            "object_type": r.object_type,
            "object_id": r.object_id,
            "detail": r.detail or {},
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/conversations")
def admin_list_conversations(
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(_require_admin),
):
    convs = (db.query(Conversation)
             .order_by(Conversation.last_message_at.desc())
             .limit(min(limit, 200))
             .all())
    out = []
    for c in convs:
        p = c.persona
        state = c.state or {}
        out.append({
            "id": c.id,
            "user_id": c.user_id,
            "title": c.title,
            "persona_name": p.name if p else "-",
            "stage_idx": state.get("stage_idx", 0),
            "photos_sent": state.get("photos_sent", 0),
            "red_packets": state.get("red_packets", 0),
            "message_count": len(c.messages),
            "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
            "status": c.status,
        })
    return out


@router.get("/conversations/{cid}/messages", response_model=list[MessageOut])
def admin_conv_messages(cid: int, db: Session = Depends(get_db), _=Depends(_require_admin)):
    conv = db.query(Conversation).filter(Conversation.id == cid).first()
    if not conv:
        raise HTTPException(status_code=404, detail="会话不存在")
    return (db.query(Message).filter(Message.conversation_id == cid)
            .order_by(Message.sent_at.asc()).limit(200).all())
