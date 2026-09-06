"""M4.5（R-D1~R-D4）：request-id/日志白名单、运行指标、readiness 配置探测。"""
import json
import logging

from core import metrics
from core.logging import JsonFormatter, get_request_id, set_request_id
from core.middleware import ObservabilityMiddleware
from db.database import make_engine
from llm.provider import MockLLM
from main import readiness_report


class BrokenEngine:
    def connect(self):
        raise RuntimeError("db down")


def test_metrics_llm_guard_http_render():
    metrics.reset()
    metrics.record_llm_call("chat", 0.01, ok=True)
    metrics.record_llm_call("chat", 0.02, ok=False)
    metrics.record_llm_call("json", 0.005, ok=True)
    metrics.record_guard(blocked=True, rewrote=True, fallback=True, sampled=True)
    metrics.record_http("POST", 200, 0.1)
    out = metrics.render()
    assert 'chat_llm_calls_total{kind="chat"} 2' in out
    assert 'chat_llm_calls_failed_total{kind="chat"} 1' in out
    assert 'chat_llm_latency_seconds_count{kind="json"} 1' in out
    assert 'chat_guard_events_total{kind="blocked"} 1' in out
    assert 'chat_guard_events_total{kind="fallback"} 1' in out
    assert 'chat_http_requests_total{method="POST",status="200"} 1' in out


async def test_mock_llm_records_metric():
    metrics.reset()
    llm = MockLLM()
    text = await llm.generate("s", "u")
    assert text
    assert 'chat_llm_calls_total{kind="chat"} 1' in metrics.render()


def test_json_formatter_only_whitelist_fields():
    formatter = JsonFormatter()
    record = logging.LogRecord("x", logging.INFO, "f.py", 1, "hello", (), None)
    record.request_id = "rid-1"
    record.user_id = 7
    record.content = "敏感正文"
    record.nickname = "secret"
    parsed = json.loads(formatter.format(record))
    assert parsed["message"] == "hello"
    assert parsed["request_id"] == "rid-1"
    assert parsed["user_id"] == 7
    assert "content" not in parsed
    assert "nickname" not in parsed


def test_request_id_context_default_and_set():
    assert get_request_id() == "-"
    token = set_request_id("abc")
    assert get_request_id() == "abc"
    from core.logging import reset_request_id
    reset_request_id(token)
    assert get_request_id() == "-"


async def test_middleware_request_id_state_and_header_and_metric():
    metrics.reset()
    seen = {}
    sent = []

    async def inner(scope, receive, send):
        seen["rid"] = scope["state"].get("request_id")
        await send({"type": "http.response.start", "status": 201, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send_collector(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/x",
        "headers": [(b"x-request-id", b"req-abc")],
        "state": {},
    }
    middleware = ObservabilityMiddleware(inner)
    await middleware(scope, receive, send_collector)

    assert seen["rid"] == "req-abc"
    start = sent[0]
    assert any(k.lower() == b"x-request-id" and v == b"req-abc" for k, v in start["headers"])
    assert 'chat_http_requests_total{method="POST",status="201"} 1' in metrics.render()


def test_readiness_db_down_unavailable():
    report = readiness_report(BrokenEngine())
    assert report["status"] == "unavailable"
    assert report["checks"]["db"] is False
    assert "llm" in report["checks"]


def test_readiness_ok_with_mock(monkeypatch):
    from config import settings as cfg_settings
    monkeypatch.setattr(cfg_settings, "LLM_MODE", "mock")
    engine = make_engine("sqlite://")
    try:
        report = readiness_report(engine)
    finally:
        engine.dispose()
    assert report["status"] == "ok"
    assert report["checks"]["db"] is True
    assert report["checks"]["llm"]["ready"] is True


def test_readiness_degraded_auto_without_real_key(monkeypatch):
    from config import settings as cfg_settings
    monkeypatch.setattr(cfg_settings, "LLM_MODE", "auto")
    monkeypatch.setattr(cfg_settings, "DEEPSEEK_API_KEY", "sk-placeholder")
    engine = make_engine("sqlite://")
    try:
        report = readiness_report(engine)
    finally:
        engine.dispose()
    assert report["status"] == "degraded"
    assert report["checks"]["db"] is True
    assert report["checks"]["llm"]["ready"] is False
