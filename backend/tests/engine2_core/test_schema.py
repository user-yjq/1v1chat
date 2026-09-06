"""T-02 schema：状态 v2 / 分析输出 / patch 合并"""
import pytest
from engine2.errors import Engine2SchemaError
from engine2.schema import (
    apply_patch,
    default_state_v2,
    normalize_state,
    parse_analysis,
    pick_primary,
    validate_state,
)


def test_default_state_v2():
    s = default_state_v2("tea_seller")
    assert s["v"] == 2
    assert s["stage"]["scenario_slug"] == "tea_seller"
    for key in ("stage", "meters", "facts", "photos", "economy", "negotiation", "flags"):
        assert key in s


def test_normalize_legacy_v1_migrates_preserving_progress():
    out = normalize_state({
        "stage_idx": 1,
        "stage_turns": 3,
        "photos_sent": 2,
        "red_packets": 1,
        "facts": {"job": "程序员"},
        "doubts_raised": 5,
    }, "free_chat")
    assert out["v"] == 2
    assert out["stage"]["scenario_slug"] == "free_chat"
    assert out["stage"]["idx"] == 1
    assert out["stage"]["turns"] == 3
    assert out["photos"]["sent"] == 2
    assert out["economy"]["red_packets"] == 1
    assert out["facts"] == {"job": "程序员"}


def test_normalize_legacy_missing_keys_use_defaults():
    out = normalize_state({"stage_turns": 9}, "x")
    assert out["stage"]["idx"] == 0
    assert out["stage"]["turns"] == 9
    assert out["photos"]["sent"] == 0


def test_normalize_unrecognized_state_resets_to_default():
    assert normalize_state({"v": 99, "anything": 1}, "x")["stage"]["idx"] == 0
    assert normalize_state(None, "x")["stage"]["idx"] == 0


def test_normalize_v2_cleans_and_clamps():
    raw = default_state_v2("x")
    raw["meters"]["trust"] = 500
    raw["stage"]["idx"] = -3
    raw["facts"] = {f"k{i}": "v" for i in range(30)}
    out = normalize_state(raw)
    assert out["meters"]["trust"] == 100
    assert out["stage"]["idx"] == 0
    assert len(out["facts"]) <= 20


def test_validate_state_rejects_bad_version():
    with pytest.raises(Engine2SchemaError):
        validate_state({"v": 1})
    bad = default_state_v2()
    del bad["meters"]
    with pytest.raises(Engine2SchemaError):
        validate_state(bad)


def test_apply_patch_merge_and_replace():
    state = default_state_v2("s")
    state["facts"] = {"job": "程序员"}
    state["meters"]["trust"] = 30
    out = apply_patch(state, {"facts": {"job": "程序员", "pet": "猫"}, "meters": {"trust": 99},
                             "photos": {"sent": 2, "asked": 1, "refused": 0}})
    assert out["facts"] == {"job": "程序员", "pet": "猫"}
    assert out["meters"]["trust"] == 99
    assert out["photos"]["sent"] == 2
    assert out["v"] == 2


def test_parse_analysis_validation():
    ok = parse_analysis({
        "v": 1, "primary": "casual", "intents": ["request_photo", "doubt_ai"],
        "suspicion_level": 2, "requests": {"photo": True}, "observed": {},
        "memory": [], "confidence": "low",
    })
    assert ok is not None
    assert ok["primary"] == "doubt_ai"
    forced = parse_analysis({
        "v": 1, "primary": "casual", "intents": ["casual", "objection"],
        "suspicion_level": 0, "requests": {}, "observed": {}, "memory": [],
        "confidence": "low",
    })
    assert forced["primary"] == "objection"
    assert parse_analysis({"intents": []}) is None
    assert parse_analysis("not-json") is None


def test_pick_primary_priority():
    assert pick_primary(["casual", "end_chat", "doubt_ai"]) == "doubt_ai"
    assert pick_primary(["casual"]) == "casual"
