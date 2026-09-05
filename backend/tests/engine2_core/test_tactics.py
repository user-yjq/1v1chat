"""T-07：战术路由优先级与指令拼接"""
from engine2.tactics import TACTICS, build_directive, route


def _analysis(*intents, observed=None):
    return {"intents": list(intents), "observed": observed or {}}


def test_route_priority_doubt_wins():
    a = _analysis("request_photo", "doubt_ai")
    assert route(a, "greet").key == "doubt"


def test_route_redpacket_over_photo():
    a = _analysis("request_photo", "red_packet")
    assert route(a, "greet").key == "red_packet"


def test_route_buy_gated_by_stage():
    a = _analysis("buy_intent")
    assert route(a, "reveal").key == "casual"
    assert route(a, "pitch").key == "pitch"


def test_route_casual_default():
    assert route(_analysis("casual"), "greet").key == "casual"


def test_directive_appends_photo_refuse():
    out = build_directive(TACTICS["photo"], {"action": "refuse", "reason": "还没那么熟"})
    assert "还没那么熟" in out
    assert "照片策略" in out
