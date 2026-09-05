"""T-12：v1/v2 双引擎服务级行为对照（HTTP 在沙箱不可用，见测试头注释）"""
import pytest
import services.chat_engine as v1_svc
import services.chat_engine2 as v2_svc
from models.database import Conversation, Message, Persona, Scenario, User

_STAGES = [
    {"key": "greet", "label": "刚认识", "min_turns": 1, "objective": "热络", "advance_on": []},
    {"key": "trust", "label": "聊熟了", "min_turns": 1, "objective": "交心", "advance_on": []},
    {"key": "reveal", "label": "聊到家里", "min_turns": 99, "objective": "引茶",
     "advance_on": ["buy_intent"]},
    {"key": "pitch", "label": "轻推荐", "min_turns": 99, "objective": "推荐",
     "advance_on": ["buy_intent"]},
    {"key": "deal", "label": "收尾", "min_turns": 99, "objective": "收尾", "advance_on": []},
]


class _FakeLLM:
    async def generate(self, system, user):
        return "嗯嗯，是呀，我从小在外公茶园长大的～"


@pytest.fixture()
def pair(db, monkeypatch):
    monkeypatch.setattr(v1_svc, "build_llm", lambda: _FakeLLM())
    monkeypatch.setattr(v2_svc, "_default_build_llm", lambda: _FakeLLM())
    user = User(username="pair_u", password_hash="x")
    db.add(user)
    db.flush()
    sc = Scenario(slug="pair_sc", name="卖茶", goal="自然引出外公家的茶", stages=_STAGES)
    db.add(sc)
    db.flush()
    p = Persona(name="小雨", photo_assets=["/media/tea/photo1.png"],
                photo_policy={"mode": "friendly", "need_stage_keys": ["reveal", "pitch", "deal"],
                              "max_photos": 2, "caption_template": "看～"},
                scenario_id=sc.id)
    db.add(p)
    db.flush()
    c1 = Conversation(user_id=user.id, persona_id=p.id, scenario_id=sc.id, state={})
    c2 = Conversation(user_id=user.id, persona_id=p.id, scenario_id=sc.id, state={})
    db.add_all([c1, c2])
    db.commit()
    for c in (c1, c2):
        db.refresh(c)
    return db, user, c1, c2


async def _say(db, conv, text, engine):
    db.add(Message(conversation_id=conv.id, sender_type="user", content=text))
    db.commit()
    if engine == "v1":
        plans, trace = await v1_svc.process_message(conv.id, text, conv.user_id, db)
    else:
        plans, trace, state = await v2_svc.process_message2(conv.id, text, conv.user_id, db)
        conv.state = state
    for plan in plans:
        db.add(Message(conversation_id=conv.id, sender_type="ai",
                       content=plan["content"], content_type=plan["content_type"],
                       media_url=plan.get("media_url", "")))
    db.commit()
    db.refresh(conv)
    return conv.state


def _map(st):
    if "stage_idx" in st:
        return (st["stage_idx"], st["photos_sent"], st["red_packets"])
    return (st["stage"]["idx"], st["photos"]["sent"], st["economy"]["red_packets"])


@pytest.mark.asyncio
async def test_v1_v2_parity(pair):
    db, user, c1, c2 = pair
    messages = [
        "哈喽 加个好友",
        "发张照片看看嘛",
        "发张照片看看你长啥样",
        "你老家是种茶的呀？茶叶多少钱一斤",
    ]
    expected = [(1, 0, 0), (2, 0, 0), (2, 1, 0), (3, 1, 0)]
    for text, exp in zip(messages, expected, strict=False):
        s1 = _map(await _say(db, c1, text, "v1"))
        s2 = _map(await _say(db, c2, text, "v2"))
        assert s1 == s2, (text, s1, s2)
        assert s1 == exp, text

    # 照片在 reveal 放行：v1/v2 都应发过 image 消息
    assert c1.state["photos_sent"] == 1
    assert c2.state["photos"]["sent"] == 1


@pytest.mark.asyncio
async def test_v1_v2_rollback_new_conversation(pair):
    db, user, c1, c2 = pair
    await _say(db, c2, "哈喽", "v2")
    c3 = Conversation(user_id=user.id, persona_id=c1.persona_id,
                      scenario_id=c1.scenario_id, state={})
    db.add(c3)
    db.commit()
    db.refresh(c3)
    st = await _say(db, c3, "在吗", "v1")
    assert "stage_idx" in st  # v1 语义的扁平状态
