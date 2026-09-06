"""守卫节点：破功/黑名单拦截 → 重写一次 → 兜底；可选抽样 AI 味自检。

- 黑名单为确定性快线，任何命中都不落库。
- 抽样自检（GUARD_SAMPLE_RATE）用 LLM 对文字回复打 AI 味分，高分触发重写。
- 照片直发不经过文字检查。
"""
import random
import re

from core import metrics as app_metrics
from engine2.defaults import pick_fallback
from engine2.nodes.actor import generate_reply

_BANNED = [
    "我是ai", "我是一个ai", "我是人工智能", "我是机器人", "我属于ai",
    "我被训练", "我被编程", "我是程序", "语言模型", "大模型", "我由模型",
    "作为ai", "我不能透露", "系统提示", "我的设定", "我扮演着", "我在扮演",
    "ai助手", "智能体",
]
_BANNED_WORDS = ["ai", "gpt", "机器人", "人工智能", "模型", "程序", "助手"]
_MARKDOWN = re.compile(r"(^#{1,6}\s)|(```)|(\*\*)|(^\s*[-*+]\s)", re.MULTILINE)
_FLAVOR_SYSTEM = (
    "你是微信聊天质量评审。对下面这条回复打分，只输出 JSON："
    '{"ai_flavor": 0.0, "reason": "..."}。ai_flavor 0-1，越高越像 AI/机器人语气。'
)


def _blocked_words(text: str) -> list[str]:
    lowered = (text or "").lower()
    hit = [w for w in _BANNED if w.lower() in lowered]
    for w in _BANNED_WORDS:
        if w.lower() in lowered and w not in hit:
            hit.append(w)
    if _MARKDOWN.search(text or ""):
        hit.append("markdown")
    return hit


def _rewrite_instruction(words: list[str]) -> str:
    return (
        "上一版回复不过关，绝对不能出现这些字眼：" + "、".join(words)
        + "；不要使用任何格式符号或列表。用更像真人随手打字的方式，换个说法重说一遍。"
    )


async def _flavor_score(ctx, content: str):
    """抽样自检打分；未启用/不支持/未命中抽样时返回 None。"""
    rate = float(getattr(ctx.config, "guard_sample_rate", 0.0) or 0.0)
    llm = ctx.llm
    if rate <= 0 or not hasattr(llm, "extract_json"):
        return None
    if random.random() >= rate:
        return None
    ctx.scratch["llm_calls"] = ctx.scratch.get("llm_calls", 0) + 1
    try:
        raw = await llm.extract_json(_FLAVOR_SYSTEM, (content or "")[:400])
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    try:
        return float(raw.get("ai_flavor"))
    except (TypeError, ValueError):
        return None


async def guard(ctx) -> dict:
    actions = ctx.scratch.get("actions_out") or []
    info = {
        "blocked": False,
        "rewrote": False,
        "used_fallback": False,
        "sampled": False,
        "words": [],
    }

    async def fix(action: dict, words: list[str]) -> None:
        """拦截 → 重写一次 → 仍命中则兜底。"""
        info["blocked"] = True
        info["words"] = words
        enabled = getattr(ctx.config, "guard_enabled", True)
        if enabled:
            ctx.scratch["llm_calls"] = ctx.scratch.get("llm_calls", 0) + 1
            rewritten = await generate_reply(ctx, _rewrite_instruction(words))
            info["rewrote"] = True
            if not _blocked_words(rewritten):
                action["content"] = rewritten
                return
        action["content"] = pick_fallback(ctx.user_message)
        info["used_fallback"] = True

    for action in actions:
        if action.get("kind") != "reply_text":
            continue
        words = _blocked_words(action.get("content", ""))
        if words:
            await fix(action, words)

    # 抽样 AI 味自检（默认 5%），只作用于文字回复
    if not info["blocked"]:
        target = next((a for a in actions if a.get("kind") == "reply_text"), None)
        if target:
            score = await _flavor_score(ctx, target.get("content", ""))
            if score is not None and score >= 0.7:
                info["sampled"] = True
                await fix(target, ["ai_flavor"])

    ctx.scratch["actions_out"] = actions
    ctx.scratch["guard"] = info
    app_metrics.record_guard(
        blocked=info["blocked"],
        rewrote=info["rewrote"],
        fallback=info["used_fallback"],
        sampled=info["sampled"],
    )
    return {}
