"""
Reflector Agent - 事后复盘
"""
import json
from typing import Dict, Any
from llm.deepseek_provider import make_reflector_llm
from llm.prompts import load_prompt


def _format_history(history: list, max_turns: int = 6) -> str:
    if not history:
        return "(无历史对话)"
    recent = history[-max_turns:]
    return "\n".join(
        f"{'用户' if m.get('role') == 'user' else 'AI'}：{m.get('content', '')}"
        for m in recent
    )


async def reflect(state: Dict[str, Any]) -> Dict[str, Any]:
    llm = make_reflector_llm()

    messages_text = _format_history(state.get("history", []) + [
        {"role": "user", "content": state.get("user_message", "")},
        {"role": "ai", "content": state.get("ai_response", "")},
    ])

    template = load_prompt("reflector")
    prompt = template.format(
        messages=messages_text,
        profile=str(state.get("profile", {})),
    )

    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    content = response.content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {}

    current = state.get("profile", {})

    def _merge(existing, new):
        return list(set(existing + new))

    trust_delta = parsed.get("trust_level_delta", 0)
    new_trust = max(0, min(100, current.get("trust_level", 50) + trust_delta))

    return {
        "profile": {
            **current,
            "identity_hints": _merge(current.get("identity_hints", []), parsed.get("new_identity_hints", [])),
            "intent_signals": _merge(current.get("intent_signals", []), parsed.get("new_intent_signals", [])),
            "scam_patterns": _merge(current.get("scam_patterns", []), parsed.get("new_scam_patterns", [])),
            "trust_level": new_trust,
            "emotional_state": parsed.get("emotional_state", current.get("emotional_state", "neutral")),
            "relationship_stage": parsed.get("relationship_stage", current.get("relationship_stage", "initial")),
            "confidence": max(0.0, min(1.0, current.get("confidence", 0.0) + parsed.get("confidence_delta", 0))),
            "summary": parsed.get("summary", current.get("summary", "")),
        },
        "done": True,
    }
