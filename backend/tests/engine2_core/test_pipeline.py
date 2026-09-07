"""T-04/T-11：薄管线端到端（mock，无 DB）"""
from types import SimpleNamespace

import pytest
from engine2.pipeline import run_turn
from engine2.schema import TurnContext, default_state_v2
from llm.provider import LLMCircuitOpenError


class _FakeLLM:
    async def generate(self, system, user):
        return "嗯嗯，我也这么觉得，你呢？"


def _persona():
    return SimpleNamespace(
        name="桃桃", age=23, gender="女", city="成都", occupation="奶茶店兼职",
        personality="自来熟", speaking_style="短句多", bio="",
        redlines=["不暴露AI"], photo_assets=["/media/life/photo1.jpg"],
        photo_policy={"mode": "instant", "max_photos": 3, "caption_template": "看～"},
    )


def _ctx(message, persona=None):
    return TurnContext(
        conversation_id=7, user_id=1, persona=persona, scenario=None,
        user_message=message, state=default_state_v2("free_chat"),
        llm=_FakeLLM(),
        config=SimpleNamespace(turn_timeout_s=5, guard_enabled=True, state_facts_max=20),
    )


class _RaisingLLM(_FakeLLM):
    async def generate(self, system, user):
        raise LLMCircuitOpenError("upstream open")


@pytest.mark.asyncio
async def test_pipeline_llm_circuit_open_falls_back():
    """R-A2：熔断异常在 actor 边界被吞掉 → 本轮自动走降级话术（不暴露 AI、不 500）。"""
    ctx = _ctx("你在干嘛呢")
    ctx.llm = _RaisingLLM()
    state, actions, trace = await run_turn(ctx)
    act_node = next(n for n in trace["nodes"] if n["name"] == "act")
    assert act_node["ok"] is True  # actor 内部已捕获 LLM 异常，节点不视为失败
    assert len(actions) == 1 and actions[0]["kind"] == "reply_text"
    from engine2.defaults import FALLBACK_LINES, pick_fallback
    assert actions[0]["content"] in FALLBACK_LINES or actions[0]["content"] == pick_fallback(ctx.user_message)


@pytest.mark.asyncio
async def test_pipeline_casual_turn():
    ctx = _ctx("哈哈哈今天摸鱼一天")
    state, actions, trace = await run_turn(ctx)
    assert any(a["kind"] == "reply_text" for a in actions)
    assert trace["engine"] == "engine2"
    assert trace["llm_calls"] >= 1
    assert state["stage"]["turns"] == 1
    assert trace["decisions"]["tactic"] in ("casual",)


@pytest.mark.asyncio
async def test_pipeline_photo_send_skips_llm():
    ctx = _ctx("发张照片看看嘛", persona=_persona())
    state, actions, trace = await run_turn(ctx)
    photo_actions = [a for a in actions if a["kind"] == "send_photo"]
    assert photo_actions and photo_actions[0]["media_url"] == "/media/life/photo1.jpg"
    assert trace["decisions"]["photo"] == "send"
    assert state["photos"]["sent"] == 1


@pytest.mark.asyncio
async def test_pipeline_remember_and_stage_turns():
    ctx = _ctx("我在北京上班，养了一只猫")
    state, actions, trace = await run_turn(ctx)
    assert state["facts"].get("work_city") == "北京"
    assert state["facts"].get("pet") == "猫"
    assert state["stage"]["turns"] == 1
