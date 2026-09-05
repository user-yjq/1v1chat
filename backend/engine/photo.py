"""
照片策略（方案 C，确定性决策，不依赖模型）
mode:
- instant   ：要就给（最多 max_photos 张）
- friendly   ：聊到 need_stage_keys 里的阶段才给，否则嘴甜拒绝
- red_packet ：收到红包/转账才解锁第一张，否则吊着（可暗示）
- dangle     ：一直吊着不给，转移话题/撒娇哄着
"""

from models.database import Persona

_DEFAULT_REFUSE = {
    "friendly": "咱俩还没熟到能发照片的程度，等再聊聊呗",
    "red_packet": "哼，想看照片得先有点表示吧～",
    "dangle": "就不给你看，你哄哄我再说",
}


def _policy(persona: Persona) -> dict:
    return persona.photo_policy if isinstance(persona.photo_policy, dict) else {}


def _reason(persona: Persona, mode: str) -> str:
    p = _policy(persona)
    return (p.get("refuse_reason") or _DEFAULT_REFUSE.get(mode)
            or "现在不太方便发，改天哈")


def decide_photo(persona: Persona | None, state: dict, events: dict[str, bool],
                 stage_key: str = "") -> dict:
    """
    返回动作：
    - send：本回合直接发照片（附带 media_url/caption）
    - refuse：本回合拒绝，reason 转成给 Actor 的指令
    - none：不涉及照片
    """
    if not persona or not persona.photo_assets:
        return {"action": "none"}

    p = _policy(persona)
    mode = p.get("mode", "instant")
    wants = bool(events.get("request_photo"))
    got_red = bool(events.get("red_packet"))
    max_photos = int(p.get("max_photos", 3))
    sent = state.get("photos_sent", 0)

    if sent >= max_photos:
        return {"action": "refuse", "reason": "就这几张啦，再多真没有了"}
    if not wants and not (got_red and mode == "red_packet"):
        return {"action": "none"}

    assets = persona.photo_assets
    media_url = assets[sent % len(assets)]
    caption = p.get("caption_template") or "给你看下～"

    if mode == "instant" and wants:
        return {"action": "send", "media_url": media_url, "caption": caption}

    if mode == "friendly":
        need_keys = p.get("need_stage_keys", []) or []
        if stage_key in need_keys or got_red:
            return {"action": "send", "media_url": media_url, "caption": caption}
        return {"action": "refuse", "reason": _reason(persona, mode)}

    if mode == "red_packet":
        if got_red and sent == 0:
            return {"action": "send", "media_url": media_url, "caption": caption}
        return {"action": "refuse", "reason": _reason(persona, mode)}

    # dangle
    return {"action": "refuse", "reason": _reason(persona, mode)}
