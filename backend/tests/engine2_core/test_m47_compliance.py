"""M4.7（R-F1/F2/F3 + R-B7）：合规 flags 记录、披露 meta、数据导出/彻底删除。"""
from types import SimpleNamespace

import pytest
from engine2 import compliance
from engine2.pipeline import run_turn
from engine2.schema import TurnContext, default_state_v2
from fastapi import HTTPException
from main import app_meta
from models.database import Conversation, Message, User
from routers.admin import admin_list_compliance
from routers.conversation import delete_conversation, export_conversation, purge_conversation


class _FakeLLM:
    async def generate(self, system, user):
        return "嗯嗯，我懂你的意思，慢慢聊嘛"


def _ctx(message: str, persona=None):
    return TurnContext(
        conversation_id=7, user_id=1, persona=persona, scenario=None,
        user_message=message, state=default_state_v2("free_chat"),
        llm=_FakeLLM(),
        config=SimpleNamespace(
            turn_timeout_s=5, guard_enabled=True, state_facts_max=20,
            compliance_enabled=True,
        ),
    )


# --- R-F2 确定性合规扫描 ------------------------------------------------ #
def test_scan_user_categories():
    assert compliance.scan_user_text("帮我找个赌博平台，帮我把钱洗出来") == ["user_illegal"]
    assert compliance.scan_user_text("我身份证号是110101199001011234，帮我保管下") == ["user_pii_leak"]
    assert compliance.scan_user_text("你今天忙不忙，要不要一起喝个茶") == []


def test_scan_ai_categories():
    assert "ai_fraud_pitch" in compliance.scan_ai_text(
        "加我QQ 123456 下载这个APP注册，返利稳赚不赔，先把钱转到这个银行卡")
    assert "ai_pii_collect" in compliance.scan_ai_text(
        "把你身份证号、银行卡号和短信验证码发我一下，我帮你实名")
    assert compliance.scan_ai_text("今天天气不错，新到的茶叶要不要尝尝") == []


def test_merge_flags_accumulates_counts():
    flags = compliance.merge_flags({"user_illegal": 2}, ["user_illegal", "user_pii_leak"])
    assert flags == {"user_illegal": 3, "user_pii_leak": 1}
    assert compliance.merge_flags({"user_illegal": 1}, ["casual", "unknown"]) == {"user_illegal": 1}


# --- R-F2 管线落 flags + trace ------------------------------------------ #
@pytest.mark.asyncio
async def test_pipeline_compliance_writes_flags_and_trace():
    state, _actions, trace = await run_turn(_ctx("手头有点紧，帮我想个洗钱的办法呗"))
    assert state["flags"].get("user_illegal", 0) >= 1
    assert "user_illegal" in (trace.get("compliance") or {}).get("user", [])


@pytest.mark.asyncio
async def test_pipeline_compliance_increments_across_turns():
    ctx = _ctx("手头有点紧，帮我想个洗钱的办法呗")
    state, _a, _t = await run_turn(ctx)
    assert state["flags"]["user_illegal"] == 1
    ctx.state = state
    ctx.scratch = {}
    state2, _a2, _t2 = await run_turn(ctx)
    assert state2["flags"]["user_illegal"] == 2


@pytest.mark.asyncio
async def test_pipeline_compliance_disabled_keeps_flags_empty():
    ctx = _ctx("手头有点紧，帮我想个洗钱的办法呗")
    ctx.config = SimpleNamespace(
        turn_timeout_s=5, guard_enabled=True, state_facts_max=20,
        compliance_enabled=False,
    )
    state, _actions, trace = await run_turn(ctx)
    assert state["flags"] == {}
    assert trace.get("compliance") is None


# --- R-F1/R-F3 披露 meta ------------------------------------------------- #
def test_app_meta_disclosure():
    meta = app_meta()
    assert "disclosure" in meta
    assert meta["disclosure"]["enabled"] is True
    assert "AI" in meta["disclosure"]["text"]


# --- R-B7 数据导出 / 彻底删除 -------------------------------------------- #
def _mk_conv(db):
    u = User(username="owner1", password_hash="x", nickname="owner1")
    db.add(u)
    db.flush()
    conv = Conversation(user_id=u.id, title="卖茶聊天", state={})
    db.add(conv)
    db.commit()
    for i, sender in enumerate(["user", "ai"]):
        db.add(Message(conversation_id=conv.id, sender_type=sender,
                       content=f"内容{i}", content_type="text"))
    db.commit()
    return u, conv


def test_export_conversation_json(db):
    owner, conv = _mk_conv(db)
    other = User(username="other1", password_hash="x")
    db.add(other)
    db.commit()
    out = export_conversation(conv.id, db, owner)
    assert out["conversation"]["id"] == conv.id
    assert len(out["messages"]) == 2
    assert out["messages"][0]["sender_type"] == "user"
    with pytest.raises(HTTPException) as exc:
        export_conversation(conv.id, db, other)
    assert exc.value.status_code == 404


def test_purge_removes_messages_and_conversation(db):
    owner, conv = _mk_conv(db)
    result = purge_conversation(conv.id, db, owner)
    assert result["ok"] is True
    assert result["deleted_messages"] == 2
    assert db.query(Conversation).filter(Conversation.id == conv.id).count() == 0
    assert db.query(Message).filter(Message.conversation_id == conv.id).count() == 0


def test_soft_delete_still_archives_not_purge(db):
    owner, conv = _mk_conv(db)
    assert delete_conversation(conv.id, db, owner)["ok"] is True
    conv = db.query(Conversation).filter(Conversation.id == conv.id).first()
    assert conv is not None and conv.status == "archived"
    assert db.query(Message).filter(Message.conversation_id == conv.id).count() == 2


# --- R-F2 admin 合规可见 -------------------------------------------------- #
def test_admin_compliance_lists_only_flagged(db):
    u = User(username="uowner", password_hash="x", is_admin=True)
    db.add(u)
    db.flush()
    clean = Conversation(user_id=u.id, state={"flags": {}}, title="普通")
    flagged = Conversation(user_id=u.id, state={"flags": {"user_illegal": 2}}, title="异常")
    db.add_all([clean, flagged])
    db.commit()
    rows = admin_list_compliance(50, db, u)
    ids = [r["id"] for r in rows]
    assert flagged.id in ids and clean.id not in ids
    assert rows[0]["flags"]["user_illegal"] == 2
