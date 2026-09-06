"""结构化日志（M4.5 R-D3）：JSON 输出 + request_id 上下文 + 白名单字段脱敏。

设计约束：日志永不含用户消息正文等敏感内容；调用方只能通过 extra 白名单字段
携带非敏感上下文（user_id/conversation_id 等）。
"""
import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

_request_id: ContextVar[str] = ContextVar("request_id", default="-")

# 允许进入日志的非敏感 extra 白名单
_EXTRA_FIELDS = (
    "request_id", "method", "path", "status", "duration_ms",
    "user_id", "conversation_id", "engine", "version", "llm_kind",
)


def get_request_id() -> str:
    return _request_id.get()


def set_request_id(value: str):
    return _request_id.set(value)


def reset_request_id(token) -> None:
    _request_id.reset(token)


class JsonFormatter(logging.Formatter):
    """日志行 → 单行 JSON；只挑白名单字段，未知 extra 一律丢弃。"""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
        }
        for key in _EXTRA_FIELDS:
            if key == "request_id":
                continue
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """给应用专用 logger（1v1chat）挂 JSON handler；关闭 uvicorn 纯文本 access。"""
    logger = logging.getLogger("1v1chat")
    if not getattr(logger, "_json_configured", False):
        logger.setLevel(level)
        logger.propagate = False
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger._json_configured = True  # type: ignore[attr-defined]
    logging.getLogger("uvicorn.access").disabled = True
    return logger
