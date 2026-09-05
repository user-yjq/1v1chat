"""T-09：感知节点规则分析 + 降级"""
from engine2.nodes.analyzer import regex_analyze


def test_request_photo_and_suspicion():
    out = regex_analyze("发张照片看看你长啥样嘛")
    assert "request_photo" in out["intents"]
    assert out["requests"]["photo"] is True


def test_doubt_ai_levels():
    hard = regex_analyze("别装了，你确定是机器人吧")
    assert "doubt_ai" in hard["intents"]
    assert hard["suspicion_level"] >= 2
    soft = regex_analyze("你是不是AI呀")
    assert "doubt_ai" in soft["intents"]
    assert soft["suspicion_level"] >= 1


def test_probe_not_doubt():
    out = regex_analyze("你要是AI就眨眨眼，怎么证明你是真人")
    assert "probe" in out["intents"]
    assert "doubt_ai" not in out["intents"]


def test_redpacket_sent_observed():
    out = regex_analyze("给你发了个红包，收一下")
    assert "red_packet" in out["intents"]
    assert out["observed"]["sent_redpacket"] is True


def test_buy_intent_and_primary():
    out = regex_analyze("你老家茶叶怎么卖，多少钱一斤")
    assert "buy_intent" in out["intents"]
    assert out["primary"] == "buy_intent"


def test_casual_default():
    out = regex_analyze("哈哈哈今天天气不错")
    assert out["primary"] == "casual"
