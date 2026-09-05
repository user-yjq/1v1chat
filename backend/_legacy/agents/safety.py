"""
Safety Agent - AI 感检测 + 一致性
"""
import json
from typing import Dict, Any
from llm.deepseek_provider import make_safety_llm
from llm.prompts import load_prompt


def _format_history(history: list, max_turns: int = 6) -> str:
    if not history:
        return "(无历史对话)"
    recent = history[-max_turns:]
    return "\n".join(
        f"{'用户' if m.get('role') == 'user' else 'AI'}：{m.get('content', '')}"
        for m in recent
    )


async def check_safety(state: Dict[str, Any]) -> Dict[str, Any]:
    llm = make_safety_llm()

    template = load_prompt("safety")
    prompt = template.format(
        persona=str(state.get("ai_persona", {})),
        history=_format_history(state.get("history", [])),
        ai_response=state.get("ai_response", ""),
    )

    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    content = response.content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {"pass": True, "ai_smell_score": 0.0, "consistency_score": 1.0, "issues": [], "suggestion": ""}

    passed = parsed.get("pass", True)
    issues = parsed.get("issues", [])

    return {
        "safety_passed": passed,
        "safety_issues": issues,
    }
