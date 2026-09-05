"""
Actor Agent - 角色演绎 (ReAct)
"""
import json
from typing import Dict, Any
from llm.deepseek_provider import make_actor_llm
from llm.prompts import load_prompt


def _format_history(history: list, max_turns: int = 10) -> str:
    if not history:
        return "(无历史对话)"
    recent = history[-max_turns:]
    return "\n".join(
        f"{'用户' if m.get('role') == 'user' else 'AI'}：{m.get('content', '')}"
        for m in recent
    )


async def generate_response(state: Dict[str, Any]) -> Dict[str, Any]:
    llm = make_actor_llm()

    template = load_prompt("actor")
    prompt = template.format(
        current_persona=str(state.get("ai_persona", {})),
        profile=str(state.get("profile", {})),
        strategy=str(state.get("strategy", {})),
        history=_format_history(state.get("history", [])),
        user_message=state.get("user_message", ""),
    )

    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    ai_response = response.content.strip()

    return {
        "ai_response": ai_response,
        "ai_response_type": "text",
        "ai_media_url": "",
        "tool_calls": [],
    }
