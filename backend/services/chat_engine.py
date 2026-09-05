"""
聊天引擎（方案 C）
流程：事件识别 → 状态推进/照片策略（确定性）→ 单次 Actor 生成 → 状态回写
每轮最多 1 次 LLM 调用（发照片场景 0 次，用预设话术）
"""

from engine.events import detect_events, primary_event
from engine.photo import decide_photo
from engine.prompting import directive_for, system_prompt, user_context
from engine.state import (
    advance_stage,
    current_stage,
    facts_text,
    load_state,
    save_state,
    stage_block_text,
)
from llm.provider import build_llm
from models.database import Conversation, Message
from sqlalchemy.orm import Session


class EngineError(Exception):
    pass


def _history_text(db: Session, conversation_id: int, user_message: str, limit: int = 10) -> str:
    msgs = (db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.sent_at.asc())
            .all())
    if msgs and msgs[-1].sender_type == "user" and msgs[-1].content == user_message:
        msgs = msgs[:-1]  # 去掉刚保存的当前消息，避免重复
    recent = msgs[-limit:]
    return "\n".join(
        f"{'对方：' if m.sender_type == 'user' else '你：'}{m.content}" for m in recent
    )


async def process_message(
    conversation_id: int,
    user_message: str,
    user_id: int,
    db: Session,
) -> tuple[list[dict], dict]:
    """
    处理一轮用户消息：
    - 内部决策（事件/阶段/照片）全部确定性完成
    - AI 消息由本函数“规划”返回（不落库），由路由层负责持久化
    返回 (ai_messages, trace)
    """
    conv = (db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first())
    if not conv:
        raise EngineError("会话不存在")

    persona = conv.persona
    scenario = persona.scenario if persona else conv.scenario

    state = load_state(conv)
    state["stage_turns"] = state.get("stage_turns", 0) + 1

    events = detect_events(user_message)
    if events.get("red_packet"):
        state["red_packets"] = state.get("red_packets", 0) + 1
    if events.get("doubt_ai"):
        state["doubts_raised"] = state.get("doubts_raised", 0) + 1

    stage = current_stage(scenario, state)
    stage_key = stage.get("key", "") if stage else ""
    stage_block = stage_block_text(scenario, state)
    facts = facts_text(state)

    decision = decide_photo(persona, state, events, stage_key) if persona else {"action": "none"}
    trace = {
        "events": events,
        "primary_event": primary_event(events),
        "stage_key": stage_key,
        "stage_idx": state.get("stage_idx", 0),
    }

    ai_messages: list[dict] = []

    if decision.get("action") == "send":
        state["photos_sent"] = state.get("photos_sent", 0) + 1
        ai_messages.append({
            "sender_type": "ai",
            "content": decision.get("caption", "给你看下～"),
            "content_type": "image",
            "media_url": decision.get("media_url", ""),
        })
        trace["photo_action"] = "send"
    else:
        if decision.get("action") == "refuse":
            trace["photo_action"] = "refuse"
        directive = directive_for(events, decision, stage_key)
        llm = build_llm()
        system = system_prompt(persona, scenario)
        history = _history_text(db, conversation_id, user_message)
        user = user_context(stage_block, facts, directive, history, user_message)
        text = (await llm.generate(system, user)).strip() or "嗯嗯，我在呢～"
        ai_messages.append({
            "sender_type": "ai",
            "content": text,
            "content_type": "text",
            "media_url": "",
        })

    advanced = advance_stage(scenario, state, events)
    if advanced:
        trace["stage_advanced_to"] = state.get("stage_idx", 0)

    trace.update({
        "photos_sent": state.get("photos_sent", 0),
        "red_packets": state.get("red_packets", 0),
        "doubts_raised": state.get("doubts_raised", 0),
    })
    save_state(conv, state)

    return ai_messages, trace
