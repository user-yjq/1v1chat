"""认证路由（M4.6：登录防爆破 + refresh 轮换/登出撤销）"""
from core.ratelimit import (
    check_register_rate,
    login_is_locked,
    record_login_failure,
    reset_login_failures,
)
from core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)
from db.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Request
from models.database import User
from models.schemas import TokenOut, UserCreate, UserLogin, UserOut
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/auth", tags=["认证"])


class RefreshIn(BaseModel):
    refresh_token: str


class LogoutIn(BaseModel):
    refresh_token: str = ""


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _issue_pair(db: Session, user: User) -> TokenOut:
    access = create_access_token({"sub": str(user.id)})
    refresh = create_refresh_token(db, user.id)
    return TokenOut(
        access_token=access,
        refresh_token=refresh,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut)
def register(data: UserCreate, request: Request, db: Session = Depends(get_db)):
    username = (data.username or "").strip()
    password = data.password or ""
    if len(username) < 2:
        raise HTTPException(status_code=400, detail="用户名至少 2 个字符")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    # 人机校验（阶段量级）：按 IP 限流；正式上线可换验证码
    check_register_rate(_client_ip(request))
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(password),
        nickname=data.nickname or username,
    )
    db.add(user)
    db.flush()
    pair = _issue_pair(db, user)
    db.commit()
    return pair


@router.post("/login", response_model=TokenOut)
def login(data: UserLogin, db: Session = Depends(get_db)):
    identity = (data.username or "").strip()
    if login_is_locked(identity):
        raise HTTPException(status_code=429, detail="尝试次数过多，账号已临时锁定，请稍后再试")
    user = db.query(User).filter(User.username == identity).first()
    if not user or not verify_password(data.password or "", user.password_hash):
        record_login_failure(identity)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    reset_login_failures(identity)
    pair = _issue_pair(db, user)
    db.commit()
    return pair


@router.post("/refresh", response_model=TokenOut)
def refresh(data: RefreshIn, db: Session = Depends(get_db)):
    rotated = rotate_refresh_token(db, data.refresh_token)
    if not rotated:
        raise HTTPException(status_code=401, detail="refresh token 无效或已过期")
    new_raw, user_id = rotated
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    db.commit()
    return TokenOut(
        access_token=create_access_token({"sub": str(user.id)}),
        refresh_token=new_raw,
        user=UserOut.model_validate(user),
    )


@router.post("/logout")
def logout(data: LogoutIn, db: Session = Depends(get_db)):
    if data.refresh_token:
        revoke_refresh_token(db, data.refresh_token)
        db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
