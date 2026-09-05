"""守卫节点：破功/黑名单拦截 → 重写一次 → 兜底。不阻断照片直发。"""
import re

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


async def guard(ctx) -> dict:
    actions = ctx.scratch.get("actions_out") or []
    info = {"blocked": False, "rewrote": False, "used_fallback": False, "words": []}
    for action in actions:
        if action.get("kind") != "reply_text":
            continue
        words = _blocked_words(action.get("content", ""))
        if not words:
            continue
        info["blocked"] = True
        info["words"] = words
        enabled = getattr(ctx.config, "guard_enabled", True)
        if enabled:
            ctx.scratch["llm_calls"] = ctx.scratch.get("llm_calls", 0) + 1
            rewritten = await generate_reply(ctx, _rewrite_instruction(words))
            info["rewrote"] = True
            if not _blocked_words(rewritten):
                action["content"] = rewritten
                continue
        action["content"] = pick_fallback(ctx.user_message)
        info["used_fallback"] = True
    ctx.scratch["actions_out"] = actions
    ctx.scratch["guard"] = info
    return {}
