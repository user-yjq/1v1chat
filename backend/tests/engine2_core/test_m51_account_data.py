"""M5.1（R-B7 账号级收尾）：/api/me/data 导出与彻底删除的数据权边界。"""
from datetime import datetime

import pytest
from core.security import get_current_user
from fastapi import HTTPException
from models.database import (
    AuditLog,
    AuthToken,
    Conversation,
    Message,
    Persona,
    Scenario,
    User,
)
from routers.account import export_account_data, purge_account_data


def _mk_user(db, username: str, is_admin: bool = False) -> User:
    u = User(username=username, password_hash="x", nickname=username, is_admin=is_admin)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_persona(db, name: str = "小茶") -> Persona:
    sc = Scenario(slug=f"sc-{name}", name=f"{name}剧本", stages=[])
    db.add(sc)
    db.commit()
    p = Persona(name=name, scenario_id=sc.id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _mk_conv(db, user: User, persona: Persona | None = None,
             archived: bool = False, msgs: int = 1, with_internal: bool = False):
    conv = Conversation(
        user_id=user.id,
        persona_id=persona.id if persona else None,
        title="会话",
        state={"flags": {"user_illegal": 1}} if with_internal else {"stage": "greet"},
    )
    if archived:
        conv.status = "archived"
    db.add(conv)
    db.commit()
    db.refresh(conv)
    for i in range(msgs):
        db.add(Message(
            conversation_id=conv.id,
            sender_type="user" if i % 2 == 0 else "ai",
            content=f"内容{i}",
            content_type="text",
            agent_trace={"nodes": ["x"]} if with_internal else {},
        ))
    db.commit()
    db.refresh(conv)
    return conv


def _mk_token(db, user: User) -> AuthToken:
    t = AuthToken(user_id=user.id, token_hash=f"tok{user.id}", expires_at=datetime(2099, 1, 1))
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


# --- GET 导出：只含本人数据，最小化字段 -------------------------------- #
def test_account_export_aggregates_only_own_conversations(db):
    a = _mk_user(db, "alice")
    b = _mk_user(db, "bob")
    p = _mk_persona(db)
    c1 = _mk_conv(db, a, p, msgs=2, with_internal=True)
    c2 = _mk_conv(db, a, archived=True, msgs=1)
    _mk_conv(db, b, msgs=3)  # 他人数据不得出现在导出里

    out = export_account_data(db, a)
    assert out["account"]["username"] == "alice"
    assert out["exported_at"]
    convs = out["conversations"]
    assert {c["conversation"]["id"] for c in convs} == {c1.id, c2.id}
    assert "conversation" in convs[0] and "messages" in convs[0]
    # 归档会话也属于用户数据，一并导出
    assert any(c["conversation"]["id"] == c2.id for c in convs)


def test_account_export_excludes_internal_state_and_trace(db):
    a = _mk_user(db, "carol")
    _mk_conv(db, a, msgs=2, with_internal=True)
    out = export_account_data(db, a)
    for c in out["conversations"]:
        assert "state" not in c["conversation"]
        assert "agent_trace" not in c["conversation"]
        for m in c["messages"]:
            assert "agent_trace" not in m
            assert m["content"] in {"内容0", "内容1"}


# --- DELETE 彻底删除：账号与全部数据闭环 -------------------------------- #
def test_account_purge_removes_all_user_data_and_account(db):
    a = _mk_user(db, "dave", is_admin=True)
    b = _mk_user(db, "erin")
    p = _mk_persona(db)
    c1 = _mk_conv(db, a, p, msgs=2)
    c2 = _mk_conv(db, a, archived=True, msgs=1)
    _mk_token(db, a)
    AuditLog(admin_user_id=a.id, action="persona.update", object_type="persona",
             object_id=1, detail={})
    b_conv = _mk_conv(db, b, msgs=3)
    _mk_token(db, b)

    res = purge_account_data(db, a)
    assert res["ok"] is True
    assert res["deleted_conversations"] == 2
    assert res["deleted_messages"] == 3

    assert db.query(User).filter(User.id == a.id).count() == 0
    assert db.query(Conversation).filter(Conversation.user_id == a.id).count() == 0
    assert db.query(Message).filter(Message.conversation_id.in_([c1.id, c2.id])).count() == 0
    assert db.query(AuthToken).filter(AuthToken.user_id == a.id).count() == 0
    # 审计：原操作者引用置空 + 新增 account.purge 留痕（对象为数字 id，非 FK）
    actor_rows = db.query(AuditLog).filter(AuditLog.object_id == a.id).all()
    assert all(r.admin_user_id is None for r in actor_rows)
    assert any(r.action == "account.purge" for r in actor_rows)
    # 共享目录与旁人数据不受影响
    assert db.query(Persona).filter(Persona.id == p.id).count() == 1
    assert db.query(Scenario).count() == 1
    assert db.query(User).filter(User.id == b.id).count() == 1
    assert db.query(Conversation).filter(Conversation.id == b_conv.id).count() == 1
    assert db.query(Message).filter(Message.conversation_id == b_conv.id).count() == 3
    assert db.query(AuthToken).filter(AuthToken.user_id == b.id).count() == 1


# --- 路由与权限边界 ----------------------------------------------------- #
def test_account_data_routes_registered():
    from main import app

    def has_route(path: str, method: str) -> bool:
        return any(getattr(r, "path", "") == path and method in (r.methods or set())
                   for r in app.routes)

    assert has_route("/api/me/data", "GET")
    assert has_route("/api/me/data", "DELETE")


def test_account_endpoints_require_auth(db):
    with pytest.raises(HTTPException) as exc:
        get_current_user(None, db)
    assert exc.value.status_code == 401
