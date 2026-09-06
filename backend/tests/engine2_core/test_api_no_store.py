"""ApiNoStoreMiddleware：/api/* 响应带 Cache-Control: no-store（防陈旧缓存）。"""

from core.middleware import ApiNoStoreMiddleware


async def _run(path: str) -> list[dict]:
    sent = []

    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send_collector(message):
        sent.append(message)

    scope = {"type": "http", "method": "GET", "path": path, "headers": []}
    await ApiNoStoreMiddleware(inner)(scope, receive, send_collector)
    return sent


async def test_api_responses_have_no_store():
    sent = await _run("/api/personas")
    headers = dict(sent[0]["headers"])
    assert headers[b"cache-control"] == b"no-store"


async def test_non_api_responses_untouched():
    sent = await _run("/assets/app.js")
    assert sent[0]["headers"] == []
