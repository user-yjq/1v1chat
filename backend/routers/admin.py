"""管理后台 API（is_admin）：人设/剧本维护 + 会话查看"""

from core.security import get_current_user
from db.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from models.database import Conversation, Message, Persona, Scenario, User
from models.schemas import MessageOut, PersonaOut, ScenarioOut
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


def _require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


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
def admin_create_persona(data: PersonaIn, db: Session = Depends(get_db), _=Depends(_require_admin)):
    p = Persona(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/personas/{pid}", response_model=PersonaOut)
def admin_update_persona(pid: int, data: PersonaIn, db: Session = Depends(get_db), _=Depends(_require_admin)):
    p = db.query(Persona).filter(Persona.id == pid).first()
    if not p:
        raise HTTPException(status_code=404, detail="人设不存在")
    for k, v in data.model_dump().items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.get("/scenarios", response_model=list[ScenarioOut])
def admin_list_scenarios(db: Session = Depends(get_db), _=Depends(_require_admin)):
    return db.query(Scenario).order_by(Scenario.id.asc()).all()


@router.post("/scenarios", response_model=ScenarioOut, status_code=201)
def admin_create_scenario(data: ScenarioIn, db: Session = Depends(get_db), _=Depends(_require_admin)):
    if db.query(Scenario).filter(Scenario.slug == data.slug).first():
        raise HTTPException(status_code=400, detail="slug 已存在")
    sc = Scenario(**data.model_dump())
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return sc


@router.put("/scenarios/{sid}", response_model=ScenarioOut)
def admin_update_scenario(sid: int, data: ScenarioIn, db: Session = Depends(get_db), _=Depends(_require_admin)):
    sc = db.query(Scenario).filter(Scenario.id == sid).first()
    if not sc:
        raise HTTPException(status_code=404, detail="剧本不存在")
    for k, v in data.model_dump().items():
        setattr(sc, k, v)
    db.commit()
    db.refresh(sc)
    return sc


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
