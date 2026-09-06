from types import SimpleNamespace

from _legacy.engine_v1.state import advance_stage, current_stage, default_state, stage_block_text


def scenario(stages):
    return SimpleNamespace(stages=stages, goal="目标")


STAGES = [
    {"key": "greet", "label": "刚认识", "min_turns": 2, "objective": "热络", "advance_on": []},
    {"key": "reveal", "label": "聊到家里", "min_turns": 5, "objective": "引茶", "advance_on": ["buy_intent"]},
    {"key": "deal", "label": "收尾", "min_turns": 0, "objective": "收尾", "advance_on": []},
]


def test_no_premature_advance():
    sc = scenario(STAGES)
    st = default_state()
    st["stage_turns"] = 1
    assert advance_stage(sc, st, {"buy_intent": True}) is False


def test_advance_by_turns():
    sc = scenario(STAGES)
    st = default_state()
    st["stage_turns"] = 2
    assert advance_stage(sc, st, {}) is True
    assert st["stage_idx"] == 1 and st["stage_turns"] == 0


def test_advance_on_event_only_when_configured():
    sc = scenario(STAGES)
    st = default_state()
    st["stage_idx"] = 1
    st["stage_turns"] = 20  # 有 advance_on 的阶段不再按轮次推进
    assert advance_stage(sc, st, {}) is False
    assert advance_stage(sc, st, {"buy_intent": True}) is True
    assert st["stage_idx"] == 2


def test_stage_current_and_text():
    sc = scenario(STAGES)
    st = default_state()
    cur = current_stage(sc, st)
    assert cur["key"] == "greet"
    assert "刚认识" in stage_block_text(sc, st)


def test_ends_at_last_stage():
    sc = scenario(STAGES)
    st = default_state()
    st["stage_idx"] = 2
    assert advance_stage(sc, st, {}) is False
