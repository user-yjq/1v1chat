"""engine2 确定性策略：心理计分、剧本阶段推进、照片谈判。

全部为纯函数：输入 state/analysis/persona，输出决策或新状态片段，便于单测与复现。
照片素材 URL 只在此处从 persona.photo_assets 白名单选出（模型永不输出 URL）。
"""
from models.database import Persona, Scenario

_DEFAULT_REFUSE = {
    "friendly": "咱俩还没熟到能发照片的程度，等再聊聊呗",
    "red_packet": "哼，想看照片得先有点表示吧～",
    "dangle": "就不给你看，你哄哄我再说",
}


def stage_of(scenario: Scenario | None, state: dict) -> dict | None:
    if not scenario or not scenario.stages:
        return None
    stages = list(scenario.stages)
    idx = max(0, min(int(state["stage"]["idx"]), len(stages) - 1))
    return {"_idx": idx, **stages[idx]}


def stage_key(scenario: Scenario | None, state: dict) -> str:
    stage = stage_of(scenario, state)
    return stage.get("key", "") if stage else ""


def stage_block_text(scenario: Scenario | None, state: dict) -> str:
    stage = stage_of(scenario, state)
    if not stage:
        return "（自由聊天，没有固定阶段）"
    idx = stage["_idx"]
    total = len(scenario.stages)
    label = stage.get("label", stage.get("key", ""))
    objective = stage.get("objective", "")
    turns = int(state["stage"].get("turns", 0))
    return f"阶段 {idx + 1}/{total}【{label}】（本阶段已聊 {turns} 轮）：{objective}"


def facts_text(state: dict, limit: int = 5) -> str:
    facts = state.get("facts") or {}
    items = list(facts.items())[:limit]
    if not items:
        return "（暂时没有太多对方的信息）"
    return "；".join(f"{k}：{v}" for k, v in items)


def heat_text(state: dict) -> str:
    m = state["meters"]
    trust = m.get("trust", 10)
    suspicion = m.get("suspicion", 0)
    if trust >= 70:
        heat = "对方对你已经比较信任，像老朋友"
    elif trust >= 45:
        heat = "对方对你印象不错，聊得比较熟"
    else:
        heat = "你们刚认识不久，还不算熟"
    if suspicion >= 60:
        heat += "；注意：对方似乎有点起疑，言行要自然，别慌别辩解"
    return heat


def update_meters(state: dict, analysis: dict) -> dict:
    """按架构 §6.1 计分表更新 trust/interest/suspicion（0-100 封顶）。"""
    cur = state["meters"]
    trust = cur.get("trust", 10)
    interest = cur.get("interest", 20)
    suspicion = cur.get("suspicion", 0)
    intents = set(analysis.get("intents") or [])
    memory = analysis.get("memory") or []
    observed = analysis.get("observed") or {}

    def clamp(n: int) -> int:
        return max(0, min(100, n))

    if "casual" in intents or not intents:
        trust += 2
        suspicion = max(0, suspicion - 1)
    if memory:
        trust += 3
        interest += 2
    if "request_photo" in intents:
        trust += 1
    if observed.get("sent_redpacket") or "red_packet" in intents:
        trust += 10
        interest += 8
        suspicion = max(0, suspicion - 3)
    if "buy_intent" in intents:
        interest += 8
    if "objection" in intents:
        trust -= 2
        interest -= 6
    if "doubt_ai" in intents:
        trust -= 3
        suspicion += 15
    if "probe" in intents:
        suspicion += 10
        trust -= 3
    if analysis.get("tone") in ("angry", "sarcastic"):
        trust -= 1
    return {
        "trust": clamp(trust),
        "interest": clamp(interest),
        "suspicion": clamp(suspicion),
    }


def decide_stage_advance(scenario: Scenario | None, state: dict, analysis: dict) -> tuple[int, bool]:
    """满足推进条件则前进 1 幕（最多 1 幕），返回 (新 idx, 是否推进)。"""
    if not scenario or not scenario.stages:
        return int(state["stage"]["idx"]), False
    stages = list(scenario.stages)
    idx = int(state["stage"]["idx"])
    if idx >= len(stages) - 1:
        return idx, False
    turns = int(state["stage"].get("turns", 0))
    cfg = stages[idx]
    min_turns = int(cfg.get("min_turns", 3))
    advance_on = cfg.get("advance_on") or []
    intents = set(analysis.get("intents") or [])
    if advance_on:
        if not any(e in intents for e in advance_on):
            return idx, False
    elif turns < min_turns:
        return idx, False
    return idx + 1, True


def _policy(persona: Persona) -> dict:
    p = persona.photo_policy
    return p if isinstance(p, dict) else {}


def _refuse_reason(persona: Persona, mode: str, policy: dict) -> str:
    return (
        policy.get("refuse_reason")
        or _DEFAULT_REFUSE.get(mode)
        or "现在不太方便发，改天哈"
    )


def negotiate_photo(
    persona: Persona | None,
    state: dict,
    stage_key: str,
    analysis: dict,
) -> dict:
    """照片谈判决策。返回动作：send / refuse / none。

    关键约束（架构 §14）：media_url 只能取 persona.photo_assets 白名单。
    """
    if not persona or not persona.photo_assets:
        return {"action": "none"}
    policy = _policy(persona)
    mode = str(policy.get("mode", "instant"))
    max_photos = max(0, int(policy.get("max_photos", 3)))
    intents = set(analysis.get("intents") or [])
    wants = "request_photo" in intents
    got_red = bool((analysis.get("observed") or {}).get("sent_redpacket"))
    trust = int(state["meters"].get("trust", 10))
    sent = int(state["photos"].get("sent", 0))
    assets = persona.photo_assets
    caption = str(policy.get("caption_template") or "给你看下～")

    if max_photos > 0 and sent >= max_photos:
        return {"action": "refuse", "reason": "就这几张啦，再多真没有了"}
    if not wants and not (got_red and mode == "red_packet"):
        return {"action": "none"}

    if mode == "instant" and wants:
        media = assets[sent % len(assets)]
        return {"action": "send", "media_url": media, "caption": caption}

    if mode == "friendly":
        need_keys = policy.get("need_stage_keys") or []
        trust_gate = int(policy.get("trust_gate", 55))
        allowed = stage_key in need_keys or trust >= trust_gate or got_red
        if wants and allowed and (max_photos == 0 or sent < max_photos):
            media = assets[sent % len(assets)]
            return {"action": "send", "media_url": media, "caption": caption}
        if wants:
            return {"action": "refuse", "reason": _refuse_reason(persona, mode, policy)}
        return {"action": "none"}

    if mode == "red_packet":
        if wants and got_red and sent == 0:
            media = assets[sent % len(assets)]
            return {"action": "send", "media_url": media, "caption": caption}
        if not wants and got_red and sent == 0:
            media = assets[sent % len(assets)]
            return {"action": "send", "media_url": media, "caption": caption}
        if wants:
            return {"action": "refuse", "reason": _refuse_reason(persona, mode, policy)}
        return {"action": "none"}

    # dangle：默认一直吊着；max_photos<=0 时永远不发
    if wants and max_photos > 0 and got_red and sent == 0:
        media = assets[sent % len(assets)]
        return {"action": "send", "media_url": media, "caption": caption}
    if wants:
        return {"action": "refuse", "reason": _refuse_reason(persona, mode, policy)}
    return {"action": "none"}
