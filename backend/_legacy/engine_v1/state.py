"""
会话运行状态（方案 C）
- state 存于 Conversation.state(JSON)：阶段下标/阶段轮次/事实/照片计数/红包计数
- 阶段推进规则：当前阶段 min_turns 内不跳，满足后一次最多推进 1 个阶段
"""

from models.database import Conversation, Scenario


def default_state() -> dict:
    return {
        "stage_idx": 0,
        "stage_turns": 0,
        "facts": {},
        "photos_sent": 0,
        "red_packets": 0,
        "doubts_raised": 0,
    }


def load_state(conv: Conversation) -> dict:
    base = default_state()
    if conv.state:
        base.update({k: v for k, v in conv.state.items() if v is not None})
    return base


def save_state(conv: Conversation, state: dict) -> None:
    conv.state = state


def stages_of(scenario: Scenario | None) -> list[dict]:
    if not scenario or not scenario.stages:
        return []
    return list(scenario.stages)


def current_stage(scenario: Scenario | None, state: dict) -> dict | None:
    stages = stages_of(scenario)
    if not stages:
        return None
    idx = max(0, min(state.get("stage_idx", 0), len(stages) - 1))
    stage = dict(stages[idx])
    stage["_idx"] = idx
    return stage


def advance_stage(scenario: Scenario | None, state: dict, events: dict[str, bool]) -> bool:
    """满足推进条件则前进 1 个阶段，并重置阶段轮次"""
    stages = stages_of(scenario)
    if not stages:
        return False
    idx = state.get("stage_idx", 0)
    if idx >= len(stages) - 1:
        return False
    stage = stages[idx]
    min_turns = int(stage.get("min_turns", 3))
    advance_on = stage.get("advance_on", []) or []
    if advance_on:
        # 配置了 advance_on 的阶段：只有命中事件才推进
        if not any(events.get(e) for e in advance_on):
            return False
    elif state.get("stage_turns", 0) < min_turns:
        return False
    state["stage_idx"] = idx + 1
    state["stage_turns"] = 0
    return True


def stage_block_text(scenario: Scenario | None, state: dict) -> str:
    stage = current_stage(scenario, state)
    if not stage:
        return "（自由聊天，没有固定阶段）"
    idx = stage["_idx"]
    total = len(stages_of(scenario))
    label = stage.get("label", stage.get("key", ""))
    objective = stage.get("objective", "")
    turns = state.get("stage_turns", 0)
    return f"阶段 {idx + 1}/{total}【{label}】（本阶段已聊 {turns} 轮）：{objective}"


def facts_text(state: dict) -> str:
    parts = [f"关系进展：已聊到第 {state.get('stage_turns', 0)} 轮",
             f"发过照片 {state.get('photos_sent', 0)} 张",
             f"收到红包/转账 {state.get('red_packets', 0)} 次"]
    facts = state.get("facts") or {}
    if facts:
        parts.append("；".join(f"{k}：{v}" for k, v in facts.items()))
    return "；".join(parts)
