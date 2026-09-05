"""T-08：记忆抽取、隐私忽略、上限"""
from types import SimpleNamespace

import pytest
from engine2.nodes.memory import extract_facts, memory
from engine2.schema import TurnContext, default_state_v2


def test_extract_facts_basic():
    facts = extract_facts("我在北京上班，养了一只猫")
    assert facts.get("work_city") == "北京"
    assert facts.get("pet") == "猫"


def test_extract_facts_ignores_sensitive():
    assert extract_facts("我电话13800000000，住在朝阳区") == {}
    assert extract_facts("我手机号是138，家里住xx路") == {}


@pytest.mark.asyncio
async def test_memory_node_merges_and_caps():
    state = default_state_v2("s")
    state["facts"] = {f"old{i}": "v" for i in range(19)}
    ctx = TurnContext(
        conversation_id=1, user_id=1, persona=None, scenario=None,
        user_message="我在上海工作，养了条狗",
        state=state,
        config=SimpleNamespace(state_facts_max=20),
        scratch={"analysis": {"memory": [{"attr": "job", "value": "设计师"}]}},
    )
    patch = await memory(ctx)
    assert patch["facts"].get("work_city") == "上海"
    assert patch["facts"]["job"] == "设计师"
    assert len(patch["facts"]) == 20
    assert "old0" not in patch["facts"]
