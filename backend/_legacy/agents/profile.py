"""
Profile Agent - 对方画像识别
"""
import json
from typing import Dict, Any
from llm.deepseek_provider import make_profile_llm
from llm.prompts import load_prompt


def _format_history(history: list, max_turns: int = 8) -> str:
    if not history:
        return "(无历史对话)"
    recent = history[-max_turns:]
    return "\n".join(
        f"{'用户' if m.get('role') == 'user' else 'AI'}：{m.get('content', '')}"
        for m in recent
    )


async def analyze_profile(state: Dict[str, Any]) -> Dict[str, Any]:
    llm = make_profile_llm()
    user_msg = state.get("user_message", "")
    history_text = _format_history(state.get("history", []))
    current = state.get("profile", {})

    template = load_prompt("profile")
    prompt = template.format(
        history=history_text, user_message=user_msg, current_profile=str(current)
    )

    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    content = response.content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}

    def _merge(existing, new):
        return list(set(existing + new))

    return {
        "profile": {
            "identity_hints": _merge(current.get("identity_hints", []), parsed.get("new_identity_hints", [])),
            "occupation_hints": _merge(current.get("occupation_hints", []), parsed.get("new_occupation_hints", [])),
            "intent_signals": _merge(current.get("intent_signals", []), parsed.get("new_intent_signals", [])),
            "scam_patterns": _merge(current.get("scam_patterns", []), parsed.get("new_scam_patterns", [])),
            "relationship_stage": parsed.get("relationship_stage", current.get("relationship_stage", "initial")),
            "trust_level": parsed.get("trust_level", current.get("trust_level", 50)),
            "emotional_state": parsed.get("emotional_state", current.get("emotional_state", "neutral")),
            "confidence": parsed.get("confidence", current.get("confidence", 0.0)),
            "summary": parsed.get("summary", current.get("summary", "")),
        }
    }
