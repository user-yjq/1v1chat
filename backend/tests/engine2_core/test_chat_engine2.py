"""T-11：chat_engine2 卖茶剧本走查（mock，内存库，不落状态）"""
import pytest
import services.chat_engine2 as engine2_svc
from engine2.schema import validate_state
from models.database import Conversation, Message, Persona, Scenario, User


class _FakeLLM:
    async def generate(self, system, user):
        return "嗯嗯，是呀，我从小在外公茶园长大的～"


STAGES = [
    {"key": "greet", "label": "刚认识", "min_turns": 1, "objective": "热络", "advance_on": []},
    {"key": "trust", "label": "聊熟了", "min_turns": 1, "objective": "交心", "advance_on": []},
    {"key": "reveal", "label": "聊到家里", "min_turns": 99, "objective": "引茶", "advance_on": ["buy_intent"]},
    {"key": "pitch", "label": "轻推荐", "min_turns": 99, "objective": "推荐", "advance_on": ["buy_intent"]},
    {"key": "deal", "label": "收尾", "min_turns": 99, "objective": "收尾", "advance_on": []},
]


@pytest.fixture()
def tea_conv(db):
    user = User(username="tea2", password_hash="x")
    db.add(user)
    db.flush()
    sc = Scenario(slug="tea_walk2", name="卖茶", goal="自然引出外公家的茶", stages=STAGES)
    db.add(sc)
    db.flush()
    p = Persona(name="小雨", photo_assets=["/media/tea/photo1.png"],
                photo_policy={"mode": "friendly", "need_stage_keys": ["reveal", "pitch", "deal"],
                              "max_photos": 2, "caption_template": "看～"},
                scenario_id=sc.id)
    db.add(p)
    db.flush()
    conv = Conversation(user_id=user.id, persona_id=p.id, scenario_id=sc.id, state={})
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return db, user, conv


async def _say(db, conv, user, text, monkeypatch):
    db.add(Message(conversation_id=conv.id, sender_type="user", content=text))
    db.commit()
    monkeypatch.setattr(engine2_svc, "_default_build_llm", lambda: _FakeLLM())
    plans, trace, state = await engine2_svc.process_message2(conv.id, text, user.id, db)
    validate_state(state)
    for plan in plans:
        db.add(Message(conversation_id=conv.id, sender_type="ai", content=plan["content"],
                       content_type=plan["content_type"], media_url=plan.get("media_url", "")))
    conv.state = state
    db.commit()
    db.refresh(conv)
    return plans, trace, state


@pytest.mark.asyncio
async def test_tea_walkthrough_engine2(tea_conv, monkeypatch):
    db, user, conv = tea_conv

    _, _, st = await _say(db, conv, user, "哈喽 加个好友", monkeypatch)
    assert st["stage"]["idx"] == 1  # greet(min1) → trust

    # trust 阶段要照片：谈判基于推进前阶段（trust），应拒绝且不推进到 reveal
    plans, _, st = await _say(db, conv, user, "发张照片看看嘛", monkeypatch)
    assert st["photos"]["sent"] == 0
    assert st["stage"]["idx"] == 2  # 该轮到达 trust 且满足 min1 → 推进到 reveal
    assert st["stage"]["turns"] == 0

    # reveal 阶段闲聊几轮不会推进（min_turns=99 + advance_on=buy_intent）
    for _ in range(3):
        _, _, st = await _say(db, conv, user, "感觉你这人挺真的，哈哈哈哈", monkeypatch)
    assert st["stage"]["idx"] == 2

    # reveal 阶段再要照片：放行发图
    plans, _, st = await _say(db, conv, user, "发张照片看看你长啥样", monkeypatch)
    assert st["photos"]["sent"] == 1
    assert any(p["content_type"] == "image" for p in plans)

    # 主动问价 → buy_intent 让 reveal 推进到 pitch
    _, _, st = await _say(db, conv, user, "你老家是种茶的呀？茶叶多少钱一斤", monkeypatch)
    assert st["stage"]["idx"] == 3

    # 表达想买 → pitch 推进到 deal
    _, _, st = await _say(db, conv, user, "那我想买半斤尝尝，怎么弄", monkeypatch)
    assert st["stage"]["idx"] == 4


@pytest.mark.asyncio
async def test_engine2_owner_and_message_limit(db, monkeypatch):
    user_a = User(username="a2", password_hash="x")
    user_b = User(username="b2", password_hash="x")
    db.add_all([user_a, user_b])
    db.flush()
    conv = Conversation(user_id=user_a.id, state={})
    db.add(conv)
    db.commit()
    monkeypatch.setattr(engine2_svc, "_default_build_llm", lambda: _FakeLLM())
    with pytest.raises(engine2_svc.Engine2Error):
        await engine2_svc.process_message2(conv.id, "你好", user_b.id, db)
    with pytest.raises(engine2_svc.Engine2Error):
        await engine2_svc.process_message2(conv.id, "长" * 3000, user_a.id, db)
