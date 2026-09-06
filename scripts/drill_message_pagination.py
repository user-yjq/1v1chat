#!/usr/bin/env python3
"""R-B5 演练：万级消息会话游标分页走查（无重复/无缺口 + 耗时读数）。

用法（仓库根目录）：
    PYTHONPATH=backend .venv/bin/python scripts/drill_message_pagination.py

内存 SQLite + 模型元数据建表（含 ix_messages_conversation_sent_at），
插入 12000 条消息后分页走查，全部断言通过即 PASS。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from models.database import Base, Conversation, Message, User  # noqa: E402
from routers.conversation import page_messages  # noqa: E402
from sqlalchemy import create_engine, inspect  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

TOTAL = 12000
PAGE = 500


def main() -> int:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(username="drill", password_hash="x")
    db.add(user)
    db.flush()
    conv = Conversation(user_id=user.id, title="万级会话", state={})
    db.add(conv)
    db.commit()

    started = time.perf_counter()
    db.bulk_save_objects(
        [Message(conversation_id=conv.id, sender_type="user" if i % 2 else "ai",
                 content=f"m{i}", content_type="text") for i in range(1, TOTAL + 1)]
    )
    db.commit()
    insert_s = time.perf_counter() - started

    idxs = {ix["name"] for ix in inspect(engine).get_indexes("messages")}
    print(f"  [{'PASS' if 'ix_messages_conversation_sent_at' in idxs else 'FAIL'}] 联合索引存在")

    seen: list[int] = []
    pages_list: list[list[int]] = []
    cursor: int | None = None
    first_page_s = 0.0
    pages = 0
    walk_started = time.perf_counter()
    while True:
        page_started = time.perf_counter()
        rows = page_messages(db, conv.id, limit=PAGE, before_id=cursor)
        elapsed = time.perf_counter() - page_started
        if first_page_s == 0.0:
            first_page_s = elapsed
        if not rows:
            break
        pages += 1
        pages_list.append([m.id for m in rows])
        seen.extend(m.id for m in rows)
        cursor = rows[0].id
        if len(rows) < PAGE:
            break
    walk_s = time.perf_counter() - walk_started

    total_ok = (len(seen) == TOTAL and len(set(seen)) == TOTAL
                and sorted(seen) == list(range(1, TOTAL + 1))
                and all(p == sorted(p) and len(p) == len(set(p)) for p in pages_list))
    print(f"  [{'PASS' if total_ok else 'FAIL'}] {TOTAL} 条消息 {pages} 页走查：无重复/无缺口/升序")
    print(f"  插入 {TOTAL} 条耗时 {insert_s * 1000:.0f} ms；首页 {PAGE} 条查询 {first_page_s * 1000:.1f} ms；"
          f"整页走查 {walk_s * 1000:.0f} ms")
    db.close()
    engine.dispose()
    if not total_ok:
        return 1
    print("drill_message_pagination: PASS（万级消息游标分页走查）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
