"""M4.8（R-B5）：消息联合索引 + 游标分页（无重复/无缺口、越权 404、limit 收敛）。"""
import pytest
from fastapi import HTTPException
from models.database import Conversation, Message, User
from routers.conversation import get_messages, page_messages
from sqlalchemy import inspect


def _seed(db, n=20, username="owner48"):
    u = User(username=username, password_hash="x", nickname=username)
    db.add(u)
    db.flush()
    conv = Conversation(user_id=u.id, title="长对话", state={})
    db.add(conv)
    db.commit()
    for i in range(1, n + 1):
        db.add(Message(conversation_id=conv.id, sender_type="user" if i % 2 else "ai",
                       content=f"消息{i}", content_type="text"))
    db.commit()
    return u, conv


def _ids(rows):
    return [m.id for m in rows]


def test_messages_composite_index_created(db):
    u, conv = _seed(db)
    idxs = {ix["name"]: set(ix["column_names"])
            for ix in inspect(db.get_bind()).get_indexes("messages")}
    assert "ix_messages_conversation_sent_at" in idxs
    assert idxs["ix_messages_conversation_sent_at"] == {"conversation_id", "sent_at"}


def test_default_returns_latest_asc(db):
    _u, conv = _seed(db, n=20)
    rows = page_messages(db, conv.id, limit=5)
    assert _ids(rows) == [16, 17, 18, 19, 20]


def test_cursor_pages_cover_all_without_gap(db):
    _u, conv = _seed(db, n=100)
    tail = page_messages(db, conv.id, limit=40)
    head = page_messages(db, conv.id, limit=60, before_id=tail[0].id)
    all_ids = _ids(head) + _ids(tail)
    assert all_ids == list(range(1, 101))


def test_illegal_cursor_raises_404(db):
    _u, conv = _seed(db)
    with pytest.raises(HTTPException) as exc:
        page_messages(db, conv.id, before_id=99999)
    assert exc.value.status_code == 404


def test_limit_is_clamped(db):
    _u, conv = _seed(db, n=600)
    rows = page_messages(db, conv.id, limit=99999)
    assert len(rows) == 500


def test_route_owner_boundary_preserved(db):
    owner, conv = _seed(db)
    other = User(username="other48", password_hash="x")
    db.add(other)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        get_messages(conv.id, 50, None, db, other)
    assert exc.value.status_code == 404
