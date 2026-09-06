"""ASGI 观测中间件（M4.5 R-D1/R-D2/R-D3）：
注入/透传 X-Request-Id、JSON 访问日志、HTTP 指标。日志不含消息正文。
"""
import time
import uuid

from core import metrics
from core.logging import configure_logging, reset_request_id, set_request_id
from starlette.datastructures import Headers

logger = configure_logging()


class ObservabilityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = set_request_id(request_id)
        scope.setdefault("state", {})["request_id"] = request_id

        method = scope.get("method", "")
        path = scope.get("path", "")
        status = {"code": 0}
        started = time.perf_counter()

        async def _send(message):
            if message["type"] == "http.response.start":
                status["code"] = message.get("status", 0)
                header_list = list(message.get("headers") or [])
                if not any(k.lower() == b"x-request-id" for k, _ in header_list):
                    header_list.append((b"x-request-id", request_id.encode()))
                message = {**message, "headers": header_list}
            await send(message)

        try:
            await self.app(scope, receive, _send)
        except Exception:
            logger.exception("http_error", extra={
                "request_id": request_id, "method": method, "path": path,
                "status": status["code"] or 500,
            })
            raise
        finally:
            code = status["code"] or 500
            seconds = time.perf_counter() - started
            metrics.record_http(method, code, seconds)
            logger.info("http_request", extra={
                "request_id": request_id, "method": method, "path": path,
                "status": code, "duration_ms": round(seconds * 1000, 1),
            })
            reset_request_id(token)


class ApiNoStoreMiddleware:
    """API 响应禁止缓存：/api/* 一律带 Cache-Control: no-store。

    防浏览器/中间代理把旧响应（如人设列表）当新鲜缓存返回，
    导致部署/seed 后前端仍看到空数据。静态资源不走本中间件。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or not scope.get("path", "").startswith("/api/"):
            await self.app(scope, receive, send)
            return

        async def _send(message):
            if message["type"] == "http.response.start":
                header_list = list(message.get("headers") or [])
                if not any(k.lower() == b"cache-control" for k, _ in header_list):
                    header_list.append((b"cache-control", b"no-store"))
                message = {**message, "headers": header_list}
            await send(message)

        await self.app(scope, receive, _send)
