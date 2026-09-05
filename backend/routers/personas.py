"""人设/剧本浏览（新对话选择 & 后台管理用）"""

from core.security import get_current_user
from db.database import get_db
from fastapi import APIRouter, Depends
from models.database import Persona, User
from models.schemas import PersonaSummary
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/personas", tags=["人设"])


@router.get("", response_model=list[PersonaSummary])
def list_personas(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    personas = (db.query(Persona)
                .filter(Persona.is_active.is_(True))
                .order_by(Persona.id.asc())
                .all())
    return [PersonaSummary.model_validate(p) for p in personas]
