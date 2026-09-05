"""进程内滑动窗口限流（v0.3，单机够用；多实例需换 Redis，见架构 §11）"""
import threading
import time
from collections import defaultdict, deque

from config import settings
from fastapi import HTTPException

_WINDOW_S = 60.0
_hits: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def _allow(key: str, limit: int) -> bool:
    now = time.monotonic()
    with _lock:
        window = _hits[key]
        while window and now - window[0] > _WINDOW_S:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True


def check_chat_rate(user_id: int) -> None:
    """单用户每轮限流；超限抛 429。"""
    if not _allow(f"chat:{user_id}", max(1, int(settings.CHAT_RATE_PER_MIN))):
        raise HTTPException(status_code=429, detail="消息太频繁了，稍等一下再发")


def reset() -> None:
    """测试用：清空计数。"""
    with _lock:
        _hits.clear()
