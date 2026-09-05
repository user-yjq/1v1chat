"""engine2 对外服务（v2）。

与 v1 服务的关键差异：本服务**不写库不提交**，返回 (ai_plans, trace, state)，
由路由层在单个事务内统一保存 user 消息 / AI 消息 / 会话状态（架构 §10/§11）。
"""
from types import SimpleNamespace

from config import settings
from engine2.errors import Engine2Error
from engine2.pipeline import run_turn
from engine2.schema import TurnContext, normalize_state, validate_state
from llm.provider import build_llm as _default_build_llm
from models.database import Conversation, Message
from sqlalchemy.orm import Session


def _history_text(db: Session, conversation_id: int, user_message: str, limit: int = 10) -> str:
    msgs = (db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.sent_at.asc())
            .all())
    if msgs and msgs[-1].sender_type == "user" and msgs[-1].content == user_message:
        msgs = msgs[:-1]
    recent = msgs[-limit:]
    return "\n".join(
        f"{'对方：' if m.sender_type == 'user' else '你：'}{m.content}" for m in recent
    )


def _config() -> SimpleNamespace:
    return SimpleNamespace(
        turn_timeout_s=settings.TURN_TIMEOUT_S,
        guard_enabled=settings.GUARD_ENABLED,
        guard_sample_rate=settings.GUARD_SAMPLE_RATE,
        history_limit=settings.HISTORY_LIMIT,
        state_facts_max=settings.STATE_FACTS_MAX,
        actor_max_tokens=settings.ACTOR_MAX_TOKENS,
        actor_temperature=settings.ACTOR_TEMPERATURE,
        msg_max_len=settings.MSG_MAX_LEN,
    )


def _to_plans(actions: list[dict]) -> list[dict]:
    plans = []
    for action in actions:
        if action.get("kind") == "send_photo":
            plans.append({
                "sender_type": "ai",
                "content": action.get("content", "给你看下～"),
                "content_type": "image",
                "media_url": action.get("media_url", ""),
            })
        else:
            plans.append({
                "sender_type": "ai",
                "content": action.get("content", ""),
                "content_type": "text",
                "media_url": "",
            })
    return plans


async def process_message2(
    conversation_id: int,
    user_message: str,
    user_id: int,
    db: Session,
) -> tuple[list[dict], dict, dict]:
    """处理一轮消息。返回 (ai_plans, trace, new_state)。"""
    if len(user_message) > settings.MSG_MAX_LEN:
        raise Engine2Error(f"消息过长（上限 {settings.MSG_MAX_LEN} 字）")
    conv = (db.query(Conversation)
            .filter(Conversation.id == conversation_id,
                    Conversation.user_id == user_id)
            .first())
    if not conv:
        raise Engine2Error("对话不存在")
    persona = conv.persona
    scenario = persona.scenario if persona else conv.scenario
    slug = scenario.slug if scenario else None
    state = normalize_state(conv.state, slug)
    validate_state(state)
    ctx = TurnContext(
        conversation_id=conv.id,
        user_id=user_id,
        persona=persona,
        scenario=scenario,
        user_message=user_message,
        state=state,
        history_text=_history_text(db, conv.id, user_message,
                                   limit=int(settings.HISTORY_LIMIT)),
        db=db,
        llm=_default_build_llm(),
        config=_config(),
    )
    new_state, actions, trace = await run_turn(ctx)
    return _to_plans(actions), trace, new_state
