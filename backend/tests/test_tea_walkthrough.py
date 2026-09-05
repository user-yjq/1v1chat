"""卖茶剧本全流程走查：从加好友到 buy_intent 推进到成交，照片只在 reveal 之后发出"""
import pytest
import services.chat_engine as engine_mod
from models.database import Conversation, Message, Persona, Scenario, User


class FakeLLM:
    async def generate(self, system: str, user: str) -> str:
        return "嗯嗯，是呀，我从小在外公茶园长大的～"


STAGES = [
    {"key": "greet", "label": "刚认识", "min_turns": 1, "objective": "热络", "advance_on": []},
    {"key": "trust", "label": "聊熟了", "min_turns": 1, "objective": "交心", "advance_on": []},
    {"key": "reveal", "label": "聊到家里", "min_turns": 8, "objective": "引茶", "advance_on": ["buy_intent"]},
    {"key": "pitch", "label": "轻推荐", "min_turns": 99, "objective": "推荐", "advance_on": ["buy_intent"]},
    {"key": "deal", "label": "收尾", "min_turns": 0, "objective": "收尾", "advance_on": []},
]


@pytest.fixture()
def tea_conv(db):
    user = User(username="tea_u", password_hash="x")
    db.add(user)
    db.flush()
    sc = Scenario(slug="tea_walk", name="卖茶", goal="自然引出外公家的茶", stages=STAGES)
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


async def say(db, conv, user, text, monkeypatch):
    db.add(Message(conversation_id=conv.id, sender_type="user", content=text))
    db.commit()
    monkeypatch.setattr(engine_mod, "build_llm", lambda: FakeLLM())
    plans, trace = await engine_mod.process_message(conv.id, text, user.id, db)
    for plan in plans:
        db.add(Message(conversation_id=conv.id, sender_type="ai", content=plan["content"],
                       content_type=plan["content_type"], media_url=plan.get("media_url", "")))
    db.commit()
    db.refresh(conv)
    return plans


@pytest.mark.asyncio
async def test_tea_walkthrough(tea_conv, monkeypatch):
    db, user, conv = tea_conv

    await say(db=db, conv=conv, user=user, text="哈喽 加个好友", monkeypatch=monkeypatch)
    assert conv.state["stage_idx"] == 1  # 第一条闲聊把 greet(min1) 推到 trust

    # trust 阶段要照片：friendly 未到 reveal，应嘴甜拒绝（这条消息同时把 trust 推到 reveal）
    await say(db=db, conv=conv, user=user, text="发张照片看看嘛", monkeypatch=monkeypatch)
    assert conv.state["stage_idx"] == 2
    assert conv.state["photos_sent"] == 0

    # reveal 阶段闲聊几轮（min_turns=8 不会自动往前跳）
    await say(db=db, conv=conv, user=user, text="感觉你这人挺真的，哈哈哈哈", monkeypatch=monkeypatch)
    assert conv.state["stage_idx"] == 2

    # reveal 阶段再要照片：friendly 放行发图
    await say(db=db, conv=conv, user=user, text="发张照片看看你长啥样", monkeypatch=monkeypatch)
    assert conv.state["photos_sent"] == 1

    # 主动问价 → buy_intent 让 reveal 推到 pitch
    await say(db=db, conv=conv, user=user, text="你老家是种茶的呀？茶叶多少钱一斤", monkeypatch=monkeypatch)
    assert conv.state["stage_idx"] == 3

    # 表达想买 → pitch 推到 deal
    await say(db=db, conv=conv, user=user, text="那我想买半斤尝尝，怎么弄", monkeypatch=monkeypatch)
    assert conv.state["stage_idx"] == 4

    st = conv.state
    assert st["photos_sent"] == 1 and st["red_packets"] == 0
