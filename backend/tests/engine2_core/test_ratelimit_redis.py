"""R-A3：REDIS_URL 配置后限流走 Redis（跨 worker 一致），默认/异常回退进程内。"""
import os

import pytest
from core import ratelimit


@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="需要 REDIS_URL（Redis）")
def test_redis_window_enforced():
    ratelimit.reset()
    client = ratelimit._redis()
    assert client is not None, "REDIS_URL 已配置但未拿到 client"
    ratelimit.reset()
    key = "test:user:4242"
    limit = 3
    assert [ratelimit._allow_redis(client, key, limit) for _ in range(3)] == [True, True, True]
    assert ratelimit._allow_redis(client, key, limit) is False
    ratelimit.reset()


@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="需要 REDIS_URL（Redis）")
def test_redis_check_chat_rate_uses_redis_backend(monkeypatch):
    ratelimit.reset()
    client = ratelimit._redis()
    assert client is not None
    monkeypatch.setattr("core.ratelimit.settings.CHAT_RATE_PER_MIN", 2)
    user_id = 5150
    ratelimit.reset()
    ratelimit.check_chat_rate(user_id)  # 1
    ratelimit.check_chat_rate(user_id)  # 2
    with pytest.raises(Exception) as exc:
        ratelimit.check_chat_rate(user_id)  # 3 -> 429
    assert exc.value.status_code == 429
    ratelimit.reset()
