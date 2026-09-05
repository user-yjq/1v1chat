"""
Router Agent - 意图分类
"""
import json
from typing import Dict, Any
from llm.deepseek_provider import make_router_llm
from llm.prompts import load_prompt


def _format_history(history: list, max_turns: int = 5) -> str:
    if not history:
        return "(无历史对话)"
    recent = history[-max_turns:]
    return "\n".join(
        f"{'用户' if m.get('role') == 'user' else 'AI'}：{m.get('content', '')}"
        for m in recent
    )


async def route_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    llm = make_router_llm()
    user_msg = state.get("user_message", "")
    history_text = _format_history(state.get("history", []))

    template = load_prompt("router")
    prompt = template.format(message=user_msg, history=history_text)

    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    content = response.content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"intent": "unknown", "confidence": 0.0, "key_signals": []}

    return {
        "intent": parsed.get("intent", "unknown"),
        "intent_confidence": parsed.get("confidence", 0.0),
        "intent_signals": parsed.get("key_signals", []),
    }
