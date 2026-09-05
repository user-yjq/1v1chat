"""
Strategy Agent - 应对策略生成
"""
import json
from typing import Dict, Any
from llm.deepseek_provider import make_strategy_llm
from llm.prompts import load_prompt


def _format_history(history: list, max_turns: int = 5) -> str:
    if not history:
        return "(无历史对话)"
    recent = history[-max_turns:]
    return "\n".join(
        f"{'用户' if m.get('role') == 'user' else 'AI'}：{m.get('content', '')}"
        for m in recent
    )


async def decide_strategy(state: Dict[str, Any]) -> Dict[str, Any]:
    llm = make_strategy_llm()

    template = load_prompt("strategy")
    prompt = template.format(
        profile=str(state.get("profile", {})),
        intent=state.get("intent", "unknown"),
        history=_format_history(state.get("history", [])),
    )

    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    content = response.content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        parsed = {
            "primary_strategy": "cooperate",
            "secondary_strategy": "probe_back",
            "reasoning": "",
            "tone_suggestion": "自然友好",
            "avoid_topics": [],
        }

    return {"strategy": parsed}
