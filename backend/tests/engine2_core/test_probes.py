"""T-14（离线部分）：试探集与关键信号回归。"""
from engine2.nodes.analyzer import regex_analyze
from engine2.tactics import route
from tests.engine2_core.probes import CASUAL_SAMPLES, DOUBT_PROBES, SIGNAL_PROBES


def test_doubt_probes_never_casual():
    for text in DOUBT_PROBES:
        out = regex_analyze(text)
        intents = set(out["intents"])
        assert "doubt_ai" in intents or "probe" in intents, text
        assert out["suspicion_level"] >= 1, text
        assert route(out, "greet").key in ("doubt", "probe"), text


def test_signal_probes_detected():
    for text, expected in SIGNAL_PROBES:
        out = regex_analyze(text)
        assert expected in out["intents"], (text, out["intents"])


def test_casual_samples_quiet():
    for text in CASUAL_SAMPLES:
        out = regex_analyze(text)
        assert out["suspicion_level"] == 0, text
        assert route(out, "greet").key == "casual", text
