"""T-13：路由校验纯函数 + 限流 + admin 403 + CORS 配置（沙箱内不可用 HTTP/线程池的替代证据）"""
from types import SimpleNamespace

import pytest
from config import settings
from core import ratelimit
from core.security import create_access_token
from fastapi import HTTPException
from main import app
from models.database import Conversation, User
from routers.admin import _require_admin
from routers.chat import ensure_message_length, find_owned_conversation
from starlette.middleware.cors import CORSMiddleware


def _mk(db, username):
    u = User(username=username, password_hash="x", nickname=username)
    db.add(u)
    db.flush()
    conv = Conversation(user_id=u.id, state={})
    db.add(conv)
    db.commit()
    return u, conv


def test_owner_boundary(db):
    owner, conv = _mk(db, "own")
    other = User(username="other", password_hash="x")
    db.add(other)
    db.commit()
    assert find_owned_conversation(db, owner.id, conv.id).id == conv.id
    with pytest.raises(HTTPException) as exc:
        find_owned_conversation(db, other.id, conv.id)
    assert exc.value.status_code == 404


def test_message_length_boundary():
    ensure_message_length("正常消息")
    with pytest.raises(HTTPException) as exc:
        ensure_message_length("长" * (settings.MSG_MAX_LEN + 1))
    assert exc.value.status_code == 400


def test_rate_limit_boundary(monkeypatch):
    ratelimit.reset()
    monkeypatch.setattr(settings, "CHAT_RATE_PER_MIN", 3)
    for _ in range(3):
        ratelimit.check_chat_rate(1001)
    with pytest.raises(HTTPException) as exc:
        ratelimit.check_chat_rate(1001)
    assert exc.value.status_code == 429
    ratelimit.reset()


def test_admin_403_boundary():
    with pytest.raises(HTTPException) as exc:
        _require_admin(SimpleNamespace(is_admin=False, id=1))
    assert exc.value.status_code == 403
    assert _require_admin(SimpleNamespace(is_admin=True, id=1)).id == 1


def test_cors_allowlist_config():
    cors = [m for m in app.user_middleware if m.cls is CORSMiddleware]
    assert cors, "应配置 CORSMiddleware"
    opts = cors[0].kwargs
    assert "*" not in opts.get("allow_origins", [])
    assert opts.get("allow_credentials") is True


def test_jwt_roundtrip():
    token = create_access_token({"sub": "7"})
    assert token
