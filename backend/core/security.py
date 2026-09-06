"""认证 / 安全工具（bcrypt 原生 + JWT）"""
import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
from config import settings
from db.database import get_db
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from models.database import AuthToken, User
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    to_encode.update({"type": "access", "exp": datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_MINUTES))})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌") from None


# --- refresh token（M4.6 R-C3：可撤销，DB 只存 sha256）------------------------ #
def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_refresh_token(db: Session, user_id: int) -> str:
    """签发一条 refresh token 并落库（未 commit，由路由统一提交）。"""
    raw = secrets.token_urlsafe(48)
    db.add(AuthToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
    ))
    db.flush()
    return raw


def _find_refresh_token(db: Session, raw: str) -> AuthToken | None:
    if not raw:
        return None
    return db.query(AuthToken).filter(AuthToken.token_hash == _hash_token(raw)).first()


def rotate_refresh_token(db: Session, raw: str) -> tuple[str, int] | None:
    """刷新轮换：旧 token 标记 revoked；返回 (新 token, user_id)；无效/已撤销/过期返回 None。"""
    token = _find_refresh_token(db, raw)
    if not token or token.revoked or token.expires_at <= datetime.utcnow():
        return None
    token.revoked = True
    token.last_used_at = datetime.utcnow()
    new_raw = create_refresh_token(db, token.user_id)
    return new_raw, token.user_id


def revoke_refresh_token(db: Session, raw: str) -> bool:
    """登出撤销；幂等（找不到也返回 True 语义=已不可用）。"""
    token = _find_refresh_token(db, raw)
    if not token or token.revoked:
        return False
    token.revoked = True
    token.last_used_at = datetime.utcnow()
    return True


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效令牌")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")
    return user
