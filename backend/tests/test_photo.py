from types import SimpleNamespace

from engine.photo import decide_photo

ASSETS = ["/media/1.png", "/media/2.png", "/media/3.png"]


def persona(policy):
    return SimpleNamespace(photo_assets=ASSETS, photo_policy=policy)


def state(**kw):
    return {"photos_sent": 0, "red_packets": 0, **kw}


def test_instant_sends_on_request():
    p = persona({"mode": "instant", "max_photos": 3})
    d = decide_photo(p, state(), {"request_photo": True}, "free")
    assert d["action"] == "send" and d["media_url"]


def test_instant_capped():
    p = persona({"mode": "instant", "max_photos": 1})
    s = state(photos_sent=1)
    assert decide_photo(p, s, {"request_photo": True}, "free")["action"] == "refuse"


def test_friendly_needs_stage():
    p = persona({"mode": "friendly", "need_stage_keys": ["reveal", "pitch"]})
    assert decide_photo(p, state(), {"request_photo": True}, "greet")["action"] == "refuse"
    assert decide_photo(p, state(), {"request_photo": True}, "reveal")["action"] == "send"


def test_red_packet_unlocks():
    p = persona({"mode": "red_packet", "max_photos": 1})
    # 没红包：要照片也拒绝
    assert decide_photo(p, state(), {"request_photo": True}, "free")["action"] == "refuse"
    # 收了红包：解锁
    s = state(red_packets=0)
    d = decide_photo(p, s, {"red_packet": True}, "free")
    assert d["action"] == "send"


def test_dangle_never_sends():
    p = persona({"mode": "dangle", "max_photos": 0})
    assert decide_photo(p, state(red_packets=5), {"request_photo": True}, "free")["action"] == "refuse"
    assert decide_photo(p, state(), {"request_photo": True}, "free")["action"] == "refuse"
