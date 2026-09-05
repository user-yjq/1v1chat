"""引擎端到端（离线）：事件/照片策略/状态推进 在 process_message 内确定性地发生"""
import pytest
import services.chat_engine as engine_mod
from models.database import Conversation, Message, Persona, Scenario, User


class FakeLLM:
    def __init__(self, text: str):
        self.text = text

    async def generate(self, system: str, user: str) -> str:
        return self.text


def make_persona(db, mode: str = "instant", stages=None):
    user = User(username="u1", password_hash="x")
    db.add(user)
    db.flush()
    sc = Scenario(
        slug="s1", name="剧本", goal="目标", stages=stages or
        [{"key": "free", "label": "闲聊", "min_turns": 9999, "objective": "闲聊", "advance_on": []}],
    )
    db.add(sc)
    db.flush()
    policy = {"mode": mode, "max_photos": 3,
              "need_stage_keys": ["reveal"], "caption_template": "看～"}
    p = Persona(name="测试", photo_assets=["/media/1.png", "/media/2.png"],
                photo_policy=policy, scenario_id=sc.id)
    db.add(p)
    db.flush()
    conv = Conversation(user_id=user.id, persona_id=p.id, scenario_id=sc.id, state={})
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return user, conv, p


async def send(db, conv, user, text, monkeypatch, reply="哈喽呀，在的呢～"):
    db.add(Message(conversation_id=conv.id, sender_type="user", content=text))
    db.commit()
    monkeypatch.setattr(engine_mod, "build_llm", lambda: FakeLLM(reply))
    ai_plans, trace = await engine_mod.process_message(conv.id, text, user.id, db)
    for plan in ai_plans:
        db.add(Message(conversation_id=conv.id, sender_type="ai",
                       content=plan["content"], content_type=plan["content_type"],
                       media_url=plan.get("media_url", "")))
    db.commit()
    db.refresh(conv)
    return ai_plans, trace


@pytest.mark.asyncio
async def test_instant_photo_on_request(db, monkeypatch):
    user, conv, _ = make_persona(db, "instant")
    ai, trace = await send(db, conv, user, "发张照片看看", monkeypatch)
    assert ai[0]["content_type"] == "image"
    assert ai[0]["media_url"].startswith("/media/")
    assert conv.state["photos_sent"] == 1
    assert trace["photo_action"] == "send"


@pytest.mark.asyncio
async def test_friendly_refuses_before_reveal_stage(db, monkeypatch):
    user, conv, _ = make_persona(db, "friendly")
    ai, trace = await send(db, conv, user, "发张照片看看嘛", monkeypatch)
    assert ai[0]["content_type"] == "text"   # 未到 reveal，嘴甜拒绝
    assert conv.state["photos_sent"] == 0
    assert trace["photo_action"] == "refuse"


@pytest.mark.asyncio
async def test_friendly_sends_after_reveal_stage(db, monkeypatch):
    stages = [
        {"key": "greet", "label": "认识", "min_turns": 1, "objective": "热络", "advance_on": []},
        {"key": "reveal", "label": "熟了", "min_turns": 5, "objective": "可发照片", "advance_on": []},
    ]
    user, conv, _ = make_persona(db, "friendly", stages)
    await send(db, conv, user, "嗨，你好呀", monkeypatch)   # 推进到 reveal
    assert conv.state["stage_idx"] == 1
    ai, _ = await send(db, conv, user, "发张照片看看嘛", monkeypatch)
    assert ai[0]["content_type"] == "image"
    assert conv.state["photos_sent"] == 1


@pytest.mark.asyncio
async def test_red_packet_unlock_photo(db, monkeypatch):
    user, conv, _ = make_persona(db, "red_packet")
    ai, _ = await send(db, conv, user, "发张照片呗", monkeypatch)
    assert ai[0]["content_type"] == "text"          # 没红包先吊着
    assert conv.state["photos_sent"] == 0
    ai, _ = await send(db, conv, user, "给你发了红包，收下呀", monkeypatch)
    assert ai[0]["content_type"] == "image"         # 红包解锁
    assert conv.state["red_packets"] == 1
    assert conv.state["photos_sent"] == 1


@pytest.mark.asyncio
async def test_buy_event_advances_tea_stage(db, monkeypatch):
    stages = [
        {"key": "greet", "label": "认识", "min_turns": 1, "objective": "热络", "advance_on": []},
        {"key": "reveal", "label": "引茶", "min_turns": 5, "objective": "聊家", "advance_on": ["buy_intent"]},
        {"key": "deal", "label": "成交", "min_turns": 0, "objective": "收尾", "advance_on": []},
    ]
    user, conv, _ = make_persona(db, "instant", stages)
    await send(db, conv, user, "你好呀", monkeypatch)
    assert conv.state["stage_idx"] == 1
    ai, _ = await send(db, conv, user, "你家这个茶叶多少钱一斤？", monkeypatch)
    assert conv.state["stage_idx"] == 2            # buy_intent 推进到 deal
    assert ai[0]["content_type"] == "text"


@pytest.mark.asyncio
async def test_doubt_ai_still_generates_text(db, monkeypatch):
    user, conv, _ = make_persona(db, "instant")
    ai, _ = await send(db, conv, user, "你是机器人吧", monkeypatch)
    assert ai[0]["content_type"] == "text"
    assert ai[0]["content"] == "哈喽呀，在的呢～"
    assert conv.state["doubts_raised"] == 1
