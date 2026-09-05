"""T-05/T-06：心理计分、阶段推进、照片谈判"""
from types import SimpleNamespace

from engine2.policies import (
    decide_stage_advance,
    negotiate_photo,
    update_meters,
)
from engine2.schema import default_state_v2


def _persona(mode="instant", max_photos=3, assets=("a.jpg", "b.jpg"), extra=None):
    policy = {"mode": mode, "max_photos": max_photos, "photo_assets_hint": ""}
    policy.update(extra or {})
    return SimpleNamespace(photo_policy=policy, photo_assets=list(assets))


def _scenario(stages):
    return SimpleNamespace(slug="s", stages=stages)


def _state(**kw):
    s = default_state_v2("s")
    s.update(kw)
    return s


def test_meters_suspicion_and_clamp():
    state = _state(meters={"trust": 10, "interest": 20, "suspicion": 99})
    out = update_meters(state, {"intents": ["probe", "red_packet"],
                                "observed": {"sent_redpacket": True}, "tone": "neutral"})
    assert out["suspicion"] == 100
    assert out["trust"] == 17
    assert out["interest"] == 28


def test_meters_casual_decays_suspicion():
    state = _state(meters={"trust": 10, "interest": 20, "suspicion": 30})
    out = update_meters(state, {"intents": ["casual"], "memory": [], "tone": "neutral"})
    assert out["suspicion"] == 29
    assert out["trust"] == 12


def test_stage_advance_by_turns():
    sc = _scenario([
        {"key": "a", "min_turns": 2, "objective": "x"},
        {"key": "b", "min_turns": 1, "objective": "y"},
    ])
    state = _state(stage={"scenario_slug": "s", "idx": 0, "turns": 1})
    idx, ok = decide_stage_advance(sc, state, {"intents": ["casual"]})
    assert (idx, ok) == (0, False)
    state["stage"]["turns"] = 2
    idx, ok = decide_stage_advance(sc, state, {"intents": ["casual"]})
    assert (idx, ok) == (1, True)


def test_stage_advance_requires_event():
    sc = _scenario([
        {"key": "reveal", "min_turns": 99, "advance_on": ["buy_intent"]},
        {"key": "deal", "min_turns": 0},
    ])
    state = _state(stage={"scenario_slug": "s", "idx": 0, "turns": 50})
    idx, ok = decide_stage_advance(sc, state, {"intents": ["casual"]})
    assert ok is False
    idx, ok = decide_stage_advance(sc, state, {"intents": ["buy_intent"]})
    assert (idx, ok) == (1, True)


def test_photo_instant_sends_until_cap():
    p = _persona(mode="instant", max_photos=2)
    state = _state(photos={"sent": 0, "asked": 1, "refused": 0})
    d1 = negotiate_photo(p, state, "greet", {"intents": ["request_photo"]})
    assert d1["action"] == "send"
    assert d1["media_url"] == "a.jpg"
    state["photos"]["sent"] = 1
    d2 = negotiate_photo(p, state, "greet", {"intents": ["request_photo"]})
    assert d2["media_url"] == "b.jpg"
    state["photos"]["sent"] = 2
    d3 = negotiate_photo(p, state, "greet", {"intents": ["request_photo"]})
    assert d3["action"] == "refuse"


def test_photo_friendly_needs_trust_or_stage_or_redpacket():
    p = _persona(mode="friendly", max_photos=2,
                 extra={"need_stage_keys": ["reveal"], "trust_gate": 60})
    state = _state(meters={"trust": 20, "interest": 20, "suspicion": 0},
                   photos={"sent": 0, "asked": 1, "refused": 0})
    assert negotiate_photo(p, state, "greet", {"intents": ["request_photo"]})["action"] == "refuse"
    state["meters"]["trust"] = 70
    assert negotiate_photo(p, state, "greet", {"intents": ["request_photo"]})["action"] == "send"
    state["meters"]["trust"] = 20
    assert negotiate_photo(p, state, "reveal", {"intents": ["request_photo"]})["action"] == "send"
    state["meters"]["trust"] = 20
    assert negotiate_photo(
        p, state, "greet",
        {"intents": ["request_photo"], "observed": {"sent_redpacket": True}},
    )["action"] == "send"


def test_photo_red_packet_mode_unlocks_once():
    p = _persona(mode="red_packet", max_photos=3)
    state = _state(photos={"sent": 0, "asked": 1, "refused": 0})
    req = {"intents": ["request_photo"], "observed": {"sent_redpacket": True}}
    assert negotiate_photo(p, state, "greet", req)["action"] == "send"
    state["photos"]["sent"] = 1
    assert negotiate_photo(p, state, "greet", req)["action"] == "refuse"


def test_photo_dangle_never_sends():
    p = _persona(mode="dangle", max_photos=0,
                 extra={"refuse_reason": "不给你看"})
    state = _state(photos={"sent": 0, "asked": 2, "refused": 2})
    req = {"intents": ["request_photo"], "observed": {"sent_redpacket": True}}
    assert negotiate_photo(p, state, "greet", req)["action"] == "refuse"


def test_photo_none_without_assets_or_request():
    p = _persona(mode="instant", assets=())
    state = _state()
    assert negotiate_photo(p, state, "greet", {"intents": ["request_photo"]})["action"] == "none"
    p2 = _persona(mode="instant", assets=("a.jpg",))
    assert negotiate_photo(p2, state, "greet", {"intents": ["casual"]})["action"] == "none"
