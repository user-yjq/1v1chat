"""engine2 兜底话术与常量（不触发 Guard 黑名单）"""

FALLBACK_LINES = (
    "嗯嗯，我在听呢，你继续说～",
    "哈哈 我懂你的意思，慢慢聊嘛",
    "我刚在忙别的事，你说，我听着",
)


def pick_fallback(text: str) -> str:
    return FALLBACK_LINES[len(text) % len(FALLBACK_LINES)]
