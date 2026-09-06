"""聊天限流（NFR-SEC-3 / R-A3）。

- 默认：进程内滑动窗口（单机/开发，零依赖）。
- 可选 Redis：配置 `REDIS_URL` 后切换为 INCR+EXPIRE 固定窗口（跨 worker 一致）；
  Redis 不可用时自动降级到进程内实现，避免误伤用户（fail-open 于计数、不再 500）。
- `reset()` 供测试清理两种后端。
"""
import threading
import time
from collections import defaultdict, deque

from config import settings
from fastapi import HTTPException

try:
    import redis as _redis_lib  # type: ignore
except ImportError:  # pragma: no cover - 未安装 redis-py 时仅用进程内实现
    _redis_lib = None

_WINDOW_S = 60.0
_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()
_client = None


def _allow_local(key: str, limit: int) -> bool:
    """进程内滑动窗口；与旧实现一致。"""
    now = time.monotonic()
    with _lock:
        window = _hits[key]
        while window and now - window[0] > _WINDOW_S:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True


def _redis() -> object | None:
    """懒连接 Redis；未配置/不可用时返回 None（回退进程内）。"""
    global _client
    url = (settings.REDIS_URL or "").strip()
    if not url or _redis_lib is None:
        return None
    if _client is None:
        _client = _redis_lib.Redis.from_url(url, decode_responses=True)
    return _client


def _allow_redis(client, key: str, limit: int) -> bool:
    """Redis 固定窗口（INCR + 61s 过期）。失败降级到进程内窗口。"""
    try:
        count = int(client.incr(f"rl:{key}"))
        if count == 1:
            client.expire(f"rl:{key}", int(_WINDOW_S) + 1)
        return count <= limit
    except Exception:  # noqa: BLE001 —— Redis 抖动不能把聊天打挂
        return _allow_local(key, limit)


def _allow(key: str, limit: int) -> bool:
    client = _redis()
    if client is not None:
        return _allow_redis(client, key, limit)
    return _allow_local(key, limit)


def check_chat_rate(user_id: int) -> None:
    """单用户每轮限流；超限抛 429。"""
    if not _allow(f"chat:{user_id}", max(1, int(settings.CHAT_RATE_PER_MIN))):
        raise HTTPException(status_code=429, detail="消息太频繁了，稍等一下再发")


def reset() -> None:
    """测试用：清空进程内计数与 Redis 键。"""
    with _lock:
        _hits.clear()
    client = _redis()
    if client is None:
        return
    try:
        for key in client.scan_iter("rl:*", count=200):
            client.delete(key)
    except Exception:  # noqa: BLE001
        pass
