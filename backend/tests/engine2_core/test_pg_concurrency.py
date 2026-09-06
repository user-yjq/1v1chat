"""R-A1：PG advisory 会话锁（跨 worker 串行同会话写入）+ sqlite no-op。"""
import os
import threading
import time

import pytest
from routers.chat import _acquire_turn_lock, _lock_key
from sqlalchemy import create_engine, text


def test_lock_key_stable_positive_and_scattered():
    a = _lock_key(7)
    assert isinstance(a, int) and a > 0
    assert _lock_key(7) == a  # 同一会话恒定（跨进程可复现）
    assert _lock_key(7) != _lock_key(8)
    assert _lock_key(999999) < (1 << 63)


def test_sqlite_lock_is_noop(db):
    _acquire_turn_lock(db, 12345)  # 不抛、不锁（sqlite 单写者）


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"),
                    reason="需要 TEST_DATABASE_URL（PG）")
def test_pg_advisory_lock_serializes_same_conversation():
    url = os.environ["TEST_DATABASE_URL"]
    key = _lock_key(42)
    engine = create_engine(url, pool_pre_ping=True)
    started = threading.Event()

    def holder():
        with engine.connect() as conn:
            conn.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
            started.set()
            time.sleep(1.2)  # 持有锁期间，另一连接应被阻塞

    t = threading.Thread(target=holder)
    t.start()
    assert started.wait(5), "holder 未拿到锁"
    begin = time.monotonic()
    with engine.connect() as conn2:
        # 第二个连接尝试同会话锁：必须等 holder 释放
        conn2.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
    elapsed = time.monotonic() - begin
    t.join(timeout=5)
    engine.dispose()
    assert elapsed >= 0.8, f"锁未真正串行（耗时 {elapsed:.2f}s）"
