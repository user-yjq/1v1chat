"""M4.6（R-C2/C3/C5/C6）：登录防爆破、refresh 轮换/撤销、审计、admin 引导。"""
import hashlib
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from config import settings
from core import ratelimit
from core.admin_bootstrap import _create_admin_if_empty
from core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    revoke_refresh_token,
    rotate_refresh_token,
)
from fastapi import HTTPException
from models.database import AuditLog, AuthToken, User
from models.schemas import UserCreate, UserLogin
from routers import auth as auth_router
from routers.admin import admin_list_audit, record_admin_audit


def _mk_user(db, name: str = "u1") -> User:
    user = User(username=name, password_hash="x", nickname=name)
    db.add(user)
    db.flush()
    return user


def _sha(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# --- R-C3 refresh 轮换/撤销 ------------------------------------------------ #
def test_access_token_carries_short_lived_access_type():
    import time

    from jose import jwt

    token = create_access_token({"sub": "1"})
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    assert payload["type"] == "access"
    remaining = int(payload["exp"]) - int(time.time())
    assert 0 < remaining <= settings.ACCESS_TOKEN_MINUTES * 60 + 5


def test_refresh_rotate_revokes_old_and_blocks_reuse(db):
    user = _mk_user(db)
    raw = create_refresh_token(db, user.id)
    db.commit()
    row = db.query(AuthToken).filter_by(user_id=user.id).first()
    assert row and not row.revoked

    new_raw, user_id = rotate_refresh_token(db, raw)
    db.commit()
    assert user_id == user.id
    old = db.query(AuthToken).filter(AuthToken.token_hash == _sha(raw)).first()
    assert old.revoked is True
    assert rotate_refresh_token(db, raw) is None  # 旧 token 复用被拒

    assert revoke_refresh_token(db, new_raw) is True
    db.commit()
    assert rotate_refresh_token(db, new_raw) is None  # 登出后新 token 失效


def test_refresh_expired_rejected(db):
    user = _mk_user(db)
    raw = create_refresh_token(db, user.id)
    token = db.query(AuthToken).filter(AuthToken.token_hash == _sha(raw)).first()
    token.expires_at = datetime.utcnow() - timedelta(minutes=1)
    db.commit()
    assert rotate_refresh_token(db, raw) is None


# --- R-C2 登录防爆破 ------------------------------------------------------- #
def test_login_lock_helpers(monkeypatch):
    ratelimit.reset()
    monkeypatch.setattr(settings, "LOGIN_FAIL_LIMIT", 3)
    monkeypatch.setattr(settings, "LOGIN_LOCK_MINUTES", 15)
    for _ in range(3):
        ratelimit.record_login_failure("alice")
    assert ratelimit.login_is_locked("alice") is True
    ratelimit.reset_login_failures("alice")
    assert ratelimit.login_is_locked("alice") is False


def test_login_route_locks_after_failures(db, monkeypatch):
    monkeypatch.setattr(settings, "LOGIN_FAIL_LIMIT", 3)
    user = User(username="tester", password_hash=hash_password("pw123456"), nickname="tester")
    db.add(user)
    db.commit()
    for _ in range(3):
        with pytest.raises(HTTPException) as exc:
            auth_router.login(UserLogin(username="tester", password="wrong-pass"), db)
        assert exc.value.status_code == 401
    with pytest.raises(HTTPException) as exc:
        auth_router.login(UserLogin(username="tester", password="pw123456"), db)
    assert exc.value.status_code == 429
    ratelimit.reset_login_failures("tester")


def test_register_rejects_short_credentials(db):
    request = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
    with pytest.raises(HTTPException) as exc:
        auth_router.register(UserCreate(username="a", password="123456"), request, db)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        auth_router.register(UserCreate(username="okname", password="123"), request, db)
    assert exc.value.status_code == 400


# --- R-C5 审计 ------------------------------------------------------------- #
def test_admin_audit_record_and_list(db):
    admin = _mk_user(db, "boss")
    admin.is_admin = True
    db.flush()
    record_admin_audit(db, admin, "persona.create", "persona", 1,
                       after={"name": "小雅"})
    db.commit()

    rows = db.query(AuditLog).all()
    assert len(rows) == 1
    assert rows[0].action == "persona.create"
    assert rows[0].detail.get("after", {}).get("name") == "小雅"

    out = admin_list_audit(10, db, admin)
    assert out[0]["admin_username"] == "boss"
    assert out[0]["object_type"] == "persona"


# --- R-C6 admin 引导（仅空表） --------------------------------------------- #
def test_bootstrap_admin_only_on_empty_table(db, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_USERNAME", "rootadmin")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_PASSWORD", "secret-123")
    _create_admin_if_empty(db)
    admins = db.query(User).filter(User.username == "rootadmin").all()
    assert len(admins) == 1
    assert admins[0].is_admin is True

    _create_admin_if_empty(db)  # 表已非空：跳过
    assert db.query(User).filter(User.username == "rootadmin").count() == 1


def test_bootstrap_skipped_without_env(db, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_USERNAME", "")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_PASSWORD", "")
    _create_admin_if_empty(db)
    assert db.query(User).count() == 0
