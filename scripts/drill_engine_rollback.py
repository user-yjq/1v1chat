#!/usr/bin/env python3
"""R-E4 回滚演练：同一人设/剧本/输入分别走 v1 与 v2 引擎。

用法（仓库根目录）：
    PYTHONPATH=backend .venv/bin/python scripts/drill_engine_rollback.py

内存 SQLite + FakeLLM（不发起任何真实调用）。断言两条引擎路径都产出一轮
回复、状态可持久化且不抛错，即 v1 回滚点可用。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import services.chat_engine as v1_svc  # noqa: E402
import services.chat_engine2 as v2_svc  # noqa: E402
from models.database import Base, Conversation, Message, Persona, Scenario, User  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

_STAGES = [
    {"key": "greet", "label": "刚认识", "min_turns": 1, "objective": "热络", "advance_on": []},
    {"key": "reveal", "label": "聊熟了", "min_turns": 99, "objective": "引茶",
     "advance_on": ["buy_intent"]},
]


class _FakeLLM:
    async def generate(self, system, user):
        return "嗯嗯，是呀，我从小在外公茶园长大的～"


def _mk_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)()


async def _run_engine(db, conv, text, engine) -> str:
    db.add(Message(conversation_id=conv.id, sender_type="user", content=text))
    db.commit()
    if engine == "v1":
        plans, _trace = await v1_svc.process_message(conv.id, text, conv.user_id, db)
    else:
        plans, _trace, state = await v2_svc.process_message2(conv.id, text, conv.user_id, db)
        conv.state = state
    first = plans[0] if plans else {"content": ""}
    for plan in plans:
        db.add(Message(conversation_id=conv.id, sender_type="ai",
                       content=plan["content"], content_type=plan["content_type"],
                       media_url=plan.get("media_url", "")))
    db.commit()
    return str(first.get("content", ""))


def main() -> int:
    import importlib

    importlib.reload(v1_svc)
    importlib.reload(v2_svc)
    v1_svc.build_llm = lambda: _FakeLLM()  # type: ignore[assignment]
    v2_svc._default_build_llm = lambda: _FakeLLM()  # type: ignore[assignment]

    engine, db = _mk_db()
    user = User(username="rollback_drill", password_hash="x")
    db.add(user)
    db.flush()
    sc = Scenario(slug="rollback_sc", name="卖茶", goal="自然引出外公家的茶", stages=_STAGES)
    db.add(sc)
    db.flush()
    p = Persona(name="小雨", photo_assets=["/media/tea/photo1.png"],
                photo_policy={"mode": "friendly", "need_stage_keys": ["reveal"],
                              "max_photos": 2, "caption_template": "看～"},
                scenario_id=sc.id)
    db.add(p)
    db.flush()
    c1 = Conversation(user_id=user.id, persona_id=p.id, scenario_id=sc.id, state={})
    c2 = Conversation(user_id=user.id, persona_id=p.id, scenario_id=sc.id, state={})
    db.add_all([c1, c2])
    db.commit()

    text = "外公家的茶听着不错，多少钱一斤呀"
    reply_v1 = asyncio.run(_run_engine(db, c1, text, "v1"))
    reply_v2 = asyncio.run(_run_engine(db, c2, text, "v2"))
    ok = bool(reply_v1) and bool(reply_v2)
    print(f"  v1 回复：{reply_v1[:40]}")
    print(f"  v2 回复：{reply_v2[:40]}")
    print(f"  消息落库：v1={db.query(Message).filter(Message.conversation_id == c1.id).count()} 条，"
          f"v2={db.query(Message).filter(Message.conversation_id == c2.id).count()} 条")
    db.close()
    engine.dispose()
    if not ok:
        return 1
    print("drill_engine_rollback: PASS（默认 v2 可用，ENGINE_VERSION=v1 回滚点仍可出消息）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
